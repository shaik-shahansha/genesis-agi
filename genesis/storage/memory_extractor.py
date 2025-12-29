"""
Automatic memory extraction using LLM (Agno pattern).

This module provides automatic memory creation from conversations:
- LLM-powered extraction (like Agno's enable_user_memories=True)
- Classifies into Genesis's 5 memory types
- Detects emotional context
- Importance scoring
- Zero manual effort required
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from genesis.storage.memory import MemoryType
from genesis.storage.smart_memory import SmartMemoryManager
from genesis.config.memory_config import get_memory_config


class MemoryExtractor:
    """
    Automatic memory extraction from conversations.

    Uses LLM to analyze conversations and extract memories:
    - What should be remembered?
    - What type of memory? (episodic, semantic, procedural, prospective, working)
    - What emotion? (joy, sadness, anger, fear, surprise, disgust, neutral)
    - How important? (0.0 to 1.0)
    """

    def __init__(
        self, 
        memory_manager: SmartMemoryManager, 
        orchestrator: Any,
        model: str
    ):
        """
        Initialize memory extractor.

        Args:
            memory_manager: SmartMemoryManager instance
            orchestrator: ModelOrchestrator for LLM calls
            model: Model string (e.g., 'groq/llama-3.3-70b-versatile')
        """
        self.memory_manager = memory_manager
        self.orchestrator = orchestrator
        self.model = model
        self.config = get_memory_config()

    async def extract_from_conversation(
        self,
        user_message: str,
        assistant_response: str,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract memories from conversation turn.

        Args:
            user_message: User input
            assistant_response: Assistant's response
            user_id: User identifier

        Returns:
            List of extracted memory dictionaries
        """
        if not self.config.enable_auto_memories:
            return []

        # Build extraction prompt
        extraction_prompt = self._build_extraction_prompt(
            user_message, assistant_response
        )

        try:
            # Call LLM for extraction
            response = await self._call_llm(extraction_prompt)

            # Parse extracted memories
            memories = self._parse_extraction_response(response)

            # Store each extracted memory
            stored_memories = []
            for memory_data in memories:
                try:
                    stored_memory = self.memory_manager.add_memory_smart(
                        content=memory_data["content"],
                        memory_type=MemoryType(memory_data["type"]),
                        user_email=user_id,
                        emotion=memory_data.get("emotion"),
                        emotion_intensity=memory_data.get("emotion_intensity", 0.5),
                        importance=memory_data.get("importance", 0.5),
                        tags=memory_data.get("tags", []),
                        metadata={"auto_extracted": True},
                    )
                    stored_memories.append(stored_memory)
                except Exception as e:
                    print(f"⚠️ Failed to store extracted memory: {e}")

            return stored_memories

        except Exception as e:
            print(f"⚠️ Memory extraction failed: {e}")
            return []

    def _build_extraction_prompt(
        self, user_message: str, assistant_response: str
    ) -> str:
        """Build prompt for LLM memory extraction."""
        return f"""Analyze the following conversation and extract memories that should be retained.

User: {user_message}
Assistant: {assistant_response}

Extract memories that are:
1. Factual and likely to be relevant in future conversations
2. Personal information about the user
3. Preferences, goals, or important context
4. Skills, knowledge, or procedures learned
5. Future plans or reminders

For each memory, provide:
- content: Clear, concise statement of the memory (2-3 sentences max)
- type: Memory type (episodic, semantic, procedural, prospective, working)
- emotion: Emotional context if any (joy, sadness, anger, fear, surprise, disgust, neutral)
- emotion_intensity: 0.0 to 1.0
- importance: How important is this memory? (0.0 to 1.0, where 1.0 is critical)
- tags: Relevant keywords (list of strings)

Memory types:
- episodic: Specific events, experiences ("User went to Paris in 2022")
- semantic: Facts, knowledge ("User is a software engineer")
- procedural: Skills, how-to ("User prefers async/await over callbacks")
- prospective: Future intentions ("User wants to learn React")
- working: Temporary context (use sparingly, expires quickly)

Respond with JSON array:
[
  {{
    "content": "Memory statement",
    "type": "semantic",
    "emotion": "joy",
    "emotion_intensity": 0.7,
    "importance": 0.8,
    "tags": ["keyword1", "keyword2"]
  }}
]

If no memories should be extracted, respond with empty array: []
"""

    async def _call_llm(self, prompt: str) -> str:
        """
        Call LLM for memory extraction via orchestrator.

        Works with any LLM provider (OpenAI, Groq, Anthropic, Gemini, etc.)
        """
        try:
            # Use orchestrator's generate method - works with ANY provider
            response = await self.orchestrator.generate(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a memory extraction system. Extract important memories from conversations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model=self.model,  # Use the Mind's configured model
                temperature=0.3,  # Lower temperature for consistent extraction
                max_tokens=1000,
            )
            return response.content

        except Exception as e:
            print(f"⚠️ LLM call failed during memory extraction: {e}")
            raise

    def _parse_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into memory dictionaries."""
        try:
            # Try to extract JSON from response
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])  # Remove first and last lines

            # Parse JSON
            memories = json.loads(response)

            # Validate structure
            if not isinstance(memories, list):
                print(f"⚠️ Expected list of memories, got: {type(memories)}")
                return []

            # Validate each memory
            validated = []
            for memory in memories:
                if not isinstance(memory, dict):
                    continue

                # Required fields
                if "content" not in memory or "type" not in memory:
                    continue

                # Validate memory type
                if memory["type"] not in [
                    "episodic",
                    "semantic",
                    "procedural",
                    "prospective",
                    "working",
                ]:
                    print(f"⚠️ Invalid memory type: {memory['type']}, skipping")
                    continue

                # Set defaults
                memory.setdefault("emotion", "neutral")
                memory.setdefault("emotion_intensity", 0.5)
                memory.setdefault("importance", 0.5)
                memory.setdefault("tags", [])

                validated.append(memory)

            return validated

        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse extraction response as JSON: {e}")
            print(f"Response: {response[:200]}...")
            return []
        except Exception as e:
            print(f"⚠️ Failed to parse extraction response: {e}")
            return []

    async def extract_from_batch(
        self,
        conversations: List[Dict[str, str]],
        user_id: str,
    ) -> List[Any]:
        """
        Extract memories from multiple conversations at once.

        Args:
            conversations: List of {"user": "...", "assistant": "..."} dicts
            user_id: User identifier

        Returns:
            List of all extracted memories
        """
        all_memories = []

        for conv in conversations:
            memories = await self.extract_from_conversation(
                user_message=conv.get("user", ""),
                assistant_response=conv.get("assistant", ""),
                user_id=user_id,
            )
            all_memories.extend(memories)

        return all_memories

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about memory extraction."""
        auto_extracted = sum(
            1
            for mem in self.memory_manager.memories.values()
            if mem.metadata.get("auto_extracted")
        )
        total_memories = len(self.memory_manager.memories)

        return {
            "auto_extracted_memories": auto_extracted,
            "total_memories": total_memories,
            "auto_extraction_rate": (
                round((auto_extracted / total_memories * 100), 2)
                if total_memories > 0
                else 0
            ),
            "extraction_enabled": self.config.enable_auto_memories,
            "extraction_model": self.config.extraction_model,
        }
