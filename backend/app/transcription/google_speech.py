import logging
import os
import queue
import threading
import time
import wave
from datetime import datetime

import numpy as np
from app.transcription.common import (
    BaseTranscriber,
    StreamingTranscriptionResult,
    TranscriptionMethod,
    TranscriptionResult,
)
from google.cloud import speech

# Configure logging
logger = logging.getLogger(__name__)


class GoogleSpeechTranscriber(BaseTranscriber):
    """Transcriber using Google Cloud Speech-to-Text API."""

    def __init__(self, model_checkpoint: str):
        """Initialize the Google Speech transcriber.

        Args:
            model_checkpoint: Name/identifier of the model to use
        """
        super().__init__(model_checkpoint)
        self.language_code = "en-US"
        self.client = self._get_speech_client()
        self.streaming_config = None
        self.is_streaming = False
        self.sample_rate = 16000  # Default sample rate

        # Queue for audio data
        self.audio_queue = queue.Queue()

        # Thread for streaming
        self.streaming_thread = None

        # Latest transcript
        self.interim_result = ""
        self.final_result = ""

    @property
    def method(self) -> TranscriptionMethod:
        """Return the transcription method used by this transcriber."""
        return TranscriptionMethod.GOOGLE_SPEECH

    def _get_speech_client(self):
        """Get or initialize Google Speech client."""
        # Check if GOOGLE_APPLICATION_CREDENTIALS environment variable is set
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            logger.warning(
                "GOOGLE_APPLICATION_CREDENTIALS environment variable is not set"
            )

        # Use environment variable GOOGLE_APPLICATION_CREDENTIALS
        return speech.SpeechClient()

    def transcribe_file(self, audio_path: str) -> TranscriptionResult:
        """Transcribe audio file using Google Cloud Speech-to-Text API."""
        start_time = time.time()

        try:
            # Load audio file
            with wave.open(audio_path, "rb") as wf:
                # Get parameters
                frame_rate = wf.getframerate()
                n_frames = wf.getnframes()
                n_channels = wf.getnchannels()

                # Read frames
                frames = wf.readframes(n_frames)

                # Convert to numpy array
                samples = np.frombuffer(frames, dtype=np.int16)

                # Reshape based on number of channels
                if n_channels > 1:
                    samples = samples.reshape(-1, n_channels)

            if len(samples.shape) > 1:
                # Convert stereo to mono by averaging channels
                samples = samples.mean(axis=1)

            # Convert to int16 (required format for LINEAR16 encoding)
            samples = samples.astype(np.int16)

            # Convert numpy array to bytes
            audio_bytes = samples.tobytes()

            # Configure the request
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=frame_rate,
                language_code=self.language_code,
                enable_automatic_punctuation=True,
                model=self.model_checkpoint
                if self.model_checkpoint != "default"
                else None,
            )

            # Send the request to Google Cloud
            response = self.client.recognize(config=config, audio=audio)

            # Process the response
            results = []
            for result in response.results:
                results.append(result.alternatives[0].transcript)

            text = " ".join(results)

        except Exception as e:
            logger.error(f"Error transcribing with Google Speech: {e}")
            text = ""

        time_spent = time.time() - start_time
        logger.info(f"Transcribed text: {text}")
        logger.info(f"Transcription took {time_spent:.2f} seconds")

        return TranscriptionResult(
            text=text,
            timestamp=datetime.now().isoformat(),
            time_spent_sec=time_spent,
            method=self.method,
        )

    def _audio_generator(self):
        """Generate audio chunks from the queue."""
        while self.is_streaming:
            try:
                # Get audio data from queue with timeout to allow checking is_streaming flag
                chunk = self.audio_queue.get(block=True, timeout=0.5)

                # None is the signal to stop
                if chunk is None:
                    logger.debug("Received None chunk, stopping generator")
                    break

                # Convert numpy array to bytes if needed
                if isinstance(chunk, np.ndarray):
                    # Convert to mono if needed
                    if len(chunk.shape) > 1:
                        chunk = chunk.mean(axis=1)

                    # Ensure int16 format
                    if chunk.dtype != np.int16:
                        chunk = (chunk * 32768.0).astype(np.int16)

                    # Convert to bytes
                    chunk = chunk.tobytes()

                # Yield the chunk for streaming
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

            except queue.Empty:
                # Just continue if queue is empty
                continue
            except Exception as e:
                logger.error(f"Error in audio generator: {e}")
                break

        logger.debug("Audio generator stopped")

    def _streaming_thread_func(self):
        """Function to run in a separate thread for streaming recognition."""
        try:
            logger.info("Starting streaming recognition thread")

            # Create streaming config
            streaming_config = speech.StreamingRecognitionConfig(
                config=speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=self.sample_rate,
                    language_code=self.language_code,
                    enable_automatic_punctuation=True,
                    model=self.model_checkpoint
                    if self.model_checkpoint != "default"
                    else None,
                ),
                interim_results=True,
            )

            # Create audio generator
            audio_generator = self._audio_generator()

            # Start streaming recognition
            responses = self.client.streaming_recognize(
                streaming_config,
                audio_generator,
            )

            # Process responses
            for response in responses:
                if not self.is_streaming:
                    break

                if not response.results:
                    continue

                # The `results` list is consecutive. For streaming, we only care about
                # the first result being considered, since once it's `is_final`, it
                # moves on to considering the next utterance.
                result = response.results[0]
                if not result.alternatives:
                    continue

                # Get transcript
                transcript = result.alternatives[0].transcript

                if result.is_final:
                    # This is a final result
                    logger.debug(f"Final result: {transcript}")
                    if self.final_result:
                        self.final_result += " " + transcript.strip()
                    else:
                        self.final_result = transcript.strip()
                    self.interim_result = ""
                else:
                    # This is an interim result
                    logger.debug(f"Interim result: {transcript}")
                    self.interim_result = transcript.strip()

            logger.info("Streaming recognition completed")

        except Exception as e:
            logger.error(f"Error in streaming thread: {e}")
        finally:
            self.is_streaming = False
            logger.info("Streaming thread exiting")

    def transcribe_chunk(
        self, chunk: np.ndarray, is_final: bool = False
    ) -> StreamingTranscriptionResult:
        """Process a chunk of audio data using Google Speech streaming API.

        This method adds the chunk to the audio queue for processing by the streaming thread.

        Args:
            chunk: Audio data as numpy array
            is_final: Whether this is the final chunk

        Returns:
            StreamingTranscriptionResult with the current transcription
        """
        try:
            if not self.is_streaming:
                logger.warning("Streaming not started. Call start_stream() first.")
                return StreamingTranscriptionResult(
                    text=self.final_result, is_final=is_final
                )

            # Add chunk to queue if not empty and not final
            if len(chunk) > 0 and not is_final:
                self.audio_queue.put(chunk)

            # If this is the final chunk, signal the end of the stream
            if is_final:
                logger.info("Final chunk received, stopping stream")
                self.stop_stream()
                return StreamingTranscriptionResult(
                    text=self.final_result, is_final=True
                )

            # Return the current transcription
            current_text = self.final_result
            if self.interim_result:
                if current_text:
                    current_text += " " + self.interim_result
                else:
                    current_text = self.interim_result

            return StreamingTranscriptionResult(text=current_text, is_final=False)

        except Exception as e:
            logger.error(f"Error processing chunk with Google Speech: {e}")
            # Return last known good state and mark as final due to error
            return StreamingTranscriptionResult(
                text=self.final_result,
                is_final=True,  # Mark as final since we encountered an error
            )

    def start_stream(self) -> None:
        """Start streaming recognition session."""
        try:
            # Don't start if already streaming
            if self.is_streaming:
                logger.warning("Streaming already started")
                return

            # Clear the audio queue
            while not self.audio_queue.empty():
                self.audio_queue.get()

            # Reset results
            self.final_result = ""
            self.interim_result = ""

            # Set streaming flag
            self.is_streaming = True

            # Start streaming thread
            self.streaming_thread = threading.Thread(
                target=self._streaming_thread_func,
                daemon=True,
            )
            self.streaming_thread.start()

            logger.info("Google Speech streaming session started")

        except Exception as e:
            logger.error(f"Error starting Google Speech streaming session: {e}")
            self.is_streaming = False

    def stop_stream(self) -> None:
        """Stop streaming recognition session."""
        try:
            if not self.is_streaming:
                logger.warning("Streaming not started")
                return

            logger.info("Stopping Google Speech streaming session")

            # Set flag to stop the streaming thread
            self.is_streaming = False

            # Put None in the queue to signal the end of the stream
            self.audio_queue.put(None)

            # Wait for the streaming thread to finish (with timeout)
            if self.streaming_thread and self.streaming_thread.is_alive():
                self.streaming_thread.join(timeout=2.0)

            # Clear the audio queue
            while not self.audio_queue.empty():
                self.audio_queue.get()

            logger.info("Google Speech streaming session stopped")

        except Exception as e:
            logger.error(f"Error stopping Google Speech streaming session: {e}")
