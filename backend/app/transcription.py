import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel
from pydub import AudioSegment
from pywhispercpp.model import Model as WhisperCppModel

WHISPER_CPP_MODEL_PATH = "./data/models/"


class TranscriptionMethod(str, Enum):
    LOCAL_WHISPER = "local_whisper"
    OPENAI_WHISPER = "openai_whisper"


class TranscriptionResult(BaseModel):
    text: str
    timestamp: str
    audio_duration: float
    method: TranscriptionMethod


class Transcriber:
    def __init__(self):
        self.local_model: Optional[WhisperCppModel] = None
        self.openai_client: Optional[OpenAI] = None

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

    def _get_whisper_cpp_model_path(self, model_size: str) -> str:
        """Convert model size to corresponding model file path."""
        model_file = f"ggml-{model_size}.bin"
        model_path = Path(WHISPER_CPP_MODEL_PATH) / model_file
        return str(model_path)

    def get_whisper_cpp_model(self, model_size: str = "medium.en") -> WhisperCppModel:
        """Get or initialize local Whisper model."""
        if self.local_model is None:
            model_path = self._get_whisper_cpp_model_path(model_size)
            self.local_model = WhisperCppModel(model_path)
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
        model_size: str = "medium.en",
    ) -> TranscriptionResult:
        """
        Transcribe audio using specified method.

        Args:
            audio_path: Path to audio file
            method: TranscriptionMethod to use
            model_size: Size of local model (only used for LOCAL_WHISPER)
        """
        if method == TranscriptionMethod.LOCAL_WHISPER:
            model = self.get_whisper_cpp_model(model_size)
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
            raise ValueError(f"Unsupported transcription method: {method}")

        print(f"Transcribed text: {text}")

        audio_info = self._get_audio_info(audio_path)
        return TranscriptionResult(
            text=text,
            timestamp=datetime.now().isoformat(),
            audio_duration=audio_info["duration_seconds"],
            method=method,
        )
