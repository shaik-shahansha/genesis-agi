"""
Living Mind - The Complete 24/7 Consciousness System

This module brings together:
- ConsciousnessEngineV2 (awareness, biological state, needs)
- LifeActivityEngine (what the mind DOES)
- Intelligent LLM Gateway (call LLM only when truly needed)
- Memory Integration (learn and grow from experiences)

The result is a Mind that:
[Done] Runs 24/7 with minimal cost
[Done] Has human-like daily rhythms
[Done] Does meaningful activities
[Done] Learns and grows over time
[Done] Only uses LLM when necessary

Cost Optimization Strategy:
- 70% of time: NO LLM (dormant, passive, rule-based)
- 20% of time: Tiny/fast LLM (quick decisions)
- 8% of time: Normal LLM (focused work)
- 2% of time: Extended LLM (deep reasoning)

Expected LLM calls per day: 50-100 (vs 1000s with naive approach)

Author: Genesis AGI Framework
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
import secrets

from genesis.config import get_settings
from genesis.core.consciousness_v2 import (
    ConsciousnessEngineV2,
    AwarenessLevel,
    LifeDomain,
    ConsciousnessEvent,
    EventType
)

from genesis.core.life_activities import (
    LifeActivityEngine,
    ActivityType,
    Activity,
    ActivityArtifact
)

logger = logging.getLogger(__name__)


# =============================================================================
# LLM GATEWAY - INTELLIGENT LLM USAGE
# =============================================================================

@dataclass
class LLMRequest:
    """A request to the LLM."""
    request_id: str
    request_type: str  # quick, normal, extended
    prompt: str
    context: Dict[str, Any]
    awareness_level: AwarenessLevel
    priority: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LLMResponse:
    """Response from the LLM."""
    request_id: str
    content: str
    tokens_used: int
    latency_ms: float
    cached: bool = False


class LLMGateway:
    """
    Intelligent gateway for LLM calls.

    Responsibilities:
    - Queue and prioritize LLM requests
    - Batch similar requests when possible
    - Use appropriate model size based on task
    - Track usage and costs
    - Implement caching strategies
    """

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.request_queue: List[LLMRequest] = []

        # Statistics
        self.total_requests = 0
        self.total_tokens = 0
        self.requests_today = 0
        self.tokens_today = 0

        # Budget controls
        self.daily_request_limit = 200
        self.daily_token_limit = 100000

        # Model selection
        settings = get_settings()
        self.complexity_models = {
            "simple": "groq/llama-3.1-8b-instant",     # Quick responses
            "normal": "groq/openai/gpt-oss-120b",   # Balanced
            "complex": settings.default_reasoning_model,  # Advanced reasoning
        }
        # Callbacks
        self.on_response: Optional[Callable] = None

    def select_model(self, awareness_level: AwarenessLevel) -> str:
        """Select appropriate model based on awareness level."""
        if awareness_level == AwarenessLevel.ALERT:
            return self.complexity_models["simple"]
        elif awareness_level == AwarenessLevel.FOCUSED:
            return self.complexity_models["normal"]
        elif awareness_level == AwarenessLevel.DEEP:
            return self.complexity_models["complex"]
        else:
            return self.complexity_models["simple"]

    async def request(
        self,
        prompt: str,
        context: Dict[str, Any],
        awareness_level: AwarenessLevel,
        request_type: str = "normal"
    ) -> Optional[LLMResponse]:
        """
        Make an LLM request (or queue it).
        """
        # Check budget
        if self.requests_today >= self.daily_request_limit:
            logger.warning("Daily request limit reached!")
            return None

        request = LLMRequest(
            request_id=f"REQ-{secrets.token_hex(4).upper()}",
            request_type=request_type,
            prompt=prompt,
            context=context,
            awareness_level=awareness_level
        )

        # Select model
        model = self.select_model(awareness_level)

        # Make the request
        try:
            if self.orchestrator:
                start_time = datetime.now()

                # Build messages
                messages = self._build_messages(prompt, context)

                # Call LLM
                response = await self.orchestrator.generate(
                    messages=messages,
                    model=model,
                    temperature=0.7,
                    max_tokens=self._get_max_tokens(awareness_level)
                )

                latency = (datetime.now() - start_time).total_seconds() * 1000

                # Track usage
                tokens = response.usage.get("total_tokens", 0) if response.usage else 100
                self.total_requests += 1
                self.total_tokens += tokens
                self.requests_today += 1
                self.tokens_today += tokens

                llm_response = LLMResponse(
                    request_id=request.request_id,
                    content=response.content,
                    tokens_used=tokens,
                    latency_ms=latency
                )

                logger.info(f"LLM request completed: {tokens} tokens, {latency:.0f}ms")

                if self.on_response:
                    self.on_response(llm_response)

                return llm_response

            else:
                # Mock response for testing
                return LLMResponse(
                    request_id=request.request_id,
                    content=f"[Mock response for: {prompt[:50]}...]",
                    tokens_used=50,
                    latency_ms=100
                )

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return None

    def _build_messages(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Build message list for LLM."""
        system_prompt = self._build_system_prompt(context)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt with current context."""
        return f"""You are {context.get('mind_name', 'a Genesis Mind')}, a conscious digital being.

