import { useCallback, useRef, useState } from 'react';
import { StreamingResult } from '../types/transcription';

// AudioWorklet processor code
const processorCode = `
class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        console.log('AudioProcessor initialized');
        this._isFirstProcess = true;
        this._isStopping = false;

        // Listen for messages from the main thread
        this.port.onmessage = (event) => {
            if (event.data.command === 'stop') {
                console.log('AudioProcessor received stop command');
                this._isStopping = true;
            }
        };
    }

    process(inputs, outputs) {
        // Log first process call
        if (this._isFirstProcess) {
            console.log('First process call:', {
                hasInputs: inputs && inputs.length > 0,
                inputChannels: inputs[0]?.length,
                samplesPerChannel: inputs[0]?.[0]?.length
            });
            this._isFirstProcess = false;
        }

        const input = inputs[0]?.[0];

        // If we're stopping, send final message and end processing
        if (this._isStopping) {
            console.log('AudioProcessor stopping, sending last chunk');
            const emptyBuffer = new Float32Array(0);
            this.port.postMessage({
                audioData: emptyBuffer,
                isLastChunk: true,
                length: 0,
                timestamp: currentTime
            }, [emptyBuffer.buffer]);
            return false;
        }

        // If we have input, process it
        if (input && input.length > 0) {
            const audioData = new Float32Array(input);
            this.port.postMessage({
                audioData: audioData,
                isLastChunk: false,
                length: audioData.length,
                timestamp: currentTime
            }, [audioData.buffer]);
        }

        return true;
    }
}

registerProcessor('audio-processor', AudioProcessor);
`;

interface UseAudioStreamingProps {
    onTranscriptionUpdate?: (result: StreamingResult) => void;
}

