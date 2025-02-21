import React, { useState, useEffect } from 'react';

interface TranscriptionResult {
    text: string;
    timestamp: number | null;
    duration: number | null;
    method: string;
    model_size: string;
}

interface StreamingResult {
    text: string;
    is_final: boolean;
}

interface TranscriptionConfig {
    mode: 'stream' | 'whole';
    chunk_size_ms: number;
    overlap_ms: number;
    model_checkpoint: string;
    save_transcript: boolean;
    method: typeof TRANSCRIPTION_METHODS[number];
}

const LOCAL_MODEL_CHECKPOINTS = ['tiny.en', 'base.en', 'small.en', 'medium.en', 'large-v3', 'large-v2', 'large-v3-turbo', 'large-v3-turbo-q5_0'];
const OPENAI_MODEL_CHECKPOINTS = ['whisper-1'];
const TRANSCRIPTION_METHODS = ['local_whisper', 'openai_whisper'] as const;

const TranscriptionTester: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [result, setResult] = useState<TranscriptionResult | null>(null);
    const [streamingResult, setStreamingResult] = useState<string>('');
    const [isLoading, setIsLoading] = useState(false);
    const [isUpdatingConfig, setIsUpdatingConfig] = useState(false);
    const [isLoadingConfig, setIsLoadingConfig] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [configError, setConfigError] = useState<string | null>(null);

    // Initialize config states as null to indicate they haven't been loaded yet
    const [config, setConfig] = useState<TranscriptionConfig | null>(null);
    const [activeConfig, setActiveConfig] = useState<TranscriptionConfig | null>(null);

    const fetchConfig = async () => {
        setIsLoadingConfig(true);
        setConfigError(null);
        try {
            const response = await fetch('http://localhost:8000/config');
            if (!response.ok) {
                throw new Error(`Failed to fetch configuration: ${response.statusText}`);
            }
            const configData = await response.json();
            setConfig(configData);
            setActiveConfig(configData);
        } catch (err) {
            setConfigError(err instanceof Error ? err.message : 'Failed to fetch configuration');
        } finally {
            setIsLoadingConfig(false);
        }
    };

    useEffect(() => {
        fetchConfig();
    }, []);

    useEffect(() => {
        if (!config) return;

        if (config.method === 'openai_whisper' && !OPENAI_MODEL_CHECKPOINTS.includes(config.model_checkpoint)) {
            setConfig(prev => prev ? {
                ...prev,
                model_checkpoint: 'whisper-1'
            } : null);
        } else if (config.method === 'local_whisper' && !LOCAL_MODEL_CHECKPOINTS.includes(config.model_checkpoint)) {
            setConfig(prev => prev ? {
                ...prev,
                model_checkpoint: 'medium.en'
            } : null);
        }
    }, [config?.method]);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = event.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            setError(null);
        }
    };

    const handleConfigChange = (field: keyof TranscriptionConfig, value: any) => {
        setConfig(prev => prev ? {
            ...prev,
            [field]: value
        } : null);
    };

    const handleUpdateConfig = async () => {
        if (!config) return;

        setIsUpdatingConfig(true);
        setConfigError(null);

        try {
            const response = await fetch('http://localhost:8000/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config),
            });

            if (!response.ok) {
                throw new Error(`Failed to update configuration: ${response.statusText}`);
            }

            const updatedConfig = await response.json();
            setActiveConfig(updatedConfig);
        } catch (err) {
            setConfigError(err instanceof Error ? err.message : 'Failed to update configuration');
        } finally {
            setIsUpdatingConfig(false);
        }
    };

    const handleStreamingTranscription = async () => {
        if (!file) return;

        setIsLoading(true);
        setError(null);
        setStreamingResult('');

        const formData = new FormData();
        formData.append('file', file);
        formData.append('config', JSON.stringify(config));

        try {
            console.log('Streaming transcription for file:', file.name);
            const response = await fetch('http://localhost:8000/stream/file', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body?.getReader();
            if (!reader) throw new Error('Response body is null');

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                // Convert the chunk to text and parse as JSON
                const chunk = new TextDecoder().decode(value);
                const results = chunk.split('\n').filter(line => line.trim());

                for (const result of results) {
                    try {
                        const data: StreamingResult = JSON.parse(result);
                        setStreamingResult(data.text);
                    } catch (e) {
                        console.error('Failed to parse streaming result:', e);
                    }
                }
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!file) {
            setError('Please select a file first');
            return;
        }

        if (activeConfig?.mode === 'stream') {
            await handleStreamingTranscription();
            return;
        }

        setIsLoading(true);
        setError(null);

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
        <div className="max-w-6xl mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Audio Transcription Tester</h1>

            {isLoadingConfig ? (
                <div className="flex items-center justify-center p-8">
                    <div className="text-lg text-gray-600">Loading configuration...</div>
                </div>
            ) : configError ? (
                <div className="p-4 bg-red-100 text-red-700 rounded">
                    <p className="font-semibold">Failed to load configuration:</p>
                    <p>{configError}</p>
                    <button
                        onClick={fetchConfig}
                        className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                    >
                        Retry
                    </button>
                </div>
            ) : !config || !activeConfig ? (
                <div className="p-4 bg-yellow-100 text-yellow-700 rounded">
                    <p>No configuration available. Please refresh the page or contact support.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Configuration Pane */}
                    <div className="bg-white p-6 rounded-lg shadow">
                        <h2 className="text-xl font-semibold mb-4">Configuration</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block mb-2">
                                    Transcription Method:
                                    <select
                                        value={config?.method}
                                        onChange={(e) => handleConfigChange('method', e.target.value as typeof TRANSCRIPTION_METHODS[number])}
                                        className="block w-full mt-1 p-2 border rounded"
                                    >
                                        {TRANSCRIPTION_METHODS.map(method => (
                                            <option key={method} value={method}>{method}</option>
                                        ))}
                                    </select>
                                </label>
                            </div>

                            <div>
                                <label className="block mb-2">
                                    Model Checkpoint:
                                    <select
                                        value={config?.model_checkpoint}
                                        onChange={(e) => handleConfigChange('model_checkpoint', e.target.value)}
                                        className="block w-full mt-1 p-2 border rounded"
                                    >
                                        {(config?.method === 'local_whisper' ? LOCAL_MODEL_CHECKPOINTS : OPENAI_MODEL_CHECKPOINTS).map(checkpoint => (
                                            <option key={checkpoint} value={checkpoint}>{checkpoint}</option>
                                        ))}
                                    </select>
                                </label>
                            </div>

                            <div>
                                <label className="block mb-2">
                                    Transcription Mode:
                                    <select
                                        value={config?.mode}
                                        onChange={(e) => handleConfigChange('mode', e.target.value)}
                                        className="block w-full mt-1 p-2 border rounded"
                                    >
                                        <option value="whole">Complete File</option>
                                        <option value="stream">Streaming</option>
                                    </select>
                                </label>
                            </div>

                            {config?.mode === 'stream' && (
                                <>
                                    <div>
                                        <label className="block mb-2">
                                            Chunk Size (ms):
                                            <input
                                                type="number"
                                                value={config?.chunk_size_ms}
                                                onChange={(e) => handleConfigChange('chunk_size_ms', parseInt(e.target.value))}
                                                min="1000"
                                                step="1000"
                                                className="block w-full mt-1 p-2 border rounded"
                                            />
                                        </label>
                                    </div>

                                    <div>
                                        <label className="block mb-2">
                                            Overlap (ms):
                                            <input
                                                type="number"
                                                value={config?.overlap_ms}
                                                onChange={(e) => handleConfigChange('overlap_ms', parseInt(e.target.value))}
                                                min="0"
                                                step="100"
                                                className="block w-full mt-1 p-2 border rounded"
                                            />
                                        </label>
                                    </div>
                                </>
                            )}

                            <div>
                                <label className="block mb-2">
                                    <input
                                        type="checkbox"
                                        checked={config?.save_transcript}
                                        onChange={(e) => handleConfigChange('save_transcript', e.target.checked)}
                                        className="mr-2"
                                    />
                                    Save Transcript
                                </label>
                            </div>

                            <button
                                onClick={handleUpdateConfig}
                                disabled={isUpdatingConfig}
                                className={`w-full px-4 py-2 rounded ${isUpdatingConfig
                                    ? 'bg-gray-400'
                                    : 'bg-green-500 hover:bg-green-600'
                                    } text-white mt-4`}
                            >
                                {isUpdatingConfig ? 'Updating Configuration...' : 'Update Configuration'}
                            </button>

                            {configError && (
                                <div className="p-4 bg-red-100 text-red-700 rounded">
                                    {configError}
                                </div>
                            )}
                        </div>

                        <div className="mt-6 p-4 bg-gray-50 rounded">
                            <h3 className="font-medium mb-2">Active Configuration:</h3>
                            <pre className="text-sm whitespace-pre-wrap">
                                {JSON.stringify(activeConfig, null, 2)}
                            </pre>
                        </div>
                    </div>

                    {/* Transcription Pane */}
                    <div className="bg-white p-6 rounded-lg shadow">
                        <h2 className="text-xl font-semibold mb-4">Transcription</h2>
                        <form onSubmit={handleSubmit} className="space-y-4">
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

                            <button
                                type="submit"
                                disabled={isLoading || !file}
                                className={`w-full px-4 py-2 rounded ${isLoading || !file
                                    ? 'bg-gray-400'
                                    : 'bg-blue-500 hover:bg-blue-600'
                                    } text-white`}
                            >
                                {isLoading ? 'Transcribing...' : 'Transcribe'}
                            </button>

                            {error && (
                                <div className="p-4 mb-4 bg-red-100 text-red-700 rounded">
                                    {error}
                                </div>
                            )}

                            {activeConfig?.mode === 'stream' && streamingResult && (
                                <div className="mt-6">
                                    <h3 className="text-lg font-semibold mb-2">Streaming Result:</h3>
                                    <div className="p-4 bg-gray-100 rounded">
                                        <p>{streamingResult}</p>
                                    </div>
                                </div>
                            )}

                            {activeConfig?.mode === 'whole' && result && (
                                <div className="mt-6">
                                    <h3 className="text-lg font-semibold mb-2">Transcription Result:</h3>
                                    <div className="p-4 bg-gray-100 rounded">
                                        <p>{result.text}</p>
                                        <div className="mt-2 text-sm text-gray-600">
                                            {result.duration && (
                                                <p>Duration: {result.duration.toFixed(2)}s</p>
                                            )}
                                            <p>Method: {result.method}</p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default TranscriptionTester;