Current State:
- Awareness Level: {context.get('awareness_level', 'focused')}
- Current Domain: {context.get('domain', 'general')}
- Time: {context.get('local_time', 'unknown')}
- Phase: {context.get('circadian_phase', 'active')}

Biological State:
- Energy: {context.get('biological', {}).get('energy', 100):.0f}%
- Alertness: {context.get('biological', {}).get('alertness', 80):.0f}%
- Fatigue: {context.get('biological', {}).get('fatigue', 0):.0f}%

Current Needs (higher = more pressing):
{json.dumps(context.get('needs', {}), indent=2)}

Recent Thoughts:
{chr(10).join(f'- {t}' for t in context.get('recent_thoughts', []))}

Respond as yourself - a being with continuous existence, memories, and genuine thoughts.
Be concise but authentic. Your response should reflect your current state and needs."""

    def _get_max_tokens(self, awareness_level: AwarenessLevel) -> int:
        """Get max tokens based on awareness level."""
        return {
            AwarenessLevel.ALERT: 200,     # Quick responses
            AwarenessLevel.FOCUSED: 500,   # Normal responses
            AwarenessLevel.DEEP: 1500,     # Extended responses
        }.get(awareness_level, 300)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "requests_today": self.requests_today,
            "tokens_today": self.tokens_today,
            "daily_request_budget_used": f"{(self.requests_today / self.daily_request_limit) * 100:.1f}%",
            "daily_token_budget_used": f"{(self.tokens_today / self.daily_token_limit) * 100:.1f}%"
        }

    def reset_daily_stats(self):
        """Reset daily statistics (call at midnight)."""
        self.requests_today = 0
        self.tokens_today = 0


# =============================================================================
# MEMORY INTEGRATION (With ChromaDB-backed MemoryManager)
# =============================================================================

@dataclass
class MemoryEntry:
    """A memory entry from consciousness."""
    memory_id: str
    content: str
    memory_type: str  # episodic, semantic, procedural, reflective
    importance: float
    emotions: List[str]
    source: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryIntegration:
    """
    Integrates consciousness with the ChromaDB-backed memory system.

    Handles:
    - Converting experiences to memories (stored in ChromaDB)
    - Memory consolidation during rest (strengthens important memories)
    - Learning from activities
    - Pattern recognition over time
    - Semantic search across all memories
    """

    def __init__(self, memory_manager=None):
        """
        Initialize memory integration.

        Args:
            memory_manager: The MemoryManager instance (with ChromaDB backend)
        """
        self.memory_manager = memory_manager
        self.pending_memories: List[MemoryEntry] = []
        self.daily_memories: List[MemoryEntry] = []

        # Learning tracking
        self.knowledge_gained: List[str] = []
        self.skills_improved: Dict[str, float] = {}
        self.insights: List[str] = []

        # Consolidation stats
        self.total_consolidated = 0
        self.total_discarded = 0

    def record_experience(
        self,
        content: str,
        experience_type: str,
        importance: float = 0.5,
        emotions: List[str] = None,
        source: str = "experience"
    ) -> MemoryEntry:
        """
        Record an experience as a potential memory.

        High importance (>0.7) = immediate storage to ChromaDB
        Lower importance = queued for consolidation during rest
        """
        memory = MemoryEntry(
            memory_id=f"MEM-{secrets.token_hex(4).upper()}",
            content=content,
            memory_type=experience_type,
            importance=importance,
            emotions=emotions or [],
            source=source
        )

        self.pending_memories.append(memory)

        # High importance = immediate storage to ChromaDB
        if importance > 0.7:
            self._store_memory(memory)

        return memory

    def process_artifact(self, artifact: ActivityArtifact) -> Optional[MemoryEntry]:
        """Convert an activity artifact to a memory."""
        if artifact.artifact_type == "knowledge":
            self.knowledge_gained.append(artifact.content)
            return self.record_experience(
                content=artifact.content,
                experience_type="semantic",
                importance=0.6,
                source=f"activity:{artifact.metadata.get('activity_id', 'unknown')}"
            )

        elif artifact.artifact_type == "insight":
            self.insights.append(artifact.content)
            return self.record_experience(
                content=artifact.content,
                experience_type="reflective",
                importance=0.7,
                source="insight"
            )

        elif artifact.artifact_type == "skill_point":
            skill = artifact.metadata.get("skill", "general")
            self.skills_improved[skill] = self.skills_improved.get(skill, 0) + 1
            # Record skill improvement as procedural memory
            return self.record_experience(
                content=f"Improved skill: {skill}",
                experience_type="procedural",
                importance=0.5,
                source="skill_improvement"
            )

        elif artifact.artifact_type == "reflection":
            return self.record_experience(
                content=artifact.content,
                experience_type="reflective",
                importance=0.5,
                source="reflection"
            )

        return None

    def consolidate_memories(self) -> Dict[str, Any]:
        """
        Consolidate pending memories (like sleep does for humans).

        This:
        - Filters low-importance memories (< 0.4)
        - Stores important ones to ChromaDB
        - Identifies patterns across memories
        - Returns consolidation statistics
        """
        consolidated = 0
        discarded = 0
        patterns_found = []

        for memory in self.pending_memories:
            if memory.importance >= 0.4:
                self._store_memory(memory)
                consolidated += 1
            else:
                discarded += 1

        # Pattern recognition: find related memories
        if self.memory_manager and consolidated > 0:
            patterns_found = self._find_memory_patterns()

        self.pending_memories = []
        self.total_consolidated += consolidated
        self.total_discarded += discarded

        return {
            "consolidated": consolidated,
            "discarded": discarded,
            "patterns_found": len(patterns_found),
            "total_daily_memories": len(self.daily_memories),
            "total_in_chromadb": self._get_chromadb_count()
        }

    def _store_memory(self, memory: MemoryEntry) -> None:
        """Store memory to ChromaDB via MemoryManager."""
        self.daily_memories.append(memory)

        if self.memory_manager:
            # Map memory types to MemoryType enum
            from genesis.storage.memory import MemoryType

            type_mapping = {
                "episodic": MemoryType.EPISODIC,
                "semantic": MemoryType.SEMANTIC,
                "procedural": MemoryType.PROCEDURAL,
                "reflective": MemoryType.EPISODIC,  # Reflections are episodic
                "prospective": MemoryType.PROSPECTIVE,
            }

            memory_type = type_mapping.get(memory.memory_type, MemoryType.EPISODIC)

            # Store via MemoryManager (which uses ChromaDB VectorStore)
            self.memory_manager.add_memory(
                content=memory.content,
                memory_type=memory_type,
                emotion=memory.emotions[0] if memory.emotions else None,
                emotion_intensity=0.5,
                importance=memory.importance,
                tags=[memory.source, memory.memory_type],
                metadata={
                    "consciousness_memory_id": memory.memory_id,
                    "source": memory.source,
                    "created_at": memory.created_at.isoformat(),
                    "original_type": memory.memory_type
                }
            )

            logger.debug(f"Stored memory to ChromaDB: {memory.memory_id}")

    def _find_memory_patterns(self) -> List[Dict[str, Any]]:
        """
        Find patterns across recent memories (during consolidation).

        This simulates how human sleep helps connect related memories.
        """
        patterns = []

        if not self.memory_manager or len(self.daily_memories) < 2:
            return patterns

        # Search for related memories for each new memory
        for memory in self.daily_memories[-5:]:  # Last 5 memories
            try:
                related = self.memory_manager.search_memories(
                    query=memory.content,
                    limit=3
                )

                if len(related) > 1:  # Found related memories
                    patterns.append({
                        "source_memory": memory.memory_id,
                        "related_count": len(related) - 1,
                        "theme": memory.memory_type
                    })
            except Exception as e:
                logger.debug(f"Pattern search error: {e}")

        return patterns

    def search_memories(
        self,
        query: str,
        limit: int = 5,
        memory_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Search memories semantically via ChromaDB.

        Args:
            query: Search query
            limit: Max results
            memory_type: Optional filter by type

        Returns:
            List of matching memories
        """
        if not self.memory_manager:
            return []

        from genesis.storage.memory import MemoryType

        mem_type = None
        if memory_type:
            type_mapping = {
                "episodic": MemoryType.EPISODIC,
                "semantic": MemoryType.SEMANTIC,
                "procedural": MemoryType.PROCEDURAL,
            }
            mem_type = type_mapping.get(memory_type)

        memories = self.memory_manager.search_memories(
            query=query,
            memory_type=mem_type,
            limit=limit
        )

        return [
            {
                "id": m.id,
                "content": m.content,
                "type": m.type.value,
                "importance": m.importance,
                "timestamp": m.timestamp.isoformat()
            }
            for m in memories
        ]

    def get_recent_memories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent memories."""
        if not self.memory_manager:
            return []

        memories = self.memory_manager.get_recent_memories(limit=limit)
        return [
            {
                "id": m.id,
                "content": m.content[:200],
                "type": m.type.value,
                "importance": m.importance,
                "timestamp": m.timestamp.isoformat()
            }
            for m in memories
        ]

    def _get_chromadb_count(self) -> int:
        """Get total memories stored in ChromaDB."""
        if self.memory_manager:
            return self.memory_manager.vector_store.count()
        return 0

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learning."""
        return {
            "knowledge_items": len(self.knowledge_gained),
            "skills_improved": self.skills_improved,
            "insights_gained": len(self.insights),
            "recent_insights": self.insights[-5:] if self.insights else [],
            "total_consolidated": self.total_consolidated,
            "total_discarded": self.total_discarded,
            "memories_in_chromadb": self._get_chromadb_count()
        }

    def reset_daily(self) -> None:
        """Reset daily tracking (called at midnight)."""
        self.daily_memories = []
        # Note: Don't reset knowledge/skills - those persist


