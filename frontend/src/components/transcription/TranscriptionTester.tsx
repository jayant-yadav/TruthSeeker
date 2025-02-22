import React from 'react';
import { ConfigurationPanel } from './ConfigurationPanel';
import { TranscriptionPanel } from './TranscriptionPanel';

export const TranscriptionTester: React.FC = () => {
    return (
        <div className="max-w-6xl mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Audio Transcription Tester</h1>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <ConfigurationPanel />
                <TranscriptionPanel />
            </div>
        </div>
    );
};