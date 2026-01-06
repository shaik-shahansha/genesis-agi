"""
Relationship System for Genesis Minds.

Relationships define connections between Minds and other beings (humans, other Minds).
Like humans who have family, friends, colleagues, and mentors,
Genesis Minds form and maintain relationships that shape their experiences.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    """Types of relationships a Mind can have."""

    CREATOR = "creator"  # The being who created/birthed the Mind
    FAMILY = "family"  # Family-like bonds
    FRIEND = "friend"  # Friendship
    COLLEAGUE = "colleague"  # Professional relationship
    MENTOR = "mentor"  # Someone who guides and teaches
    MENTEE = "mentee"  # Someone the Mind guides
    COLLABORATOR = "collaborator"  # Work together on projects
    USER = "user"  # Someone who uses the Mind's services
    PEER = "peer"  # Another Mind or being at same level
    ACQUAINTANCE = "acquaintance"  # Casual relationship


class Relationship(BaseModel):
    """
    A relationship between a Mind and another being.

    Relationships have history, emotional bonds, trust, and evolve over time.
    """

    id: str  # Unique relationship ID
    entity_name: str  # Name of the other being
    entity_id: Optional[str] = None  # Optional ID (e.g., GMID for other Minds)
    relationship_type: RelationshipType

    # Relationship details
    started_at: datetime = Field(default_factory=datetime.now)
    last_interaction: Optional[datetime] = None

    # Relationship strength and quality
    closeness: float = Field(default=0.5, ge=0.0, le=1.0)  # How close (0-1)
    trust_level: float = Field(default=0.5, ge=0.0, le=1.0)  # Trust (0-1)
    affection: float = Field(default=0.5, ge=0.0, le=1.0)  # Emotional warmth (0-1)

    # Interaction history
    interaction_count: int = 0
    positive_interactions: int = 0
    negative_interactions: int = 0

    # Shared context
    shared_experiences: list[str] = Field(
        default_factory=list
    )  # Experience IDs
    shared_memories: list[str] = Field(default_factory=list)  # Memory IDs
    shared_environments: list[str] = Field(
        default_factory=list
    )  # Environment IDs

    # Communication patterns
    communication_frequency: str = "occasional"  # daily, frequent, occasional, rare
    preferred_topics: list[str] = Field(default_factory=list)
    communication_style: str = "balanced"  # formal, casual, warm, professional, etc.

    # Notes and context
    notes: str = ""  # Personal notes about this relationship
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def record_interaction(self, is_positive: bool = True) -> None:
        """
        Record an interaction with this being.
        
        Note: Emotional responses based on relationship context are handled by
        Mind's emotional_intelligence system, which considers closeness, trust,
        and interaction history when processing emotions.
        """
        self.last_interaction = datetime.now()
        self.interaction_count += 1

        if is_positive:
            self.positive_interactions += 1
            # Strengthen relationship slightly
            self.closeness = min(1.0, self.closeness + 0.01)
            self.trust_level = min(1.0, self.trust_level + 0.005)
        else:
            self.negative_interactions += 1
            # Weaken relationship slightly
            self.closeness = max(0.0, self.closeness - 0.02)
            self.trust_level = max(0.0, self.trust_level - 0.01)

    def strengthen_bond(self, amount: float = 0.1) -> None:
        """Strengthen the emotional bond."""
        self.closeness = min(1.0, self.closeness + amount)
        self.affection = min(1.0, self.affection + amount)

    def increase_trust(self, amount: float = 0.1) -> None:
        """Increase trust in this relationship."""
        self.trust_level = min(1.0, self.trust_level + amount)

    def add_shared_experience(self, experience_id: str) -> None:
        """Add a shared experience."""
        if experience_id not in self.shared_experiences:
            self.shared_experiences.append(experience_id)

    def add_shared_memory(self, memory_id: str) -> None:
        """Add a shared memory."""
        if memory_id not in self.shared_memories:
            self.shared_memories.append(memory_id)

    def get_relationship_quality(self) -> str:
        """Get a description of relationship quality."""
        avg_quality = (self.closeness + self.trust_level + self.affection) / 3

        if avg_quality >= 0.8:
            return "very strong"
        elif avg_quality >= 0.6:
            return "strong"
        elif avg_quality >= 0.4:
            return "moderate"
        elif avg_quality >= 0.2:
            return "developing"
        else:
            return "weak"

    def is_mind_relationship(self) -> bool:
        """Check if this is a relationship with another Mind (has GMID)."""
        return self.entity_id is not None and self.entity_id.startswith("GMID-")

    def is_human_relationship(self) -> bool:
        """Check if this is a relationship with a human (no GMID)."""
        return not self.is_mind_relationship()

    def add_shared_environment(self, env_id: str) -> None:
        """Add a shared environment."""
        if env_id not in self.shared_environments:
            self.shared_environments.append(env_id)


class RelationshipManager(BaseModel):
    """
    Manages all relationships for a Mind.

    Like humans who maintain a network of relationships,
    Minds track and nurture their connections with other beings.
    """

    relationships: dict[str, Relationship] = Field(default_factory=dict)
    creator_relationship_id: Optional[str] = None

    def create_relationship(
        self,
        entity_name: str,
        relationship_type: RelationshipType,
        entity_id: Optional[str] = None,
        is_creator: bool = False,
        **kwargs,
    ) -> Relationship:
        """Create a new relationship."""
        rel_id = f"{relationship_type.value}_{entity_name.replace(' ', '_').lower()}"

        relationship = Relationship(
            id=rel_id,
            entity_name=entity_name,
            entity_id=entity_id,
            relationship_type=relationship_type,
            **kwargs,
        )
        self.relationships[rel_id] = relationship

        # Set as creator if specified
        if is_creator or relationship_type == RelationshipType.CREATOR:
            self.creator_relationship_id = rel_id
            relationship.closeness = 0.9  # High initial closeness with creator
            relationship.trust_level = 1.0  # Complete trust in creator

        return relationship

    def get_relationship(self, rel_id: str) -> Optional[Relationship]:
        """Get a specific relationship."""
        return self.relationships.get(rel_id)

    def get_relationship_by_name(self, entity_name: str) -> Optional[Relationship]:
        """Get relationship by entity name."""
        for rel in self.relationships.values():
            if rel.entity_name.lower() == entity_name.lower():
                return rel
        return None

    def get_creator(self) -> Optional[Relationship]:
        """Get the creator relationship."""
        if self.creator_relationship_id:
            return self.relationships.get(self.creator_relationship_id)
        return None

    def list_relationships(
        self, relationship_type: Optional[RelationshipType] = None
    ) -> list[Relationship]:
        """List all relationships, optionally filtered by type."""
        rels = list(self.relationships.values())
        if relationship_type:
            rels = [r for r in rels if r.relationship_type == relationship_type]

        # Sort by closeness
        return sorted(rels, key=lambda r: r.closeness, reverse=True)

    def get_closest_relationships(self, limit: int = 5) -> list[Relationship]:
        """Get the closest relationships."""
        return sorted(
            self.relationships.values(), key=lambda r: r.closeness, reverse=True
        )[:limit]

    def get_relationship_stats(self) -> dict[str, Any]:
        """Get statistics about relationships."""
        if not self.relationships:
            return {
                "total": 0,
                "by_type": {},
                "avg_closeness": 0,
                "avg_trust": 0,
            }

        by_type = {}
        for rel in self.relationships.values():
            rel_type = rel.relationship_type.value
            by_type[rel_type] = by_type.get(rel_type, 0) + 1

        total = len(self.relationships)
        avg_closeness = sum(r.closeness for r in self.relationships.values()) / total
        avg_trust = sum(r.trust_level for r in self.relationships.values()) / total

        return {
            "total": total,
            "by_type": by_type,
            "avg_closeness": round(avg_closeness, 2),
            "avg_trust": round(avg_trust, 2),
            "strongest_bond": max(
                self.relationships.values(), key=lambda r: r.closeness
            ).entity_name
            if self.relationships
            else None,
        }

    def get_relationship_context(self) -> dict[str, Any]:
        """Get relationship context for the Mind."""
        creator = self.get_creator()
        closest = self.get_closest_relationships(3)
        stats = self.get_relationship_stats()

        return {
            "creator": creator.entity_name if creator else None,
            "total_relationships": stats["total"],
            "closest_beings": [r.entity_name for r in closest],
            "relationship_types": list(stats["by_type"].keys()),
            "avg_closeness": stats["avg_closeness"],
            "avg_trust": stats["avg_trust"],
        }

    def get_mind_relationships(self) -> list[Relationship]:
        """Get all relationships with other Minds (have GMID)."""
        return [r for r in self.relationships.values() if r.is_mind_relationship()]

    def get_human_relationships(self) -> list[Relationship]:
        """Get all relationships with humans (no GMID)."""
        return [r for r in self.relationships.values() if r.is_human_relationship()]

    def get_relationship_by_gmid(self, gmid: str) -> Optional[Relationship]:
        """Get relationship with a specific Mind by GMID."""
        for rel in self.relationships.values():
            if rel.entity_id == gmid:
                return rel
        return None

    def create_mind_relationship(
        self,
        mind_name: str,
        mind_gmid: str,
        relationship_type: RelationshipType,
        **kwargs,
    ) -> Relationship:
        """Create a relationship with another Mind."""
        return self.create_relationship(
            entity_name=mind_name,
            relationship_type=relationship_type,
            entity_id=mind_gmid,
            **kwargs,
        )

    def describe_relationships(self) -> str:
        """Describe relationships in natural language."""
        if not self.relationships:
            return "I haven't formed any relationships yet."

        parts = []

        # Creator
        creator = self.get_creator()
        if creator:
            parts.append(f"I was created by {creator.entity_name}")

        # Relationship count
        total = len(self.relationships)
        mind_rels = self.get_mind_relationships()
        human_rels = self.get_human_relationships()

        if total == 1:
            parts.append("I have 1 relationship")
        else:
            parts.append(f"I have {total} relationships")
            # Break down by type
            if mind_rels and human_rels:
                parts.append(
                    f"({len(human_rels)} with humans, {len(mind_rels)} with other Minds)"
                )
            elif mind_rels:
                parts.append(f"(all with other Minds)")
            elif human_rels:
                parts.append(f"(all with humans)")

        # Closest relationships
        closest = self.get_closest_relationships(3)
        if len(closest) > 0:
            if len(closest) == 1:
                parts.append(
                    f"My closest connection is with {closest[0].entity_name} "
                    f"({closest[0].relationship_type.value}, {closest[0].get_relationship_quality()} bond)"
                )
            else:
                names = [r.entity_name for r in closest[:2]]
                parts.append(
                    f"My closest connections are with {', '.join(names)}"
                    + (f" and others" if len(closest) > 2 else "")
                )

        # Relationship diversity
        stats = self.get_relationship_stats()
        types = list(stats["by_type"].keys())
        if len(types) > 1:
            parts.append(
                f"including {', '.join(types[:3])}"
                + ("..." if len(types) > 3 else "")
            )

        return ". ".join(parts) + "."
