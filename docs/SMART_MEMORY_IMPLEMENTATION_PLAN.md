# Smart Memory Implementation Plan (Pure ChromaDB)

## Goal
Replace mem0 dependency with pure ChromaDB + smart features in ~7 hours of work.

## Phase 1: Core Features (4-5 hours)

### Task 1: Smart Deduplication (2 hours)
**File:** `genesis/storage/memory_deduplication.py`

```python
"""Smart deduplication to prevent duplicate memories."""

from typing import Optional, Tuple, List
from genesis.storage.memory import Memory, MemoryType
from genesis.storage.vector_store import VectorStore


class MemoryDeduplicator:
    """Prevents duplicate memories using similarity detection."""
    
    def __init__(self, vector_store: VectorStore, similarity_threshold: float = 0.85):
        self.vector_store = vector_store
        self.threshold = similarity_threshold
    
    def find_similar(
        self, 
        content: str, 
        memory_type: MemoryType,
        n_results: int = 5
    ) -> List[dict]:
        """Find similar existing memories."""
        return self.vector_store.search(
            query=content,
            n_results=n_results,
            filter_metadata={"type": memory_type.value}
        )
    
    def check_duplicate(self, content: str, memory_type: MemoryType) -> Optional[str]:
        """
        Check if very similar memory exists.
        
        Returns:
            Memory ID if duplicate found, None otherwise
        """
        similar = self.find_similar(content, memory_type, n_results=1)
        
        if similar and similar[0]["distance"] < (1 - self.threshold):
            return similar[0]["id"]
        
        return None
    
    def should_merge(self, content: str, memory_type: MemoryType) -> Tuple[bool, Optional[str]]:
        """
        Determine if new content should merge with existing.
        
        Returns:
            (should_merge, existing_memory_id)
        """
        duplicate_id = self.check_duplicate(content, memory_type)
        
        if duplicate_id:
            return (True, duplicate_id)
        
        return (False, None)
```

**Integration:**
```python
# genesis/storage/memory.py

class MemoryManager:
    def __init__(self, mind_id: str):
        # ... existing code ...
        self.deduplicator = MemoryDeduplicator(self.vector_store)
```

---

### Task 2: Memory Update Logic (2 hours)
**File:** `genesis/storage/memory.py` (enhancement)

```python
class MemoryManager:
    def add_memory_smart(
        self,
        content: str,
        memory_type: MemoryType,
        **kwargs
    ) -> Memory:
        """
        Add memory with smart deduplication.
        
        If similar memory exists (>85% similarity):
        - Updates existing memory
        - Boosts importance
        - Preserves history
        
        Otherwise:
        - Creates new memory
        """
        # Check for duplicates
        should_merge, existing_id = self.deduplicator.should_merge(content, memory_type)
        
        if should_merge and existing_id and existing_id in self.memories:
            # Update existing memory
            existing = self.memories[existing_id]
            
            # Merge content (prefer newer)
            existing.content = content
            
            # Boost importance
            new_importance = kwargs.get("importance", 0.5)
            existing.importance = max(existing.importance, new_importance)
            
            # Update access tracking
            existing.access_count += 1
            existing.last_accessed = datetime.now()
            
            # Merge tags
            new_tags = kwargs.get("tags", [])
            existing.tags = list(set(existing.tags + new_tags))
            
            # Update vector store
            self.vector_store.add_memory(
                memory_id=existing.id,
                content=existing.content,
                metadata={
                    "type": existing.type.value,
                    "importance": existing.importance,
                    "tags": ",".join(existing.tags),
                }
            )
            
            return existing
        
        # Create new memory (no duplicate found)
        return self.add_memory(content, memory_type, **kwargs)
```

**Usage:**
```python
# Before (creates duplicates):
memory1 = manager.add_memory("User likes pizza", MemoryType.SEMANTIC)
memory2 = manager.add_memory("User loves pizza", MemoryType.SEMANTIC)  # Duplicate!

# After (updates existing):
memory1 = manager.add_memory_smart("User likes pizza", MemoryType.SEMANTIC)
memory2 = manager.add_memory_smart("User loves pizza", MemoryType.SEMANTIC)  # Updates memory1
```

---

### Task 3: Temporal Decay (30 minutes)
**File:** `genesis/storage/memory.py` (enhancement)

