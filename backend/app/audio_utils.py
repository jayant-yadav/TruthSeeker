import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

WHISPER_SAMPLE_RATE_HZ = 16000


class AudioBuffer:
    def __init__(self, chunk_size_ms: int, overlap_ms: int, sample_rate: int):
        """Initialize audio buffer for accumulating samples.

        Args:
            chunk_size_ms: Size of each chunk in milliseconds
            overlap_ms: Overlap between consecutive chunks in milliseconds
            sample_rate: Sample rate of the audio (default 16kHz for Whisper)
        """
        self.chunk_size_ms = chunk_size_ms
        self.overlap_ms = min(
            overlap_ms, chunk_size_ms
        )  # Ensure overlap doesn't exceed chunk size
        self.sample_rate = sample_rate
        self.samples_per_chunk = int((chunk_size_ms / 1000) * sample_rate)
        self.overlap_samples = int((self.overlap_ms / 1000) * sample_rate)
        self.buffer: list[float] = []

    def add_samples(self, new_samples: np.ndarray) -> list[np.ndarray]:
        """Add new samples to the buffer and return complete chunks if available.

        Args:
            new_samples: New audio samples to add

        Returns:
            List of complete chunks (if any)
        """
        # Add new samples to buffer
        self.buffer.extend(new_samples.tolist())

        # Extract complete chunks
        complete_chunks = []
        while len(self.buffer) >= self.samples_per_chunk:
            chunk = np.array(self.buffer[: self.samples_per_chunk], dtype=np.float32)
            complete_chunks.append(chunk)
            # Keep the overlapping portion for the next chunk
            self.buffer = self.buffer[self.samples_per_chunk - self.overlap_samples :]

        return complete_chunks

    def get_remaining_samples(self) -> np.ndarray:
        """Get any remaining samples in the buffer and clear it."""
        if not self.buffer:
            return np.array([], dtype=np.float32)

        samples = np.array(self.buffer, dtype=np.float32)
        self.buffer = []
        return samples


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
            wf.setframerate(WHISPER_SAMPLE_RATE_HZ)
            wf.writeframes(audio_data.tobytes())

        return temp_path

    except Exception as e:
        print(f"Error preparing audio for OpenAI: {e}")
        if "temp_path" in locals():
            temp_path.unlink(missing_ok=True)
        return None
