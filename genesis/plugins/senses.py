"""Senses Plugin - Multi-modal perception for Genesis Minds.

Integrates vision, audio, and speech capabilities into Minds,
enabling them to see, hear, and speak.

Features:
- Camera/video input and scene understanding
- Microphone input and speech recognition
- Text-to-speech output with emotion
- Multi-modal sensory coordination
- Sensory memory integration

Example:
    from genesis.plugins.senses import SensesPlugin
    from genesis.senses import VisionConfig, SpeechInputConfig, SpeechOutputConfig

    # Configure senses
    config = MindConfig()
    config.add_plugin(SensesPlugin(
        vision_config=VisionConfig(
            camera_enabled=True,
            vision_api="openai",
            api_key="sk-..."
        ),
        speech_input_config=SpeechInputConfig(
            microphone_enabled=True,
            stt_api="openai",
            api_key="sk-..."
        ),
        speech_output_config=SpeechOutputConfig(
            tts_api="openai",
            api_key="sk-...",
            voice="alloy"
        )
    ))

    mind = Mind.birth("Maria", config=config)

    # Use senses
    await mind.senses.speak("Hello! I can speak!")
    description = await mind.senses.look_at("Who is in the room?")
    text = await mind.senses.listen_for(duration=5)
"""

import asyncio
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from genesis.plugins.base import Plugin
from genesis.senses import (
    SensesOrchestrator,
    VisionConfig,
    SpeechInputConfig,
    SpeechOutputConfig,
    SenseType
)

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class SensesPlugin(Plugin):
    """Plugin for multi-modal sensory perception.

    Enables Minds to see, hear, and speak through integrated
    vision, audio, and speech modules.
    """

    def __init__(
        self,
        vision_config: Optional[VisionConfig] = None,
        speech_input_config: Optional[SpeechInputConfig] = None,
        speech_output_config: Optional[SpeechOutputConfig] = None,
        auto_activate: bool = True,
        active_senses: Optional[list] = None,
        **config
    ):
        """Initialize senses plugin.

        Args:
            vision_config: Vision module configuration
            speech_input_config: Speech input configuration
            speech_output_config: Speech output configuration
            auto_activate: Auto-activate senses on birth (default: True)
            active_senses: List of senses to activate (default: all enabled)
            **config: Additional plugin configuration
        """
        super().__init__(**config)
        self.vision_config = vision_config
        self.speech_input_config = speech_input_config
        self.speech_output_config = speech_output_config
        self.auto_activate = auto_activate
        self.active_senses = active_senses or []
        self.senses: Optional[SensesOrchestrator] = None

    def get_name(self) -> str:
        return "senses"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Multi-modal sensory perception (vision, audio, speech)"

    def on_init(self, mind: "Mind") -> None:
        """Initialize senses orchestrator."""
        self.senses = SensesOrchestrator(
            vision_config=self.vision_config,
            speech_input_config=self.speech_input_config,
            speech_output_config=self.speech_output_config
        )
        mind.senses = self.senses
        logger.info("Initialized senses orchestrator")

    async def on_birth(self, mind: "Mind") -> None:
        """Initialize senses on birth."""
        if self.senses:
            try:
                await self.senses.initialize()
                logger.info("Senses initialized")

                if self.auto_activate:
                    # Determine which senses to activate
                    senses_to_activate = self.active_senses.copy() if self.active_senses else []

                    if not senses_to_activate:
                        # Auto-detect based on configuration
                        if self.vision_config and self.vision_config.camera_enabled:
                            senses_to_activate.append("vision")
                        if self.speech_input_config and self.speech_input_config.microphone_enabled:
                            senses_to_activate.append("audio")
                        if self.speech_output_config and self.speech_output_config.audio_enabled:
                            senses_to_activate.append("speech")

                    if senses_to_activate:
                        await self.senses.activate_senses(senses_to_activate)
                        logger.info(f"Auto-activated senses: {senses_to_activate}")

            except Exception as e:
                logger.error(f"Failed to initialize senses: {e}")

    async def on_terminate(self, mind: "Mind") -> None:
        """Cleanup senses on termination."""
        if self.senses:
            try:
                await self.senses.close()
                logger.info("Closed senses")
            except Exception as e:
                logger.error(f"Failed to close senses: {e}")

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add senses capabilities to system prompt."""
        if not self.senses:
            return ""

        summary = self.senses.get_sensory_summary()
        active = summary.get("active_senses", [])

        if not active:
            return ""

        sections = [
            "SENSORY CAPABILITIES:",
            f"- Active senses: {', '.join(active)}",
            ""
        ]

        if "vision" in active:
            sections.append("👁 VISION:")
            sections.append("  - You can SEE the environment through camera")
            sections.append("  - Use look_at() to capture and describe scenes")
            sections.append("  - You can recognize objects and faces")
            sections.append("")

        if "audio" in active:
            sections.append("👂 AUDIO:")
            sections.append("  - You can HEAR speech and sounds through microphone")
            sections.append("  - Use listen_for() to capture and transcribe speech")
            sections.append("  - You understand spoken language")
            sections.append("")

        if "speech" in active:
            sections.append("🗣 SPEECH:")
            sections.append("  - You can SPEAK using text-to-speech")
            sections.append("  - Use speak() to communicate verbally")
            sections.append("  - You can express emotions through voice modulation")
            sections.append("")

        sections.append("Use your senses to perceive and interact with the real world.")

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save senses configuration."""
        data = {
            "auto_activate": self.auto_activate,
            "active_senses": self.active_senses
        }

        # Save vision config
        if self.vision_config:
            data["vision_config"] = {
                "camera_enabled": self.vision_config.camera_enabled,
                "camera_index": self.vision_config.camera_index,
                "vision_api": self.vision_config.vision_api.value,
                "model": self.vision_config.model,
                "detail_level": self.vision_config.detail_level,
                "resolution": self.vision_config.resolution
            }

        # Save speech input config
        if self.speech_input_config:
            data["speech_input_config"] = {
                "microphone_enabled": self.speech_input_config.microphone_enabled,
                "device_index": self.speech_input_config.device_index,
                "stt_api": self.speech_input_config.stt_api.value,
                "model": self.speech_input_config.model,
                "language": self.speech_input_config.language
            }

        # Save speech output config
        if self.speech_output_config:
            data["speech_output_config"] = {
                "audio_enabled": self.speech_output_config.audio_enabled,
                "tts_api": self.speech_output_config.tts_api.value,
                "voice_id": self.speech_output_config.voice_id,
                "model": self.speech_output_config.model,
                "voice": self.speech_output_config.voice,
                "language": self.speech_output_config.language,
                "speed": self.speech_output_config.speed
            }

        # Save recent sensory inputs
        if self.senses:
            recent_inputs = self.senses.get_recent_sensory_inputs(limit=20)
            data["recent_sensory_inputs"] = [
                {
                    "sense_type": inp.sense_type.value,
                    "timestamp": inp.timestamp.isoformat(),
                    "processed_data": inp.processed_data,
                    "importance": inp.importance
                }
                for inp in recent_inputs
            ]

        return data

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore senses configuration."""
        if "auto_activate" in data:
            self.auto_activate = data["auto_activate"]

        if "active_senses" in data:
            self.active_senses = data["active_senses"]

        # Restore configurations
        if "vision_config" in data:
            from genesis.senses import VisionAPI
            vc = data["vision_config"]
            self.vision_config = VisionConfig(
                camera_enabled=vc.get("camera_enabled", False),
                camera_index=vc.get("camera_index", 0),
                vision_api=VisionAPI(vc.get("vision_api", "openai")),
                model=vc.get("model", "gpt-4-vision-preview"),
                detail_level=vc.get("detail_level", "high"),
                resolution=tuple(vc.get("resolution", (640, 480)))
            )

        if "speech_input_config" in data:
            from genesis.senses.speech_input import STTAPI
            sic = data["speech_input_config"]
            self.speech_input_config = SpeechInputConfig(
                microphone_enabled=sic.get("microphone_enabled", False),
                device_index=sic.get("device_index"),
                stt_api=STTAPI(sic.get("stt_api", "openai")),
                model=sic.get("model", "whisper-1"),
                language=sic.get("language", "en")
            )

        if "speech_output_config" in data:
            from genesis.senses.speech_output import TTSAPI
            soc = data["speech_output_config"]
            self.speech_output_config = SpeechOutputConfig(
                audio_enabled=soc.get("audio_enabled", True),
                tts_api=TTSAPI(soc.get("tts_api", "openai")),
                voice_id=soc.get("voice_id"),
                model=soc.get("model", "tts-1"),
                voice=soc.get("voice", "alloy"),
                language=soc.get("language", "en"),
                speed=soc.get("speed", 1.0)
            )

        # Reinitialize orchestrator
        self.on_init(mind)

    def get_status(self) -> Dict[str, Any]:
        """Get senses status."""
        status = super().get_status()

        if self.senses:
            summary = self.senses.get_sensory_summary()
            status.update(summary)

        return status
