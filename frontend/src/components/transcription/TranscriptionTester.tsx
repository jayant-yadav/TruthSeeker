import React from 'react';
import { ConfigurationPanel } from './ConfigurationPanel';
import { TranscriptionPanel } from './TranscriptionPanel';
import { useNavigate } from 'react-router-dom';
export const TranscriptionTester: React.FC = () => {

    const navigate = useNavigate();

    const handleDemoClick = () => {
        navigate('/demo');
    };

    return (
        <div className="max-w-6xl mx-auto p-4">
            <div className='flex mb-2 justify-between'>
            <h1 className="text-2xl font-bold mb-4">Audio Transcription Tester</h1>
            <button
             onClick={handleDemoClick} 
            className={`w-[240px] h-[40px] px-4 py-2 rounded bg-black hover:bg-red-500  text-white`}
            >Demo</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <ConfigurationPanel />
                <TranscriptionPanel />
            </div>
        </div>
    );
};