import logging
import time
from datetime import datetime

import numpy as np
from app.transcription.common import (
    BaseTranscriber,
    StreamingTranscriptionResult,
    TranscriptionMethod,
    TranscriptionResult,
)
from app.transcription.utils import prepare_openai_audio
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)


class OpenAIWhisperTranscriber(BaseTranscriber):
    """Transcriber using OpenAI's Whisper API."""

    def __init__(self, model_checkpoint: str):
        super().__init__(model_checkpoint)
        self.openai_client = self._get_openai_client()

    @property
    def method(self) -> TranscriptionMethod:
        return TranscriptionMethod.OPENAI_WHISPER

    def _get_openai_client(self) -> OpenAI:
        """Get or initialize OpenAI client."""
        return OpenAI()

    def transcribe_file(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio file using OpenAI's Whisper API."""
        start_time = time.time()

        with open(audio_path, "rb") as audio_file:
            response = self.openai_client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
            text = response.text

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
        """Process a chunk of audio data using OpenAI's Whisper API."""
        try:
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
                    response = self.openai_client.audio.transcriptions.create(**kwargs)
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
            logger.error(f"Error processing chunk with OpenAI Whisper: {e}")
            # Return last known good state and mark as final due to error
            return StreamingTranscriptionResult(
                text=self.current_text,
                is_final=True,  # Mark as final since we encountered an error
            )
