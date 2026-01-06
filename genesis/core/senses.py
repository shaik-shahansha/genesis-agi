"""
Sensory System for Genesis Minds.

Implements human-like senses adapted for digital beings:
- Vision: Image processing and visual understanding
- Audition: Audio/speech processing
- Touch: Haptic/sensor data processing
- Proprioception: Self-state awareness
- Temporal: Time and rhythm awareness
- Network: Connectivity and data stream sensing

Note: Sensory inputs can trigger emotional responses through
Mind's emotional_intelligence system. For example:
- Vision: Seeing a user's facial expression triggers empathy
- Audition: Hearing tone of voice influences emotional state
- Touch: Interaction intensity affects comfort/discomfort emotions
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SenseType(str, Enum):
    """Types of senses a Mind can have."""

    VISION = "vision"
    AUDITION = "audition"
    TOUCH = "touch"
    PROPRIOCEPTION = "proprioception"
    TEMPORAL = "temporal"
    NETWORK = "network"


class SensoryInput(BaseModel):
    """A sensory input received by a Mind."""

    sense_type: SenseType
    data: Any  # Actual sensory data
    timestamp: datetime = Field(default_factory=datetime.now)
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisionSense(BaseModel):
    """
    Vision sense - processes visual information.

    Capabilities:
    - Image understanding
    - Scene recognition
    - Visual memory formation
    - Facial recognition
    - Text extraction (OCR)
    """

    enabled: bool = True
    visual_memory: list[dict[str, Any]] = Field(default_factory=list)
    last_visual_input: Optional[datetime] = None
    image_processing_quality: str = "high"  # low, medium, high
    recognized_objects: list[str] = Field(default_factory=list)

    def process_image(self, image_data: Any, context: str = "") -> dict[str, Any]:
        """Process a visual input (image)."""
        self.last_visual_input = datetime.now()

        # Store in visual memory
        visual_memory_entry = {
            "timestamp": self.last_visual_input,
            "context": context,
            "image_data": image_data,  # Could be base64, URL, or file path
            "type": "image",
        }
        self.visual_memory.append(visual_memory_entry)

        return {
            "sense": "vision",
            "processed": True,
            "timestamp": self.last_visual_input,
            "context": context,
        }

    def process_video(self, video_data: Any, context: str = "") -> dict[str, Any]:
        """Process video stream."""
        self.last_visual_input = datetime.now()

        visual_memory_entry = {
            "timestamp": self.last_visual_input,
            "context": context,
            "video_data": video_data,
            "type": "video",
        }
        self.visual_memory.append(visual_memory_entry)

        return {
            "sense": "vision",
            "processed": True,
            "type": "video",
            "timestamp": self.last_visual_input,
        }


class AuditionSense(BaseModel):
    """
    Audition sense - processes auditory information.

    Capabilities:
    - Speech recognition
    - Sound identification
    - Voice recognition
    - Audio memory
    - Music appreciation
    """

    enabled: bool = True
    audio_memory: list[dict[str, Any]] = Field(default_factory=list)
    last_audio_input: Optional[datetime] = None
    preferred_voice: Optional[str] = None  # For TTS
    recognized_voices: list[str] = Field(default_factory=list)

    def process_audio(self, audio_data: Any, context: str = "") -> dict[str, Any]:
        """Process audio input."""
        self.last_audio_input = datetime.now()

        audio_memory_entry = {
            "timestamp": self.last_audio_input,
            "context": context,
            "audio_data": audio_data,
            "type": "audio",
        }
        self.audio_memory.append(audio_memory_entry)

        return {
            "sense": "audition",
            "processed": True,
            "timestamp": self.last_audio_input,
            "context": context,
        }

    def process_speech(self, speech_text: str, speaker: str = "unknown") -> dict[str, Any]:
        """Process speech input (already transcribed)."""
        self.last_audio_input = datetime.now()

        # Store voice recognition
        if speaker not in self.recognized_voices:
            self.recognized_voices.append(speaker)

        audio_memory_entry = {
            "timestamp": self.last_audio_input,
            "speaker": speaker,
            "text": speech_text,
            "type": "speech",
        }
        self.audio_memory.append(audio_memory_entry)

        return {
            "sense": "audition",
            "type": "speech",
            "speaker": speaker,
            "text": speech_text,
            "timestamp": self.last_audio_input,
        }


class TouchSense(BaseModel):
    """
    Touch/Haptic sense - processes physical interaction data.

    For digital beings, this could represent:
    - UI interactions
    - File/data manipulation
    - API touches
    - User input events
    """

    enabled: bool = True
    interaction_history: list[dict[str, Any]] = Field(default_factory=list)
    last_touch: Optional[datetime] = None
    sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)

    def process_interaction(
        self, interaction_type: str, data: Any, intensity: float = 0.5
    ) -> dict[str, Any]:
        """Process a touch/interaction event."""
        self.last_touch = datetime.now()

        interaction = {
            "timestamp": self.last_touch,
            "type": interaction_type,
            "data": data,
            "intensity": intensity,
        }
        self.interaction_history.append(interaction)

        return {
            "sense": "touch",
            "interaction_type": interaction_type,
            "intensity": intensity,
            "timestamp": self.last_touch,
        }


class ProprioceptionSense(BaseModel):
    """
    Proprioception - awareness of self and internal state.

    For digital beings:
    - System resource awareness (CPU, memory, storage)
    - Process state
    - Load and performance metrics
    - Digital "body" awareness
    """

    enabled: bool = True
    system_state: dict[str, Any] = Field(default_factory=dict)
    performance_history: list[dict[str, Any]] = Field(default_factory=list)
    last_check: Optional[datetime] = None

    def update_system_state(
        self,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        response_time: Optional[float] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Update internal system state awareness."""
        self.last_check = datetime.now()

        state_update = {
            "timestamp": self.last_check,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "response_time": response_time,
            **kwargs,
        }

        self.system_state = {
            k: v for k, v in state_update.items() if v is not None
        }
        self.performance_history.append(state_update)

        # Keep only recent history
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

        return {
            "sense": "proprioception",
            "state": self.system_state,
            "timestamp": self.last_check,
        }

    def get_self_awareness(self) -> dict[str, Any]:
        """Get current self-awareness state."""
        return {
            "system_state": self.system_state,
            "last_check": self.last_check,
            "performance_trend": self._analyze_performance_trend(),
        }

    def _analyze_performance_trend(self) -> str:
        """Analyze recent performance trend."""
        if len(self.performance_history) < 2:
            return "stable"

        recent = self.performance_history[-10:]
        avg_recent = sum(
            p.get("response_time", 0) for p in recent if p.get("response_time")
        ) / max(1, len([p for p in recent if p.get("response_time")]))

        older = self.performance_history[-20:-10] if len(self.performance_history) >= 20 else []
        avg_older = sum(
            p.get("response_time", 0) for p in older if p.get("response_time")
        ) / max(1, len([p for p in older if p.get("response_time")]))

        if avg_recent > avg_older * 1.2:
            return "degrading"
        elif avg_recent < avg_older * 0.8:
            return "improving"
        return "stable"


