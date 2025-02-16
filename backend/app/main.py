import json
import tempfile
from asyncio import Semaphore
from datetime import datetime
from pathlib import Path
from typing import Literal

from app.transcription import Transcriber, TranscriptionMethod, TranscriptionResult
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()


class TranscriptionConfig(BaseModel):
    mode: Literal["stream", "whole"] = "whole"
    chunk_size_ms: int = 3000
    model_size: str = "medium.en"
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
    async with transcriber_lock:  # Ensure exclusive access to transcriber
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
                temp_path, method=config.method, model_size=config.model_size
            )

            if config.save_transcript:
                save_transcript(result)

            return result
        finally:
            # Clean up temp file
            Path(temp_path).unlink()


@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    raise NotImplementedError


@app.get("/config")
async def get_config():
    return TranscriptionConfig()


@app.post("/config")
async def update_config(config: TranscriptionConfig):
    # Here you could persist the config if needed
    return config
