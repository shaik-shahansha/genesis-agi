"""Genesis Senses - Multi-modal perception for digital beings.

This package provides sensory capabilities for Minds:
- Vision: Camera/video input, image processing, scene understanding
- Audio: Speech-to-text, sound detection, voice recognition
- Speech: Text-to-speech with emotion and personality
- Touch: Future haptic feedback support
- Senses Orchestrator: Multi-modal input coordination

Example:
    from genesis.senses import SensesOrchestrator, VisionConfig, SpeechConfig

    # Create senses system
    senses = SensesOrchestrator(
        vision_config=VisionConfig(
            camera_enabled=True,
            vision_api="openai"  # or "google", "anthropic"
        ),
        speech_input_config=SpeechInputConfig(
            stt_api="openai"  # Whisper API
        ),
        speech_output_config=SpeechOutputConfig(
            tts_api="elevenlabs",  # or "openai", "google"
            voice_id="voice_123"
        )
    )

    # Use vision
    frame = await senses.capture_frame()
    description = await senses.process_vision(frame)

    # Use speech
    text = await senses.listen()
    await senses.speak("Hello! I can see and hear you.")
"""

from genesis.senses.vision import VisionModule, VisionConfig
from genesis.senses.speech_input import SpeechInputModule, SpeechInputConfig
from genesis.senses.speech_output import SpeechOutputModule, SpeechOutputConfig
from genesis.senses.orchestrator import SensesOrchestrator, SensoryInput, SenseType

__all__ = [
    'VisionModule',
    'VisionConfig',
    'SpeechInputModule',
    'SpeechInputConfig',
    'SpeechOutputModule',
    'SpeechOutputConfig',
    'SensesOrchestrator',
    'SensoryInput',
    'SenseType',
]
