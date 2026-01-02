"""Memory management system for Genesis Minds."""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from genesis.storage.vector_store import VectorStore


class MemoryType(str, Enum):
    """Types of memories."""

    EPISODIC = "episodic"  # Personal experiences: "I did X and felt Y"
    SEMANTIC = "semantic"  # Facts and knowledge: "X is Y"
    PROCEDURAL = "procedural"  # Skills: "How to do X"
    PROSPECTIVE = "prospective"  # Future intent: "I need to do X"
    WORKING = "working"  # Active context (short-term)


class Memory(BaseModel):
    """A single memory."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def __hash__(self):
        """Make Memory hashable by ID."""
        return hash(self.id)
    
    def __eq__(self, other):
        """Compare memories by ID."""
        if isinstance(other, Memory):
            return self.id == other.id
        return False

    # Emotional context
    emotion: Optional[str] = None
    emotion_intensity: Optional[float] = None

    # Importance and access
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    # Associations
    tags: List[str] = Field(default_factory=list)
    related_memory_ids: List[str] = Field(default_factory=list)

    # User context (for user-specific memories)
    user_email: Optional[str] = None  # Email of user involved in this memory
    relationship_context: Optional[str] = None  # 'personal', 'shared', 'generic'

    # Environment context (location awareness)
    environment_id: Optional[str] = None  # ID of environment where memory was created
    environment_name: Optional[str] = None  # Name of environment for easy reference

    # Context
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def access(self) -> None:
        """Record memory access."""
        self.access_count += 1
        self.last_accessed = datetime.now()
    
    def get_relevance_score(self) -> float:
        """Calculate current relevance score with temporal decay.
        
        Considers:
        - Base importance (0.0 - 1.0)
        - Temporal decay (older memories decay at 1% per day)
        - Access frequency boost (frequently accessed = more relevant)
        
        Returns:
            Relevance score (0.0 - 1.3, can exceed 1.0 with access boost)
        """
        # Base importance
        base = self.importance
        
        # Temporal decay (1% per day, exponential)
        age_days = (datetime.now() - self.timestamp).days
        decay_factor = 0.99 ** age_days
        
        # Access boost (up to +0.3 for frequently accessed memories)
        access_boost = min(self.access_count * 0.05, 0.3)
        
        return base * decay_factor + access_boost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "emotion": self.emotion,
            "emotion_intensity": self.emotion_intensity,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "tags": self.tags,
            "related_memory_ids": self.related_memory_ids,
            "user_email": self.user_email,
            "relationship_context": self.relationship_context,
            "environment_id": self.environment_id,
            "environment_name": self.environment_name,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create from dictionary."""
        # Convert timestamp strings back to datetime
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if isinstance(data.get("last_accessed"), str) and data["last_accessed"]:
            data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])

        return cls(**data)


