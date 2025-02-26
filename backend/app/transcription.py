import os
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

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
    time_spent_sec: float
    method: TranscriptionMethod


@dataclass
class StreamingTranscriptionResult:
    text: str
    is_final: bool


class Transcriber:
    def __init__(
        self,
        method: TranscriptionMethod,
        model_checkpoint,
    ):
        """Initialize transcriber with specified method and model.

        Args:
            method: TranscriptionMethod to use (LOCAL_WHISPER or OPENAI_WHISPER)
            model_checkpoint: Name of the model to use for local Whisper (e.g. 'medium.en')
        """
        self.method = method
        self.model_checkpoint = model_checkpoint
        self.local_model = None
        self.openai_client = None
        self.current_text = ""
        self.last_chunk_text = ""

        # Initialize the appropriate model based on method
        if method == TranscriptionMethod.LOCAL_WHISPER:
            self.local_model = self._get_whisper_cpp_model(model_checkpoint)
        elif method == TranscriptionMethod.OPENAI_WHISPER:
            self.openai_client = self._get_openai_client()

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

    def _get_whisper_cpp_model(self, model_checkpoint: str) -> WhisperCppModel:
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

    def _get_openai_client(self) -> OpenAI:
        """Get or initialize OpenAI client."""
        if self.openai_client is None:
            self.openai_client = OpenAI()
        return self.openai_client

    def transcribe_file(
        self,
        audio_path: str,
    ) -> TranscriptionResult:
        """
        Transcribe audio file using the configured method.

        Args:
            audio_path: Path to audio file
        """
        start_time = time.time()

        if self.method == TranscriptionMethod.LOCAL_WHISPER:
            if self.local_model is None:
                raise RuntimeError("Local Whisper model not initialized")
            segments = self.local_model.transcribe(audio_path, n_processors=1)
            text = " ".join([segment.text for segment in segments])

        elif self.method == TranscriptionMethod.OPENAI_WHISPER:
            if self.openai_client is None:
                raise RuntimeError("OpenAI client not initialized")
            with open(audio_path, "rb") as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file
                )
                text = response.text

        time_spent = time.time() - start_time
        print(f"Transcribed text: {text}")
        print(f"Transcription took {time_spent:.2f} seconds")

        return TranscriptionResult(
            text=text,
            timestamp=datetime.now().isoformat(),
            time_spent_sec=time_spent,
            method=self.method,
        )

    def start_stream(self) -> None:
        """Initialize streaming mode."""
        self.current_text = ""
        self.last_chunk_text = ""

    def stop_stream(self) -> None:
        """Clean up streaming resources."""
        self.current_text = ""
        self.last_chunk_text = ""

    def transcribe_chunk(
        self,
        chunk: np.ndarray,
        is_final: bool = False,
    ) -> StreamingTranscriptionResult:
        """Process a chunk of audio data and return partial transcription.

        Args:
            chunk: numpy array of audio samples (float32, mono, 16kHz)
            is_final: whether this is the final chunk in the stream

        Returns:
            StreamingTranscriptionResult with partial transcription and finality status.
            is_final will be True when:
            1. This is the last chunk in the stream (is_final=True passed in)
            2. A natural sentence break is detected
            3. An error occurred and we're returning the last known good state
        """
        try:
            # Transcribe the chunk
            if self.method == TranscriptionMethod.LOCAL_WHISPER:
                if self.local_model is None:
                    raise RuntimeError("Local Whisper model not initialized")
                # Use last chunk's text as initial prompt if available
                segments = self.local_model.transcribe(
                    chunk,
                    n_processors=1,
                    initial_prompt=self.last_chunk_text,
                    single_segment=True,
                    print_realtime=False,
                    print_progress=False,
                    print_timestamps=False,
                )
                text = " ".join([segment.text for segment in segments])
            else:
                if self.openai_client is None:
                    raise RuntimeError("OpenAI client not initialized")
                # For OpenAI API, we need to create a temporary file
                temp_path = prepare_openai_audio(chunk)
                if temp_path is None:
                    return StreamingTranscriptionResult(
                        text=self.current_text, is_final=is_final
                    )
                try:
                    # Use OpenAI API
                    with open(temp_path, "rb") as audio_file:
                        kwargs = {"model": "whisper-1", "file": audio_file}
                        response = self.openai_client.audio.transcriptions.create(
                            **kwargs
                        )
                        text = response.text
                finally:
                    temp_path.unlink(missing_ok=True)

            # Store this chunk's text for next iteration
            self.last_chunk_text = text.strip()

            # Only append new text if it's not already part of current_text
            if text.strip():
                if self.current_text:
                    self.current_text += " " + text.strip()
                else:
                    self.current_text = text.strip()

            return StreamingTranscriptionResult(
                text=self.current_text, is_final=is_final
            )

        except Exception as e:
            print(f"Error processing chunk: {e}")
            # Return last known good state and mark as final due to error
            return StreamingTranscriptionResult(
                text=self.current_text,
                is_final=True,  # Mark as final since we encountered an error
            )
