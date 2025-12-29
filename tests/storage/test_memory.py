"""Tests for the memory management system."""

import pytest
from genesis.storage.memory import MemoryManager, Memory, MemoryType


class TestMemory:
    """Test Memory model."""

    def test_memory_creation(self):
        """Test creating a memory."""
        memory = Memory(
            type=MemoryType.EPISODIC,
            content="I had a great conversation today",
            emotion="joy",
            emotion_intensity=0.8,
            importance=0.7,
            tags=["conversation", "positive"],
        )

        assert memory.type == MemoryType.EPISODIC
        assert memory.content == "I had a great conversation today"
        assert memory.emotion == "joy"
        assert memory.access_count == 0

    def test_memory_access(self):
        """Test accessing a memory."""
        memory = Memory(
            type=MemoryType.SEMANTIC,
            content="Python is a programming language",
        )

        assert memory.access_count == 0
        assert memory.last_accessed is None

        memory.access()
        assert memory.access_count == 1
        assert memory.last_accessed is not None

    def test_memory_serialization(self):
        """Test memory to_dict and from_dict."""
        memory = Memory(
            type=MemoryType.PROCEDURAL,
            content="How to solve a Rubik's cube",
            importance=0.6,
            tags=["skill", "puzzle"],
        )

        # Serialize
        data = memory.to_dict()
        assert data["type"] == "procedural"
        assert data["content"] == "How to solve a Rubik's cube"

        # Deserialize
        restored = Memory.from_dict(data)
        assert restored.type == MemoryType.PROCEDURAL
        assert restored.content == memory.content
        assert restored.importance == memory.importance


class TestMemoryManager:
    """Test MemoryManager."""

    def test_add_memory(self, memory_manager: MemoryManager):
        """Test adding a memory."""
        memory = memory_manager.add_memory(
            content="I learned about quantum physics",
            memory_type=MemoryType.SEMANTIC,
            importance=0.8,
            tags=["learning", "science"],
        )

        assert memory.id in memory_manager.memories
        assert memory_manager.vector_store.count() == 1

    def test_get_memory(self, memory_manager: MemoryManager):
        """Test retrieving a memory."""
        memory = memory_manager.add_memory(
            content="Test memory",
            memory_type=MemoryType.EPISODIC,
        )

        retrieved = memory_manager.get_memory(memory.id)
        assert retrieved is not None
        assert retrieved.content == "Test memory"
        assert retrieved.access_count == 1  # Should increment on access

    def test_add_important_memory_to_working_memory(self, memory_manager: MemoryManager):
        """Test that important memories are added to working memory."""
        memory = memory_manager.add_memory(
            content="Very important event",
            memory_type=MemoryType.EPISODIC,
            importance=0.9,  # High importance
        )

        working = memory_manager.get_working_memory()
        assert len(working) == 1
        assert working[0].id == memory.id

    def test_working_memory_capacity(self, memory_manager: MemoryManager):
        """Test working memory capacity limit."""
        # Add more memories than capacity
        for i in range(15):
            memory_manager.add_memory(
                content=f"Important memory {i}",
                memory_type=MemoryType.EPISODIC,
                importance=0.9,
            )

        working = memory_manager.get_working_memory()
        assert len(working) <= memory_manager.working_memory_capacity

    def test_search_memories(self, memory_manager: MemoryManager, sample_memories):
        """Test semantic memory search."""
        # Add sample memories
        for mem_data in sample_memories:
            memory_manager.add_memory(**mem_data)

        # Search for programming-related memories
        results = memory_manager.search_memories("programming", limit=5)
        assert len(results) > 0
        assert any("Python" in mem.content for mem in results)

    def test_search_memories_by_type(self, memory_manager: MemoryManager, sample_memories):
        """Test searching memories by type."""
        # Add sample memories
        for mem_data in sample_memories:
            memory_manager.add_memory(**mem_data)

        # Search only episodic memories
        results = memory_manager.search_memories(
            "conversation",
            memory_type=MemoryType.EPISODIC,
        )

        assert all(mem.type == MemoryType.EPISODIC for mem in results)

    def test_get_recent_memories(self, memory_manager: MemoryManager, sample_memories):
        """Test getting recent memories."""
        # Add sample memories
        for mem_data in sample_memories:
            memory_manager.add_memory(**mem_data)

        recent = memory_manager.get_recent_memories(limit=2)
        assert len(recent) == 2
        # Should be sorted by timestamp (most recent first)
        assert recent[0].timestamp >= recent[1].timestamp

    def test_get_important_memories(self, memory_manager: MemoryManager):
        """Test getting important memories."""
        memory_manager.add_memory("Low importance", MemoryType.EPISODIC, importance=0.3)
        memory_manager.add_memory("High importance", MemoryType.EPISODIC, importance=0.9)
        memory_manager.add_memory("Medium importance", MemoryType.EPISODIC, importance=0.6)

        important = memory_manager.get_important_memories(min_importance=0.7)
        assert len(important) == 1
        assert important[0].content == "High importance"

    def test_consolidate_memories(self, memory_manager: MemoryManager, sample_memories):
        """Test memory consolidation statistics."""
        # Add sample memories
        for mem_data in sample_memories:
            memory_manager.add_memory(**mem_data)

        stats = memory_manager.consolidate_memories()
        assert stats["total_memories"] == 3
        assert stats["episodic"] == 1
        assert stats["semantic"] == 1
        assert stats["procedural"] == 1

    def test_memory_serialization(self, memory_manager: MemoryManager):
        """Test serializing and deserializing memory manager."""
        # Add memories
        memory_manager.add_memory("Memory 1", MemoryType.EPISODIC, importance=0.8)
        memory_manager.add_memory("Memory 2", MemoryType.SEMANTIC, importance=0.6)

        # Serialize
        data = memory_manager.to_dict()
        assert len(data["memories"]) == 2
        assert data["mind_id"] == "test-mind-123"

        # Deserialize
        restored = MemoryManager.from_dict(data)
        assert len(restored.memories) == 2
        assert restored.mind_id == "test-mind-123"
