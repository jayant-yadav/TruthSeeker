import abc
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import numpy as np
from pydantic import BaseModel
from pydub import AudioSegment

# Configure logging
logger = logging.getLogger(__name__)

WHISPER_CPP_MODEL_PATH = Path("./models/").resolve()


class TranscriptionMethod(str, Enum):
    LOCAL_WHISPER = "local_whisper"
    OPENAI_WHISPER = "openai_whisper"
    GOOGLE_SPEECH = "google_speech"


class TranscriptionResult(BaseModel):
    text: str
    timestamp: str
    time_spent_sec: float
    method: TranscriptionMethod


@dataclass
class StreamingTranscriptionResult:
    text: str
    is_final: bool


class BaseTranscriber(abc.ABC):
    """Abstract base class defining the interface for all transcribers."""

    def __init__(self, model_checkpoint: str):
        """Initialize the transcriber.

        Args:
            model_checkpoint: Name/identifier of the model to use
        """
        self.model_checkpoint = model_checkpoint
        self.current_text = ""
        self.last_chunk_text = ""

    @property
    @abc.abstractmethod
    def method(self) -> TranscriptionMethod:
        """Return the transcription method used by this transcriber."""
        pass

    @abc.abstractmethod
    def transcribe_file(self, audio_path: str) -> TranscriptionResult:
        """Transcribe an audio file.

        Args:
            audio_path: Path to the audio file

        Returns:
            TranscriptionResult with the transcribed text and metadata
        """
        pass

    @abc.abstractmethod
    def transcribe_chunk(
        self, chunk: np.ndarray, is_final: bool = False
    ) -> StreamingTranscriptionResult:
        """Process a chunk of audio data and return partial transcription.

        Args:
            chunk: numpy array of audio samples (float32, mono, 16kHz)
            is_final: whether this is the final chunk in the stream

        Returns:
            StreamingTranscriptionResult with partial transcription and finality status
        """
        pass

    def start_stream(self) -> None:
        """Initialize streaming mode."""
        self.current_text = ""
        self.last_chunk_text = ""

    def stop_stream(self) -> None:
        """Clean up streaming resources."""
        self.current_text = ""
        self.last_chunk_text = ""

    def _get_audio_info(self, audio_path: str) -> dict:
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
