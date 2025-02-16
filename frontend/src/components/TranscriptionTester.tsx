import React, { useState } from 'react';

interface TranscriptionResult {
    text: string;
    timestamp: number | null;
    duration: number | null;
    method: string;
    model_size: string;
}

const TranscriptionTester: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [result, setResult] = useState<TranscriptionResult | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = event.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            setError(null);
        }
    };

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!file) {
            setError('Please select a file first');
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
        <div className="max-w-2xl mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Audio Transcription Tester</h1>

            <form onSubmit={handleSubmit} className="mb-6">
                <div className="mb-4">
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
                    className={`px-4 py-2 rounded ${isLoading || !file
                        ? 'bg-gray-400'
                        : 'bg-blue-500 hover:bg-blue-600'
                        } text-white`}
                >
                    {isLoading ? 'Transcribing...' : 'Transcribe'}
                </button>
            </form>

            {error && (
                <div className="p-4 mb-4 bg-red-100 text-red-700 rounded">
                    {error}
                </div>
            )}

            {result && (
                <div className="mt-6">
                    <h2 className="text-xl font-semibold mb-2">Transcription Result:</h2>
                    <div className="p-4 bg-gray-100 rounded">
                        <p>{result.text}</p>
                        <div className="mt-2 text-sm text-gray-600">
                            {result.duration && <p>Duration: {result.duration.toFixed(2)}s</p>}
                            <p>Method: {result.method}</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default TranscriptionTester;