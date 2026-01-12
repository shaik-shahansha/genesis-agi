"""Tests to ensure memory user scoping and privacy."""

from genesis.storage.memory import MemoryManager, MemoryType


def test_memory_user_scoping_personal_vs_shared():
    manager = MemoryManager(mind_id="test-user-scope")

    # Personal memory belonging to user_b (should not be visible to user_a)
    personal = manager.add_memory(
        content="User B's private email is b@example.com",
        memory_type=MemoryType.SEMANTIC,
        user_email="user_b@example.com",
        relationship_context="personal",
    )

    # Shared memory belonging to user_b (should be visible to others)
    shared = manager.add_memory(
        content="User B likes coffee",
        memory_type=MemoryType.SEMANTIC,
        user_email="user_b@example.com",
        relationship_context="shared",
    )

    # Search as user A
    results_a = manager.search_memories(query="User B", limit=10, user_email="user_a@example.com")
    contents_a = [r.content for r in results_a]

    assert personal.content not in contents_a
    assert shared.content in contents_a

    # Search as user B
    results_b = manager.search_memories(query="User B", limit=10, user_email="user_b@example.com")
    contents_b = [r.content for r in results_b]

    assert personal.content in contents_b
    assert shared.content in contents_b


def test_get_recent_memories_restores_user_email():
    manager1 = MemoryManager(mind_id="test-reconstruct")
    mem = manager1.add_memory(
        content="Private note for user U",
        memory_type=MemoryType.SEMANTIC,
        user_email="u@example.com",
        relationship_context="personal",
    )

    # Create a new manager instance which should load from vector store
    manager2 = MemoryManager(mind_id="test-reconstruct")
    # Ensure in-memory cache is empty
    manager2.memories = {}

    recent = manager2.get_recent_memories(limit=10)
    # Find our memory
    found = next((m for m in recent if m.id == mem.id), None)
    assert found is not None
    assert found.user_email == "u@example.com"
