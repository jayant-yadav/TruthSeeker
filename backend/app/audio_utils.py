import tempfile
from pathlib import Path
from typing import AsyncIterator, Optional

import numpy as np
from pydub import AudioSegment


async def stream_audio_file(
    file_path: Path,
    chunk_duration_ms: int = 3000,
    overlap_ms: int = 1000,
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

    # Calculate chunk sizes
    chunk_size = int(chunk_duration_ms * audio.frame_rate / 1000)
    overlap_size = int(overlap_ms * audio.frame_rate / 1000)

    # Stream chunks
    current_position = 0
    while current_position < len(audio):
        # Extract chunk with overlap
        chunk_end = min(current_position + chunk_size, len(audio))
        chunk = audio[current_position:chunk_end]

        # Convert to numpy array and normalize
        samples = np.array(chunk.get_array_of_samples()).astype(np.float32) / 32768.0

        yield samples

        # Move to next chunk, considering overlap
        current_position += chunk_size - overlap_size


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