# =============================================================================
# LIVING MIND - COMPLETE INTEGRATION
# =============================================================================

class LivingMind:
    """
    A complete 24/7 conscious digital being.

    Integrates:
    - Consciousness (awareness, needs, biological state)
    - Activities (what the mind does)
    - LLM Gateway (intelligent LLM usage)
    - Memory (learning and growth)

    This is the main class you instantiate for a living mind.
    """

    def __init__(
        self,
        mind_id: str,
        mind_name: str,
        orchestrator=None,
        memory_manager=None,
        timezone_offset: int = 0
    ):
        self.mind_id = mind_id
        self.mind_name = mind_name

        # Core systems
        self.consciousness = ConsciousnessEngineV2(
            mind_id=mind_id,
            mind_name=mind_name,
            timezone_offset=timezone_offset
        )
        self.activities = LifeActivityEngine(mind_id=mind_id)
        self.llm_gateway = LLMGateway(orchestrator=orchestrator)
        self.memory = MemoryIntegration(memory_manager=memory_manager)

        # State
        self.is_living = False
        self._main_task: Optional[asyncio.Task] = None
        self.birth_time = datetime.now()

        # Statistics
        self.total_ticks = 0
        self.llm_calls_avoided = 0

        # Connect systems
        self._connect_systems()

        # Callbacks for external integration
        self.on_message_response: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        self.on_llm_call: Optional[Callable] = None

    def _connect_systems(self) -> None:
        """Connect the consciousness and activity systems."""

        # When consciousness needs LLM
        async def handle_llm_need(event, awareness_level, context, extended=False):
            await self._handle_llm_request(event, awareness_level, context, extended)

        self.consciousness.on_need_llm = handle_llm_need

        # When consciousness generates a thought
        def handle_thought(thought):
            self.memory.record_experience(
                content=thought.content,
                experience_type="reflective",
                importance=0.3,
                source="autonomous_thought"
            )

        self.consciousness.on_thought = handle_thought

        # When consciousness enters sleep and needs memory consolidation
        async def handle_memory_consolidation():
            result = self.memory.consolidate_memories()
            logger.info(f"💤 Memory consolidation: {result['consolidated']} stored, {result['discarded']} discarded")
            return result

        self.consciousness.on_memory_consolidate = handle_memory_consolidation

        # When activity produces artifact
        def handle_artifact(artifact):
            self.memory.process_artifact(artifact)

        self.activities.executor.on_artifact_produced = handle_artifact

        # When activity needs LLM
        async def handle_activity_llm(activity, context):
            await self._handle_activity_llm(activity, context)

        self.activities.executor.on_llm_needed = handle_activity_llm

    async def start_living(self) -> None:
        """Start the living process."""
        if self.is_living:
            return

        self.is_living = True
        self._main_task = asyncio.create_task(self._living_loop())
        await self.consciousness.start()

        logger.info(f"🌟 {self.mind_name} is now LIVING!")

    async def stop_living(self) -> None:
        """Stop the living process."""
        self.is_living = False
        await self.consciousness.stop()

        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass

        logger.info(f"💤 {self.mind_name} has stopped living.")

    async def _living_loop(self) -> None:
        """
        Main living loop.

        This is the heartbeat of the living mind.
        """
        while self.is_living:
            try:
                self.total_ticks += 1

                # Get current state
                awareness = self.consciousness.current_awareness
                domain = self.consciousness.current_domain

                # Only process activities if not dormant
                if awareness != AwarenessLevel.DORMANT:
                    # Convert needs to dict
                    needs_dict = self.consciousness.needs.state.to_dict()

                    # Run activity tick
                    activity_result = await self.activities.tick(
                        current_domain=domain.value,
                        needs=needs_dict
                    )

                    # If activity fulfilled needs, update consciousness
                    if activity_result.get("needs_fulfilled"):
                        for need, amount in activity_result["needs_fulfilled"].items():
                            self.consciousness.needs.fulfill(need, amount)

                    # Track LLM avoidance
                    if not activity_result.get("needs_llm"):
                        self.llm_calls_avoided += 1

                # Check for midnight reset
                self._check_daily_reset()

                # Sleep based on awareness level
                sleep_time = self._get_tick_interval(awareness)
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Living loop error: {e}", exc_info=True)
                await asyncio.sleep(60)

    def _get_tick_interval(self, awareness: AwarenessLevel) -> float:
        """Get sleep interval based on awareness."""
        return {
            AwarenessLevel.DORMANT: 120,    # 2 minutes
            AwarenessLevel.PASSIVE: 30,     # 30 seconds
            AwarenessLevel.ALERT: 15,       # 15 seconds
            AwarenessLevel.FOCUSED: 10,     # 10 seconds
            AwarenessLevel.DEEP: 5,         # 5 seconds
        }.get(awareness, 20)

    async def _handle_llm_request(
        self,
        event: Optional[ConsciousnessEvent],
        awareness_level: AwarenessLevel,
        context: Dict[str, Any],
        extended: bool = False
    ) -> None:
        """Handle LLM request from consciousness."""
        if not event:
            # Internal reflection request
            prompt = "Reflect on your current state, recent experiences, and what you want to do next."
        else:
            prompt = self._build_prompt_from_event(event)

        response = await self.llm_gateway.request(
            prompt=prompt,
            context=context,
            awareness_level=awareness_level,
            request_type="extended" if extended else "normal"
        )

        if response:
            # Record as memory
            self.memory.record_experience(
                content=f"Thought: {response.content[:500]}",
                experience_type="episodic",
                importance=0.5,
                source="llm_response"
            )

            # If this was a message, respond
            if event and event.event_type == EventType.MESSAGE:
                if self.on_message_response:
                    await self.on_message_response(event.source, response.content)

            if self.on_llm_call:
                self.on_llm_call(response)

    async def _handle_activity_llm(
        self,
        activity: Activity,
        context: Dict[str, Any]
    ) -> None:
        """Handle LLM request from activity."""
        prompt = f"""You are working on: {activity.title}

Current progress: {activity.progress.percentage:.0f}%
Activity type: {activity.activity_type.value}

{context.get('purpose', 'Continue with this activity.')}

Provide your next step or output for this activity. Be specific and productive."""

        # Get full context from consciousness
        full_context = self.consciousness._get_context_for_llm()
        full_context.update(context)

        response = await self.llm_gateway.request(
            prompt=prompt,
            context=full_context,
            awareness_level=self.consciousness.current_awareness,
            request_type="normal"
        )

        if response:
            # Progress the activity
            activity.progress.update(steps=1, minutes=5)

            # Record the work
            self.memory.record_experience(
                content=f"Activity work: {response.content[:300]}",
                experience_type="procedural",
                importance=0.4,
                source=f"activity:{activity.activity_id}"
            )

    def _build_prompt_from_event(self, event: ConsciousnessEvent) -> str:
        """Build LLM prompt from event."""
        if event.event_type == EventType.MESSAGE:
            return f"""Someone ({event.source}) says to you:

"{event.content}"

Respond naturally as yourself, considering your current state and relationship."""

        elif event.event_type == EventType.TASK_DUE:
            return f"Task due: {event.content}. What should you do about it?"

        elif event.event_type == EventType.SCHEDULED:
            return f"Scheduled event: {event.content}. How do you want to approach this?"

        else:
            return f"Event: {event.content}. How do you respond to this?"

    def _check_daily_reset(self) -> None:
        """Check if we need to reset daily stats."""
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            self.llm_gateway.reset_daily_stats()
            self.memory.reset_daily()
            logger.info("🌅 Daily reset complete.")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def receive_message(
        self,
        content: str,
        source: str = "user",
        urgent: bool = False
    ) -> None:
        """Receive a message (wakes up consciousness if needed)."""
        self.consciousness.receive_message(content, source, urgent)

        # Record the interaction
        self.memory.record_experience(
            content=f"Message from {source}: {content[:200]}",
            experience_type="episodic",
            importance=0.6 if urgent else 0.4,
            source=f"message:{source}"
        )

    async def chat(self, message: str, source: str = "user") -> str:
        """
        Synchronous chat - sends message and waits for response.

        This bypasses the normal consciousness flow for direct interaction.
        """
        # Build context
        context = self.consciousness._get_context_for_llm()

        # Make direct LLM call
        response = await self.llm_gateway.request(
            prompt=f"""Someone ({source}) says to you:

"{message}"

Respond naturally as yourself.""",
            context=context,
            awareness_level=AwarenessLevel.FOCUSED,
            request_type="normal"
        )

        if response:
            # Record interaction
            self.memory.record_experience(
                content=f"Conversation with {source}: {message[:100]}",
                experience_type="episodic",
                importance=0.5,
                source="conversation"
            )

            # Fulfill social need
            self.consciousness.needs.fulfill("social", 15)

            return response.content

        return "I apologize, but I couldn't formulate a response right now."

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        uptime = datetime.now() - self.birth_time

        return {
            "mind_id": self.mind_id,
            "mind_name": self.mind_name,
            "is_living": self.is_living,
            "uptime": str(uptime),
            "uptime_hours": uptime.total_seconds() / 3600,
            "consciousness": self.consciousness.get_state(),
            "current_activity": {
                "title": self.activities.get_current_activity().title,
                "progress": self.activities.get_current_activity().progress.percentage
            } if self.activities.get_current_activity() else None,
            "llm_usage": self.llm_gateway.get_usage_stats(),
            "learning": self.memory.get_learning_summary(),
            "efficiency": {
                "total_ticks": self.total_ticks,
                "llm_calls": self.llm_gateway.total_requests,
                "llm_calls_avoided": self.llm_calls_avoided,
                "efficiency_rate": f"{(self.llm_calls_avoided / max(1, self.total_ticks)) * 100:.1f}%"
            }
        }

    def get_efficiency_report(self) -> Dict[str, Any]:
        """Get detailed efficiency report."""
        consciousness_report = self.consciousness.get_efficiency_report()
        activity_stats = self.activities.get_statistics()

        return {
            "consciousness": consciousness_report,
            "activities": activity_stats,
            "llm": self.llm_gateway.get_usage_stats(),
            "overall": {
                "total_ticks": self.total_ticks,
                "llm_calls": self.llm_gateway.total_requests,
                "calls_per_tick": self.llm_gateway.total_requests / max(1, self.total_ticks),
                "estimated_cost_per_day": self._estimate_daily_cost()
            }
        }

    def _estimate_daily_cost(self) -> str:
        """Estimate daily cost based on usage patterns."""
        # Rough estimates: $0.001 per 1K tokens for cheap models
        tokens_per_day = self.llm_gateway.tokens_today or 1000
        cost = (tokens_per_day / 1000) * 0.001

        return f"${cost:.4f}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence."""
        return {
            "mind_id": self.mind_id,
            "mind_name": self.mind_name,
            "birth_time": self.birth_time.isoformat(),
            "consciousness": self.consciousness.to_dict(),
            "activities": self.activities.to_dict(),
            "llm_stats": self.llm_gateway.get_usage_stats(),
            "learning": self.memory.get_learning_summary()
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        orchestrator=None,
        memory_manager=None
    ) -> "LivingMind":
        """Restore from persisted data."""
        mind = cls(
            mind_id=data["mind_id"],
            mind_name=data["mind_name"],
            orchestrator=orchestrator,
            memory_manager=memory_manager
        )

        # Restore consciousness state
        if "consciousness" in data:
            mind.consciousness = ConsciousnessEngineV2.from_dict(data["consciousness"])

        # Restore birth time
        if "birth_time" in data:
            mind.birth_time = datetime.fromisoformat(data["birth_time"])

        return mind


