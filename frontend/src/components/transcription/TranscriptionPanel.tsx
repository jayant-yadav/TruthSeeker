import React, { useState } from 'react';
import { useAudioStreaming } from '../../hooks/useAudioStreaming';
import { TranscriptionResult } from '../../types/transcription';

export const TranscriptionPanel: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [result, setResult] = useState<TranscriptionResult | null>(null);
    const [streamingResult, setStreamingResult] = useState<string>('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const { isStreaming, isEndOfFile, error: streamingError, startStreaming, stopStreaming } = useAudioStreaming({
        onTranscriptionUpdate: (result) => {
            setStreamingResult(result.text);
        },
    });

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = event.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            setError(null);
            setResult(null);
            setStreamingResult('');

            // If we were streaming, stop
            if (isStreaming) {
                stopStreaming();
            }
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

    return (
        <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Transcription</h2>
            <div className="space-y-4">
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
                </div>

                <div className="flex space-x-4">
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
                        {isStreaming ? (isEndOfFile ? 'Transcription Complete' : 'Stop Streaming') : 'Start Real-time Streaming'}
                    </button>
                </div>

                {(error || streamingError) && (
                    <div className="p-4 bg-red-100 text-red-700 rounded">
                        {error || streamingError}
                    </div>
                )}

                {streamingResult && (
                    <div className="mt-6">
                        <h3 className="text-lg font-semibold mb-2">Streaming Result:</h3>
                        <div className="p-4 bg-gray-100 rounded">
                            <p>{streamingResult}</p>
                        </div>
                    </div>
                )}

                {result && (
                    <div className="mt-6">
                        <h3 className="text-lg font-semibold mb-2">Transcription Result:</h3>
                        <div className="p-4 bg-gray-100 rounded">
                            <p>{result.text}</p>
                            <div className="mt-2 text-sm text-gray-600">
                                <p>Duration: {result.audio_duration.toFixed(2)}s</p>
                                <p>Method: {result.method}</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};