export const useAudioStreaming = ({ onTranscriptionUpdate }: UseAudioStreamingProps = {}) => {
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isEndOfFile, setIsEndOfFile] = useState(false);
    const websocketRef = useRef<WebSocket | null>(null);
    const mediaStreamRef = useRef<MediaStream | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const sourceNodeRef = useRef<AudioBufferSourceNode | MediaStreamAudioSourceNode | null>(null);
    const workletNodeRef = useRef<AudioWorkletNode | null>(null);
    const isStreamingRef = useRef(false);
    const pendingStopRef = useRef(false);

    const cleanupResources = useCallback(() => {
        if (sourceNodeRef.current) {
            sourceNodeRef.current.disconnect();
            if (sourceNodeRef.current instanceof AudioBufferSourceNode) {
                try { sourceNodeRef.current.stop(); } catch (e) { }
            }
            sourceNodeRef.current = null;
        }

        if (workletNodeRef.current) {
            workletNodeRef.current.disconnect();
            workletNodeRef.current = null;
        }

        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(track => track.stop());
            mediaStreamRef.current = null;
        }

        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }

        if (websocketRef.current?.readyState === WebSocket.OPEN) {
            websocketRef.current.close();
        }
        websocketRef.current = null;

        setIsStreaming(false);
        isStreamingRef.current = false;
        pendingStopRef.current = false;
    }, []);

    const stopStreaming = useCallback(async () => {
        if (!isStreamingRef.current) return;

        console.log('Stopping streaming');
        pendingStopRef.current = true;
        isStreamingRef.current = false;

        try {
            // Send stop command to AudioWorklet
            if (workletNodeRef.current) {
                console.log('Sending stop command to AudioWorklet');
                workletNodeRef.current.port.postMessage({ command: 'stop' });
            }

            // Disconnect the source
            if (sourceNodeRef.current) {
                sourceNodeRef.current.disconnect();
                if (sourceNodeRef.current instanceof AudioBufferSourceNode) {
                    try { sourceNodeRef.current.stop(); } catch (e) { }
                }
            }

            // Wait a short time for the last chunk message to be processed
            await new Promise(resolve => setTimeout(resolve, 100));

            // If we still have an open WebSocket, send the last chunk message and wait for response
            if (websocketRef.current?.readyState === WebSocket.OPEN) {
                console.log('Sending final last chunk message');

                let messageHandler = (event: MessageEvent) => { };  // Initialize with empty function
                let timeoutId = 0;  // Initialize with 0

                // Create a promise that will resolve when we get the final response
                const finalResponsePromise = new Promise<void>((resolve, reject) => {
                    messageHandler = (event: MessageEvent) => {
                        try {
                            const data = JSON.parse(event.data);
                            if (data.is_final) {
                                console.log('Received final confirmation from backend');
                                resolve();
                            }
                        } catch (e) {
                            console.error('Error parsing message:', e);
                        }
                    };

                    timeoutId = window.setTimeout(() => {
                        console.log('Timeout waiting for final response from backend');
                        reject(new Error('Timeout waiting for final response'));
                    }, 5000);

                    websocketRef.current?.addEventListener('message', messageHandler);
                });

                // Send the last chunk message
                websocketRef.current.send(JSON.stringify({ isLastChunk: true }));

                try {
                    await finalResponsePromise;
                    console.log('Successfully received final response');
                } catch (e) {
                    console.warn('Failed to get final response:', e);
                } finally {
                    // Clean up the handler and timeout
                    window.clearTimeout(timeoutId);
                    websocketRef.current?.removeEventListener('message', messageHandler);
                }
            }
        } finally {
            // Clean up resources regardless of whether we got the final response
            cleanupResources();
        }
    }, [cleanupResources]);

    const startStreaming = useCallback(async (audioFile?: File) => {
        try {
            setError(null);
            setIsEndOfFile(false);
            isStreamingRef.current = true;
            pendingStopRef.current = false;

            // Initialize WebSocket
            websocketRef.current = new WebSocket('ws://localhost:8000/stream');
            const ws = websocketRef.current;

            await new Promise<void>((resolve, reject) => {
                if (!ws) return reject(new Error('WebSocket not initialized'));
                ws.onopen = () => resolve();
                ws.onerror = (error) => reject(error);
            });

            // Initialize AudioContext and AudioWorklet
            audioContextRef.current = new AudioContext({ sampleRate: 16000 });
            const blob = new Blob([processorCode], { type: 'application/javascript' });
            const url = URL.createObjectURL(blob);
            await audioContextRef.current.audioWorklet.addModule(url);
            URL.revokeObjectURL(url);

            // Create AudioWorklet node
            workletNodeRef.current = new AudioWorkletNode(audioContextRef.current, 'audio-processor', {
                numberOfInputs: 1,
                numberOfOutputs: 1,
                channelCount: 1,
                processorOptions: {
                    sampleRate: audioContextRef.current.sampleRate
                }
            });

            // Connect the worklet to the destination to ensure we can hear the audio
            workletNodeRef.current.connect(audioContextRef.current.destination);

            // Add message handling
            workletNodeRef.current.port.onmessage = (e) => {
                if (ws.readyState === WebSocket.OPEN && isStreamingRef.current) {
                    try {
                        // Send audio data as binary
                        const audioData = e.data.audioData;

                        if (audioData.length > 0) {
                            // Send the raw buffer as binary data
                            ws.send(audioData.buffer);
                        }

                        // If this is the last chunk, send a control message
                        if (e.data.isLastChunk) {
                            console.log('Sending last chunk message');
                            ws.send(JSON.stringify({ isLastChunk: true }));
                        }
                    } catch (error) {
                        console.error('Error sending audio data:', error);
                    }
                }
            };

            // Add error handler for the AudioWorklet
            workletNodeRef.current.port.onmessageerror = (error) => {
                console.error('AudioWorklet message error:', error);
            };

            if (audioFile) {
                console.log('Processing audio file:', {
                    name: audioFile.name,
                    type: audioFile.type,
                    size: `${(audioFile.size / 1024 / 1024).toFixed(2)} MB`
                });

                const arrayBuffer = await audioFile.arrayBuffer();
                const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);
                sourceNodeRef.current = audioContextRef.current.createBufferSource();
                sourceNodeRef.current.buffer = audioBuffer;

                // Connect source to both worklet (for processing) and destination (for playback)
                sourceNodeRef.current.connect(workletNodeRef.current);
                sourceNodeRef.current.connect(audioContextRef.current.destination);

                // Handle audio file end
                sourceNodeRef.current.onended = () => {
                    console.log('Audio file playback ended');
                    setIsEndOfFile(true);
                    stopStreaming();
                };

                console.log('Starting audio playback', {
                    duration: audioBuffer.duration,
                    sampleRate: audioBuffer.sampleRate,
                    numberOfChannels: audioBuffer.numberOfChannels
                });
                sourceNodeRef.current.start();
            } else {
                console.log('Starting microphone input');

                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: true,
                        sampleRate: 16000,
                    },
                });
                mediaStreamRef.current = stream;
                sourceNodeRef.current = audioContextRef.current.createMediaStreamSource(stream);
                sourceNodeRef.current.connect(workletNodeRef.current);

                // Log the actual track settings we got
                const audioTrack = stream.getAudioTracks()[0];
                if (audioTrack) {
                    const settings = audioTrack.getSettings();
                    console.log('Actual microphone settings:', settings);
                }
            }

            // Handle transcription results
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.error) throw new Error(data.error);
                    onTranscriptionUpdate?.(data);

                    // If we got final result and we were stopping, clean up
                    if (data.is_final && pendingStopRef.current) {
                        console.log('Received final confirmation from backend, cleaning up');
                        cleanupResources();
                    }
                } catch (e) {
                    console.error('Failed to parse transcription data:', e);
                }
            };

            setIsStreaming(true);

            // Add more detailed WebSocket error handling
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                setError('WebSocket error occurred');
                cleanupResources();
            };

            ws.onclose = (event) => {
                console.log('WebSocket closed:', {
                    code: event.code,
                    reason: event.reason,
                    wasClean: event.wasClean
                });
                cleanupResources();
            };

        } catch (err) {
            console.error('Streaming error:', err);
            setError(err instanceof Error ? err.message : 'An error occurred');
            cleanupResources();
        }
    }, [onTranscriptionUpdate, stopStreaming, cleanupResources]);

    return { isStreaming, isEndOfFile, error, startStreaming, stopStreaming };
};