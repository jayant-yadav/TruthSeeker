import React, { useState, useRef } from 'react';
import { useAudioStreaming } from '../hooks/useAudioStreaming';

export const AudioTranscriber: React.FC = () => {
    const [transcription, setTranscription] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const { isStreaming, startStreaming, stopStreaming } = useAudioStreaming({
        onTranscriptionUpdate: (result) => {
            setTranscription(result.text);

            if (result.is_final) {
                console.log('Final transcription received');
            }
        },
    });

    const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        try {
            await startStreaming(file);
        } catch (error) {
            console.error('Error starting stream:', error);
            alert('Failed to start streaming');
        }
    };

    const handleStopClick = () => {
        stopStreaming();
    };

    return (
        <div className="p-4">
            <div className="mb-4">
                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    accept="audio/*"
                    className="mb-2"
                    disabled={isStreaming}
                />

                {isStreaming && (
                    <button
                        onClick={handleStopClick}
                        className="ml-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                    >
                        Stop Streaming
                    </button>
                )}
            </div>

            <div className="mt-4">
                <h3 className="text-lg font-semibold mb-2">Transcription:</h3>
                <div className="p-4 bg-gray-100 rounded min-h-[100px] whitespace-pre-wrap">
                    {transcription || 'No transcription yet...'}
                </div>
            </div>
        </div>
    );
};