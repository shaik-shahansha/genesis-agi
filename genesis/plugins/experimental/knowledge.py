"""Knowledge Plugin - EXPERIMENTAL (basic graph only)."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.knowledge import KnowledgeGraph

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class KnowledgePlugin(Plugin):
    """
    Adds knowledge graph system.

    ⚠️ EXPERIMENTAL WARNING:
    - Basic entity-relationship storage only
    - Limited inference (just transitivity)
    - No real graph database (should use Neo4j)
    - No advanced query language

    Use only for:
    - Basic knowledge tracking
    - Simple relationship storage
    - Prototyping knowledge systems

    For REAL knowledge graphs, we need:
    - Neo4j or proper graph DB
    - Advanced inference rules
    - SPARQL or Cypher queries
    - Ontology support
    """

    def __init__(self, **config):
        super().__init__(**config)
        self.knowledge: Optional[KnowledgeGraph] = None

    def get_name(self) -> str:
        return "knowledge"

    def get_version(self) -> str:
        return "0.1.4-experimental"

    def get_description(self) -> str:
        return "⚠️ EXPERIMENTAL: Basic knowledge graph"

    def on_init(self, mind: "Mind") -> None:
        self.knowledge = KnowledgeGraph(mind_gmid=mind.identity.gmid)
        mind.knowledge = self.knowledge

    def extend_system_prompt(self, mind: "Mind") -> str:
        if not self.knowledge:
            return ""

        stats = self.knowledge.get_knowledge_stats()

        return f"""
⚠️ EXPERIMENTAL KNOWLEDGE GRAPH (basic only):
- Entities: {stats.get('total_entities', 0)}
- Relationships: {stats.get('total_relationships', 0)}

Note: Basic knowledge tracking only. Limited reasoning.
"""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        if not self.knowledge:
            return {}
        return {"knowledge": self.knowledge.to_dict()}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        if "knowledge" in data:
            self.knowledge = KnowledgeGraph.from_dict(data["knowledge"])
            mind.knowledge = self.knowledge
