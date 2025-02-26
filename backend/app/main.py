import json
import tempfile
from asyncio import Semaphore
from datetime import datetime
from pathlib import Path

import numpy as np
from app.audio_utils import WHISPER_SAMPLE_RATE_HZ, AudioBuffer
from app.transcription import Transcriber, TranscriptionMethod, TranscriptionResult
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    WebSocket,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()


class TranscriptionConfig(BaseModel):
    model_checkpoint: str = "whisper-1"
    method: TranscriptionMethod = TranscriptionMethod.OPENAI_WHISPER
    save_transcript: bool = True
    chunk_size_ms: int = 2000
    overlap_ms: int = 200


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
active_config = TranscriptionConfig()
transcriber = Transcriber(
    method=active_config.method,
    model_checkpoint=active_config.model_checkpoint,
)
transcriber_lock = Semaphore(1)  # Allow only one transcription at a time


def save_transcript(result: TranscriptionResult):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("transcripts")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"transcript_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(result.model_dump(), f, indent=2)


@app.get("/config")
async def get_config():
    """Get the current active configuration."""
    return active_config


@app.post("/config")
async def update_config(config: TranscriptionConfig):
    """Update the configuration and reinitialize the transcriber."""
    global active_config, transcriber

    async with transcriber_lock:
        # Update the active configuration
        active_config = config

        # Create a new transcriber with the updated config
        transcriber = Transcriber(
            method=config.method,
            model_checkpoint=config.model_checkpoint,
        )

        return active_config


@app.post("/transcribe/file")
async def transcribe_file(file: UploadFile = File(...)):
    """Transcribe a file using the current active configuration."""
    global transcriber

    async with transcriber_lock:
        if not file.filename:
            raise ValueError("Filename is required")
        file_extension = Path(file.filename).suffix

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=file_extension
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            # Use the existing transcriber instance
            result = transcriber.transcribe_file(temp_path)

            if active_config.save_transcript:
                save_transcript(result)

            return result
        finally:
            # Clean up temp file
            Path(temp_path).unlink()


@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for real-time audio streaming."""
    print("New WebSocket connection attempt")
    await websocket.accept()
    print("WebSocket connection accepted")

    transcribe_func = transcriber.transcribe_chunk

    try:
        # Initialize streaming mode
        transcriber.start_stream()
        print("Transcriber streaming mode initialized")

        # Create audio buffer for accumulating samples
        audio_buffer = AudioBuffer(
            chunk_size_ms=active_config.chunk_size_ms,
            overlap_ms=active_config.overlap_ms,
            sample_rate=WHISPER_SAMPLE_RATE_HZ,
        )
        print(
            f"Audio buffer created with chunk size {active_config.chunk_size_ms}ms and overlap {active_config.overlap_ms}ms"
        )

        while True:
            # Receive message
            try:
                message = await websocket.receive()
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

            try:
                if (message["type"] == "websocket.receive") and ("bytes" in message):
                    # Handle binary audio data
                    audio_data = message["bytes"]
                    data_len = len(audio_data) if audio_data else 0

                    if not audio_data or data_len == 0:
                        print("Skipping empty audio data")
                        continue

                    try:
                        # Convert to numpy array
                        samples = np.frombuffer(audio_data, dtype=np.float32)

                        # Add samples to buffer and get complete chunks
                        complete_chunks = audio_buffer.add_samples(samples)

                        # Process each complete chunk
                        for chunk in complete_chunks:
                            result = transcribe_func(chunk)
                            await websocket.send_json({
                                "text": result.text,
                                "is_final": False,
                            })
                    except Exception as e:
                        print(f"Error processing audio data: {e}")
                        continue

                elif (message["type"] == "websocket.receive") and ("text" in message):
                    # Handle control message
                    try:
                        data = json.loads(message["text"])
                        print(f"Received control message: {data}")
                        if data.get("isLastChunk"):
                            print("Processing final chunk")
                            # Process any remaining samples
                            remaining_samples = audio_buffer.get_remaining_samples()
                            if len(remaining_samples) > 0:
                                result = transcribe_func(
                                    remaining_samples, is_final=True
                                )
                                await websocket.send_json({
                                    "text": result.text,
                                    "is_final": True,
                                })

                            print(f"Processed final chunk: {result.text}")

                            continue

                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON message: {e}")
                        continue

                elif message["type"] == "websocket.disconnect":
                    print("Client disconnected")
                    break

            except Exception as e:
                print(f"Error handling message: {e}")
                continue

    except Exception as e:
        print(f"Error in WebSocket connection: {e}")
    finally:
        print("Cleaning up connection")
        transcriber.stop_stream()
        try:
            # Check if the connection is already closed before trying to close it
            if not websocket.client_state.DISCONNECTED:
                await websocket.close()
            else:
                print("WebSocket already closed by client")
        except Exception as e:
            print(f"Error closing websocket: {e}")
