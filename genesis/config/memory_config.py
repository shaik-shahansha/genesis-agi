"""
Memory configuration for Genesis Minds.

Optimized settings for pure ChromaDB + Smart Implementation:
- Smart deduplication (prevents duplicate memories)
- Automatic extraction (Agno pattern)
- Memory blocks (Letta pattern)
- Temporal decay (relevance over time)
- LLM reranking (optional, better accuracy)
- Consolidation (periodic cleanup)
- Genesis's rich semantics (5 types + emotions)

No external dependencies - 100% built-in!
"""

from typing import Dict, List, Any
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class MemoryConfig(BaseSettings):
    """Optimal memory configuration for Genesis Minds."""
    
    model_config = ConfigDict(env_prefix='GENESIS_MEMORY_')

    # ===== Smart Memory Features (Pure ChromaDB) =====
    enable_smart_deduplication: bool = True
    deduplication_threshold: float = 0.85  # 85% similarity = duplicate
    
    enable_temporal_decay: bool = True
    decay_rate: float = 0.99  # 1% decay per day
    
    enable_consolidation: bool = True
    consolidation_interval: int = 86400  # 24 hours (in seconds)
    consolidation_archive_age_days: int = 365  # Archive after 1 year
    consolidation_archive_importance: float = 0.3  # Archive if importance < 0.3
    
    enable_llm_reranking: bool = False  # Optional (adds LLM call overhead)
    reranking_model: str = "groq/llama-3.3-70b-versatile"  # Fast + cheap

    # ===== Automatic Extraction (Agno pattern) =====
    enable_auto_memories: bool = True
    extraction_model: str = "gpt-4o-mini"  # Fast + cheap for extraction
    extraction_temperature: float = 0.3  # Low temperature for consistent extraction

    # ===== Memory Blocks (Letta pattern) =====
    core_memory_enabled: bool = True
    core_blocks: List[str] = ["persona", "human", "context"]
    block_limits: Dict[str, int] = {
        "persona": 5000,  # Mind's identity
        "human": 5000,  # Current user preferences
        "context": 3000,  # Active conversation
    }

    # ===== Genesis Semantics (keep) =====
    memory_types: List[str] = [
        "episodic",
        "semantic",
        "procedural",
        "prospective",
        "working",
    ]
    enable_emotional_context: bool = True
    enable_importance_scoring: bool = True
    working_memory_capacity: int = 12  # Human-like 7±2 items

    # ===== Storage & Performance =====
    vector_store: str = "chromadb"  # or "qdrant", "pinecone", "weaviate"
    database_backend: str = "sqlite"  # or "postgresql" for production
    retrieval_limit: int = 5  # Top-k memories per query
    cache_embeddings: bool = True

    # ===== Agent Autonomy =====
    enable_memory_tools: bool = True  # Letta-style self-editing
    allow_self_editing: bool = True
    auto_consolidation: bool = True  # Dream-like memory consolidation
    consolidation_interval: int = 3600  # Seconds (1 hour)

    # ===== Memory Extraction Settings =====
    min_importance_threshold: float = 0.3  # Only extract important info
    deduplication: bool = True  # Avoid duplicate memories
    context_window_size: int = 10  # Messages to consider for extraction


# Default configuration (optimal balance)
DEFAULT_MEMORY_CONFIG = MemoryConfig()


def get_memory_config() -> MemoryConfig:
    """Get memory configuration."""
    return DEFAULT_MEMORY_CONFIG
