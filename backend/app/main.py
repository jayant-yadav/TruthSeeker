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
from app.transcription.google_speech import GoogleSpeechTranscriber
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
    direct_streaming: bool = False  # Option to stream directly without buffering


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
    elif method == TranscriptionMethod.GOOGLE_SPEECH:
        return GoogleSpeechTranscriber(model_checkpoint)
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


# Helper function to determine if direct streaming should be used
def should_use_direct_streaming(config: TranscriptionConfig) -> bool:
    """Determine if direct streaming should be used based on the config.

    Google Speech API works best with direct streaming, while Whisper-based
    methods work better with buffered streaming.

    Args:
        config: The current transcription configuration

    Returns:
        bool: True if direct streaming should be used, False otherwise
    """
    # Always use direct streaming if explicitly configured
    if config.direct_streaming:
        return True

    # For Google Speech, recommend direct streaming by default
    if config.method == TranscriptionMethod.GOOGLE_SPEECH:
        return True

    # For Whisper-based methods, use buffered streaming by default
    return False


def adapt_audio_format(samples: np.ndarray, method: TranscriptionMethod) -> np.ndarray:
    """Adapt audio format for different transcription methods.

    Args:
        samples: Audio samples as numpy array
        method: The transcription method

    Returns:
        Adapted audio samples
    """
    # Google Speech API expects int16 samples
    if method == TranscriptionMethod.GOOGLE_SPEECH:
        # If samples are float32 in [-1.0, 1.0] range, convert to int16
        if samples.dtype == np.float32:
            return (samples * 32768.0).astype(np.int16)

    # For other methods, ensure float32 format
    if samples.dtype != np.float32:
        return samples.astype(np.float32)

    return samples


@app.get("/config")
async def get_config():
    """Get the current active configuration.

    Returns:
        TranscriptionConfig: The current configuration including:
        - model_checkpoint: The model to use for transcription
        - method: The transcription method (LOCAL_WHISPER, OPENAI_WHISPER, GOOGLE_SPEECH)
        - save_transcript: Whether to save transcripts to disk
        - chunk_size_ms: Size of audio chunks in milliseconds
        - overlap_ms: Overlap between consecutive chunks in milliseconds
        - direct_streaming: Whether to stream audio directly to the transcriber without buffering
    """
    return active_config


@app.post("/config")
async def update_config(config: TranscriptionConfig):
    """Update the configuration and reinitialize the transcriber.

    Args:
        config: The new configuration to apply

    Returns:
        TranscriptionConfig: The updated configuration

    Note:
        Setting direct_streaming=True will bypass the audio buffer and send audio
        directly to the transcriber. This may result in lower quality transcriptions
        for Whisper-based methods but can reduce latency.

        For Google Speech API, direct streaming is recommended and will be used by
        default even if direct_streaming=False, unless you explicitly set it to False
        and are aware of the potential issues.
    """
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

        # Determine if we should use direct streaming based on the transcription method
        use_direct_streaming = should_use_direct_streaming(active_config)

        # Create audio buffer for accumulating samples if not using direct streaming
        if not use_direct_streaming:
            audio_buffer = AudioBuffer(
                chunk_size_ms=active_config.chunk_size_ms,
                overlap_ms=active_config.overlap_ms,
                sample_rate=WHISPER_SAMPLE_RATE_HZ,
            )
            logger.info(
                f"Audio buffer created with chunk size {active_config.chunk_size_ms}ms and overlap {active_config.overlap_ms}ms"
            )
        else:
            logger.info(
                f"Direct streaming mode enabled for {active_config.method} - bypassing audio buffer"
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

                        if use_direct_streaming:
                            # Adapt audio format for the specific transcription method
                            adapted_samples = adapt_audio_format(
                                samples, active_config.method
                            )

                            # Stream directly to transcriber without buffering
                            result = transcriber.transcribe_chunk(adapted_samples)

                            # Only send response if there's text to send
                            if result.text:
                                await websocket.send_json({
                                    "text": result.text,
                                    "is_final": False,
                                })
                        else:
                            # Add samples to buffer and get complete chunks
                            complete_chunks = audio_buffer.add_samples(samples)

                            # Process each complete chunk
                            for chunk in complete_chunks:
                                # Adapt audio format for the specific transcription method
                                adapted_chunk = adapt_audio_format(
                                    chunk, active_config.method
                                )

                                result = transcriber.transcribe_chunk(adapted_chunk)

                                # Only send response if there's text to send
                                if result.text:
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
                            # Process any remaining samples if not using direct streaming
                            if not use_direct_streaming:
                                remaining_samples = audio_buffer.get_remaining_samples()
                                if len(remaining_samples) > 0:
                                    # Adapt audio format for the specific transcription method
                                    adapted_remaining = adapt_audio_format(
                                        remaining_samples, active_config.method
                                    )

                                    result = transcriber.transcribe_chunk(
                                        adapted_remaining, is_final=True
                                    )
                                    await websocket.send_json({
                                        "text": result.text,
                                        "is_final": True,
                                    })
                                else:
                                    # No remaining samples, just send a final empty chunk
                                    empty_array = (
                                        np.array([], dtype=np.int16)
                                        if active_config.method
                                        == TranscriptionMethod.GOOGLE_SPEECH
                                        else np.array([], dtype=np.float32)
                                    )

                                    result = transcriber.transcribe_chunk(
                                        empty_array, is_final=True
                                    )
                                    await websocket.send_json({
                                        "text": result.text,
                                        "is_final": True,
                                    })
                            else:
                                # For direct streaming, send a final empty chunk
                                # Use the appropriate data type based on the transcription method
                                empty_array = (
                                    np.array([], dtype=np.int16)
                                    if active_config.method
                                    == TranscriptionMethod.GOOGLE_SPEECH
                                    else np.array([], dtype=np.float32)
                                )

                                result = transcriber.transcribe_chunk(
                                    empty_array, is_final=True
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
