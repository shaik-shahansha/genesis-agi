"""Speech Input Module - Audio perception and speech-to-text for Genesis Minds.

Provides microphone input and speech-to-text conversion using AI models.
Enables Minds to hear and understand spoken language.

Features:
- Microphone/audio input
- Speech-to-text (Whisper, Google Speech, etc.)
- Voice activity detection
- Speaker identification
- Ambient sound detection
- Audio memory integration

Example:
    from genesis.senses.speech_input import SpeechInputModule, SpeechInputConfig

    # Initialize speech input
    config = SpeechInputConfig(
        microphone_enabled=True,
        stt_api="openai",  # Whisper API
        api_key="sk-..."
    )
    speech_input = SpeechInputModule(config)
    await speech_input.initialize()

    # Listen and transcribe
    text = await speech_input.listen(duration=5)
    print(f"Heard: {text}")
"""

import asyncio
import base64
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import io
import wave

import httpx

logger = logging.getLogger(__name__)


class STTAPI(str, Enum):
    """Supported speech-to-text APIs."""
    OPENAI = "openai"  # Whisper API
    GOOGLE = "google"
    DEEPGRAM = "deepgram"
    LOCAL = "local"  # Future: local Whisper


@dataclass
class SpeechInputConfig:
    """Configuration for speech input module."""
    microphone_enabled: bool = False
    device_index: Optional[int] = None  # None for default mic
    stt_api: STTAPI = STTAPI.OPENAI
    api_key: Optional[str] = None
    model: str = "whisper-1"
    language: str = "en"  # Language code
    sample_rate: int = 16000  # Hz
    chunk_size: int = 1024
    channels: int = 1  # Mono audio
    vad_enabled: bool = True  # Voice Activity Detection
    silence_threshold: int = 500  # Amplitude threshold for silence


