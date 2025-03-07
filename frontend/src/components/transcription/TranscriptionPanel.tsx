import React, { useState, useEffect, useRef } from 'react';
import { useAudioStreaming } from '../../hooks/useAudioStreaming';
import { TranscriptionResult } from '../../types/transcription';

type InputMode = 'file' | 'microphone';

export const TranscriptionPanel: React.FC = () => {
    const [inputMode, setInputMode] = useState<InputMode>('file');
    const [file, setFile] = useState<File | null>(null);
    const [audioDuration, setAudioDuration] = useState<number | null>(null);
    const [result, setResult] = useState<TranscriptionResult | null>(null);
    const [streamingResult, setStreamingResult] = useState<string>('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [micPermission, setMicPermission] = useState<boolean | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    const { isStreaming, isEndOfFile, error: streamingError, startStreaming, stopStreaming } = useAudioStreaming({
        onTranscriptionUpdate: (result) => {
            setStreamingResult(result.text);
        },
    });

    // Check for microphone permission when switching to mic mode
    useEffect(() => {
        if (inputMode === 'microphone' && micPermission === null) {
            const checkMicPermission = async () => {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    // Stop all tracks immediately after getting permission
                    stream.getTracks().forEach(track => track.stop());
                    setMicPermission(true);
                } catch (err) {
                    console.error('Microphone permission error:', err);
                    setMicPermission(false);
                    setError('Microphone access denied. Please allow microphone access in your browser settings.');
                }
            };

            checkMicPermission();
        }
    }, [inputMode, micPermission]);

    const handleInputModeChange = (mode: InputMode) => {
        // If we were streaming, stop
        if (isStreaming) {
            stopStreaming();
        }

        setInputMode(mode);
        setFile(null);
        setError(null);
        setResult(null);
        setStreamingResult('');
        setAudioDuration(null);

        // Reset mic permission check when switching to file mode
        if (mode === 'file') {
            setMicPermission(null);
        }
    };

    const calculateAudioDuration = (file: File) => {
        const url = URL.createObjectURL(file);

        if (!audioRef.current) {
            audioRef.current = new Audio();
        }

        audioRef.current.src = url;

        audioRef.current.onloadedmetadata = () => {
            if (audioRef.current) {
                setAudioDuration(audioRef.current.duration);
                // Revoke the URL to free up memory
                URL.revokeObjectURL(url);
            }
        };

        audioRef.current.onerror = () => {
            setError('Could not determine audio duration');
            URL.revokeObjectURL(url);
        };
    };

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = event.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            setError(null);
            setResult(null);
            setStreamingResult('');
            setAudioDuration(null);

            // Calculate audio duration
            calculateAudioDuration(selectedFile);

            // If we were streaming, stop
            if (isStreaming) {
                stopStreaming();
            }

            // Log file info
            console.log('Selected audio file:', {
                name: selectedFile.name,
                type: selectedFile.type,
                size: `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`
            });
        }
    };

    const handleTranscribeFile = async () => {
        if (!file) {
            setError('Please select a file first');
            return;
        }

        setIsLoading(true);
        setError(null);
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:8000/transcribe/file', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            setResult(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setIsLoading(false);
        }
    };

    const handleStartMicStreaming = () => {
        if (micPermission === false) {
            setError('Microphone access denied. Please allow microphone access in your browser settings.');
            return;
        }

        setError(null);
        startStreaming(); // No file parameter means use microphone
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Transcription</h2>
            <div className="space-y-4">
                {/* Input Mode Selection */}
                <div className="flex space-x-4 mb-4">
                    <button
                        onClick={() => handleInputModeChange('file')}
                        className={`flex-1 px-4 py-2 rounded ${inputMode === 'file'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                    >
                        Audio File
                    </button>
                    <button
                        onClick={() => handleInputModeChange('microphone')}
                        className={`flex-1 px-4 py-2 rounded ${inputMode === 'microphone'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                    >
                        Microphone
                    </button>
                </div>

                {/* Audio Configuration Info */}
                <div className="text-sm text-gray-600 bg-gray-100 p-3 rounded">
                    <p>
                        <strong>Optimal audio settings:</strong> 16kHz sample rate, mono channel
                        {inputMode === 'file' ? ' (files will be automatically converted)' : ''}
                    </p>
                </div>

                {/* File Input (only shown in file mode) */}
                {inputMode === 'file' && (
                    <div>
                        <label className="block mb-2">
                            Select audio file:
                            <input
                                type="file"
                                accept="audio/*"
                                onChange={handleFileChange}
                                className="block w-full mt-1 p-2 border rounded"
                            />
                        </label>
                        {file && (
                            <div className="mt-1 text-sm text-gray-600">
                                Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                                {audioDuration !== null && <span> • Duration: {audioDuration.toFixed(2)}s</span>}
                            </div>
                        )}
                    </div>
                )}

                {/* Microphone Info (only shown in mic mode) */}
                {inputMode === 'microphone' && (
                    <div className="bg-gray-50 p-3 rounded border border-gray-200">
                        <p className="text-sm">
                            {micPermission === true ? (
                                <span className="text-green-600">✓ Microphone access granted</span>
                            ) : micPermission === false ? (
                                <span className="text-red-600">✗ Microphone access denied</span>
                            ) : (
                                <span className="text-gray-600">Checking microphone access...</span>
                            )}
                        </p>
                        <p className="text-xs mt-1 text-gray-500">
                            For best results, speak clearly and minimize background noise
                        </p>
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex space-x-4">
                    {inputMode === 'file' && (
                        <>
                            <button
                                onClick={handleTranscribeFile}
                                disabled={isLoading || !file || isStreaming}
                                className={`flex-1 px-4 py-2 rounded ${isLoading || !file || isStreaming
                                    ? 'bg-gray-400'
                                    : 'bg-blue-500 hover:bg-blue-600'
                                    } text-white`}
                            >
                                {isLoading ? 'Transcribing...' : 'Transcribe Full File'}
                            </button>

                            <button
                                onClick={isStreaming ? stopStreaming : startStreaming.bind(null, file!)}
                                disabled={!file || isLoading || (isStreaming && isEndOfFile)}
                                className={`flex-1 px-4 py-2 rounded ${!file || isLoading || (isStreaming && isEndOfFile)
                                    ? 'bg-gray-400'
                                    : isStreaming
                                        ? 'bg-red-500 hover:bg-red-600'
                                        : 'bg-green-500 hover:bg-green-600'
                                    } text-white`}
                            >
                                {isStreaming
                                    ? (isEndOfFile ? 'Transcription Complete' : 'Stop Streaming')
                                    : 'Start Real-time Streaming'}
                            </button>
                        </>
                    )}

                    {inputMode === 'microphone' && (
                        <button
                            onClick={isStreaming ? stopStreaming : handleStartMicStreaming}
                            disabled={(isStreaming && isEndOfFile) || micPermission === false}
                            className={`flex-1 px-4 py-2 rounded ${(isStreaming && isEndOfFile) || micPermission === false
                                ? 'bg-gray-400'
                                : isStreaming
                                    ? 'bg-red-500 hover:bg-red-600'
                                    : 'bg-green-500 hover:bg-green-600'
                                } text-white`}
                        >
                            {isStreaming
                                ? (isEndOfFile ? 'Transcription Complete' : 'Stop Microphone')
                                : 'Start Microphone'}
                        </button>
                    )}
                </div>

                {/* Error Display */}
                {(error || streamingError) && (
                    <div className="p-4 bg-red-100 text-red-700 rounded">
                        {error || streamingError}
                    </div>
                )}

                {/* Streaming Status */}
                {isStreaming && (
                    <div className="flex items-center mt-2">
                        <div className="w-3 h-3 bg-red-500 rounded-full mr-2 animate-pulse"></div>
                        <span className="text-sm text-gray-700">
                            {inputMode === 'microphone' ? 'Listening...' : 'Streaming...'}
                        </span>
                    </div>
                )}

                {/* Streaming Result Display */}
                {streamingResult && (
                    <div className="mt-6">
                        <h3 className="text-lg font-semibold mb-2">Streaming Result:</h3>
                        <div className="p-4 bg-gray-100 rounded">
                            <p>{streamingResult}</p>
                        </div>
                    </div>
                )}

                {/* Final Result Display (only for file mode) */}
                {inputMode === 'file' && result && (
                    <div className="mt-6">
                        <h3 className="text-lg font-semibold mb-2">Transcription Result:</h3>
                        <div className="p-4 bg-gray-100 rounded">
                            <p>{result.text}</p>
                            <div className="mt-2 text-sm text-gray-600">
                                <p>Method: {result.method}</p>
                                <p>Processing time: {result.time_spent_sec.toFixed(2)}s</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};