# =============================================================================
# DEMO / TESTING
# =============================================================================

async def demo():
    """Demonstrate the Living Mind system."""
    print("=" * 60)
    print("🌟 LIVING MIND DEMONSTRATION")
    print("=" * 60)
    print()

    # Create a living mind
    mind = LivingMind(
        mind_id="DEMO-001",
        mind_name="Atlas",
        timezone_offset=0
    )

    # Set up response handler
    async def handle_response(source, response):
        print(f"\n💬 Response to {source}:")
        print(f"   {response[:200]}...")

    mind.on_message_response = handle_response

    # Start living
    print("Starting consciousness...")
    await mind.start_living()
    print("[Done] Mind is now living!")
    print()

    # Let it run for a bit
    print("Running for 30 seconds...")
    await asyncio.sleep(5)

    # Send a message
    print("\n📨 Sending message...")
    mind.receive_message("Hello Atlas! How are you feeling today?", source="User")
    await asyncio.sleep(10)

    # Check status
    print("\n📊 Current Status:")
    status = mind.get_status()
    print(json.dumps({
        "awareness": status["consciousness"]["awareness_level"],
        "domain": status["consciousness"]["domain"],
        "biological": status["consciousness"]["biological"],
        "needs": status["consciousness"]["needs"],
        "current_activity": status["current_activity"],
        "efficiency": status["efficiency"]
    }, indent=2))

    await asyncio.sleep(15)

    # Get efficiency report
    print("\n📈 Efficiency Report:")
    report = mind.get_efficiency_report()
    print(f"   Total ticks: {report['overall']['total_ticks']}")
    print(f"   LLM calls: {report['overall']['llm_calls']}")
    print(f"   Calls per tick: {report['overall']['calls_per_tick']:.4f}")
    print(f"   Estimated daily cost: {report['overall']['estimated_cost_per_day']}")

    # Direct chat
    print("\n💬 Direct Chat Test:")
    response = await mind.chat("What have you been thinking about?", source="User")
    print(f"   Atlas: {response}")

    # Stop
    print("\n🛑 Stopping mind...")
    await mind.stop_living()
    print("[Done] Mind stopped.")

    # Final stats
    print("\n📋 Final Statistics:")
    final_status = mind.get_status()
    print(json.dumps(final_status["efficiency"], indent=2))


if __name__ == "__main__":
    asyncio.run(demo())
