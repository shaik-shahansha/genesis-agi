"""Knowledge Graph System for Genesis Minds.

Enables Minds to:
- Build structured knowledge representations
- Store entities, relationships, and properties
- Query knowledge efficiently
- Infer new knowledge from existing facts
- Share knowledge with other Minds
- Visualize knowledge structures
"""

import secrets
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Set, Tuple
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Types of entities in knowledge graph."""

    CONCEPT = "concept"  # Abstract concept
    OBJECT = "object"  # Physical or digital object
    PERSON = "person"  # Human or Mind
    EVENT = "event"  # Happening or occurrence
    SKILL = "skill"  # Capability or skill
    DOMAIN = "domain"  # Knowledge domain
    TOOL = "tool"  # Tool or resource
    FACT = "fact"  # Factual statement


class RelationType(str, Enum):
    """Types of relationships between entities."""

    IS_A = "is_a"  # Inheritance (Python is_a ProgrammingLanguage)
    PART_OF = "part_of"  # Composition (NumPy part_of Python_ecosystem)
    HAS_PROPERTY = "has_property"  # Property (Python has_property dynamic_typing)
    RELATED_TO = "related_to"  # General relation
    ENABLES = "enables"  # Causation (Python enables web_development)
    REQUIRES = "requires"  # Dependency (Django requires Python)
    SIMILAR_TO = "similar_to"  # Similarity
    OPPOSITE_OF = "opposite_of"  # Opposition
    CREATED_BY = "created_by"  # Creation
    USED_IN = "used_in"  # Application


class Entity(BaseModel):
    """An entity in the knowledge graph."""

    entity_id: str = Field(default_factory=lambda: f"ENT-{secrets.token_hex(6).upper()}")

    # Entity definition
    name: str
    entity_type: EntityType
    description: Optional[str] = None

    # Properties
    properties: Dict[str, Any] = Field(default_factory=dict)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    confidence: float = 1.0  # How confident we are in this entity's existence (0.0-1.0)

    # Source tracking
    learned_from: Optional[str] = None  # Task, experience, or Mind that provided this
    evidence_count: int = 1  # How many times we've seen this entity

    # Connections
    outgoing_relations: int = 0  # Count of relationships where this is subject
    incoming_relations: int = 0  # Count of relationships where this is object

    # Tags for categorization
    tags: List[str] = Field(default_factory=list)

    def add_property(self, key: str, value: Any) -> None:
        """Add or update a property."""
        self.properties[key] = value
        self.updated_at = datetime.now()

    def increase_evidence(self) -> int:
        """Increase evidence count (saw entity again)."""
        self.evidence_count += 1
        # Increase confidence (but cap at 1.0)
        self.confidence = min(1.0, self.confidence + 0.05)
        return self.evidence_count


class Relationship(BaseModel):
    """A relationship between two entities."""

    relation_id: str = Field(default_factory=lambda: f"REL-{secrets.token_hex(6).upper()}")

    # Relationship definition
    subject_id: str  # Entity ID (subject)
    relation_type: RelationType
    object_id: str  # Entity ID (object)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    confidence: float = 1.0  # Confidence in this relationship (0.0-1.0)
    strength: float = 1.0  # Strength of relationship (0.0-1.0)

    # Source tracking
    learned_from: Optional[str] = None
    evidence_count: int = 1

    # Properties of the relationship itself
    properties: Dict[str, Any] = Field(default_factory=dict)

    def increase_evidence(self) -> int:
        """Increase evidence count."""
        self.evidence_count += 1
        self.confidence = min(1.0, self.confidence + 0.05)
        self.strength = min(1.0, self.strength + 0.02)
        return self.evidence_count


class KnowledgeQuery(BaseModel):
    """A query to the knowledge graph."""

    query_type: str  # "find_entity", "find_path", "find_related", "infer"
    parameters: Dict[str, Any]
    results: List[Any] = Field(default_factory=list)
    executed_at: datetime = Field(default_factory=datetime.now)


class KnowledgeGraph:
    """
    Knowledge graph system for a Mind.

    Stores and queries structured knowledge about the world.
    """

    def __init__(self, mind_gmid: str):
        """Initialize knowledge graph for a Mind."""
        self.mind_gmid = mind_gmid

        # Core graph storage
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}

        # Indexes for fast lookup
        self._entity_name_index: Dict[str, str] = {}  # name -> entity_id
        self._type_index: Dict[EntityType, List[str]] = {}  # type -> [entity_ids]
        self._relation_index: Dict[str, List[str]] = {}  # entity_id -> [relation_ids]

        # Statistics
        self.total_inferences: int = 0
        self.knowledge_confidence: float = 0.0  # Overall knowledge quality

    def add_entity(
        self,
        name: str,
        entity_type: EntityType,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        learned_from: Optional[str] = None
    ) -> Entity:
        """Add a new entity to the knowledge graph."""
        # Check if entity already exists
        existing_id = self._entity_name_index.get(name.lower())
        if existing_id:
            # Entity exists, increase evidence
            entity = self.entities[existing_id]
            entity.increase_evidence()

            # Update properties if provided
            if properties:
                for key, value in properties.items():
                    entity.add_property(key, value)

            return entity

        # Create new entity
        entity = Entity(
            name=name,
            entity_type=entity_type,
            description=description,
            properties=properties or {},
            learned_from=learned_from
        )

        # Store entity
        self.entities[entity.entity_id] = entity
        self._entity_name_index[name.lower()] = entity.entity_id

        # Update type index
        if entity_type not in self._type_index:
            self._type_index[entity_type] = []
        self._type_index[entity_type].append(entity.entity_id)

        # Update relation index
        self._relation_index[entity.entity_id] = []

        return entity

    def add_relationship(
        self,
        subject: str,  # Entity name or ID
        relation_type: RelationType,
        object: str,  # Entity name or ID
        properties: Optional[Dict[str, Any]] = None,
        learned_from: Optional[str] = None
    ) -> Relationship:
        """Add a relationship between two entities."""
        # Resolve entity IDs
        subject_id = self._resolve_entity_id(subject)
        object_id = self._resolve_entity_id(object)

        if not subject_id or not object_id:
            raise ValueError(f"Could not find entities: {subject}, {object}")

        # Check if relationship already exists
        for rel_id in self._relation_index.get(subject_id, []):
            rel = self.relationships[rel_id]
            if (rel.subject_id == subject_id and
                rel.relation_type == relation_type and
                rel.object_id == object_id):
                # Relationship exists, increase evidence
                rel.increase_evidence()
                return rel

        # Create new relationship
        relationship = Relationship(
            subject_id=subject_id,
            relation_type=relation_type,
            object_id=object_id,
            properties=properties or {},
            learned_from=learned_from
        )

        # Store relationship
        self.relationships[relationship.relation_id] = relationship

        # Update relation indexes
        if subject_id not in self._relation_index:
            self._relation_index[subject_id] = []
        self._relation_index[subject_id].append(relationship.relation_id)

        # Update entity connection counts
        self.entities[subject_id].outgoing_relations += 1
        self.entities[object_id].incoming_relations += 1

        return relationship

    def _resolve_entity_id(self, name_or_id: str) -> Optional[str]:
        """Resolve entity name or ID to entity ID."""
        # Check if it's already an ID
        if name_or_id in self.entities:
            return name_or_id

        # Look up by name
        return self._entity_name_index.get(name_or_id.lower())

    def find_entity(
        self,
        name: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> List[Entity]:
        """Find entities matching criteria."""
        results = []

        # Start with all entities or filter by type
        if entity_type:
            candidate_ids = self._type_index.get(entity_type, [])
            candidates = [self.entities[eid] for eid in candidate_ids]
        else:
            candidates = list(self.entities.values())

        # Filter by name
        if name:
            candidates = [e for e in candidates if name.lower() in e.name.lower()]

        # Filter by properties
        if properties:
            for key, value in properties.items():
                candidates = [
                    e for e in candidates
                    if key in e.properties and e.properties[key] == value
                ]

        return candidates

    def find_related(
        self,
        entity: str,  # Name or ID
        relation_type: Optional[RelationType] = None,
        direction: str = "outgoing"  # "outgoing", "incoming", or "both"
    ) -> List[Tuple[Entity, Relationship, Entity]]:
        """Find entities related to the given entity."""
        entity_id = self._resolve_entity_id(entity)
        if not entity_id:
            return []

        results = []

        # Find outgoing relationships
        if direction in ["outgoing", "both"]:
            for rel_id in self._relation_index.get(entity_id, []):
                rel = self.relationships[rel_id]

                # Filter by relation type
                if relation_type and rel.relation_type != relation_type:
                    continue

                subject = self.entities[rel.subject_id]
                object = self.entities[rel.object_id]
                results.append((subject, rel, object))

        # Find incoming relationships
        if direction in ["incoming", "both"]:
            for rel in self.relationships.values():
                if rel.object_id == entity_id:
                    # Filter by relation type
                    if relation_type and rel.relation_type != relation_type:
                        continue

                    subject = self.entities[rel.subject_id]
                    object = self.entities[rel.object_id]
                    results.append((subject, rel, object))

        return results

    def find_path(
        self,
        start_entity: str,
        end_entity: str,
        max_depth: int = 5
    ) -> Optional[List[Tuple[Entity, Relationship]]]:
        """Find path between two entities using BFS."""
        start_id = self._resolve_entity_id(start_entity)
        end_id = self._resolve_entity_id(end_entity)

        if not start_id or not end_id:
            return None

        # BFS to find shortest path
        queue = [(start_id, [])]  # (entity_id, path)
        visited = set()

        while queue:
            current_id, path = queue.pop(0)

            if current_id == end_id:
                # Found path!
                return path

            if current_id in visited or len(path) >= max_depth:
                continue

            visited.add(current_id)

            # Explore neighbors
            for rel_id in self._relation_index.get(current_id, []):
                rel = self.relationships[rel_id]
                neighbor_id = rel.object_id

                if neighbor_id not in visited:
                    new_path = path + [(self.entities[neighbor_id], rel)]
                    queue.append((neighbor_id, new_path))

        return None  # No path found

    def infer_knowledge(self) -> List[Relationship]:
        """
        Infer new relationships based on existing knowledge.

        Implements basic inference rules:
        - Transitivity: If A is_a B and B is_a C, then A is_a C
        - Composition: If A part_of B and B part_of C, then A part_of C
        """
        inferred = []

        # Transitivity for IS_A relationships
        for rel1 in self.relationships.values():
            if rel1.relation_type == RelationType.IS_A:
                # Find entities where object is subject of another IS_A
                for rel2 in self.relationships.values():
                    if (rel2.relation_type == RelationType.IS_A and
                        rel1.object_id == rel2.subject_id):

                        # Can infer: rel1.subject IS_A rel2.object
                        # Check if this relationship already exists
                        exists = any(
                            r.subject_id == rel1.subject_id and
                            r.relation_type == RelationType.IS_A and
                            r.object_id == rel2.object_id
                            for r in self.relationships.values()
                        )

                        if not exists:
                            # Infer new relationship
                            new_rel = Relationship(
                                subject_id=rel1.subject_id,
                                relation_type=RelationType.IS_A,
                                object_id=rel2.object_id,
                                confidence=min(rel1.confidence, rel2.confidence) * 0.9,
                                learned_from="inference"
                            )
                            inferred.append(new_rel)

                            # Add to graph
                            self.relationships[new_rel.relation_id] = new_rel
                            self._relation_index[rel1.subject_id].append(new_rel.relation_id)

                            self.total_inferences += 1

        return inferred

    def query(
        self,
        query_text: str
    ) -> Dict[str, Any]:
        """
        Natural language query (simplified).

        Example queries:
        - "What is Python?"
        - "What properties does Python have?"
        - "What is related to machine learning?"
        - "How is Python related to NumPy?"
        """
        query_lower = query_text.lower()

        # Pattern matching for common query types
        if "what is" in query_lower or "what are" in query_lower:
            # Entity definition query
            entity_name = query_lower.split("what is ")[-1].split("what are ")[-1].strip("?")
            entities = self.find_entity(name=entity_name)

            if entities:
                entity = entities[0]
                return {
                    "query": query_text,
                    "answer": entity.description or f"{entity.name} is a {entity.entity_type.value}",
                    "entity": entity.name,
                    "properties": entity.properties,
                    "related_count": entity.outgoing_relations + entity.incoming_relations
                }

        elif "related to" in query_lower:
            # Relationship query
            entity_name = query_lower.split("related to ")[-1].strip("?")
            related = self.find_related(entity_name, direction="both")

            return {
                "query": query_text,
                "entity": entity_name,
                "related_entities": [
                    {
                        "name": obj.name if subj.entity_id == self._resolve_entity_id(entity_name) else subj.name,
                        "relation": rel.relation_type.value
                    }
                    for subj, rel, obj in related
                ],
                "count": len(related)
            }

        return {
            "query": query_text,
            "error": "Could not understand query"
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        type_distribution = {}
        for entity_type in EntityType:
            type_distribution[entity_type.value] = len(
                self._type_index.get(entity_type, [])
            )

        relation_distribution = {}
        for rel_type in RelationType:
            relation_distribution[rel_type.value] = len([
                r for r in self.relationships.values()
                if r.relation_type == rel_type
            ])

        # Calculate average confidence
        avg_entity_confidence = (
            sum(e.confidence for e in self.entities.values()) / len(self.entities)
            if self.entities else 0.0
        )

        avg_relation_confidence = (
            sum(r.confidence for r in self.relationships.values()) / len(self.relationships)
            if self.relationships else 0.0
        )

        return {
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
            "total_inferences": self.total_inferences,
            "entity_type_distribution": type_distribution,
            "relation_type_distribution": relation_distribution,
            "average_entity_confidence": round(avg_entity_confidence, 2),
            "average_relation_confidence": round(avg_relation_confidence, 2),
            "most_connected_entity": max(
                self.entities.values(),
                key=lambda e: e.outgoing_relations + e.incoming_relations
            ).name if self.entities else None
        }

    def export_for_visualization(self) -> Dict[str, Any]:
        """Export knowledge graph in format suitable for visualization."""
        nodes = []
        edges = []

        for entity in self.entities.values():
            nodes.append({
                "id": entity.entity_id,
                "label": entity.name,
                "type": entity.entity_type.value,
                "confidence": entity.confidence,
                "connections": entity.outgoing_relations + entity.incoming_relations
            })

        for relationship in self.relationships.values():
            edges.append({
                "from": relationship.subject_id,
                "to": relationship.object_id,
                "label": relationship.relation_type.value,
                "confidence": relationship.confidence,
                "strength": relationship.strength
            })

        return {
            "nodes": nodes,
            "edges": edges
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "mind_gmid": self.mind_gmid,
            "entities": {
                eid: entity.model_dump()
                for eid, entity in self.entities.items()
            },
            "relationships": {
                rid: rel.model_dump()
                for rid, rel in self.relationships.items()
            },
            "total_inferences": self.total_inferences
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        """Deserialize from dictionary."""
        graph = cls(mind_gmid=data["mind_gmid"])

        # Restore entities
        for eid, entity_data in data.get("entities", {}).items():
            entity = Entity(**entity_data)
            graph.entities[eid] = entity
            graph._entity_name_index[entity.name.lower()] = eid

            # Rebuild type index
            if entity.entity_type not in graph._type_index:
                graph._type_index[entity.entity_type] = []
            graph._type_index[entity.entity_type].append(eid)

            # Initialize relation index
            graph._relation_index[eid] = []

        # Restore relationships
        for rid, rel_data in data.get("relationships", {}).items():
            rel = Relationship(**rel_data)
            graph.relationships[rid] = rel

            # Rebuild relation index
            if rel.subject_id in graph._relation_index:
                graph._relation_index[rel.subject_id].append(rid)

        graph.total_inferences = data.get("total_inferences", 0)

        return graph
