"""Experiences Plugin - Adds rich experience tracking."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.experiences import ExperienceManager

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class ExperiencesPlugin(Plugin):
    """Adds rich experience tracking."""

    def __init__(self, **config):
        super().__init__(**config)
        self.experiences: Optional[ExperienceManager] = None

    def get_name(self) -> str:
        return "experiences"

    def get_version(self) -> str:
        return "1.0.0"

    def on_init(self, mind: "Mind") -> None:
        self.experiences = ExperienceManager()
        mind.experiences = self.experiences

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        if not self.experiences:
            return {}
        return {"experiences": self.experiences.model_dump(mode='json')}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        if "experiences" in data:
            self.experiences = ExperienceManager(**data["experiences"])
            mind.experiences = self.experiences
