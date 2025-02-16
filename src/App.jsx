import './App.css'
import VideoBackground from './components/VideoBackground/VideoBackground'
import Dialog from './components/Dialog/Dialog'
function App() {
  return (
    <div className="root-container">
      <div className='container'>
        <div className="top-container">
          <h1>Truth Seeker</h1>
        </div>
          <VideoBackground />
          <Dialog/>
      </div>
    </div>
  )
}

export default App
