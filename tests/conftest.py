"""Pytest configuration and fixtures for Genesis tests.

**Test isolation (backlog item A2).** The suite previously shared one persistent
ChromaDB directory per `mind_id` under the real `~/.genesis`, so collections
accumulated across runs and across tests. That is not a cosmetic problem: it
produced order-dependent failures such as

    assert memory_manager.vector_store.count() == 1
    assert 596 == 1

where the test was correct and the environment was not. Those failures were
misread as pre-existing bugs for as long as they existed, and they hid real ones.

The autouse session fixture below sets `GENESIS_ENV=test` and
`GENESIS_VECTOR_STORE_MODE=ephemeral` before any settings are constructed, so a
fresh checkout is isolated by default rather than relying on every test to
remember. It runs at session scope because `get_settings()` is cached.
"""

import os
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from typing import Generator, Dict, Any

#: Scratch home for the whole session. Set in `pytest_configure` so that every
#: `Settings` constructed afterwards points here.
_TEST_HOME = Path(tempfile.mkdtemp(prefix="genesis-test-home-"))


def pytest_configure(config):
    """Set the test environment before any genesis module reads settings.

    `pytest_configure` runs before collection, so this is early enough to beat
    the `lru_cache` on `get_settings()`.
    """
    os.environ.setdefault("GENESIS_ENV", "test")
    # Hermetic vectors: in-memory rather than a shared directory on disk.
    os.environ.setdefault("GENESIS_VECTOR_STORE_MODE", "ephemeral")
    # The durable governance store is the production default; tests that want it
    # opt in explicitly (see tests/governance/test_sql_store.py).
    os.environ.setdefault("GENESIS_GOVERNANCE_STORE", "memory")

    # Point the whole suite at a throwaway home.
    #
    # `data_dir`, `minds_dir` and `logs_dir` are INDEPENDENT settings, so setting
    # only GENESIS_HOME would leave the database, Mind JSON and logs in the real
    # `~/.genesis`. (`docker-compose.yml` carries the same caveat, for the same
    # reason.)
    #
    # This became necessary when user accounts turned into rows in `genesis.db`:
    # the suite started writing into the developer's own database and reading
    # back whatever a previous run had left. That made the bootstrap-admin tests
    # order-dependent — a row created by one test satisfied "seed the admin" for
    # the next, so a test asserting "nothing was seeded" saw a leftover account.
    home = str(_TEST_HOME)
    os.environ.setdefault("GENESIS_HOME", home)
    os.environ.setdefault("DATA_DIR", f"{home}/data")
    os.environ.setdefault("MINDS_DIR", f"{home}/minds")
    os.environ.setdefault("LOGS_DIR", f"{home}/logs")

    for path in (home, f"{home}/data", f"{home}/minds", f"{home}/logs"):
        Path(path).mkdir(parents=True, exist_ok=True)


def pytest_unconfigure(config):
    """Remove the scratch home."""
    shutil.rmtree(_TEST_HOME, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def isolated_vector_store(tmp_path_factory):
    """Fail loudly if something re-enables a persistent vector store.

    A silent fall back to persistent would reintroduce exactly the
    order-dependence this fixture exists to remove, and would do so invisibly.
    """
    from genesis.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    # Read the same way `VectorStore` does: the GENESIS_-prefixed environment
    # variable, not the pydantic field name.
    mode = os.environ.get("GENESIS_VECTOR_STORE_MODE") or getattr(
        settings, "vector_store_mode", "persistent"
    )
    if mode != "ephemeral":
        raise RuntimeError(
            "tests must run with an ephemeral vector store, but "
            f"GENESIS_VECTOR_STORE_MODE resolved to {mode!r}. Set "
            "GENESIS_VECTOR_STORE_MODE=ephemeral."
        )
    return mode


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
