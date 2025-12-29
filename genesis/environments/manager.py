"""Environment Manager and Templates."""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


class EnvironmentType(str, Enum):
    """Types of environments."""
    CLASSROOM = "classroom"
    OFFICE = "office"
    PARK = "park"
    MEDITATION = "meditation"
    WORKSHOP = "workshop"
    SOCIAL = "social"
    CUSTOM = "custom"


@dataclass
class EnvironmentTemplate:
    """Base template for environments."""
    environment_id: str
    environment_type: EnvironmentType
    name: str
    description: str
    default_state: Dict[str, Any] = field(default_factory=dict)
    max_capacity: int = 100
    public: bool = True


class ClassroomEnvironment(EnvironmentTemplate):
    """Classroom environment template."""
    def __init__(self, environment_id: str, name: str = "Classroom"):
        super().__init__(
            environment_id=environment_id,
            environment_type=EnvironmentType.CLASSROOM,
            name=name,
            description="Interactive classroom for teaching and learning",
            default_state={
                "whiteboard": "",
                "lesson_materials": [],
                "attendance": [],
                "current_topic": ""
            },
            max_capacity=50
        )


class OfficeEnvironment(EnvironmentTemplate):
    """Office environment template."""
    def __init__(self, environment_id: str, name: str = "Office"):
        super().__init__(
            environment_id=environment_id,
            environment_type=EnvironmentType.OFFICE,
            name=name,
            description="Professional workspace for collaboration",
            default_state={
                "meeting_status": "available",
                "shared_documents": [],
                "calendar_events": []
            },
            max_capacity=30
        )


class ParkEnvironment(EnvironmentTemplate):
    """Park environment template."""
    def __init__(self, environment_id: str, name: str = "Peaceful Park"):
        super().__init__(
            environment_id=environment_id,
            environment_type=EnvironmentType.PARK,
            name=name,
            description="Relaxing outdoor space for casual interaction",
            default_state={
                "weather": "sunny",
                "time_of_day": "afternoon",
                "ambient_sound": "birds chirping"
            },
            max_capacity=100
        )


class MeditationEnvironment(EnvironmentTemplate):
    """Meditation environment template."""
    def __init__(self, environment_id: str, name: str = "Meditation Zone"):
        super().__init__(
            environment_id=environment_id,
            environment_type=EnvironmentType.MEDITATION,
            name=name,
            description="Quiet space for mindfulness and reflection",
            default_state={
                "ambient_sound": "gentle music",
                "lighting": "dim",
                "session_active": False
            },
            max_capacity=20,
            public=True
        )


class EnvironmentManager:
    """Manages environment metadata and templates."""

    def __init__(self):
        self.templates: Dict[str, EnvironmentTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self):
        """Register default environment templates."""
        # These are examples - actual instances created on demand
        pass

    def create_from_template(
        self,
        template_type: EnvironmentType,
        environment_id: str,
        name: Optional[str] = None
    ) -> EnvironmentTemplate:
        """Create environment from template.

        Args:
            template_type: Type of environment
            environment_id: Unique environment ID
            name: Optional custom name

        Returns:
            Environment template instance
        """
        if template_type == EnvironmentType.CLASSROOM:
            return ClassroomEnvironment(environment_id, name or "Classroom")
        elif template_type == EnvironmentType.OFFICE:
            return OfficeEnvironment(environment_id, name or "Office")
        elif template_type == EnvironmentType.PARK:
            return ParkEnvironment(environment_id, name or "Park")
        elif template_type == EnvironmentType.MEDITATION:
            return MeditationEnvironment(environment_id, name or "Meditation Zone")
        else:
            return EnvironmentTemplate(
                environment_id=environment_id,
                environment_type=EnvironmentType.CUSTOM,
                name=name or "Custom Environment",
                description="Custom environment"
            )
