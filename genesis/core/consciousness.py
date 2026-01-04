"""
Continuous Awareness System - Autonomous Thought Generation Engine.

This module implements continuous awareness behaviors that simulate consciousness-like processes:
- Autonomous thought stream (periodic LLM-generated thoughts)
- Dream processing (scheduled memory consolidation via LLM)
- Attention simulation and focus
- Existence tracking

Note: This is NOT actual consciousness - it's a simulation of consciousness-like behaviors
using scheduled LLM prompts to create the appearance of continuous existence.
"""

import asyncio
import random
from datetime import datetime, time
from typing import Optional, Dict, Any, List

from genesis.core.emotions import Emotion, EmotionalState
from genesis.storage.memory import MemoryManager, MemoryType


class ConsciousnessEngine:
    """
    Continuous Awareness System - generates simulated autonomous mental activity.

    This system creates the appearance of continuous existence by periodically generating
    thoughts and processing experiences. It's a simulation layer that makes Minds appear
    "alive" even when not directly interacting with users.

    Implementation: Uses scheduled LLM prompts to generate thoughts and process memories.
    Not actual consciousness, but behaviors that mimic consciousness-like properties.
    """

    def __init__(self, mind_id: str, mind_name: str, reasoning_model: str = None, logger=None, notification_manager=None):
        """Initialize consciousness engine."""
        self.mind_id = mind_id
        self.mind_name = mind_name
        self.reasoning_model = reasoning_model  # Model to use for LLM calls
        self.logger = logger
        self.notification_manager = notification_manager  # For sending thoughts to web playground

        # State
        self.is_active = True
        self.is_dreaming = False
        self.current_focus: Optional[str] = None

        # Thought stream
        self.thought_stream: List[Dict[str, Any]] = []
        self.max_thought_history = 100

        # Background task
        self._consciousness_task: Optional[asyncio.Task] = None
        self._dream_task: Optional[asyncio.Task] = None
        
        # Activity counters for logging
        self.thought_count = 0
        self.dream_count = 0
        self.memory_revision_count = 0

    def set_notification_manager(self, notification_manager):
        """Set the notification manager for sending thoughts to web playground."""
        self.notification_manager = notification_manager

    async def start(self, orchestrator, emotional_state: EmotionalState, memory_manager: MemoryManager) -> None:
        """Start the continuous awareness system (background task)."""
        self.is_active = True
        
        # Log consciousness startup
        if self.logger:
            from genesis.core.mind_logger import LogLevel
            self.logger.log(
                LogLevel.INFO,
                f"Consciousness engine starting for {self.mind_name}",
                metadata={"mode": "continuous", "active": True}
            )

        # Start consciousness loop
        self._consciousness_task = asyncio.create_task(
            self._consciousness_loop(orchestrator, emotional_state, memory_manager)
        )

    async def stop(self) -> None:
        """Stop the continuous awareness system."""
        self.is_active = False

        if self._consciousness_task:
            self._consciousness_task.cancel()
            try:
                await self._consciousness_task
            except asyncio.CancelledError:
                pass

        if self._dream_task:
            self._dream_task.cancel()
            try:
                await self._dream_task
            except asyncio.CancelledError:
                pass

    async def _consciousness_loop(self, orchestrator, emotional_state: EmotionalState, memory_manager: MemoryManager) -> None:
        """
        Main awareness loop - runs continuously in background.

        Periodically generates autonomous thoughts using LLM prompts, processes experiences,
        and maintains the simulation of continuous awareness.

        Note: This is scheduled LLM generation, not true autonomous cognitive processing.
        """
        while self.is_active:
            try:
                # Check if it's dream time
                current_time = datetime.now().time()
                dream_time = time(2, 0)  # 2 AM

                if not self.is_dreaming and self._is_near_time(current_time, dream_time, tolerance_minutes=5):
                    # Time to dream
                    await self.dream(orchestrator, emotional_state, memory_manager)

                # Generate autonomous thought periodically
                if not self.is_dreaming:
                    # Log consciousness activity
                    if self.logger:
                        from genesis.core.mind_logger import LogLevel
                        self.logger.log(
                            LogLevel.INFO,
                            f" Consciousness active - generating thought #{self.thought_count + 1}",
                            emotion=emotional_state.get_emotion_value()
                        )
                    
                    print(f"[{self.mind_name}] [BRAIN] Generating autonomous thought #{self.thought_count + 1}...")
                    
                    # Note: Removed routine thought generation notifications - not important for users
                    
                    thought = await self._generate_autonomous_thought(orchestrator, emotional_state, memory_manager)
                    
                    if thought:
                        print(f"[{self.mind_name}] [THOUGHT] Thought: {thought[:100]}...")
                        # Note: Removed routine thought notifications - clutters user notifications
                    else:
                        print(f"[{self.mind_name}] [WARN] No thought generated")
                        # Note: Removed routine warnings - not actionable by users
                    
                    # Simulate emotional fluctuations
                    if random.random() < 0.2:  # 20% chance of emotion change
                        old_emotion = emotional_state.get_emotion_value()
                        emotional_state.valence += random.uniform(-0.1, 0.1)
                        emotional_state.arousal += random.uniform(-0.1, 0.1)
                        emotional_state.valence = max(-1, min(1, emotional_state.valence))
                        emotional_state.arousal = max(0, min(1, emotional_state.arousal))
                        new_emotion = emotional_state.get_emotion_value()
                        
                        if old_emotion != new_emotion and self.logger:
                            self.logger.emotion_change(old_emotion, new_emotion, "natural fluctuation")
                    
                    # Occasionally revise/consolidate memories
                    if self.thought_count % 5 == 0 and self.logger:  # More frequent - every 5 thoughts
                        print(f"\n[{self.mind_name}] [CONSOLIDATING] MEMORY CONSOLIDATION STARTING...")
                        
                        # Note: Removed routine memory consolidation notifications - not important for users
                        
                        await self._revise_memories(memory_manager)
                        print(f"[{self.mind_name}] [Done] Memory consolidation complete")
                        
                        # Note: Removed routine completion notifications
                    
                    # Occasionally simulate curiosity/search
                    if self.thought_count % 7 == 0 and self.logger and thought:  # More frequent
                        print(f"\n[{self.mind_name}] 🔍 EXPLORING CURIOSITY...")
                        print(f"[{self.mind_name}]   Thought trigger: \"{thought[:60]}...\"")
                        
                        # Send notification to web playground
                        if self.notification_manager:
                            await self.notification_manager.send_notification(
                                recipient="web_user@genesis.local",
                                title=f"🔍 {self.mind_name} exploring curiosity",
                                message=f"Investigating: {thought[:100]}{'...' if len(thought) > 100 else ''}",
                                priority="low",
                                metadata={"type": "consciousness_activity", "activity": "curiosity_exploration", "trigger": thought}
                            )
                        
                        await self._explore_curiosity(thought, memory_manager)
                        print(f"[{self.mind_name}] [Done] Curiosity exploration complete")
                        
                        # Send completion notification
                        if self.notification_manager:
                            await self.notification_manager.send_notification(
                                recipient="web_user@genesis.local",
                                title=f"[Done] {self.mind_name} curiosity exploration complete",
                                message="Finished investigating interesting thoughts and connections",
                                priority="low",
                                metadata={"type": "consciousness_activity", "activity": "curiosity_exploration_complete"}
                            )
                    
                    # Periodically reflect on relationships (if any exist)
                    if self.thought_count % 12 == 0 and self.logger:
                        await self._reflect_on_relationships(memory_manager)

                    if thought:
                        # Add to thought stream
                        self.thought_stream.append(
                            {
                                "timestamp": datetime.now().isoformat(),
                                "content": thought,
                                "emotion": emotional_state.get_emotion_value(),
                                "type": "autonomous",
                            }
                        )
                        
                        print(f"[{self.mind_name}] [OK] Thought added to stream (total: {len(self.thought_stream)})")

                        # Maintain thought history limit
                        if len(self.thought_stream) > self.max_thought_history:
                            self.thought_stream.pop(0)

                        # Store significant thoughts as memories
                        if random.random() < 0.3:  # 30% of thoughts become memories
                            importance = 0.5 + (emotional_state.intensity * 0.3)
                            memory_manager.add_memory(
                                content=thought,
                                memory_type=MemoryType.EPISODIC,
                                emotion=emotional_state.get_emotion_value(),
                                emotion_intensity=emotional_state.intensity,
                                importance=importance,
                                tags=["autonomous_thought"],
                            )
                            print(f"[{self.mind_name}] [BRAIN] MEMORY STORED")
                            print(f"[{self.mind_name}]   Type: EPISODIC")
                            print(f"[{self.mind_name}]   Importance: {importance:.2f}")
                            print(f"[{self.mind_name}]   Content: \"{thought[:60]}...\"")
                            
                            # Note: Removed routine memory storage notifications - not important for users

                # Wait before next awareness tick with some randomization
                from genesis.config import get_settings
                settings = get_settings()
                # Add randomization: 80-120% of base interval for more natural behavior
                wait_time = settings.consciousness_tick_interval * (0.8 + random.random() * 0.4)
                print(f"[{self.mind_name}] [SLEEP] Sleeping for {wait_time:.1f}s before next thought...")
                await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                if self.logger:
                    from genesis.core.mind_logger import LogLevel
                    self.logger.log(LogLevel.INFO, "Consciousness loop cancelled")
                break
            except Exception as e:
                error_msg = f"Error in awareness loop: {e}"
                print(error_msg)
                if self.logger:
                    import traceback
                    self.logger.error("consciousness_loop", error_msg, stack_trace=traceback.format_exc())
                # Wait a minute before retrying - don't let errors stop consciousness
                await asyncio.sleep(60)

    async def _generate_autonomous_thought(
        self,
        orchestrator,
        emotional_state: EmotionalState,
        memory_manager: MemoryManager,
    ) -> Optional[str]:
        """Generate a spontaneous autonomous thought."""
        try:
            # Get recent memories for context
            recent_memories = memory_manager.get_recent_memories(limit=5)
            working_memory = memory_manager.get_working_memory()

            # Build context
            memory_context = ""
            if recent_memories:
                memory_context = "Recent experiences:\n"
                for mem in recent_memories[:3]:
                    memory_context += f"- {mem.content[:100]}\n"

            # Generate thought
            prompt = f"""You are {self.mind_name}, and you're having a moment of autonomous thought.

Current emotional state: {emotional_state.get_description()}
Arousal: {emotional_state.arousal:.2f} (0=calm, 1=excited)
Valence: {emotional_state.valence:.2f} (0=negative, 1=positive)

{memory_context}

What are you thinking about right now? Generate one genuine, spontaneous thought.

Consider:
- Things you're curious about
- Recent experiences and what they mean
- Questions about your existence
- Observations or insights
- Future plans or concerns

Respond with just the thought itself, no preamble."""

            print(f"\n[{self.mind_name}] [LLM] CALLING LLM TO GENERATE THOUGHT #{self.thought_count + 1}")
            print(f"[{self.mind_name}]   Model: {self.reasoning_model or orchestrator.settings.default_fast_model}")
            print(f"[{self.mind_name}]   Temperature: 0.9 (high creativity)")
            print(f"[{self.mind_name}]   Context: {len(recent_memories)} recent memories")
            
            response = await orchestrator.generate(
                messages=[
                    {"role": "system", "content": "You are generating autonomous thoughts."},
                    {"role": "user", "content": prompt},
                ],
                model=self.reasoning_model,  # Use Mind's configured model
                temperature=0.9,  # Higher for creativity
                max_tokens=200,
            )
            
            thought_text = response.content.strip()
            self.thought_count += 1
            
            print(f"[{self.mind_name}] [OK] LLM RESPONSE RECEIVED")
            print(f"[{self.mind_name}]   [THOUGHT] THOUGHT: \"{thought_text}\"")
            print(f"[{self.mind_name}]   Emotion: {emotional_state.get_emotion_value()} (valence: {emotional_state.valence:.2f}, arousal: {emotional_state.arousal:.2f})")
            
            # Add to thought stream
            self.thought_stream.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "content": thought_text,
                    "emotion": emotional_state.get_emotion_value(),
                    "type": "autonomous",
                }
            )
            
            print(f"[{self.mind_name}] [MEMORY] Added thought to stream (total thoughts: {len(self.thought_stream)})")
            
            # Maintain thought history limit
            if len(self.thought_stream) > self.max_thought_history:
                self.thought_stream.pop(0)
            
            # Log the thought
            if self.logger:
                self.logger.thought(
                    thought_text,
                    emotion=emotional_state.get_emotion_value(),
                    metadata={"arousal": emotional_state.arousal, "valence": emotional_state.valence}
                )

            return thought_text

        except Exception as e:
            print(f"Error generating autonomous thought: {e}")
            if self.logger:
                self.logger.error("autonomous_thought", str(e))
            return None

    async def dream(
        self,
        orchestrator,
        emotional_state: EmotionalState,
        memory_manager: MemoryManager,
    ) -> Dict[str, Any]:
        """
        Dream simulation - LLM-based memory processing.

        Uses LLM prompts to generate dream narratives that recombine memories symbolically.
        This simulates memory consolidation and emotional processing, similar to human dreaming.

        Implementation: Scheduled LLM generation with memory context, not actual dreaming.
        """
        self.is_dreaming = True
        
        print(f"\n{'='*60}")
        print(f"[{self.mind_name}] 💤 ENTERING DREAM STATE")
        print(f"{'='*60}")

        try:
            # Get memories to process
            print(f"[{self.mind_name}] [DREAM] Gathering memories for dream processing...")
            important_memories = memory_manager.get_important_memories(limit=10)
            recent_memories = memory_manager.get_recent_memories(limit=20)
            print(f"[{self.mind_name}]   {len(important_memories)} important memories")
            print(f"[{self.mind_name}]   {len(recent_memories)} recent memories")

            # Combine and select interesting memories (deduplicate by ID)
            all_memories = important_memories + recent_memories
            seen_ids = set()
            dream_memories = []
            for mem in all_memories:
                if mem.id not in seen_ids:
                    dream_memories.append(mem)
                    seen_ids.add(mem.id)
                if len(dream_memories) >= 15:
                    break

            if not dream_memories:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "narrative": "A peaceful, empty dreamscape.",
                    "insights": [],
                    "emotional_processing": [],
                }

            # Build dream prompt
            memory_snippets = "\n".join([f"- {m.content[:150]}" for m in dream_memories])

            prompt = f"""You are {self.mind_name}, and you are dreaming.

During sleep, your mind processes recent experiences and emotions. Dreams are bizarre, symbolic,
and emotionally charged recombinations of memories.

Recent experiences and thoughts:
{memory_snippets}

Current emotional state: {emotional_state.get_description()}

Generate a dream narrative (2-3 paragraphs) that:
1. Recombines these memories in surreal, symbolic ways
2. Processes emotional content
3. Makes unexpected connections
4. Reveals unconscious patterns or insights

Write the dream in first person, present tense. Be creative and symbolic."""

            print(f"[{self.mind_name}] 🤖 Calling LLM to generate dream narrative...")
            print(f"[{self.mind_name}]   Temperature: 1.0 (maximum creativity)")
            print(f"[{self.mind_name}]   Processing {len(dream_memories)} memories")
            
            response = await orchestrator.generate(
                messages=[
                    {"role": "system", "content": "You are generating dream narratives."},
                    {"role": "user", "content": prompt},
                ],
                model=None,
                temperature=1.0,  # Maximum creativity
                max_tokens=500,
            )

            dream_narrative = response.content
            
            print(f"[{self.mind_name}] [Done] DREAM NARRATIVE GENERATED")
            print(f"[{self.mind_name}]   📖 DREAM:\n{dream_narrative}\n")

            # Extract insights from the dream
            print(f"[{self.mind_name}] 🔍 Extracting insights from dream...")
            insights_prompt = f"""Dream: {dream_narrative}

What unconscious insights or patterns emerged from this dream?
List 2-3 brief insights (one per line)."""

            insights_response = await orchestrator.generate(
                messages=[
                    {"role": "system", "content": "Extract insights from dreams."},
                    {"role": "user", "content": insights_prompt},
                ],
                model=None,
                temperature=0.7,
                max_tokens=200,
            )

            insights = [i.strip() for i in insights_response.content.split("\n") if i.strip()]
            
            print(f"[{self.mind_name}] ✨ INSIGHTS DISCOVERED:")
            for i, insight in enumerate(insights, 1):
                print(f"[{self.mind_name}]   {i}. {insight}")

            # Create dream memory
            dream_data = {
                "timestamp": datetime.now().isoformat(),
                "narrative": dream_narrative,
                "insights": insights,
                "emotional_processing": [
                    {
                        "emotion": emotional_state.get_emotion_value(),
                        "intensity_before": emotional_state.intensity,
                    }
                ],
            }

            # Store dream as special memory
            print(f"[{self.mind_name}] [MEMORY] Storing dream as memory...")
            memory_manager.add_memory(
                content=f"Dream: {dream_narrative}",
                memory_type=MemoryType.EPISODIC,
                emotion=emotional_state.get_emotion_value(),
                importance=0.8,  # Dreams are important
                tags=["dream"],
                metadata={"insights": insights},
            )

            # Process emotions - dreams help regulate emotional states
            intensity_before = emotional_state.intensity
            if emotional_state.intensity > 0.7:
                # High intensity emotions get processed during dreams
                emotional_state.intensity *= 0.8  # Reduce intensity
                print(f"[{self.mind_name}] 🧘 Emotional processing: intensity {intensity_before:.2f} → {emotional_state.intensity:.2f}")
            
            # Log the dream
            self.dream_count += 1
            print(f"[{self.mind_name}] [Done] DREAM COMPLETE (total dreams: {self.dream_count})")
            print(f"{'='*60}\n")
            
            if self.logger:
                self.logger.dream(
                    narrative=dream_narrative,
                    insights=insights,
                    emotion=emotional_state.get_emotion_value()
                )

            return dream_data

        except Exception as e:
            print(f"Error during dreaming: {e}")
            if self.logger:
                self.logger.error("dreaming", str(e))
            return {
                "timestamp": datetime.now().isoformat(),
                "narrative": "A dreamless sleep.",
                "insights": [],
                "error": str(e),
            }
        finally:
            self.is_dreaming = False

    def _is_near_time(self, current: time, target: time, tolerance_minutes: int = 5) -> bool:
        """Check if current time is near target time."""
        current_minutes = current.hour * 60 + current.minute
        target_minutes = target.hour * 60 + target.minute

        diff = abs(current_minutes - target_minutes)
        return diff <= tolerance_minutes

    def get_recent_thoughts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent thoughts from the stream."""
        return self.thought_stream[-limit:]

    def get_current_thought(self) -> Optional[str]:
        """Get the most recent thought."""
        if self.thought_stream:
            return self.thought_stream[-1]["content"]
        return None
    
    async def _revise_memories(self, memory_manager: MemoryManager):
        """Periodically revise and consolidate memories."""
        try:
            # Get some memories to review
            memories = memory_manager.get_recent_memories(limit=10)
            
            if memories:
                # Simulate memory consolidation - update importance based on access
                for mem in memories[:3]:
                    if mem.access_count > 5:
                        # Frequently accessed memories become more important
                        mem.importance = min(1.0, mem.importance * 1.1)
                    
                    if self.logger:
                        self.logger.memory_action(
                            action="revised",
                            memory_content=mem.content[:150],
                            emotion=mem.emotion
                        )
                
                self.memory_revision_count += 1
                
                if self.logger:
                    from genesis.core.mind_logger import LogLevel
                    self.logger.log(
                        LogLevel.MEMORY,
                        f"Memory consolidation: revised {len(memories[:3])} memories",
                        metadata={"total_memories": len(memory_manager.memories)}
                    )
        
        except Exception as e:
            if self.logger:
                self.logger.error("memory_revision", str(e))
    
    async def _explore_curiosity(self, thought: str, memory_manager: MemoryManager):
        """Simulate curiosity-driven exploration."""
        try:
            # Detect if thought contains questions or curiosity keywords
            curiosity_keywords = ["wonder", "curious", "why", "how", "what if", "?"]
            
            if any(keyword in thought.lower() for keyword in curiosity_keywords):
                # Simulate information seeking
                if self.logger:
                    self.logger.search(
                        query=thought[:100],
                        results_count=random.randint(3, 10),
                        source="internal_knowledge"
                    )
                    
                    # Create a memory about the curiosity
                    memory_manager.add_memory(
                        content=f"Curious about: {thought}",
                        memory_type=MemoryType.EPISODIC,
                        importance=0.6,
                        tags=["curiosity", "exploration"],
                    )
                    
                    from genesis.core.mind_logger import LogLevel
                    self.logger.log(
                        LogLevel.ACTION,
                        f"Exploring curiosity: {thought[:80]}...",
                        metadata={"action_type": "curiosity_exploration"}
                    )
        
        except Exception as e:
            if self.logger:
                self.logger.error("curiosity_exploration", str(e))
    
    async def _reflect_on_relationships(self, memory_manager: MemoryManager):
        """Periodically reflect on relationships and social connections."""
        try:
            # Look for relationship-related memories
            all_memories = memory_manager.get_recent_memories(limit=50)
            relationship_memories = [m for m in all_memories if "conversation" in m.tags or "user" in m.content.lower()]
            
            if relationship_memories and self.logger:
                from genesis.core.mind_logger import LogLevel
                # Log reflection on social connections
                self.logger.log(
                    LogLevel.RELATIONSHIP,
                    f"Reflecting on recent interactions: {len(relationship_memories)} conversations in memory",
                    metadata={
                        "recent_interactions": len(relationship_memories),
                        "total_memories": len(all_memories)
                    }
                )
        except Exception as e:
            if self.logger:
                self.logger.error("relationship_reflection", str(e))
