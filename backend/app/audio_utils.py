import asyncio
import tempfile
import time
from pathlib import Path
from typing import AsyncIterator, Optional

import numpy as np
from pydub import AudioSegment


async def stream_audio_file(
    file_path: Path,
    chunk_duration_ms: int,
    overlap_ms: int,
) -> AsyncIterator[np.ndarray]:
    """Stream an audio file in chunks with overlap.

    Args:
        file_path: Path to audio file
        chunk_duration_ms: Duration of each chunk in milliseconds
        overlap_ms: Overlap between chunks in milliseconds

    Yields:
        Numpy array of audio samples (float32, mono, 16kHz)
    """
    audio: AudioSegment = AudioSegment.from_file(file_path)

    # Convert to mono 16kHz if needed
    if audio.channels > 1:
        audio = audio.set_channels(1)
    if audio.frame_rate != 16000:
        audio = audio.set_frame_rate(16000)

    # Stream chunks
    current_position_ms = 0
    duration_ms = len(audio)  # AudioSegment.len returns duration in milliseconds

    while current_position_ms < duration_ms:
        # Extract chunk with overlap using milliseconds
        chunk_end_ms = min(current_position_ms + chunk_duration_ms, duration_ms)
        chunk = audio[current_position_ms:chunk_end_ms]

        # Convert to numpy array and normalize
        samples = np.array(chunk.get_array_of_samples()).astype(np.float32) / 32768.0

        yield samples

        # Move to next chunk, considering overlap
        current_position_ms += chunk_duration_ms - overlap_ms


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


async def stream_audio_file_realtime(
    file_path: Path,
    chunk_duration_ms: int,
) -> AsyncIterator[np.ndarray]:
    """Stream an audio file in chunks at real-time playback speed.
    Chunks are aligned with audio playback time and buffered appropriately.

    Args:
        file_path: Path to audio file
        chunk_duration_ms: Duration of each chunk in milliseconds

    Yields:
        Numpy array of audio samples (float32, mono, 16kHz)
    """
    audio: AudioSegment = AudioSegment.from_file(file_path)

    # Convert to mono 16kHz if needed
    if audio.channels > 1:
        audio = audio.set_channels(1)
    if audio.frame_rate != 16000:
        audio = audio.set_frame_rate(16000)

    # Initialize buffer
    buffer = AudioBuffer(chunk_duration_ms)

    # Calculate small chunks for streaming (e.g., 100ms)
    stream_chunk_ms = 100  # Stream in small chunks for better real-time behavior
    current_position_ms = 0
    duration_ms = len(audio)
    start_time = time.time()

    while current_position_ms < duration_ms:
        # Calculate the elapsed time and wait if needed
        elapsed_ms = (time.time() - start_time) * 1000
        if elapsed_ms < current_position_ms:
            await asyncio.sleep((current_position_ms - elapsed_ms) / 1000)

        # Extract small chunk for streaming
        chunk_end_ms = min(current_position_ms + stream_chunk_ms, duration_ms)
        chunk = audio[current_position_ms:chunk_end_ms]

        # Convert to numpy array and normalize
        samples = np.array(chunk.get_array_of_samples()).astype(np.float32) / 32768.0

        # Check if this is the last chunk
        is_last_chunk = chunk_end_ms == duration_ms

        # Add to buffer and get complete chunks
        complete_chunks = buffer.add_samples(samples, is_end=is_last_chunk)

        # Yield complete chunks
        for chunk in complete_chunks:
            yield chunk

        # Move to next streaming chunk
        current_position_ms += stream_chunk_ms

    # Yield any remaining samples in the buffer if they form a complete chunk
    if len(buffer.buffer) >= buffer.samples_per_chunk:
        yield buffer.buffer[: buffer.samples_per_chunk]


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
