import { useCallback, useEffect, useState } from 'react';
import { TranscriptionConfig } from '../types/transcription';

export const useTranscriptionConfig = () => {
    const [config, setConfig] = useState<TranscriptionConfig | null>(null);
    const [activeConfig, setActiveConfig] = useState<TranscriptionConfig | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchConfig = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch('http://localhost:8000/config');
            if (!response.ok) {
                throw new Error(`Failed to fetch configuration: ${response.statusText}`);
            }
            const configData = await response.json();
            setConfig(configData);
            setActiveConfig(configData);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch configuration');
        } finally {
            setIsLoading(false);
        }
    }, []);

    const updateConfig = useCallback(async (newConfig: TranscriptionConfig) => {
        setError(null);
        try {
            const response = await fetch('http://localhost:8000/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newConfig),
            });

            if (!response.ok) {
                throw new Error(`Failed to update configuration: ${response.statusText}`);
            }

            const updatedConfig = await response.json();
            setConfig(newConfig);
            setActiveConfig(updatedConfig);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to update configuration');
            throw err;
        }
    }, []);

    useEffect(() => {
        fetchConfig();
    }, [fetchConfig]);

    return {
        config,
        setConfig,
        activeConfig,
        isLoading,
        error,
        updateConfig,
        fetchConfig,
    };
};