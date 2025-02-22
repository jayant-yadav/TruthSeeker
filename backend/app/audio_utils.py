import tempfile
from pathlib import Path
from typing import Optional

import numpy as np


class AudioBuffer:
    def __init__(self, chunk_size_ms: int, sample_rate: int = 16000):
        """Initialize audio buffer for real-time processing.

        Args:
            chunk_size_ms: Size of chunks to process in milliseconds
            sample_rate: Audio sample rate (Hz)
        """
        self.chunk_size_ms = chunk_size_ms
        self.sample_rate = sample_rate
        self.samples_per_chunk = int(sample_rate * chunk_size_ms / 1000)
        self.buffer = np.array([], dtype=np.float32)

    def add_samples(
        self, samples: np.ndarray, is_end: bool = False
    ) -> list[np.ndarray]:
        """Add samples to buffer and return complete chunks if available.

        Args:
            samples: New audio samples to add
            is_end: Whether this is the last batch of samples

        Returns:
            List of complete chunks ready for processing
        """
        # Add new samples to buffer
        self.buffer = np.concatenate([self.buffer, samples])

        # Extract complete chunks
        complete_chunks = []
        while len(self.buffer) >= self.samples_per_chunk:
            chunk = self.buffer[: self.samples_per_chunk]
            complete_chunks.append(chunk)
            self.buffer = self.buffer[self.samples_per_chunk :]

        # If this is the end of the stream and we have remaining samples,
        # pad the last chunk with zeros to reach the desired chunk size
        if is_end and len(self.buffer) > 0:
            padding_size = self.samples_per_chunk - len(self.buffer)
            padded_chunk = np.pad(self.buffer, (0, padding_size), mode="constant")
            complete_chunks.append(padded_chunk)
            self.buffer = np.array([], dtype=np.float32)

        return complete_chunks


def prepare_openai_audio(samples: np.ndarray) -> Optional[Path]:
    """Convert audio samples to a temporary WAV file for OpenAI API.

    Args:
        samples: Numpy array of audio samples (float32, mono, 16kHz)

    Returns:
        Path to temporary WAV file, or None if conversion failed
    """
    try:
        # Convert float32 samples to int16
        audio_data = (samples * 32768.0).astype(np.int16)

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = Path(temp_file.name)

        # Save as WAV
        import wave

        with wave.open(str(temp_path), "wb") as wf:
            wf.setnchannels(1)  # mono
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(16000)  # whisper expects 16kHz
            wf.writeframes(audio_data.tobytes())

        return temp_path

    except Exception as e:
        print(f"Error preparing audio for OpenAI: {e}")
        if "temp_path" in locals():
            temp_path.unlink(missing_ok=True)
        return None
