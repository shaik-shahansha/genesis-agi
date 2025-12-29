"""Roles Plugin - Adds role and purpose management."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.role import RoleManager

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class RolesPlugin(Plugin):
    """Adds role and purpose management."""

    def __init__(self, **config):
        super().__init__(**config)
        self.roles: Optional[RoleManager] = None

    def get_name(self) -> str:
        return "roles"

    def get_version(self) -> str:
        return "1.0.0"

    def on_init(self, mind: "Mind") -> None:
        self.roles = RoleManager()
        mind.roles = self.roles

    def extend_system_prompt(self, mind: "Mind") -> str:
        if not self.roles:
            return ""
        purpose = self.roles.describe_purpose()
        if purpose:
            return f"ROLE & PURPOSE:\n{purpose}"
        return ""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        if not self.roles:
            return {}
        return {"roles": self.roles.model_dump(mode='json')}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        if "roles" in data:
            self.roles = RoleManager(**data["roles"])
            mind.roles = self.roles
