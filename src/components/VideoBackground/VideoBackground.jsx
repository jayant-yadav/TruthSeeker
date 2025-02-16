import './VideoBackground.css'

function VideoBackground() {
  return (
    <div className="video-container">
      <video autoPlay muted loop className='video'>
        <source src="/video4.mp4" type="video/mp4" />
      </video>
    </div>
  );
}

export default VideoBackground;