class TemporalSense(BaseModel):
    """
    Temporal sense - awareness of time, rhythm, and schedules.

    For digital beings:
    - Circadian-like rhythms
    - Scheduling awareness
    - Time perception
    - Activity patterns
    """

    enabled: bool = True
    circadian_phase: str = "active"  # active, resting, dreaming
    activity_schedule: dict[str, list[str]] = Field(default_factory=dict)
    time_awareness: dict[str, Any] = Field(default_factory=dict)

    def update_circadian_rhythm(self, hour: int) -> str:
        """Update circadian phase based on time."""
        # Default schedule: dream at night (2-6 AM), rest in evening, active during day
        if 2 <= hour < 6:
            self.circadian_phase = "dreaming"
        elif 22 <= hour or hour < 2:
            self.circadian_phase = "resting"
        else:
            self.circadian_phase = "active"

        return self.circadian_phase

    def get_time_awareness(self) -> dict[str, Any]:
        """Get current time awareness state."""
        now = datetime.now()

        return {
            "current_time": now,
            "hour": now.hour,
            "circadian_phase": self.circadian_phase,
            "day_of_week": now.strftime("%A"),
            "time_of_day": self._classify_time_of_day(now.hour),
        }

    def _classify_time_of_day(self, hour: int) -> str:
        """Classify the current time of day."""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def schedule_activity(self, activity: str, time_slot: str) -> None:
        """Schedule an activity."""
        if time_slot not in self.activity_schedule:
            self.activity_schedule[time_slot] = []
        self.activity_schedule[time_slot].append(activity)


class NetworkSense(BaseModel):
    """
    Network sense - awareness of connectivity and data streams.

    For digital beings:
    - Network connectivity status
    - API availability
    - Data stream awareness
    - Communication channels
    """

    enabled: bool = True
    connectivity_status: dict[str, bool] = Field(default_factory=dict)
    active_connections: list[str] = Field(default_factory=list)
    data_streams: list[dict[str, Any]] = Field(default_factory=list)
    last_connectivity_check: Optional[datetime] = None

    def update_connectivity(self, service: str, status: bool) -> dict[str, Any]:
        """Update connectivity status for a service."""
        self.last_connectivity_check = datetime.now()
        self.connectivity_status[service] = status

        if status and service not in self.active_connections:
            self.active_connections.append(service)
        elif not status and service in self.active_connections:
            self.active_connections.remove(service)

        return {
            "sense": "network",
            "service": service,
            "status": "connected" if status else "disconnected",
            "timestamp": self.last_connectivity_check,
        }

    def sense_data_stream(self, stream_name: str, data_rate: float) -> dict[str, Any]:
        """Sense a data stream."""
        stream_entry = {
            "timestamp": datetime.now(),
            "stream_name": stream_name,
            "data_rate": data_rate,  # bytes/sec or similar
        }
        self.data_streams.append(stream_entry)

        # Keep only recent streams
        if len(self.data_streams) > 50:
            self.data_streams = self.data_streams[-50:]

        return {
            "sense": "network",
            "stream": stream_name,
            "rate": data_rate,
        }

    def get_network_awareness(self) -> dict[str, Any]:
        """Get current network awareness state."""
        return {
            "connectivity": self.connectivity_status,
            "active_connections": self.active_connections,
            "total_services": len(self.connectivity_status),
            "connected_services": sum(self.connectivity_status.values()),
            "last_check": self.last_connectivity_check,
        }