```python
class Memory(BaseModel):
    def get_relevance_score(self) -> float:
        """
        Calculate current relevance score.
        
        Factors:
        - Base importance (0.0 - 1.0)
        - Temporal decay (older = less relevant)
        - Access frequency (more used = more relevant)
        """
        # Base importance
        base = self.importance
        
        # Temporal decay (1% per day)
        age_days = (datetime.now() - self.timestamp).days
        decay = 0.99 ** age_days
        
        # Access boost (up to +0.3)
        access_boost = min(self.access_count * 0.05, 0.3)
        
        return base * decay + access_boost
```

**Integration in Search:**
```python
class MemoryManager:
    def search_memories(
        self,
        query: str,
        n_results: int = 5,
        memory_type: Optional[MemoryType] = None,
        use_relevance_scoring: bool = True
    ) -> List[Memory]:
        """Search with temporal decay."""
        # Vector search
        results = self.vector_store.search(
            query=query,
            n_results=n_results * 2,  # Get more, then rerank
            filter_metadata={"type": memory_type.value} if memory_type else None
        )
        
        # Convert to Memory objects
        memories = [self.memories[r["id"]] for r in results if r["id"] in self.memories]
        
        if use_relevance_scoring:
            # Rerank by relevance score
            memories.sort(key=lambda m: m.get_relevance_score(), reverse=True)
        
        return memories[:n_results]
```

---

## Phase 2: Optional Enhancements (3 hours)

### Task 4: Basic Consolidation (2 hours)
**File:** `genesis/storage/memory_consolidation.py`

```python
"""Memory consolidation (like sleep!)"""

from typing import List
from collections import defaultdict
from genesis.storage.memory import Memory, MemoryManager


class MemoryConsolidator:
    """Consolidate and archive memories periodically."""
    
    def __init__(self, manager: MemoryManager):
        self.manager = manager
    
    def consolidate(self):
        """Run consolidation process."""
        # 1. Archive very old, low-importance memories
        self._archive_old_memories()
        
        # 2. Merge very similar memories
        self._merge_similar_memories()
    
    def _archive_old_memories(self):
        """Archive memories older than 1 year with low importance."""
        cutoff_date = datetime.now() - timedelta(days=365)
        
        for memory in self.manager.memories.values():
            if (memory.timestamp < cutoff_date and 
                memory.importance < 0.3 and 
                memory.access_count < 3):
                # Move to archive (or just delete)
                memory.metadata["archived"] = True
                memory.metadata["archived_date"] = datetime.now().isoformat()
    
    def _merge_similar_memories(self):
        """Merge very similar memories."""
        # Group by type
        by_type = defaultdict(list)
        for memory in self.manager.memories.values():
            by_type[memory.type].append(memory)
        
        # Check for duplicates in each type
        for mem_type, memories in by_type.items():
            to_remove = set()
            
            for i, mem1 in enumerate(memories):
                if mem1.id in to_remove:
                    continue
                    
                for mem2 in memories[i+1:]:
                    if mem2.id in to_remove:
                        continue
                    
                    # Check similarity
                    similar = self.manager.vector_store.search(
                        query=mem1.content,
                        n_results=2
                    )
                    
                    if len(similar) > 1 and similar[1]["id"] == mem2.id:
                        # Very similar, merge into mem1
                        mem1.importance = max(mem1.importance, mem2.importance)
                        mem1.access_count += mem2.access_count
                        mem1.tags = list(set(mem1.tags + mem2.tags))
                        to_remove.add(mem2.id)
            
            # Remove merged memories
            for mem_id in to_remove:
                del self.manager.memories[mem_id]
```

**Usage:**
```python
# Run daily or weekly
consolidator = MemoryConsolidator(memory_manager)
consolidator.consolidate()
```

---

### Task 5: LLM-Based Reranking (3 hours)
**File:** `genesis/storage/memory_reranker.py`

```python
"""LLM-based memory reranking for better relevance."""

from typing import List
from genesis.storage.memory import Memory


class MemoryReranker:
    """Use LLM to rerank memories by relevance to query."""
    
    def __init__(self, orchestrator, model: str):
        self.orchestrator = orchestrator
        self.model = model
    
    async def rerank(
        self, 
        query: str, 
        memories: List[Memory], 
        top_k: int = 5
    ) -> List[Memory]:
        """Rerank memories using LLM."""
        
        if len(memories) <= top_k:
            return memories
        
        # Build prompt
        prompt = self._build_prompt(query, memories)
        
        # Get LLM ranking
        response = await self.orchestrator.generate(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.1
        )
        
        # Parse rankings
        rankings = self._parse_rankings(response.content, memories)
        
        return rankings[:top_k]
    
    def _build_prompt(self, query: str, memories: List[Memory]) -> str:
        """Build reranking prompt."""
        memories_text = "\n".join([
            f"{i}. {m.content} (importance: {m.importance})"
            for i, m in enumerate(memories)
        ])
        
        return f"""Rank these memories by relevance to the query.

Query: {query}

Memories:
{memories_text}

Respond with just the ranked indices (0-based), most relevant first.
Example: [2, 0, 5, 1, 3, 4]
"""
    
    def _parse_rankings(self, response: str, memories: List[Memory]) -> List[Memory]:
        """Parse LLM response and reorder memories."""
        try:
            # Extract indices from response
            import json
            indices = json.loads(response.strip())
            
            # Reorder memories
            return [memories[i] for i in indices if i < len(memories)]
        except:
            # If parsing fails, return original order
            return memories
```

