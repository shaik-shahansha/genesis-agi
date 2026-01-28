"""Vector storage using ChromaDB for semantic search."""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path

from genesis.config import get_settings


class VectorStore:
    """
    Vector storage for semantic memory using ChromaDB.

    Enables semantic search across memories, thoughts, and conversations.
    """

    def __init__(self, mind_id: str):
        """Initialize vector store for a specific Mind."""
        self.mind_id = mind_id
        self.settings = get_settings()

        # Create persistent ChromaDB client
        chroma_path = self.settings.data_dir / "chroma" / mind_id
        chroma_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name=f"mind_{mind_id}",
            metadata={"description": f"Memories for Mind {mind_id}"},
        )

    def add_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a memory to the vector store.

        Args:
            memory_id: Unique memory identifier
            content: Text content to embed
            metadata: Additional metadata
        """
        self.collection.add(
            documents=[content],
            ids=[memory_id],
            metadatas=[metadata or {}],
        )

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories.

        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Metadata filters

        Returns:
            List of matching memories with scores
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_metadata,
            )
        except Exception as e:
            # If collection doesn't exist (e.g., after clear-memories), recreate it
            if "does not exist" in str(e):
                print(f"[VECTOR_STORE] Collection not found, recreating for mind {self.mind_id}")
                self.collection = self.client.get_or_create_collection(
                    name=f"mind_{self.mind_id}",
                    metadata={"description": f"Memories for Mind {self.mind_id}"},
                )
                # Return empty results for this search
                return []
            else:
                # Re-raise other errors
                raise

        # Format results
        memories = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                memories.append(
                    {
                        "id": memory_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else None,
                    }
                )

        return memories

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory by ID."""
        results = self.collection.get(ids=[memory_id])

        if results["ids"]:
            return {
                "id": results["ids"][0],
                "content": results["documents"][0],
                "metadata": results["metadatas"][0] if results["metadatas"] else {},
            }

        return None

    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory from the vector store."""
        self.collection.delete(ids=[memory_id])

    def count(self) -> int:
        """Get total number of memories."""
        return self.collection.count()
    
    def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all memories from the vector store.
        
        Args:
            limit: Maximum number of memories to return (None = all)
            
        Returns:
            List of all memories with their metadata
        """
        # ChromaDB get() with no IDs returns all documents
        results = self.collection.get(
            limit=limit,
            include=["documents", "metadatas"]
        )
        
        memories = []
        if results["ids"]:
            for i, memory_id in enumerate(results["ids"]):
                memories.append({
                    "id": memory_id,
                    "content": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })
        
        return memories

    def clear(self) -> None:
        """Clear all memories (dangerous!)."""
        self.client.delete_collection(name=f"mind_{self.mind_id}")
        self.collection = self.client.get_or_create_collection(
            name=f"mind_{self.mind_id}",
            metadata={"description": f"Memories for Mind {self.mind_id}"},
        )