class MemoryManager:
    """
    Manages all memory types for a Mind.

    Features:
    - Episodic memory (autobiographical experiences)
    - Semantic memory (knowledge and facts)
    - Procedural memory (skills)
    - Prospective memory (future intentions)
    - Working memory (active context)
    - Vector search for semantic retrieval
    """

    def __init__(self, mind_id: str):
        """Initialize memory manager for a Mind."""
        self.mind_id = mind_id

        # All memories indexed by ID
        self.memories: Dict[str, Memory] = {}

        # Working memory (limited capacity, like human short-term memory)
        self.working_memory: List[str] = []  # Memory IDs
        self.working_memory_capacity = 12  # ~7±2 items like humans

        # Vector store for semantic search
        self.vector_store = VectorStore(mind_id)
        
        # Smart deduplication (optional, will be initialized by SmartMemoryManager)
        self.deduplicator = None

    def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        emotion: Optional[str] = None,
        emotion_intensity: Optional[float] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_email: Optional[str] = None,
        relationship_context: Optional[str] = None,
        environment_id: Optional[str] = None,
        environment_name: Optional[str] = None,
    ) -> Memory:
        """
        Add a new memory.

        Args:
            content: Memory content
            memory_type: Type of memory
            emotion: Associated emotion
            emotion_intensity: Emotion intensity (0-1)
            importance: Memory importance (0-1)
            tags: Tags for categorization
            metadata: Additional metadata
            user_email: Email of user involved in this memory
            relationship_context: Context of memory (personal/shared/generic)

        Returns:
            Created memory
        """
        memory = Memory(
            type=memory_type,
            content=content,
            emotion=emotion,
            emotion_intensity=emotion_intensity,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {},
            user_email=user_email,
            relationship_context=relationship_context or "generic",
            environment_id=environment_id,
            environment_name=environment_name,
        )

        # Store in memory index
        self.memories[memory.id] = memory

        # Add to vector store for semantic search
        # Build metadata - ChromaDB requires all values to be non-None
        vector_metadata = {
            "type": memory_type.value,
            "importance": float(importance),
            "timestamp": memory.timestamp.isoformat(),
            "tags": ",".join(tags) if tags else "",
        }
        
        # Only add emotion if it's not None
        if emotion is not None:
            vector_metadata["emotion"] = str(emotion)
        
        # Merge with any additional metadata provided, filtering out None values
        if metadata:
            for key, value in metadata.items():
                if value is not None:
                    # Ensure all values are proper types
                    if isinstance(value, (str, int, float, bool)):
                        vector_metadata[key] = value
                    else:
                        # Convert complex types to strings
                        vector_metadata[key] = str(value)
        
        self.vector_store.add_memory(
            memory_id=memory.id,
            content=content,
            metadata=vector_metadata,
        )

        # Add to working memory if important
        if importance >= 0.7:
            self._add_to_working_memory(memory.id)

        return memory

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a specific memory and mark it as accessed."""
        memory = self.memories.get(memory_id)
        if memory:
            memory.access()
        return memory

    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        min_importance: Optional[float] = None,
        user_email: Optional[str] = None,
    ) -> List[Memory]:
        """
        Search memories semantically.

        Args:
            query: Search query
            memory_type: Filter by type
            limit: Max results
            min_importance: Minimum importance threshold
            user_email: Filter by specific user's memories

        Returns:
            List of matching memories
        """
        # Build metadata filter
        filter_metadata = {}
        if memory_type:
            filter_metadata["type"] = memory_type.value
        if min_importance is not None:
            filter_metadata["importance"] = {"$gte": min_importance}

        # Search vector store
        results = self.vector_store.search(
            query=query,
            n_results=limit,
            filter_metadata=filter_metadata if filter_metadata else None,
        )

        # Convert to Memory objects and filter by user if specified
        memories = []
        for result in results:
            memory = self.memories.get(result["id"])
            if memory:
                # Filter by user_email only if explicitly specified
                if user_email:
                    # When user_email is provided, include:
                    # 1. Memories without user_email (generic, from before user tracking)
                    # 2. Memories with matching user_email
                    # 3. Memories with different user_email BUT generic/shared context
                    if memory.user_email and memory.user_email != user_email:
                        # Skip only if it's a personal memory from another user
                        if getattr(memory, 'relationship_context', 'generic') == "personal":
                            continue
                    # Include all other memories (no user_email, matching user, or generic)
                # If user_email is None, retrieve all relevant memories (no filtering)
                memory.access()
                memories.append(memory)

        return memories

    def get_recent_memories(
        self,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
    ) -> List[Memory]:
        """Get most recent memories."""
        memories = list(self.memories.values())

        # Filter by type if specified
        if memory_type:
            memories = [m for m in memories if m.type == memory_type]

        # Sort by timestamp (most recent first)
        memories.sort(key=lambda m: m.timestamp, reverse=True)

        return memories[:limit]

    def get_important_memories(
        self,
        limit: int = 10,
        min_importance: float = 0.7,
    ) -> List[Memory]:
        """Get most important memories."""
        memories = [m for m in self.memories.values() if m.importance >= min_importance]
        memories.sort(key=lambda m: m.importance, reverse=True)
        return memories[:limit]

    def get_working_memory(self) -> List[Memory]:
        """Get current working memory (active context)."""
        return [self.memories[mid] for mid in self.working_memory if mid in self.memories]

    def _add_to_working_memory(self, memory_id: str) -> None:
        """Add to working memory with capacity limit."""
        # Remove if already present
        if memory_id in self.working_memory:
            self.working_memory.remove(memory_id)

        # Add to front
        self.working_memory.insert(0, memory_id)

        # Maintain capacity limit
        if len(self.working_memory) > self.working_memory_capacity:
            self.working_memory.pop()

    def consolidate_memories(self) -> Dict[str, Any]:
        """
        Consolidate memories (like sleep/dream processing).

        Returns:
            Statistics about consolidation
        """
        stats = {
            "total_memories": len(self.memories),
            "episodic": 0,
            "semantic": 0,
            "procedural": 0,
            "prospective": 0,
            "working": len(self.working_memory),
            "high_importance": 0,
        }

        # Count by type
        for memory in self.memories.values():
            if memory.type == MemoryType.EPISODIC:
                stats["episodic"] += 1
            elif memory.type == MemoryType.SEMANTIC:
                stats["semantic"] += 1
            elif memory.type == MemoryType.PROCEDURAL:
                stats["procedural"] += 1
            elif memory.type == MemoryType.PROSPECTIVE:
                stats["prospective"] += 1

            if memory.importance >= 0.7:
                stats["high_importance"] += 1

        return stats

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return self.consolidate_memories()

    def to_dict(self) -> Dict[str, Any]:
        """Export all memories."""
        return {
            "mind_id": self.mind_id,
            "memories": {mid: mem.to_dict() for mid, mem in self.memories.items()},
            "working_memory": self.working_memory,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryManager":
        """Import memories from dictionary."""
        manager = cls(mind_id=data["mind_id"])

        # Restore memories
        for mem_data in data.get("memories", {}).values():
            memory = Memory.from_dict(mem_data)
            manager.memories[memory.id] = memory

        # Restore working memory
        manager.working_memory = data.get("working_memory", [])

        return manager
    
    def add_memory_smart(
        self,
        content: str,
        memory_type: MemoryType,
        **kwargs
    ) -> Memory:
        """
        Add memory with smart deduplication.
        
        If similar memory exists (>85% similarity by default):
        - Updates existing memory with new content
        - Boosts importance if new importance is higher
        - Preserves access history
        - Merges tags
        
        Otherwise:
        - Creates new memory normally
        
        Args:
            content: Memory content
            memory_type: Type of memory
            **kwargs: Additional memory parameters (emotion, importance, tags, etc.)
            
        Returns:
            Created or updated memory
        """
        # If no deduplicator, fall back to regular add_memory
        if not self.deduplicator:
            return self.add_memory(content, memory_type, **kwargs)
        
        # Check for duplicates
        should_merge, existing_id, similarity = self.deduplicator.should_merge(
            content, memory_type
        )
        
        if should_merge and existing_id and existing_id in self.memories:
            # Update existing memory
            existing = self.memories[existing_id]
            
            # Update content (prefer newer)
            existing.content = content
            
            # Boost importance if new is higher
            new_importance = kwargs.get("importance", 0.5)
            existing.importance = max(existing.importance, new_importance)
            
            # Update emotional context if provided
            if kwargs.get("emotion"):
                existing.emotion = kwargs["emotion"]
            if kwargs.get("emotion_intensity") is not None:
                existing.emotion_intensity = kwargs["emotion_intensity"]
            
            # Update access tracking
            existing.access_count += 1
            existing.last_accessed = datetime.now()
            
            # Merge tags (avoid duplicates)
            new_tags = kwargs.get("tags", [])
            existing.tags = list(set(existing.tags + new_tags))
            
            # Update user/environment context if provided
            if kwargs.get("user_email"):
                existing.user_email = kwargs["user_email"]
            if kwargs.get("relationship_context"):
                existing.relationship_context = kwargs["relationship_context"]
            if kwargs.get("environment_id"):
                existing.environment_id = kwargs["environment_id"]
            if kwargs.get("environment_name"):
                existing.environment_name = kwargs["environment_name"]
            
            # Merge metadata
            new_metadata = kwargs.get("metadata", {})
            existing.metadata.update(new_metadata)
            existing.metadata["updated_from_duplicate"] = True
            existing.metadata["similarity_score"] = similarity
            
            # Update vector store
            self.vector_store.add_memory(
                memory_id=existing.id,
                content=existing.content,
                metadata={
                    "type": existing.type.value,
                    "emotion": existing.emotion,
                    "importance": existing.importance,
                    "timestamp": existing.timestamp.isoformat(),
                    "tags": ",".join(existing.tags),
                }
            )
            
            return existing
        
        # Create new memory (no duplicate found)
        return self.add_memory(content, memory_type, **kwargs)
    
    def search_memories_ranked(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        use_relevance_scoring: bool = True,
        min_importance: Optional[float] = None,
        user_email: Optional[str] = None,
    ) -> List[Memory]:
        """
        Search memories with temporal decay and relevance scoring.
        
        Args:
            query: Search query
            memory_type: Filter by type
            limit: Max results
            use_relevance_scoring: Apply temporal decay + access boost
            min_importance: Minimum importance threshold
            user_email: Filter by user
            
        Returns:
            List of memories ranked by relevance
        """
        # Get more results initially for reranking
        search_limit = limit * 2 if use_relevance_scoring else limit
        
        # Use regular search
        memories = self.search_memories(
            query=query,
            memory_type=memory_type,
            limit=search_limit,
            min_importance=min_importance,
            user_email=user_email
        )
        
        if use_relevance_scoring:
            # Rerank by relevance score (combines importance, temporal decay, access frequency)
            memories.sort(key=lambda m: m.get_relevance_score(), reverse=True)
        
        return memories[:limit]

        return manager
