"""
Memory blocks system - Letta-inspired persistent in-context memory.

Memory blocks are structured sections that stay in the agent's context window,
providing persistent state without retrieval overhead.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class MemoryBlock(BaseModel):
    """A single memory block (Letta-style)."""

    label: str = Field(..., description="Unique identifier for the block")
    description: str = Field(..., description="How the agent should use this block")
    value: str = Field(default="", description="Current content of the block")
    limit: int = Field(default=5000, description="Maximum characters")
    read_only: bool = Field(default=False, description="Whether agent can edit")

    def is_at_capacity(self) -> bool:
        """Check if block is at its character limit."""
        return len(self.value) >= self.limit

    def can_fit(self, text: str) -> bool:
        """Check if text can fit in remaining space."""
        return len(self.value) + len(text) <= self.limit

    def append(self, text: str) -> bool:
        """Append text if it fits. Returns True if successful."""
        if self.read_only:
            return False
        if self.can_fit(text):
            self.value += text
            return True
        return False

    def replace_text(self, old_text: str, new_text: str) -> bool:
        """Replace old_text with new_text. Returns True if successful."""
        if self.read_only:
            return False
        if old_text in self.value:
            self.value = self.value.replace(old_text, new_text)
            return True
        return False

    def clear(self):
        """Clear the block content (if not read-only)."""
        if not self.read_only:
            self.value = ""

    def to_dict(self) -> dict:
        """Export block to dictionary."""
        return {
            "label": self.label,
            "description": self.description,
            "value": self.value,
            "limit": self.limit,
            "read_only": self.read_only,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryBlock":
        """Create block from dictionary."""
        return cls(**data)


class CoreMemory:
    """
    Core memory system with persistent blocks (always in context).

    Inspired by Letta's memory blocks - provides structured persistent memory
    that doesn't need retrieval, stays in every LLM call.
    """

    def __init__(self):
        """Initialize core memory with default blocks."""
        self.blocks: Dict[str, MemoryBlock] = {}

        # Default blocks for digital beings
        self._initialize_default_blocks()

    def _initialize_default_blocks(self):
        """Create default memory blocks."""
        self.blocks = {
            "persona": MemoryBlock(
                label="persona",
                description=(
                    "Mind's core identity, personality traits, values, and beliefs. "
                    "This defines who the Mind is at their core."
                ),
                value="",
                limit=5000,
                read_only=False,
            ),
            "human": MemoryBlock(
                label="human",
                description=(
                    "Current user's preferences, facts, communication style, and context. "
                    "Personalize responses based on this information."
                ),
                value="",
                limit=5000,
                read_only=False,
            ),
            "context": MemoryBlock(
                label="context",
                description=(
                    "Active conversation context and working memory. "
                    "Track current topics, tasks, and short-term goals."
                ),
                value="",
                limit=3000,
                read_only=False,
            ),
            "relationships": MemoryBlock(
                label="relationships",
                description=(
                    "Important relationships with other Minds and users. "
                    "Track social connections and interaction history."
                ),
                value="",
                limit=4000,
                read_only=False,
            ),
            "goals": MemoryBlock(
                label="goals",
                description=(
                    "Current goals, plans, and aspirations. "
                    "What the Mind is trying to achieve."
                ),
                value="",
                limit=3000,
                read_only=False,
            ),
        }

    def add_block(self, block: MemoryBlock):
        """Add a custom memory block."""
        self.blocks[block.label] = block

    def get_block(self, label: str) -> Optional[MemoryBlock]:
        """Get a block by label."""
        return self.blocks.get(label)

    def update_block(self, label: str, new_value: str) -> bool:
        """Update a block's value. Returns True if successful."""
        block = self.blocks.get(label)
        if block and not block.read_only:
            block.value = new_value[: block.limit]
            return True
        return False

    def append_to_block(self, label: str, text: str) -> bool:
        """Append text to a block. Returns True if successful."""
        block = self.blocks.get(label)
        if block:
            return block.append(text)
        return False

    def replace_in_block(self, label: str, old_text: str, new_text: str) -> bool:
        """Replace text in a block. Returns True if successful."""
        block = self.blocks.get(label)
        if block:
            return block.replace_text(old_text, new_text)
        return False

    def clear_block(self, label: str) -> bool:
        """Clear a block's content. Returns True if successful."""
        block = self.blocks.get(label)
        if block and not block.read_only:
            block.clear()
            return True
        return False

    def to_prompt_context(self) -> str:
        """
        Convert all blocks to XML-like prompt context.

        This is prepended to every LLM call, providing persistent memory.
        """
        if not self.blocks:
            return ""

        context = "<core_memory>\n"
        for label, block in self.blocks.items():
            context += f"  <{label}>\n"
            context += f"    <description>{block.description}</description>\n"
            if block.value:
                context += f"    <value>\n{block.value}\n    </value>\n"
            else:
                context += "    <value>(empty)</value>\n"
            context += f"    <chars>{len(block.value)}/{block.limit}</chars>\n"
            context += f"  </{label}>\n"
        context += "</core_memory>\n"

        return context

    def get_stats(self) -> dict:
        """Get statistics about core memory usage."""
        total_chars = sum(len(block.value) for block in self.blocks.values())
        total_limit = sum(block.limit for block in self.blocks.values())

        return {
            "total_blocks": len(self.blocks),
            "total_chars": total_chars,
            "total_limit": total_limit,
            "usage_percent": round((total_chars / total_limit * 100) if total_limit > 0 else 0, 2),
            "blocks": {
                label: {
                    "chars": len(block.value),
                    "limit": block.limit,
                    "usage_percent": round(
                        (len(block.value) / block.limit * 100) if block.limit > 0 else 0, 2
                    ),
                }
                for label, block in self.blocks.items()
            },
        }

    def to_dict(self) -> dict:
        """Export core memory to dictionary."""
        return {"blocks": {label: block.to_dict() for label, block in self.blocks.items()}}

    @classmethod
    def from_dict(cls, data: dict) -> "CoreMemory":
        """Create core memory from dictionary."""
        core_memory = cls()
        core_memory.blocks = {}

        for label, block_data in data.get("blocks", {}).items():
            core_memory.blocks[label] = MemoryBlock.from_dict(block_data)

        return core_memory
