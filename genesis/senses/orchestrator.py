"""Senses Orchestrator - Multi-modal sensory coordination for Genesis Minds.

Coordinates all sensory inputs (vision, audio, speech) and provides unified interface
for multi-modal perception. Manages sensory attention, prioritization, and memory integration.

Features:
- Multi-modal input coordination
- Sensory attention mechanism
- Priority-based processing
- Sensory memory integration
- Context-aware sensory activation

Example:
    from genesis.senses import (
        SensesOrchestrator,
        VisionConfig,
        SpeechInputConfig,
        SpeechOutputConfig
    )

    # Create orchestrator
    senses = SensesOrchestrator(
        vision_config=VisionConfig(camera_enabled=True),
        speech_input_config=SpeechInputConfig(microphone_enabled=True),
        speech_output_config=SpeechOutputConfig()
    )

    await senses.initialize()

    # Multi-modal perception
    await senses.activate_senses(['vision', 'audio'])
    await senses.speak("I can see and hear now!")

    # Process sensory input
    perception = await senses.perceive(duration=5)
    print(f"Saw: {perception['vision']}")
    print(f"Heard: {perception['audio']}")
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from genesis.senses.vision import VisionModule, VisionConfig
from genesis.senses.speech_input import SpeechInputModule, SpeechInputConfig
from genesis.senses.speech_output import SpeechOutputModule, SpeechOutputConfig

logger = logging.getLogger(__name__)


class SenseType(str, Enum):
    """Types of senses."""
    VISION = "vision"
    AUDIO = "audio"
    SPEECH = "speech"
    TOUCH = "touch"  # Future
    SMELL = "smell"  # Future


@dataclass
class SensoryInput:
    """Represents a sensory input."""
    sense_type: SenseType
    timestamp: datetime
    data: Any
    processed_data: Optional[str] = None
    importance: float = 0.5  # 0.0 to 1.0
    context: Dict[str, Any] = field(default_factory=dict)


class SensesOrchestrator:
    """Orchestrator for multi-modal sensory perception.

    Coordinates vision, audio, and speech modules for unified perception.
    """

    def __init__(
        self,
        vision_config: Optional[VisionConfig] = None,
        speech_input_config: Optional[SpeechInputConfig] = None,
        speech_output_config: Optional[SpeechOutputConfig] = None
    ):
        """Initialize senses orchestrator.

        Args:
            vision_config: Vision module configuration
            speech_input_config: Speech input configuration
            speech_output_config: Speech output configuration
        """
        self.vision = VisionModule(vision_config) if vision_config else None
        self.speech_input = SpeechInputModule(speech_input_config) if speech_input_config else None
        self.speech_output = SpeechOutputModule(speech_output_config) if speech_output_config else None

        self.active_senses: List[SenseType] = []
        self.sensory_buffer: List[SensoryInput] = []
        self.max_buffer_size = 100

    async def initialize(self):
        """Initialize all sensory modules."""
        if self.vision:
            await self.vision.initialize()
            logger.info("Vision module initialized")

        if self.speech_input:
            await self.speech_input.initialize()
            logger.info("Speech input module initialized")

        if self.speech_output:
            await self.speech_output.initialize()
            logger.info("Speech output module initialized")

    async def activate_senses(self, senses: List[str]):
        """Activate specific senses.

        Args:
            senses: List of sense names to activate
        """
        self.active_senses = [SenseType(sense) for sense in senses]
        logger.info(f"Activated senses: {senses}")

    async def deactivate_senses(self, senses: List[str]):
        """Deactivate specific senses.

        Args:
            senses: List of sense names to deactivate
        """
        for sense in senses:
            sense_type = SenseType(sense)
            if sense_type in self.active_senses:
                self.active_senses.remove(sense_type)
        logger.info(f"Deactivated senses: {senses}")

    async def perceive(self, duration: int = 5) -> Dict[str, Any]:
        """Perceive environment using active senses.

        Args:
            duration: Perception duration in seconds

        Returns:
            Dictionary of sensory perceptions
        """
        perceptions = {}

        tasks = []

        # Collect sensory inputs concurrently
        if SenseType.VISION in self.active_senses and self.vision:
            tasks.append(self._perceive_vision())

        if SenseType.AUDIO in self.active_senses and self.speech_input:
            tasks.append(self._perceive_audio(duration))

        # Execute all perception tasks
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, dict):
                    perceptions.update(result)
                elif isinstance(result, Exception):
                    logger.error(f"Perception error: {result}")

        return perceptions

    async def _perceive_vision(self) -> Dict[str, Any]:
        """Perceive through vision.

        Returns:
            Vision perception data
        """
        if not self.vision:
            return {}

        try:
            # Capture frame
            frame = await self.vision.capture_frame()

            if frame:
                # Describe scene
                description = await self.vision.describe_scene(frame)

                # Store sensory input
                sensory_input = SensoryInput(
                    sense_type=SenseType.VISION,
                    timestamp=datetime.now(),
                    data=frame,
                    processed_data=description,
                    importance=0.7
                )
                self._add_to_buffer(sensory_input)

                return {
                    "vision": description,
                    "vision_raw": frame
                }

        except Exception as e:
            logger.error(f"Vision perception error: {e}")

        return {}

    async def _perceive_audio(self, duration: int) -> Dict[str, Any]:
        """Perceive through audio.

        Args:
            duration: Recording duration

        Returns:
            Audio perception data
        """
        if not self.speech_input:
            return {}

        try:
            # Listen and transcribe
            text = await self.speech_input.listen(duration=duration)

            if text and text.strip():
                # Store sensory input
                sensory_input = SensoryInput(
                    sense_type=SenseType.AUDIO,
                    timestamp=datetime.now(),
                    data=text,
                    processed_data=text,
                    importance=0.8  # Speech is important
                )
                self._add_to_buffer(sensory_input)

                return {
                    "audio": text
                }

        except Exception as e:
            logger.error(f"Audio perception error: {e}")

        return {}

    async def speak(
        self,
        text: str,
        emotion: Optional[str] = None,
        speed: Optional[float] = None
    ) -> bool:
        """Speak text using speech output.

        Args:
            text: Text to speak
            emotion: Emotion for speech
            speed: Speech speed

        Returns:
            True if successful
        """
        if not self.speech_output:
            logger.warning("Speech output not available")
            return False

        try:
            await self.speech_output.speak(text, emotion=emotion, speed=speed)
            logger.info(f"Spoke: {text[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Speech output error: {e}")
            return False

    async def look_at(self, prompt: str) -> str:
        """Look at environment with specific focus.

        Args:
            prompt: What to look for

        Returns:
            Visual description
        """
        if not self.vision:
            return "Vision not available"

        try:
            frame = await self.vision.capture_frame()
            if frame:
                description = await self.vision.describe_scene(frame, prompt)
                return description

        except Exception as e:
            logger.error(f"Look at error: {e}")

        return "Could not see"

    async def listen_for(self, duration: int = 5) -> str:
        """Listen for speech.

        Args:
            duration: Listening duration

        Returns:
            Transcribed text
        """
        if not self.speech_input:
            return ""

        try:
            text = await self.speech_input.listen(duration=duration)
            return text

        except Exception as e:
            logger.error(f"Listen error: {e}")

        return ""

    def _add_to_buffer(self, sensory_input: SensoryInput):
        """Add sensory input to buffer.

        Args:
            sensory_input: Sensory input to add
        """
        self.sensory_buffer.append(sensory_input)

        # Maintain buffer size
        if len(self.sensory_buffer) > self.max_buffer_size:
            # Remove oldest, least important inputs
            self.sensory_buffer.sort(key=lambda x: (x.timestamp, x.importance))
            self.sensory_buffer = self.sensory_buffer[-self.max_buffer_size:]

    def get_recent_sensory_inputs(
        self,
        sense_type: Optional[SenseType] = None,
        limit: int = 10
    ) -> List[SensoryInput]:
        """Get recent sensory inputs.

        Args:
            sense_type: Filter by sense type
            limit: Maximum number of inputs

        Returns:
            List of recent sensory inputs
        """
        inputs = self.sensory_buffer

        if sense_type:
            inputs = [inp for inp in inputs if inp.sense_type == sense_type]

        # Sort by timestamp (most recent first)
        inputs.sort(key=lambda x: x.timestamp, reverse=True)

        return inputs[:limit]

    def get_sensory_summary(self) -> Dict[str, Any]:
        """Get summary of recent sensory inputs.

        Returns:
            Summary dictionary
        """
        summary = {
            "total_inputs": len(self.sensory_buffer),
            "active_senses": [sense.value for sense in self.active_senses],
            "by_sense": {}
        }

        # Count by sense type
        for sense_type in SenseType:
            count = len([inp for inp in self.sensory_buffer if inp.sense_type == sense_type])
            if count > 0:
                summary["by_sense"][sense_type.value] = count

        return summary

    async def close(self):
        """Cleanup all sensory modules."""
        if self.vision:
            await self.vision.close()

        if self.speech_input:
            await self.speech_input.close()

        if self.speech_output:
            await self.speech_output.close()

        logger.info("Closed all sensory modules")
