import React from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './App.css';
import { TranscriptionTester } from './components/transcription/TranscriptionTester';
import DemoPage from './components/DemoPage';

function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      {/* <TranscriptionTester /> */}
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<TranscriptionTester />} />
          <Route path="/demo" element={<DemoPage />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;