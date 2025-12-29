"""
Smart memory deduplication to prevent duplicate memories.

This module provides intelligent deduplication using vector similarity:
- Detects duplicate/similar memories before adding
- Suggests updates vs new memories
- Prevents memory bloat
- Maintains memory quality
"""

from typing import Optional, Tuple, List, Dict, Any
from genesis.storage.memory import Memory, MemoryType
from genesis.storage.vector_store import VectorStore


class MemoryDeduplicator:
    """
    Prevents duplicate memories using similarity detection.
    
    Uses vector embeddings to detect when new memory is too similar
    to existing memories (>85% similarity by default).
    """
    
    def __init__(self, vector_store: VectorStore, similarity_threshold: float = 0.85):
        """
        Initialize deduplicator.
        
        Args:
            vector_store: VectorStore instance for similarity search
            similarity_threshold: Similarity threshold (0.0-1.0) for considering duplicates
                                 0.85 = 85% similar is considered duplicate
        """
        self.vector_store = vector_store
        self.threshold = similarity_threshold
    
    def find_similar(
        self, 
        content: str, 
        memory_type: MemoryType,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar existing memories.
        
        Args:
            content: Memory content to search for
            memory_type: Type of memory to search within
            n_results: Number of similar memories to return
            
        Returns:
            List of similar memories with similarity scores
        """
        return self.vector_store.search(
            query=content,
            n_results=n_results,
            filter_metadata={"type": memory_type.value}
        )
    
    def check_duplicate(
        self, 
        content: str, 
        memory_type: MemoryType
    ) -> Optional[str]:
        """
        Check if very similar memory exists.
        
        Args:
            content: Memory content to check
            memory_type: Type of memory
            
        Returns:
            Memory ID if duplicate found (>threshold similarity), None otherwise
        """
        similar = self.find_similar(content, memory_type, n_results=1)
        
        if similar and len(similar) > 0:
            # ChromaDB distance: 0 = identical, 2 = opposite
            # Convert to similarity: similarity = 1 - (distance / 2)
            distance = similar[0].get("distance", 2.0)
            similarity = 1.0 - (distance / 2.0)
            
            if similarity >= self.threshold:
                return similar[0]["id"]
        
        return None
    
    def should_merge(
        self, 
        content: str, 
        memory_type: MemoryType
    ) -> Tuple[bool, Optional[str], float]:
        """
        Determine if new content should merge with existing.
        
        Args:
            content: New memory content
            memory_type: Type of memory
            
        Returns:
            (should_merge, existing_memory_id, similarity_score)
        """
        duplicate_id = self.check_duplicate(content, memory_type)
        
        if duplicate_id:
            # Get similarity score
            similar = self.find_similar(content, memory_type, n_results=1)
            if similar:
                distance = similar[0].get("distance", 2.0)
                similarity = 1.0 - (distance / 2.0)
                return (True, duplicate_id, similarity)
        
        return (False, None, 0.0)
    
    def get_merge_candidates(
        self, 
        content: str, 
        memory_type: MemoryType,
        min_similarity: float = 0.70
    ) -> List[Tuple[str, float]]:
        """
        Get all memories that could potentially be merged.
        
        Useful for batch consolidation.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            min_similarity: Minimum similarity to consider (default 70%)
            
        Returns:
            List of (memory_id, similarity_score) tuples
        """
        similar = self.find_similar(content, memory_type, n_results=10)
        
        candidates = []
        for mem in similar:
            distance = mem.get("distance", 2.0)
            similarity = 1.0 - (distance / 2.0)
            
            if similarity >= min_similarity:
                candidates.append((mem["id"], similarity))
        
        return candidates
