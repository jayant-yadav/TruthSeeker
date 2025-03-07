import React, { useState } from 'react';
import { TranscriptionConfig, LOCAL_MODEL_CHECKPOINTS, OPENAI_MODEL_CHECKPOINTS, TRANSCRIPTION_METHODS } from '../../types/transcription';
import { useTranscriptionConfig } from '../../hooks/useTranscriptionConfig';

// Define Google Speech model checkpoints
const GOOGLE_SPEECH_MODEL_CHECKPOINTS = ['default'] as const;

// Helper function to format method names for display
const formatMethodName = (method: string): string => {
    switch (method) {
        case 'local_whisper':
            return 'Local Whisper';
        case 'openai_whisper':
            return 'OpenAI Whisper';
        case 'google_speech':
            return 'Google Speech';
        default:
            return method;
    }
};

export const ConfigurationPanel: React.FC = () => {
    const { config, activeConfig, isLoading, error, updateConfig, setConfig } = useTranscriptionConfig();
    const [isUpdating, setIsUpdating] = useState(false);

    // Helper function to get model checkpoints based on method
    const getModelCheckpoints = (method: string) => {
        switch (method) {
            case 'local_whisper':
                return LOCAL_MODEL_CHECKPOINTS;
            case 'openai_whisper':
                return OPENAI_MODEL_CHECKPOINTS;
            case 'google_speech':
                return GOOGLE_SPEECH_MODEL_CHECKPOINTS;
            default:
                return [];
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-8">
                <div className="text-lg text-gray-600">Loading configuration...</div>
            </div>
        );
    }

    if (error || !config || !activeConfig) {
        return (
            <div className="p-4 bg-red-100 text-red-700 rounded">
                <p className="font-semibold">Failed to load configuration:</p>
                <p>{error || 'No configuration available'}</p>
            </div>
        );
    }

    const handleConfigChange = (field: keyof TranscriptionConfig, value: any) => {
        const newConfig = {
            ...config,
            [field]: value,
        };

        // If method changes, update model_checkpoint to a valid value for the new method
        if (field === 'method') {
            if (value === 'local_whisper') {
                newConfig.model_checkpoint = LOCAL_MODEL_CHECKPOINTS[0];
            } else if (value === 'openai_whisper') {
                newConfig.model_checkpoint = OPENAI_MODEL_CHECKPOINTS[0];
            } else if (value === 'google_speech') {
                newConfig.model_checkpoint = GOOGLE_SPEECH_MODEL_CHECKPOINTS[0];
            }
        }

        setConfig(newConfig);
    };

    const handleUpdateConfig = async () => {
        try {
            setIsUpdating(true);
            await updateConfig(config);
        } catch (err) {
            console.error('Failed to update config:', err);
        } finally {
            setIsUpdating(false);
        }
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Configuration</h2>
            <div className="space-y-6">
                {/* General Settings */}
                <div className="space-y-4">
                    <h3 className="text-lg font-medium">General Settings</h3>
                    <div>
                        <label className="block mb-2">
                            Transcription Method:
                            <select
                                value={config.method}
                                onChange={(e) => handleConfigChange('method', e.target.value)}
                                className="block w-full mt-1 p-2 border rounded"
                            >
                                {TRANSCRIPTION_METHODS.map(method => (
                                    <option key={method} value={method}>{formatMethodName(method)}</option>
                                ))}
                            </select>
                        </label>
                    </div>

                    <div>
                        <label className="block mb-2">
                            Model Checkpoint:
                            <select
                                value={config.model_checkpoint}
                                onChange={(e) => handleConfigChange('model_checkpoint', e.target.value)}
                                className="block w-full mt-1 p-2 border rounded"
                            >
                                {getModelCheckpoints(config.method).map(checkpoint => (
                                    <option key={checkpoint} value={checkpoint}>{checkpoint}</option>
                                ))}
                            </select>
                        </label>
                    </div>

                    <div>
                        <label className="block mb-2">
                            <input
                                type="checkbox"
                                checked={config.save_transcript}
                                onChange={(e) => handleConfigChange('save_transcript', e.target.checked)}
                                className="mr-2"
                            />
                            Save Transcript
                        </label>
                    </div>
                </div>

                {/* Streaming Settings */}
                <div className="space-y-4 border-t pt-4">
                    <h3 className="text-lg font-medium">Real-time Streaming Settings</h3>
                    <p className="text-sm text-gray-600 mb-4">
                        These settings only affect real-time streaming mode and don't impact full file transcription.
                    </p>
                    <div>
                        <label className="block mb-2">
                            Chunk Size (ms):
                            <input
                                type="number"
                                value={config.chunk_size_ms}
                                onChange={(e) => handleConfigChange('chunk_size_ms', parseInt(e.target.value))}
                                min="100"
                                step="100"
                                className="block w-full mt-1 p-2 border rounded"
                            />
                            <span className="text-sm text-gray-500">
                                How often to send audio chunks for transcription
                            </span>
                        </label>
                    </div>

                    <div>
                        <label className="block mb-2">
                            Overlap (ms):
                            <input
                                type="number"
                                value={config.overlap_ms}
                                onChange={(e) => handleConfigChange('overlap_ms', parseInt(e.target.value))}
                                min="0"
                                step="50"
                                className="block w-full mt-1 p-2 border rounded"
                            />
                            <span className="text-sm text-gray-500">
                                Overlap between consecutive chunks to improve transcription
                            </span>
                        </label>
                    </div>
                </div>

                <button
                    onClick={handleUpdateConfig}
                    disabled={isUpdating}
                    className={`w-full px-4 py-2 rounded ${isUpdating
                        ? 'bg-gray-400'
                        : 'bg-green-500 hover:bg-green-600'
                        } text-white mt-4`}
                >
                    {isUpdating ? 'Updating Configuration...' : 'Update Configuration'}
                </button>

                <div className="mt-6 p-4 bg-gray-50 rounded">
                    <h3 className="font-medium mb-2">Active Configuration:</h3>
                    <pre className="text-sm whitespace-pre-wrap">
                        {JSON.stringify(activeConfig, null, 2)}
                    </pre>
                </div>
            </div>
        </div>
    );
};