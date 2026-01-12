"""Pytest configuration and fixtures for Genesis tests."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from typing import Generator, Dict, Any

from genesis.config import Settings
from genesis.core.mind import Mind
from genesis.core.mind_config import MindConfig
from genesis.core.intelligence import Intelligence
from genesis.storage.memory import MemoryManager, MemoryType


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_settings(temp_dir: Path) -> Settings:
    """Create test settings with temporary directories."""
    settings = Settings(
        genesis_home=temp_dir / ".genesis",
        data_dir=temp_dir / ".genesis" / "data",
        minds_dir=temp_dir / ".genesis" / "minds",
        logs_dir=temp_dir / ".genesis" / "logs",
        database_url=f"sqlite:///{temp_dir / 'test.db'}",
        api_authentication_enabled=False,  # Disable for tests
    )
    return settings


@pytest.fixture
def memory_manager() -> MemoryManager:
    """Create a memory manager for testing."""
    return MemoryManager(mind_id="test-mind-123")


@pytest.fixture
def basic_mind_config() -> MindConfig:
    """Create a basic mind configuration for testing."""
    return MindConfig.minimal()


@pytest.fixture
def mock_intelligence() -> Intelligence:
    """Create a mock intelligence configuration."""
    return Intelligence(
        reasoning_model="groq/openai/gpt-oss-120b",
        fast_model="groq/llama-3.1-8b-instant",
    )


@pytest.fixture
def sample_memories() -> list[Dict[str, Any]]:
    """Sample memory data for testing."""
    return [
        {
            "content": "I learned about Python programming today",
            "type": MemoryType.SEMANTIC,
            "importance": 0.7,
            "tags": ["learning", "programming"],
        },
        {
            "content": "Had a great conversation with a user about AI",
            "type": MemoryType.EPISODIC,
            "importance": 0.8,
            "emotion": "joy",
            "tags": ["conversation", "ai"],
        },
        {
            "content": "I know how to solve quadratic equations",
            "type": MemoryType.PROCEDURAL,
            "importance": 0.6,
            "tags": ["math", "skills"],
        },
    ]
