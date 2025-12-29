"""
Smart Memory Manager - Pure ChromaDB implementation with advanced features.

This replaces the mem0 dependency with built-in smart memory features:
- Automatic deduplication (prevents duplicate memories)
- Memory updates (updates existing instead of creating duplicates)
- Temporal decay (old memories naturally become less relevant)
- LLM-based reranking (better retrieval accuracy)
- Memory consolidation (periodic cleanup and optimization)

No external dependencies required - pure ChromaDB + smart algorithms!
"""

from typing import Optional
from genesis.storage.memory import MemoryManager
from genesis.storage.memory_deduplication import MemoryDeduplicator
from genesis.storage.memory_reranker import MemoryReranker
from genesis.storage.memory_consolidation import MemoryConsolidator
from genesis.config.memory_config import get_memory_config


class SmartMemoryManager(MemoryManager):
    """
    Enhanced MemoryManager with smart features (replaces mem0).
    
    Features:
    - Smart deduplication (prevents duplicates)
    - Temporal decay (relevance scoring over time)
    - Memory updates (not just add)
    - LLM reranking (optional, better accuracy)
    - Periodic consolidation (cleanup)
    
    100% built-in, no mem0 dependency!
    """
    
    def __init__(
        self,
        mind_id: str,
        orchestrator=None,
        model: str = None
    ):
        """
        Initialize smart memory manager.
        
        Args:
            mind_id: Unique mind identifier
            orchestrator: Optional ModelOrchestrator for LLM reranking
            model: Optional model string for LLM reranking
        """
        super().__init__(mind_id)
        
        # Get memory configuration
        self.config = get_memory_config()
        self.orchestrator = orchestrator
        self.model = model
        
        # Initialize smart features
        self._init_smart_features()
    
    def _init_smart_features(self):
        """Initialize smart memory features."""
        # 1. Smart Deduplication (always enabled)
        if self.config.enable_smart_deduplication:
            self.deduplicator = MemoryDeduplicator(
                self.vector_store,
                similarity_threshold=self.config.deduplication_threshold
            )
            print(f"[OK] Smart deduplication enabled (threshold: {self.config.deduplication_threshold})")
        else:
            self.deduplicator = None
        
        # 2. LLM Reranker (optional, requires orchestrator)
        self.reranker: Optional[MemoryReranker] = None
        if (self.config.enable_llm_reranking and 
            self.orchestrator and 
            self.model):
            try:
                self.reranker = MemoryReranker(
                    self.orchestrator,
                    self.model
                )
                print("[OK] LLM-based reranking enabled")
            except Exception as e:
                print(f"[WARN] Failed to initialize reranker: {e}")
        
        # 3. Memory Consolidator (for periodic cleanup)
        if self.config.enable_consolidation:
            self.consolidator = MemoryConsolidator(self)
            print("[OK] Memory consolidation enabled")
        else:
            self.consolidator = None
    
    async def search_memories_smart(
        self,
        query: str,
        memory_type=None,
        limit: int = 10,
        use_reranking: bool = None,
        **kwargs
    ):
        """
        Smart memory search with reranking and temporal decay.
        
        Args:
            query: Search query
            memory_type: Optional memory type filter
            limit: Max results
            use_reranking: Whether to use LLM reranking (defaults to config)
            **kwargs: Additional search parameters
            
        Returns:
            List of most relevant memories
        """
        # Determine if we should use reranking
        if use_reranking is None:
            use_reranking = self.config.enable_llm_reranking and self.reranker is not None
        
        # Get more results for reranking
        search_limit = limit * 2 if use_reranking else limit
        
        # Use ranked search (with temporal decay)
        memories = self.search_memories_ranked(
            query=query,
            memory_type=memory_type,
            limit=search_limit,
            use_relevance_scoring=self.config.enable_temporal_decay,
            **kwargs
        )
        
        # Apply LLM reranking if enabled
        if use_reranking and self.reranker and memories:
            try:
                memories = await self.reranker.rerank(query, memories, limit)
            except Exception as e:
                print(f"⚠️ Reranking failed: {e}. Using temporal decay ranking.")
                memories = memories[:limit]
        else:
            memories = memories[:limit]
        
        return memories
    
    def consolidate_if_needed(self):
        """
        Run consolidation if enabled.
        
        Call this periodically (e.g., daily) to:
        - Archive old, unused memories
        - Merge very similar memories
        - Reduce memory bloat
        """
        if not self.consolidator:
            return None
        
        try:
            stats = self.consolidator.consolidate()
            print(f"📦 Memory consolidated: {stats}")
            return stats
        except Exception as e:
            print(f"⚠️ Consolidation failed: {e}")
            return None
