import json
import tempfile
from asyncio import Semaphore
from datetime import datetime
from pathlib import Path
from typing import Literal

import numpy as np
from app.audio_utils import stream_audio_file
from app.transcription import Transcriber, TranscriptionMethod, TranscriptionResult
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()


class TranscriptionConfig(BaseModel):
    mode: Literal["stream", "whole"] = "whole"
    chunk_size_ms: int = 2000
    overlap_ms: int = 0
    model_checkpoint: str = "medium.en"
    input_type: Literal["file", "microphone"] = "file"
    save_transcript: bool = True
    method: TranscriptionMethod = TranscriptionMethod.OPENAI_WHISPER


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global transcriber instance and semaphore
transcriber = Transcriber()
transcriber_lock = Semaphore(1)  # Allow only one transcription at a time


def save_transcript(result: TranscriptionResult):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("transcripts")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"transcript_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(result.model_dump(), f, indent=2)


@app.post("/transcribe/file")
async def transcribe_file(
    file: UploadFile = File(...), config: TranscriptionConfig = TranscriptionConfig()
):
    async with transcriber_lock:  # Ensure exclusive access to transcriber, which is
        # technically only relevant for the local Whisper model

        # Save uploaded file to temporary location
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
            # Transcribe the file using the specified method
            result = transcriber.transcribe(
                temp_path,
                method=config.method,
                model_checkpoint=config.model_checkpoint,
            )

            if config.save_transcript:
                save_transcript(result)

            return result
        finally:
            # Clean up temp file
            Path(temp_path).unlink()


@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async with transcriber_lock:
        try:
            # Initialize transcriber in streaming mode
            transcriber.start_streaming()

            while True:
                # Receive audio chunk as bytes
                audio_chunk = await websocket.receive_bytes()

                # Convert bytes to audio samples
                chunk = np.frombuffer(audio_chunk, dtype=np.float32)

                # Process the chunk and get intermediate transcription
                partial_result = transcriber.process_stream_chunk(chunk)

                # Send back the partial transcription
                await websocket.send_json({
                    "text": partial_result.text,
                    "is_final": partial_result.is_final,
                })

        except WebSocketDisconnect:
            # Clean up streaming resources
            transcriber.stop_streaming()
        except Exception as e:
            await websocket.send_json({"error": str(e)})
            transcriber.stop_streaming()


@app.get("/config")
async def get_config():
    return TranscriptionConfig()


@app.post("/config")
async def update_config(config: TranscriptionConfig):
    # Here you could persist the config if needed
    return config


@app.post("/stream/file")
async def stream_file(
    file: UploadFile = File(...), config: TranscriptionConfig = TranscriptionConfig()
):
    """Stream transcription from an audio file by simulating microphone input."""
    if not file.filename:
        raise ValueError("Filename is required")

    # Create temporary file outside of the generator
    temp_path = None
    file_extension = Path(str(file.filename)).suffix
    content = await file.read()  # Read content immediately

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    async def generate():
        try:
            # Initialize transcriber in streaming mode
            async with transcriber_lock:
                transcriber.start_streaming()

                # Stream chunks from the file
                async for chunk in stream_audio_file(
                    temp_path,
                    chunk_duration_ms=config.chunk_size_ms,
                    overlap_ms=config.overlap_ms,
                ):
                    # Process the chunk and get intermediate transcription
                    partial_result = transcriber.process_stream_chunk(chunk)

                    # Yield the partial transcription

                    print("\n\npartial_result:\n\n", partial_result.text)
                    yield (
                        json.dumps({
                            "text": partial_result.text,
                            "is_final": partial_result.is_final,
                        })
                        + "\n"
                    )

        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"
        finally:
            transcriber.stop_streaming()
            if temp_path:
                temp_path.unlink(missing_ok=True)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
