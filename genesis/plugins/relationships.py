"""Relationships Plugin - Adds connections with humans and other Minds."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.relationships import RelationshipManager

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class RelationshipsPlugin(Plugin):
    """Adds relationship management for connections."""

    def __init__(self, **config):
        super().__init__(**config)
        self.relationships: Optional[RelationshipManager] = None

    def get_name(self) -> str:
        return "relationships"

    def get_version(self) -> str:
        return "1.0.0"

    def on_init(self, mind: "Mind") -> None:
        self.relationships = RelationshipManager()
        mind.relationships = self.relationships

    def extend_system_prompt(self, mind: "Mind") -> str:
        if not self.relationships:
            return ""
        context = self.relationships.describe_relationships()
        if context:
            return f"RELATIONSHIPS:\n{context}"
        return ""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        if not self.relationships:
            return {}
        return {"relationships": self.relationships.model_dump(mode='json')}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        if "relationships" in data:
            self.relationships = RelationshipManager(**data["relationships"])
            mind.relationships = self.relationships
