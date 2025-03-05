import json
import logging
import tempfile
from asyncio import Semaphore
from datetime import datetime
from pathlib import Path

import numpy as np
from app.transcription.common import (
    BaseTranscriber,
    TranscriptionMethod,
    TranscriptionResult,
)
from app.transcription.local_whisper import LocalWhisperTranscriber
from app.transcription.openai_whisper import OpenAIWhisperTranscriber
from app.transcription.utils import WHISPER_SAMPLE_RATE_HZ, AudioBuffer
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    WebSocket,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)

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


def create_transcriber(
    method: TranscriptionMethod, model_checkpoint: str
) -> BaseTranscriber:
    """Factory function to create the appropriate transcriber based on the method.

    Args:
        method: The transcription method to use
        model_checkpoint: Name/identifier of the model to use

    Returns:
        An instance of the appropriate transcriber

    Raises:
        ValueError: If the method is not supported
    """
    if method == TranscriptionMethod.LOCAL_WHISPER:
        return LocalWhisperTranscriber(model_checkpoint)
    elif method == TranscriptionMethod.OPENAI_WHISPER:
        return OpenAIWhisperTranscriber(model_checkpoint)
    else:
        raise ValueError(f"Unsupported transcription method: {method}")


# Global state
active_config = TranscriptionConfig()
transcriber = create_transcriber(
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

        transcriber = create_transcriber(
            method=active_config.method,
            model_checkpoint=active_config.model_checkpoint,
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
    logger.info("New WebSocket connection attempt")
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    try:
        # Initialize streaming mode
        transcriber.start_stream()
        logger.info("Transcriber streaming mode initialized")

        # Create audio buffer for accumulating samples
        audio_buffer = AudioBuffer(
            chunk_size_ms=active_config.chunk_size_ms,
            overlap_ms=active_config.overlap_ms,
            sample_rate=WHISPER_SAMPLE_RATE_HZ,
        )
        logger.info(
            f"Audio buffer created with chunk size {active_config.chunk_size_ms}ms and overlap {active_config.overlap_ms}ms"
        )

        while True:
            # Receive message
            try:
                message = await websocket.receive()
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                break

            try:
                if (message["type"] == "websocket.receive") and ("bytes" in message):
                    # Handle binary audio data
                    audio_data = message["bytes"]
                    data_len = len(audio_data) if audio_data else 0

                    if not audio_data or data_len == 0:
                        logger.debug("Skipping empty audio data")
                        continue

                    try:
                        # Convert to numpy array
                        samples = np.frombuffer(audio_data, dtype=np.float32)

                        # Add samples to buffer and get complete chunks
                        complete_chunks = audio_buffer.add_samples(samples)

                        # Process each complete chunk
                        for chunk in complete_chunks:
                            result = transcriber.transcribe_chunk(chunk)
                            await websocket.send_json({
                                "text": result.text,
                                "is_final": False,
                            })
                    except Exception as e:
                        logger.error(f"Error processing audio data: {e}")
                        continue

                elif (message["type"] == "websocket.receive") and ("text" in message):
                    # Handle control message
                    try:
                        data = json.loads(message["text"])
                        logger.debug(f"Received control message: {data}")
                        if data.get("isLastChunk"):
                            logger.info("Processing final chunk")
                            # Process any remaining samples
                            remaining_samples = audio_buffer.get_remaining_samples()
                            if len(remaining_samples) > 0:
                                result = transcriber.transcribe_chunk(
                                    remaining_samples, is_final=True
                                )
                                await websocket.send_json({
                                    "text": result.text,
                                    "is_final": True,
                                })

                            logger.info(f"Processed final chunk: {result.text}")

                            continue

                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding JSON message: {e}")
                        continue

                elif message["type"] == "websocket.disconnect":
                    logger.info("Client disconnected")
                    break

            except Exception as e:
                logger.error(f"Error handling message: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
    finally:
        logger.info("Cleaning up connection")
        transcriber.stop_stream()
        try:
            # Check if the connection is already closed before trying to close it
            if not websocket.client_state.DISCONNECTED:
                await websocket.close()
            else:
                logger.info("WebSocket already closed by client")
        except Exception as e:
            logger.error(f"Error closing websocket: {e}")