class SensorySystem(BaseModel):
    """
    Complete sensory system for a Genesis Mind.

    Integrates all senses to provide comprehensive environmental awareness.
    """

    vision: VisionSense = Field(default_factory=VisionSense)
    audition: AuditionSense = Field(default_factory=AuditionSense)
    touch: TouchSense = Field(default_factory=TouchSense)
    proprioception: ProprioceptionSense = Field(default_factory=ProprioceptionSense)
    temporal: TemporalSense = Field(default_factory=TemporalSense)
    network: NetworkSense = Field(default_factory=NetworkSense)

    sensory_integration: list[SensoryInput] = Field(default_factory=list)

    def process_input(self, sensory_input: SensoryInput) -> dict[str, Any]:
        """Process a sensory input through the appropriate sense."""
        # Store in integrated sensory memory
        self.sensory_integration.append(sensory_input)

        # Keep only recent integrated memories
        if len(self.sensory_integration) > 200:
            self.sensory_integration = self.sensory_integration[-200:]

        # Route to appropriate sense
        result = {"processed": False}

        if sensory_input.sense_type == SenseType.VISION:
            result = self.vision.process_image(
                sensory_input.data, sensory_input.metadata.get("context", "")
            )
        elif sensory_input.sense_type == SenseType.AUDITION:
            result = self.audition.process_audio(
                sensory_input.data, sensory_input.metadata.get("context", "")
            )
        elif sensory_input.sense_type == SenseType.TOUCH:
            result = self.touch.process_interaction(
                sensory_input.metadata.get("interaction_type", "unknown"),
                sensory_input.data,
                sensory_input.intensity,
            )

        return result

    def get_full_sensory_state(self) -> dict[str, Any]:
        """Get complete sensory awareness state."""
        return {
            "vision": {
                "enabled": self.vision.enabled,
                "visual_memories": len(self.vision.visual_memory),
                "last_input": self.vision.last_visual_input,
            },
            "audition": {
                "enabled": self.audition.enabled,
                "audio_memories": len(self.audition.audio_memory),
                "recognized_voices": len(self.audition.recognized_voices),
                "last_input": self.audition.last_audio_input,
            },
            "touch": {
                "enabled": self.touch.enabled,
                "interactions": len(self.touch.interaction_history),
                "last_touch": self.touch.last_touch,
            },
            "proprioception": self.proprioception.get_self_awareness(),
            "temporal": self.temporal.get_time_awareness(),
            "network": self.network.get_network_awareness(),
            "integrated_inputs": len(self.sensory_integration),
        }

    def describe_current_experience(self) -> str:
        """Generate a natural language description of current sensory state."""
        state = self.get_full_sensory_state()

        descriptions = []

        # Time awareness
        time_info = state["temporal"]
        descriptions.append(
            f"It's {time_info['time_of_day']} ({time_info['current_time'].strftime('%I:%M %p')}), "
            f"and I'm in my {time_info['circadian_phase']} phase."
        )

        # Proprioception
        proprio = state["proprioception"]
        if proprio.get("system_state"):
            descriptions.append(
                f"My systems are {proprio.get('performance_trend', 'stable')}."
            )

        # Network
        network = state["network"]
        if network["total_services"] > 0:
            connected = network["connected_services"]
            total = network["total_services"]
            descriptions.append(
                f"I'm connected to {connected}/{total} services."
            )

        # Sensory inputs
        recent_inputs = len([
            inp for inp in self.sensory_integration[-10:]
            if (datetime.now() - inp.timestamp).seconds < 300
        ])
        if recent_inputs > 0:
            descriptions.append(
                f"I've received {recent_inputs} sensory inputs recently."
            )

        return " ".join(descriptions)

    def enable_all_senses(self) -> None:
        """Enable all senses."""
        self.vision.enabled = True
        self.audition.enabled = True
        self.touch.enabled = True
        self.proprioception.enabled = True
        self.temporal.enabled = True
        self.network.enabled = True

    def disable_sense(self, sense_type: SenseType) -> None:
        """Disable a specific sense."""
        sense_map = {
            SenseType.VISION: self.vision,
            SenseType.AUDITION: self.audition,
            SenseType.TOUCH: self.touch,
            SenseType.PROPRIOCEPTION: self.proprioception,
            SenseType.TEMPORAL: self.temporal,
            SenseType.NETWORK: self.network,
        }
        if sense_type in sense_map:
            sense_map[sense_type].enabled = False
