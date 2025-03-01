import React from 'react';
import Dialog from './Dialog/Dialog';
import VideoBackground from './VideoBackground/VideoBackground';


const DemoPage: React.FC = () => {
return (
    <div className="root-container">
      <div className="container">
        <div className="top-container">
          <h1>Truth Seeker</h1>
        </div>
        <VideoBackground />
        <Dialog />
      </div>
    </div>
  );
};

export default DemoPage;
