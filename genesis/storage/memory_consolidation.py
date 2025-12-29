"""
Memory consolidation for periodic cleanup and optimization.

This module provides "sleep-like" memory consolidation:
- Archives old, low-importance memories
- Merges very similar memories
- Reduces memory bloat over time
- Maintains memory quality
"""

from typing import List, Dict, Set
from datetime import datetime, timedelta
from collections import defaultdict

from genesis.storage.memory import Memory, MemoryManager, MemoryType


class MemoryConsolidator:
    """
    Consolidate memories periodically (like human sleep).
    
    Performs:
    - Archiving of old, unused memories
    - Merging of very similar memories
    - Cleanup of low-value memories
    """
    
    def __init__(
        self,
        manager: MemoryManager,
        archive_age_days: int = 365,
        archive_importance_threshold: float = 0.3,
        archive_access_threshold: int = 3,
        merge_similarity_threshold: float = 0.90
    ):
        """
        Initialize consolidator.
        
        Args:
            manager: MemoryManager instance
            archive_age_days: Archive memories older than this (default 1 year)
            archive_importance_threshold: Archive if importance below this
            archive_access_threshold: Archive if accessed less than this
            merge_similarity_threshold: Merge if similarity above this (90%)
        """
        self.manager = manager
        self.archive_age_days = archive_age_days
        self.archive_importance_threshold = archive_importance_threshold
        self.archive_access_threshold = archive_access_threshold
        self.merge_similarity_threshold = merge_similarity_threshold
    
    def consolidate(self) -> Dict[str, int]:
        """
        Run full consolidation process.
        
        Returns:
            Statistics: {"archived": count, "merged": count, "kept": count}
        """
        stats = {
            "archived": 0,
            "merged": 0,
            "kept": 0,
            "total_before": len(self.manager.memories)
        }
        
        # 1. Archive old, unused memories
        archived_count = self._archive_old_memories()
        stats["archived"] = archived_count
        
        # 2. Merge very similar memories
        merged_count = self._merge_similar_memories()
        stats["merged"] = merged_count
        
        # 3. Update kept count
        stats["kept"] = len(self.manager.memories)
        stats["total_after"] = stats["kept"]
        
        return stats
    
    def _archive_old_memories(self) -> int:
        """
        Archive old, low-value memories.
        
        Criteria for archiving:
        - Older than archive_age_days
        - Importance below threshold
        - Accessed less than threshold
        - Not in working memory
        
        Returns:
            Number of memories archived
        """
        cutoff_date = datetime.now() - timedelta(days=self.archive_age_days)
        archived = 0
        
        memories_to_archive = []
        
        for memory in self.manager.memories.values():
            # Skip if in working memory (active)
            if memory.id in self.manager.working_memory:
                continue
            
            # Skip if prospective (future plans, keep regardless)
            if memory.type == MemoryType.PROSPECTIVE:
                continue
            
            # Check archiving criteria
            if (memory.timestamp < cutoff_date and
                memory.importance < self.archive_importance_threshold and
                memory.access_count < self.archive_access_threshold):
                
                # Mark as archived instead of deleting
                memory.metadata["archived"] = True
                memory.metadata["archived_date"] = datetime.now().isoformat()
                memory.metadata["archive_reason"] = "old_low_value"
                
                memories_to_archive.append(memory.id)
                archived += 1
        
        # Could optionally remove from active memory index
        # For now, just mark as archived (still searchable if needed)
        
        return archived
    
    def _merge_similar_memories(self) -> int:
        """
        Merge very similar memories within each type.
        
        Returns:
            Number of memories merged
        """
        if not self.manager.deduplicator:
            # Can't merge without deduplicator
            return 0
        
        merged = 0
        
        # Group by type
        by_type: Dict[MemoryType, List[Memory]] = defaultdict(list)
        for memory in self.manager.memories.values():
            # Skip archived memories
            if memory.metadata.get("archived"):
                continue
            by_type[memory.type].append(memory)
        
        # Check for duplicates in each type
        for mem_type, memories in by_type.items():
            to_remove: Set[str] = set()
            
            for i, mem1 in enumerate(memories):
                if mem1.id in to_remove:
                    continue
                
                # Find merge candidates
                candidates = self.manager.deduplicator.get_merge_candidates(
                    mem1.content,
                    mem1.type,
                    min_similarity=self.merge_similarity_threshold
                )
                
                # Merge with first candidate (highest similarity)
                for candidate_id, similarity in candidates:
                    # Skip self
                    if candidate_id == mem1.id:
                        continue
                    
                    # Skip if already marked for removal
                    if candidate_id in to_remove:
                        continue
                    
                    mem2 = self.manager.memories.get(candidate_id)
                    if not mem2 or mem2.id in to_remove:
                        continue
                    
                    # Merge mem2 into mem1
                    self._merge_memory_pair(mem1, mem2, similarity)
                    to_remove.add(mem2.id)
                    merged += 1
                    break  # Only merge once per memory
            
            # Remove merged memories
            for mem_id in to_remove:
                if mem_id in self.manager.memories:
                    del self.manager.memories[mem_id]
        
        return merged
    
    def _merge_memory_pair(self, primary: Memory, secondary: Memory, similarity: float):
        """Merge secondary memory into primary."""
        # Boost importance
        primary.importance = max(primary.importance, secondary.importance)
        
        # Combine access counts
        primary.access_count += secondary.access_count
        
        # Update last accessed
        if secondary.last_accessed:
            if not primary.last_accessed or secondary.last_accessed > primary.last_accessed:
                primary.last_accessed = secondary.last_accessed
        
        # Merge tags (avoid duplicates)
        primary.tags = list(set(primary.tags + secondary.tags))
        
        # Merge related memory IDs
        primary.related_memory_ids = list(set(
            primary.related_memory_ids + secondary.related_memory_ids
        ))
        
        # Track the merge
        if "merged_from" not in primary.metadata:
            primary.metadata["merged_from"] = []
        primary.metadata["merged_from"].append({
            "memory_id": secondary.id,
            "content": secondary.content,
            "similarity": similarity,
            "merged_at": datetime.now().isoformat()
        })
    
    def get_consolidation_stats(self) -> Dict[str, int]:
        """Get statistics about memory consolidation state."""
        stats = {
            "total": len(self.manager.memories),
            "archived": 0,
            "active": 0,
            "merged": 0,
            "by_type": defaultdict(int)
        }
        
        for memory in self.manager.memories.values():
            if memory.metadata.get("archived"):
                stats["archived"] += 1
            else:
                stats["active"] += 1
            
            if "merged_from" in memory.metadata:
                stats["merged"] += len(memory.metadata["merged_from"])
            
            stats["by_type"][memory.type.value] += 1
        
        return dict(stats)