---

## Configuration

### Update memory_config.py

```python
class MemoryConfig(BaseSettings):
    # ... existing config ...
    
    # Smart Memory Features
    enable_smart_deduplication: bool = True
    deduplication_threshold: float = 0.85  # 85% similarity = duplicate
    
    enable_temporal_decay: bool = True
    decay_rate: float = 0.99  # 1% per day
    
    enable_consolidation: bool = True
    consolidation_interval: int = 86400  # 24 hours (in seconds)
    
    enable_llm_reranking: bool = False  # Optional (adds LLM call)
    reranking_model: str = "groq/llama-3.3-70b-versatile"
```

---

## Testing

### Test Deduplication

```python
# test_deduplication.py

from genesis.storage.memory import MemoryManager, MemoryType

manager = MemoryManager("test-mind")

# Add similar memories
mem1 = manager.add_memory_smart("User likes pizza", MemoryType.SEMANTIC)
mem2 = manager.add_memory_smart("User loves pizza", MemoryType.SEMANTIC)

# Should be same memory (updated, not duplicated)
assert mem1.id == mem2.id
assert "loves" in mem2.content
print("✅ Deduplication works!")
```

### Test Temporal Decay

```python
# test_temporal_decay.py

from datetime import datetime, timedelta
from genesis.storage.memory import Memory, MemoryType

# Create old memory
old_memory = Memory(
    type=MemoryType.SEMANTIC,
    content="Old fact",
    importance=0.8,
    timestamp=datetime.now() - timedelta(days=365)
)

# Create recent memory
new_memory = Memory(
    type=MemoryType.SEMANTIC,
    content="New fact",
    importance=0.5,
    timestamp=datetime.now()
)

# Old memory should have lower relevance despite higher importance
assert old_memory.get_relevance_score() < new_memory.get_relevance_score()
print("✅ Temporal decay works!")
```

---

## Migration Path

### Step 1: Keep Both (Recommended)
```python
# User can choose
class CompressedMemoryManager(MemoryManager):
    def __init__(self, mind_id: str, use_mem0: bool = False):
        super().__init__(mind_id)
        
        if use_mem0:
            self.mem0_client = self._init_mem0()
            self.add_memory_fn = self._add_with_mem0
        else:
            self.add_memory_fn = self.add_memory_smart
```

### Step 2: Gradual Rollout
1. Week 1: Implement deduplication
2. Week 2: Add temporal decay
3. Week 3: Add consolidation
4. Week 4: Test & benchmark

### Step 3: Compare Performance
```python
# Benchmark both approaches
results = {
    "chromadb": benchmark_chromadb(),
    "mem0": benchmark_mem0()
}

# Compare:
# - Memory count (deduplication effectiveness)
# - Query accuracy
# - Query speed
# - Token usage
```

---

## Expected Outcomes

### After Phase 1 (4-5 hours)
- ✅ No duplicate memories
- ✅ Memories update instead of duplicate
- ✅ Old memories decay naturally
- ✅ Better memory management

### After Phase 2 (7+ hours)
- ✅ Automatic memory consolidation
- ✅ LLM-powered reranking
- ✅ Production-ready memory system
- ✅ Feature parity with mem0

### Benchmark Targets
- **Deduplication:** <5% duplicate rate
- **Memory Growth:** 50% slower than without dedup
- **Query Accuracy:** +10-15% vs naive search
- **Token Usage:** -80% vs full history (even without compression)

---

## Summary

**Time Investment:** 4-7 hours  
**Dependencies Removed:** mem0ai (optional)  
**Features Gained:** 
- Smart deduplication
- Memory updates
- Temporal decay
- Consolidation

**Result:** Production-ready memory system with no required dependencies! 🎯
