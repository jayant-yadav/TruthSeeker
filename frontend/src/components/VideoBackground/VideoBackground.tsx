import React, { useState, useRef } from 'react';
import './VideoBackground.css';

const VideoBackground: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(true);

  const handlePlayPause = () => {
    if (!videoRef.current) {
      console.log('Video ref is null!');
      return;
    }

    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
      console.log('Video paused');
    } else {
      videoRef.current.play();
      setIsPlaying(true);
      console.log('Video playing');
    }
  };

  const handleMuteUnmute = () => {
    if (!videoRef.current) {
      console.log('Video ref is null!');
      return;
    }

    if (isMuted) {
      videoRef.current.muted = false;
      setIsMuted(false);
      console.log('Video unmuted');
    } else {
      videoRef.current.muted = true;
      setIsMuted(true);
      console.log('Video muted');
    }
  };

  return (
    <div className="video-container">
      <video
        ref={videoRef}
        autoPlay
        muted
        loop
        className="video"
      >
        <source src="/video4.mp4" type="video/mp4" />
        Your browser does not support the video tag.
      </video>

      <div className="controls">
        <button onClick={handlePlayPause}>
          {isPlaying ? 'Pause' : 'Play'}
        </button>
        <button onClick={handleMuteUnmute}>
          {isMuted ? 'Unmute' : 'Mute'}
        </button>
      </div>
    </div>
  );
};

export default VideoBackground;
