import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
from app.audio_utils import prepare_openai_audio
from openai import OpenAI
from pydantic import BaseModel
from pydub import AudioSegment
from pywhispercpp.model import Model as WhisperCppModel

WHISPER_CPP_MODEL_PATH = Path("./models/").resolve()


class TranscriptionMethod(str, Enum):
    LOCAL_WHISPER = "local_whisper"
    OPENAI_WHISPER = "openai_whisper"


class TranscriptionResult(BaseModel):
    text: str
    timestamp: str
    audio_duration: float
    method: TranscriptionMethod


@dataclass
class StreamingTranscriptionResult:
    text: str
    is_final: bool


class Transcriber:
    def __init__(self):
        self.local_model: Optional[WhisperCppModel] = None
        self.openai_client: Optional[OpenAI] = None
        self.current_text: str = ""

    def _get_audio_info(self, audio_path: str):
        """Get audio file information"""
        audio = AudioSegment.from_file(audio_path)

        info = {
            "filename": os.path.basename(audio_path),
            "duration_seconds": len(audio) / 1000,
            "channels": audio.channels,
            "sample_width": audio.sample_width,
            "frame_rate": audio.frame_rate,
            "file_size_mb": os.path.getsize(audio_path) / (1024 * 1024),
            "timestamp": datetime.now().isoformat(),
        }

        return info

    def _download_whisper_cpp_model(self, model_checkpoint: str):
        """Download Whisper model in the GGML format.

        Args:
            model_checkpoint: Name of the model to download (e.g. 'medium.en')
        """
        import subprocess

        # Ensure we're in the correct working directory
        model_dir = WHISPER_CPP_MODEL_PATH
        model_dir.mkdir(parents=True, exist_ok=True)

        # Run the download script with the model directory as working directory
        download_script = model_dir / "download-ggml-model.sh"
        try:
            subprocess.run([str(download_script), model_checkpoint], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to download model: {e}")

    def get_whisper_cpp_model(self, model_checkpoint: str) -> WhisperCppModel:
        """Get or initialize local Whisper model.

        Downloads the model if it doesn't exist locally.
        """
        if self.local_model is None:
            model_file = f"ggml-{model_checkpoint}.bin"
            model_path = WHISPER_CPP_MODEL_PATH / model_file

            if not model_path.exists():
                # Create models directory if it doesn't exist
                model_path.parent.mkdir(parents=True, exist_ok=True)
                # Download and convert the model
                self._download_whisper_cpp_model(model_checkpoint)

            print(f"Loading local Whisper model from {model_path}")
            self.local_model = WhisperCppModel(str(model_path))
        return self.local_model

    def get_openai_client(self) -> OpenAI:
        """Get or initialize OpenAI client."""
        if self.openai_client is None:
            self.openai_client = OpenAI()
        return self.openai_client

    def transcribe(
        self,
        audio_path: str,
        method: TranscriptionMethod,
        model_checkpoint: str,
    ) -> TranscriptionResult:
        """
        Transcribe audio using specified method.

        Args:
            audio_path: Path to audio file
            method: TranscriptionMethod to use
            model_checkpoint for local Whisper model: Name of the model to use (e.g. 'medium.en')
        """
        if method == TranscriptionMethod.LOCAL_WHISPER:
            model = self.get_whisper_cpp_model(model_checkpoint)
            segments = model.transcribe(audio_path, n_processors=1)
            text = " ".join([segment.text for segment in segments])

        elif method == TranscriptionMethod.OPENAI_WHISPER:
            client = self.get_openai_client()
            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file
                )
                text = response.text
        else:
            pass

        print(f"Transcribed text: {text}")

        audio_info = self._get_audio_info(audio_path)
        return TranscriptionResult(
            text=text,
            timestamp=datetime.now().isoformat(),
            audio_duration=audio_info["duration_seconds"],
            method=method,
        )

    def start_streaming(self) -> None:
        """Initialize streaming mode."""
        self.current_text = ""

    def stop_streaming(self) -> None:
        """Clean up streaming resources."""
        self.current_text = ""

    def process_stream_chunk(
        self, chunk: np.ndarray, is_final: bool = False
    ) -> StreamingTranscriptionResult:
        """Process a chunk of audio data and return partial transcription.

        Args:
            chunk: numpy array of audio samples (float32, mono, 16kHz)
            is_final: whether this is the final chunk

        Returns:
            StreamingTranscriptionResult with partial transcription
        """
        try:
            # Transcribe the chunk
            if self.local_model is not None:
                # For local Whisper, we can use the array directly
                # Convert float32 [-1.0, 1.0] to int16 [-32768, 32767]
                audio_data = (chunk * 32768.0).astype(np.int16)
                segments = self.local_model.transcribe(
                    audio_data.tobytes(),
                    n_processors=1,
                    n_samples=len(chunk),
                )
                text = " ".join([segment.text for segment in segments])
            else:
                # For OpenAI API, we need to create a temporary file
                temp_path = prepare_openai_audio(chunk)
                if temp_path is None:
                    return StreamingTranscriptionResult(
                        text=self.current_text, is_final=is_final
                    )
                try:
                    # Fallback to OpenAI API
                    client = self.get_openai_client()
                    with open(temp_path, "rb") as audio_file:
                        response = client.audio.transcriptions.create(
                            model="whisper-1", file=audio_file
                        )
                        text = response.text
                finally:
                    temp_path.unlink(missing_ok=True)

            # Only append new text if it's not already part of current_text
            if text.strip() and text.strip() not in self.current_text:
                if self.current_text:
                    self.current_text += " " + text.strip()
                else:
                    self.current_text = text.strip()

            return StreamingTranscriptionResult(
                text=self.current_text,
                is_final=is_final,
            )

        except Exception as e:
            print(f"Error processing chunk: {e}")
            return StreamingTranscriptionResult(
                text=self.current_text, is_final=is_final
            )
