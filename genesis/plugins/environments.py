"""Environments Plugin - Adds metaverse environment support."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.environment import EnvironmentManager

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class EnvironmentsPlugin(Plugin):
    """Adds environment and metaverse context."""

    def __init__(self, **config):
        super().__init__(**config)
        self.environments: Optional[EnvironmentManager] = None

    def get_name(self) -> str:
        return "environments"

    def get_version(self) -> str:
        return "1.0.0"

    def on_init(self, mind: "Mind") -> None:
        self.environments = EnvironmentManager()
        mind.environments = self.environments

    def extend_system_prompt(self, mind: "Mind") -> str:
        if not self.environments:
            return ""
        context = self.environments.describe_current_context()
        if context:
            return f"ENVIRONMENT:\n{context}"
        return ""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        if not self.environments:
            return {}
        return {"environments": self.environments.model_dump(mode='json')}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        if "environments" in data:
            self.environments = EnvironmentManager(**data["environments"])
            mind.environments = self.environments