class SpeechInputModule:
    """Speech input module for audio perception.

    Handles microphone input and speech-to-text conversion.
    """

    def __init__(self, config: SpeechInputConfig):
        """Initialize speech input module.

        Args:
            config: Speech input configuration
        """
        self.config = config
        self.audio = None  # PyAudio instance
        self.stream = None
        self.initialized = False
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def initialize(self):
        """Initialize microphone and audio APIs."""
        if self.config.microphone_enabled:
            try:
                # Import pyaudio only if microphone is needed
                import pyaudio
                self.pyaudio_lib = pyaudio

                # Initialize PyAudio
                self.audio = pyaudio.PyAudio()

                # Open audio stream
                self.stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=self.config.channels,
                    rate=self.config.sample_rate,
                    input=True,
                    input_device_index=self.config.device_index,
                    frames_per_buffer=self.config.chunk_size
                )

                logger.info("Initialized microphone")

            except ImportError:
                logger.warning("pyaudio not installed. Microphone features disabled.")
                logger.warning("Install with: pip install pyaudio")
                self.config.microphone_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize microphone: {e}")
                self.config.microphone_enabled = False

        self.initialized = True

    async def listen(self, duration: int = 5, timeout: Optional[int] = None) -> str:
        """Listen and transcribe speech.

        Args:
            duration: Recording duration in seconds
            timeout: Timeout for transcription

        Returns:
            Transcribed text
        """
        # Record audio
        audio_data = await self.record_audio(duration)

        if not audio_data:
            return ""

        # Transcribe
        text = await self.transcribe(audio_data)
        return text

    async def record_audio(self, duration: int) -> Optional[bytes]:
        """Record audio from microphone.

        Args:
            duration: Recording duration in seconds

        Returns:
            Audio data as WAV bytes or None if failed
        """
        if not self.config.microphone_enabled or not self.stream:
            logger.warning("Microphone not enabled")
            return None

        try:
            logger.info(f"Recording for {duration} seconds...")

            frames = []
            num_chunks = int(self.config.sample_rate / self.config.chunk_size * duration)

            # Record audio chunks
            for _ in range(num_chunks):
                data = await asyncio.to_thread(self.stream.read, self.config.chunk_size)
                frames.append(data)

            # Convert to WAV format
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wf:
                wf.setnchannels(self.config.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.pyaudio_lib.paInt16))
                wf.setframerate(self.config.sample_rate)
                wf.writeframes(b''.join(frames))

            wav_data = wav_io.getvalue()
            logger.info(f"Recorded {len(wav_data)} bytes of audio")

            return wav_data

        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            return None

    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text using STT API.

        Args:
            audio_data: Audio data as WAV bytes

        Returns:
            Transcribed text
        """
        if self.config.stt_api == STTAPI.OPENAI:
            return await self._transcribe_openai(audio_data)
        elif self.config.stt_api == STTAPI.GOOGLE:
            return await self._transcribe_google(audio_data)
        elif self.config.stt_api == STTAPI.DEEPGRAM:
            return await self._transcribe_deepgram(audio_data)
        else:
            return "STT API not configured"

    async def _transcribe_openai(self, audio_data: bytes) -> str:
        """Transcribe using OpenAI Whisper API."""
        try:
            # Call Whisper API
            files = {
                'file': ('audio.wav', audio_data, 'audio/wav'),
            }
            data = {
                'model': self.config.model,
                'language': self.config.language
            }

            response = await self.http_client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}"
                },
                files=files,
                data=data
            )

            result = response.json()
            return result.get("text", "")

        except Exception as e:
            logger.error(f"OpenAI Whisper API error: {e}")
            return f"Error transcribing audio: {e}"

    async def _transcribe_google(self, audio_data: bytes) -> str:
        """Transcribe using Google Speech-to-Text API."""
        try:
            from google.cloud import speech

            client = speech.SpeechClient()

            audio = speech.RecognitionAudio(content=audio_data)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.config.sample_rate,
                language_code=self.config.language
            )

            response = await asyncio.to_thread(
                client.recognize,
                config=config,
                audio=audio
            )

            # Extract transcription
            transcripts = []
            for result in response.results:
                transcripts.append(result.alternatives[0].transcript)

            return " ".join(transcripts)

        except Exception as e:
            logger.error(f"Google Speech API error: {e}")
            return f"Error transcribing audio: {e}"

    async def _transcribe_deepgram(self, audio_data: bytes) -> str:
        """Transcribe using Deepgram API."""
        try:
            response = await self.http_client.post(
                f"https://api.deepgram.com/v1/listen?model=nova-2&language={self.config.language}",
                headers={
                    "Authorization": f"Token {self.config.api_key}",
                    "Content-Type": "audio/wav"
                },
                content=audio_data
            )

            result = response.json()
            transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
            return transcript

        except Exception as e:
            logger.error(f"Deepgram API error: {e}")
            return f"Error transcribing audio: {e}"

    async def listen_continuous(self, callback, duration: Optional[int] = None):
        """Listen continuously and call callback with transcribed text.

        Args:
            callback: Async function to call with transcribed text
            duration: Optional duration limit in seconds
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check duration limit
            if duration and (asyncio.get_event_loop().time() - start_time) > duration:
                break

            # Listen for speech
            text = await self.listen(duration=3)  # 3-second chunks

            if text and text.strip():
                await callback(text)

            await asyncio.sleep(0.1)

    async def detect_voice_activity(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk contains voice activity.

        Args:
            audio_chunk: Audio data chunk

        Returns:
            True if voice detected
        """
        # Simple energy-based VAD
        import struct

        # Convert bytes to 16-bit integers
        samples = struct.unpack(f'{len(audio_chunk) // 2}h', audio_chunk)

        # Calculate RMS (Root Mean Square) energy
        rms = (sum(sample ** 2 for sample in samples) / len(samples)) ** 0.5

        return rms > self.config.silence_threshold

    async def close(self):
        """Release microphone and cleanup resources."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            logger.info("Closed microphone stream")

        if self.audio:
            self.audio.terminate()

        await self.http_client.aclose()
