"""
Memory tools for agent self-editing (Letta pattern).

This module provides tools for agents to manage their own memories:
- memory_replace: Precise edits to memory blocks
- memory_insert: Add new information
- memory_consolidate: Compress/summarize memories (Genesis dream-like)
"""

from typing import Dict, Any, Optional
from genesis.storage.memory_blocks import CoreMemory


class MemoryTools:
    """
    Tools for agents to edit their own memories.

    Based on Letta (MemGPT) pattern where agents can:
    1. Edit core memory blocks (persona, human, context, etc.)
    2. Insert new information
    3. Consolidate memories (compression via dreaming)
    """

    def __init__(self, core_memory: CoreMemory):
        """
        Initialize memory tools.

        Args:
            core_memory: CoreMemory instance to manage
        """
        self.core_memory = core_memory

    def memory_replace(
        self, block_label: str, old_text: str, new_text: str
    ) -> Dict[str, Any]:
        """
        Replace text in a memory block (precise editing).

        Args:
            block_label: Block to edit (persona, human, context, relationships, goals)
            old_text: Exact text to replace
            new_text: Replacement text

        Returns:
            Result dict with success status and message

        Example:
            >>> tools.memory_replace(
            ...     "human",
            ...     "User is learning Python",
            ...     "User is proficient in Python and learning Rust"
            ... )
        """
        try:
            # Get current block value
            block = self.core_memory.blocks.get(block_label)
            if not block:
                return {
                    "success": False,
                    "message": f"Block '{block_label}' not found. Available: {list(self.core_memory.blocks.keys())}",
                }

            # Check if old_text exists
            if old_text not in block.value:
                return {
                    "success": False,
                    "message": f"Text not found in block '{block_label}'. Current value:\n{block.value[:200]}...",
                }

            # Perform replacement
            new_value = block.value.replace(old_text, new_text, 1)  # Replace first occurrence

            # Update block
            success = self.core_memory.update_block(block_label, new_value)

            if success:
                return {
                    "success": True,
                    "message": f"[Done] Updated {block_label} block",
                    "old_text": old_text,
                    "new_text": new_text,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to update block (possibly over character limit: {block.limit})",
                }

        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def memory_insert(self, block_label: str, content: str) -> Dict[str, Any]:
        """
        Insert new information into memory block.

        Args:
            block_label: Block to edit (persona, human, context, relationships, goals)
            content: Content to insert

        Returns:
            Result dict with success status and message

        Example:
            >>> tools.memory_insert(
            ...     "relationships",
            ...     "User has a sister named Sarah who lives in Seattle"
            ... )
        """
        try:
            # Check if block exists
            block = self.core_memory.blocks.get(block_label)
            if not block:
                return {
                    "success": False,
                    "message": f"Block '{block_label}' not found. Available: {list(self.core_memory.blocks.keys())}",
                }

            # Append to block
            success = self.core_memory.append_to_block(
                block_label, content, separator="\n"
            )

            if success:
                return {
                    "success": True,
                    "message": f"[Done] Added to {block_label} block",
                    "content": content,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to insert (possibly over character limit: {block.limit})",
                }

        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def memory_consolidate(
        self, block_label: str, summarization_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consolidate (compress/summarize) a memory block.

        This is like Genesis's dream-like memory consolidation.
        In full implementation, would call LLM to compress.
        For now, provides framework for consolidation.

        Args:
            block_label: Block to consolidate
            summarization_prompt: Optional custom prompt for LLM

        Returns:
            Result dict with success status and message

        Example:
            >>> tools.memory_consolidate("context")
        """
        try:
            # Check if block exists
            block = self.core_memory.blocks.get(block_label)
            if not block:
                return {
                    "success": False,
                    "message": f"Block '{block_label}' not found. Available: {list(self.core_memory.blocks.keys())}",
                }

            # Get current length
            current_len = len(block.value)

            # If block is small, no consolidation needed
            if current_len < block.limit * 0.7:  # Less than 70% full
                return {
                    "success": True,
                    "message": f"Block '{block_label}' doesn't need consolidation (only {current_len}/{block.limit} characters)",
                    "skipped": True,
                }

            # In full implementation, would call LLM here to compress
            # For now, mark for consolidation
            return {
                "success": True,
                "message": f"Block '{block_label}' marked for consolidation ({current_len}/{block.limit} characters)",
                "needs_llm": True,
                "current_length": current_len,
                "max_length": block.limit,
                "utilization": round((current_len / block.limit * 100), 1),
            }

        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about memory blocks."""
        return self.core_memory.get_stats()

    def view_memory_block(self, block_label: str) -> Dict[str, Any]:
        """
        View contents of a memory block.

        Args:
            block_label: Block to view

        Returns:
            Block information dict
        """
        block = self.core_memory.blocks.get(block_label)
        if not block:
            return {
                "success": False,
                "message": f"Block '{block_label}' not found. Available: {list(self.core_memory.blocks.keys())}",
            }

        return {
            "success": True,
            "block_label": block.label,
            "description": block.description,
            "value": block.value,
            "length": len(block.value),
            "limit": block.limit,
            "utilization": round((len(block.value) / block.limit * 100), 1),
            "read_only": block.read_only,
        }

    def list_blocks(self) -> Dict[str, Any]:
        """
        List all available memory blocks.

        Returns:
            Dict with block names and descriptions
        """
        blocks_info = []
        for label, block in self.core_memory.blocks.items():
            blocks_info.append(
                {
                    "label": label,
                    "description": block.description,
                    "length": len(block.value),
                    "limit": block.limit,
                    "utilization": round((len(block.value) / block.limit * 100), 1),
                    "read_only": block.read_only,
                }
            )

        return {"success": True, "blocks": blocks_info, "total": len(blocks_info)}


def create_memory_tool_functions(memory_tools: MemoryTools) -> Dict[str, Any]:
    """
    Create function definitions for LLM tool calling.

    This provides OpenAI-compatible function definitions for agents to use.

    Args:
        memory_tools: MemoryTools instance

    Returns:
        Dict of function definitions
    """
    return {
        "memory_replace": {
            "name": "memory_replace",
            "description": "Replace text in a core memory block. Use for precise edits to existing information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "block_label": {
                        "type": "string",
                        "enum": ["persona", "human", "context", "relationships", "goals"],
                        "description": "Memory block to edit",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to replace (must match exactly)",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text",
                    },
                },
                "required": ["block_label", "old_text", "new_text"],
            },
            "function": memory_tools.memory_replace,
        },
        "memory_insert": {
            "name": "memory_insert",
            "description": "Insert new information into a core memory block. Use for adding new facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "block_label": {
                        "type": "string",
                        "enum": ["persona", "human", "context", "relationships", "goals"],
                        "description": "Memory block to edit",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to insert",
                    },
                },
                "required": ["block_label", "content"],
            },
            "function": memory_tools.memory_insert,
        },
        "memory_consolidate": {
            "name": "memory_consolidate",
            "description": "Consolidate (compress/summarize) a memory block. Use when block is getting full.",
            "parameters": {
                "type": "object",
                "properties": {
                    "block_label": {
                        "type": "string",
                        "enum": ["persona", "human", "context", "relationships", "goals"],
                        "description": "Memory block to consolidate",
                    }
                },
                "required": ["block_label"],
            },
            "function": memory_tools.memory_consolidate,
        },
        "view_memory_block": {
            "name": "view_memory_block",
            "description": "View contents of a memory block. Use to check current memory state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "block_label": {
                        "type": "string",
                        "enum": ["persona", "human", "context", "relationships", "goals"],
                        "description": "Memory block to view",
                    }
                },
                "required": ["block_label"],
            },
            "function": memory_tools.view_memory_block,
        },
        "list_memory_blocks": {
            "name": "list_memory_blocks",
            "description": "List all available memory blocks with stats.",
            "parameters": {"type": "object", "properties": {}},
            "function": memory_tools.list_blocks,
        },
    }
