"""Learning Plugin - EXPERIMENTAL (superficial implementation)."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.learning import LearningSystem

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class LearningPlugin(Plugin):
    """
    Adds learning and skill acquisition system.

    ⚠️ EXPERIMENTAL WARNING:
    - Skills are just numbers, not actual capability improvements
    - Proficiency doesn't affect LLM performance
    - No fine-tuning or RAG updates
    - This is TRACKING, not real learning

    Use only for:
    - Simulation and tracking
    - Prototyping learning systems
    - Understanding future learning architecture

    For REAL learning, we need:
    - Fine-tuning integration
    - RAG knowledge updates
    - Skill-aware prompt engineering
    - Performance-based validation
    """

    def __init__(self, **config):
        super().__init__(**config)
        self.learning: Optional[LearningSystem] = None

    def get_name(self) -> str:
        return "learning"

    def get_version(self) -> str:
        return "0.1.3-experimental"

    def get_description(self) -> str:
        return "⚠️ EXPERIMENTAL: Skill tracking (not real learning)"

    def on_init(self, mind: "Mind") -> None:
        self.learning = LearningSystem(mind_gmid=mind.identity.gmid)
        mind.learning = self.learning

    def extend_system_prompt(self, mind: "Mind") -> str:
        if not self.learning:
            return ""

        stats = self.learning.get_learning_stats()

        return f"""
⚠️ EXPERIMENTAL SKILLS (tracking only):
- Skills learned: {stats.get('total_skills', 0)}
- Average proficiency: {stats.get('average_proficiency', 0):.2f}

Note: Skill levels are tracked but don't affect actual capabilities yet.
"""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        if not self.learning:
            return {}
        return {"learning": self.learning.to_dict()}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        if "learning" in data:
            self.learning = LearningSystem.from_dict(data["learning"])
            mind.learning = self.learning
