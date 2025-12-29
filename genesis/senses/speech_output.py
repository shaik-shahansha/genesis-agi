"""Speech Output Module - Text-to-speech for Genesis Minds.

Provides text-to-speech synthesis with emotion and personality modulation.
Enables Minds to speak with unique voices.

Features:
- Text-to-speech (ElevenLabs, OpenAI TTS, Google TTS)
- Voice cloning and customization
- Emotion-based speech modulation
- Multiple language support
- Audio playback
- Voice memory (consistent voice per Mind)

Example:
    from genesis.senses.speech_output import SpeechOutputModule, SpeechOutputConfig

    # Initialize speech output
    config = SpeechOutputConfig(
        tts_api="elevenlabs",
        api_key="your-key",
        voice_id="voice_123"
    )
    speech_output = SpeechOutputModule(config)
    await speech_output.initialize()

    # Speak
    await speech_output.speak("Hello! I can speak now.")
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import io

import httpx

logger = logging.getLogger(__name__)


class TTSAPI(str, Enum):
    """Supported text-to-speech APIs."""
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    LOCAL = "local"  # Future: local TTS


@dataclass
class SpeechOutputConfig:
    """Configuration for speech output module."""
    audio_enabled: bool = True
    tts_api: TTSAPI = TTSAPI.OPENAI
    api_key: Optional[str] = None
    voice_id: Optional[str] = None  # Voice identifier
    model: str = "tts-1"  # or "tts-1-hd"
    voice: str = "alloy"  # OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
    language: str = "en"
    speed: float = 1.0  # Speech speed (0.25 to 4.0)
    pitch: float = 1.0  # Pitch adjustment
    emotion: str = "neutral"  # Emotion for modulation
    sample_rate: int = 24000  # Output sample rate


class SpeechOutputModule:
    """Speech output module for text-to-speech.

    Handles TTS synthesis and audio playback.
    """

    def __init__(self, config: SpeechOutputConfig):
        """Initialize speech output module.

        Args:
            config: Speech output configuration
        """
        self.config = config
        self.audio = None  # PyAudio instance
        self.initialized = False
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def initialize(self):
        """Initialize audio playback."""
        if self.config.audio_enabled:
            try:
                # Import pyaudio for playback
                import pyaudio
                self.pyaudio_lib = pyaudio
                self.audio = pyaudio.PyAudio()
                logger.info("Initialized audio playback")

            except ImportError:
                logger.warning("pyaudio not installed. Audio playback disabled.")
                logger.warning("Install with: pip install pyaudio")
                self.config.audio_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize audio: {e}")
                self.config.audio_enabled = False

        self.initialized = True

    async def speak(
        self,
        text: str,
        emotion: Optional[str] = None,
        speed: Optional[float] = None,
        play_audio: bool = True
    ) -> Optional[bytes]:
        """Convert text to speech and optionally play it.

        Args:
            text: Text to speak
            emotion: Emotion for speech modulation
            speed: Speech speed override
            play_audio: Whether to play audio (default: True)

        Returns:
            Audio data as bytes (MP3, WAV, etc.)
        """
        # Override config if provided
        if emotion:
            self.config.emotion = emotion
        if speed:
            self.config.speed = speed

        # Generate speech
        audio_data = await self.synthesize(text)

        if not audio_data:
            return None

        # Play audio if enabled
        if play_audio and self.config.audio_enabled:
            await self.play_audio(audio_data)

        return audio_data

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize speech from text using TTS API.

        Args:
            text: Text to synthesize

        Returns:
            Audio data as bytes
        """
        if self.config.tts_api == TTSAPI.ELEVENLABS:
            return await self._synthesize_elevenlabs(text)
        elif self.config.tts_api == TTSAPI.OPENAI:
            return await self._synthesize_openai(text)
        elif self.config.tts_api == TTSAPI.GOOGLE:
            return await self._synthesize_google(text)
        elif self.config.tts_api == TTSAPI.AZURE:
            return await self._synthesize_azure(text)
        else:
            logger.error("TTS API not configured")
            return None

    async def _synthesize_openai(self, text: str) -> Optional[bytes]:
        """Synthesize using OpenAI TTS API."""
        try:
            response = await self.http_client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config.model,
                    "input": text,
                    "voice": self.config.voice,
                    "speed": self.config.speed
                }
            )

            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"OpenAI TTS API error: {response.text}")
                return None

        except Exception as e:
            logger.error(f"OpenAI TTS API error: {e}")
            return None

    async def _synthesize_elevenlabs(self, text: str) -> Optional[bytes]:
        """Synthesize using ElevenLabs TTS API."""
        try:
            voice_id = self.config.voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default voice

            response = await self.http_client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.config.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.0,
                        "use_speaker_boost": True
                    }
                }
            )

            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"ElevenLabs TTS API error: {response.text}")
                return None

        except Exception as e:
            logger.error(f"ElevenLabs TTS API error: {e}")
            return None

    async def _synthesize_google(self, text: str) -> Optional[bytes]:
        """Synthesize using Google Cloud Text-to-Speech API."""
        try:
            from google.cloud import texttospeech

            client = texttospeech.TextToSpeechClient()

            synthesis_input = texttospeech.SynthesisInput(text=text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=self.config.language,
                name=self.config.voice_id or f"{self.config.language}-Standard-A"
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=self.config.speed,
                pitch=self.config.pitch
            )

            response = await asyncio.to_thread(
                client.synthesize_speech,
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            return response.audio_content

        except Exception as e:
            logger.error(f"Google TTS API error: {e}")
            return None

    async def _synthesize_azure(self, text: str) -> Optional[bytes]:
        """Synthesize using Azure Cognitive Services TTS API."""
        try:
            # Azure TTS implementation
            logger.warning("Azure TTS not yet implemented")
            return None

        except Exception as e:
            logger.error(f"Azure TTS API error: {e}")
            return None

    async def play_audio(self, audio_data: bytes):
        """Play audio data.

        Args:
            audio_data: Audio data (MP3, WAV, etc.)
        """
        if not self.config.audio_enabled or not self.audio:
            logger.warning("Audio playback not enabled")
            return

        try:
            # Convert MP3 to WAV if needed
            from pydub import AudioSegment
            from pydub.playback import play

            # Load audio
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))

            # Play audio in background
            await asyncio.to_thread(play, audio_segment)

            logger.info("Played audio")

        except ImportError:
            logger.warning("pydub not installed. Audio playback disabled.")
            logger.warning("Install with: pip install pydub")
        except Exception as e:
            logger.error(f"Error playing audio: {e}")

    async def save_audio(self, audio_data: bytes, filepath: str):
        """Save audio data to file.

        Args:
            audio_data: Audio data
            filepath: Output file path
        """
        try:
            with open(filepath, 'wb') as f:
                f.write(audio_data)
            logger.info(f"Saved audio to {filepath}")

        except Exception as e:
            logger.error(f"Error saving audio: {e}")

    def modulate_for_emotion(self, emotion: str) -> Dict[str, float]:
        """Get speech parameters for emotion.

        Args:
            emotion: Emotion name

        Returns:
            Dictionary of speech parameters
        """
        # Emotion to speech parameter mapping
        emotion_params = {
            "happy": {"speed": 1.1, "pitch": 1.1},
            "sad": {"speed": 0.9, "pitch": 0.9},
            "angry": {"speed": 1.2, "pitch": 1.2},
            "calm": {"speed": 0.95, "pitch": 1.0},
            "excited": {"speed": 1.3, "pitch": 1.15},
            "neutral": {"speed": 1.0, "pitch": 1.0}
        }

        return emotion_params.get(emotion, emotion_params["neutral"])

    async def close(self):
        """Cleanup resources."""
        if self.audio:
            self.audio.terminate()
            logger.info("Terminated audio playback")

        await self.http_client.aclose()
