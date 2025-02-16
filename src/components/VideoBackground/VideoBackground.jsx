import './VideoBackground.css'

function VideoBackground() {
  return (
    <div className="video-container">
      <video autoPlay loop className='video'>
        <source src="/test-video2.mp4" type="video/mp4" />
      </video>
    </div>
  );
}

export default VideoBackground;
