import logging
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from app.transcription.common import (
    BaseTranscriber,
    StreamingTranscriptionResult,
    TranscriptionMethod,
    TranscriptionResult,
)
from pywhispercpp.model import Model as WhisperCppModel

# Configure logging
logger = logging.getLogger(__name__)

WHISPER_CPP_MODEL_PATH = Path("./models/").resolve()


class LocalWhisperTranscriber(BaseTranscriber):
    """Transcriber using local Whisper model via whisper.cpp."""

    def __init__(self, model_checkpoint: str):
        super().__init__(model_checkpoint)
        self.local_model = self._get_whisper_cpp_model(model_checkpoint)

    @property
    def method(self) -> TranscriptionMethod:
        return TranscriptionMethod.LOCAL_WHISPER

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
        model_file = f"ggml-{model_checkpoint}.bin"
        model_path = WHISPER_CPP_MODEL_PATH / model_file

        if not model_path.exists():
            # Create models directory if it doesn't exist
            model_path.parent.mkdir(parents=True, exist_ok=True)
            # Download and convert the model
            self._download_whisper_cpp_model(model_checkpoint)

        logger.info(f"Loading local Whisper model from {model_path}")
        return WhisperCppModel(str(model_path))

    def transcribe_file(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio file using local Whisper model."""
        start_time = time.time()

        segments = self.local_model.transcribe(audio_path, n_processors=1)
        text = " ".join([segment.text for segment in segments])

        time_spent = time.time() - start_time
        logger.info(f"Transcribed text: {text}")
        logger.info(f"Transcription took {time_spent:.2f} seconds")

        return TranscriptionResult(
            text=text,
            timestamp=datetime.now().isoformat(),
            time_spent_sec=time_spent,
            method=self.method,
        )

    def transcribe_chunk(
        self, chunk: np.ndarray, is_final: bool = False
    ) -> StreamingTranscriptionResult:
        """Process a chunk of audio data using local Whisper model."""
        try:
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
            logger.error(f"Error processing chunk with local Whisper: {e}")
            # Return last known good state and mark as final due to error
            return StreamingTranscriptionResult(
                text=self.current_text,
                is_final=True,  # Mark as final since we encountered an error
            )
