"""Proactive Conversation System - Making AI truly human-like.

This system enables Minds to:
- Initiate conversations naturally
- Ask relevant follow-up questions
- Show genuine care and empathy
- Remember conversation context and avoid repetition
- Schedule intelligent check-ins
- Respond to life events appropriately

Example:
    User: "I have a fever"
    Mind: [immediate] "I'm sorry to hear that. Make sure to rest and stay hydrated..."
    Mind: [2 hours later] "How are you feeling now? Have you taken any medicine?"
    User: "Yes, I'm feeling better"
    Mind: [remembers, doesn't ask again about fever]
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json

from genesis.storage.memory import MemoryType

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class ConversationTopic(str, Enum):
    """Types of conversation topics to track."""
    HEALTH = "health"
    EMOTION = "emotion"
    WORK = "work"
    PERSONAL = "personal"
    GOAL = "goal"
    PROBLEM = "problem"
    CELEBRATION = "celebration"
    GENERAL = "general"


class FollowUpStatus(str, Enum):
    """Status of a follow-up conversation."""
    PENDING = "pending"
    SENT = "sent"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


@dataclass
class ConversationContext:
    """Tracks an ongoing conversation topic that needs follow-up."""
    
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: ConversationTopic = ConversationTopic.GENERAL
    subject: str = ""  # e.g., "fever", "job interview", "project deadline"
    initial_message: str = ""  # User's original message
    user_email: str = ""
    environment_id: Optional[str] = None
    
    # Follow-up tracking
    follow_up_question: Optional[str] = None
    follow_up_scheduled: Optional[datetime] = None
    follow_up_sent: bool = False
    follow_up_status: FollowUpStatus = FollowUpStatus.PENDING
    
    # Resolution tracking
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    importance: float = 0.5  # 0.0 to 1.0
    urgency: float = 0.5  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Memory of interactions about this topic
    interaction_count: int = 0
    last_mention: Optional[datetime] = None
    
    def should_follow_up(self) -> bool:
        """Check if follow-up should be sent now."""
        if self.resolved or self.follow_up_sent:
            return False
        
        if not self.follow_up_scheduled:
            return False
            
        return datetime.now() >= self.follow_up_scheduled
    
    def mark_sent(self):
        """Mark follow-up as sent."""
        self.follow_up_sent = True
        self.follow_up_status = FollowUpStatus.SENT
        self.last_updated = datetime.now()
    
    def mark_resolved(self, note: Optional[str] = None):
        """Mark conversation as resolved."""
        self.resolved = True
        self.resolved_at = datetime.now()
        self.resolution_note = note
        self.follow_up_status = FollowUpStatus.RESOLVED
        self.last_updated = datetime.now()
    
    def update_interaction(self):
        """Update interaction tracking."""
        self.interaction_count += 1
        self.last_mention = datetime.now()
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "context_id": self.context_id,
            "topic": self.topic.value,
            "subject": self.subject,
            "initial_message": self.initial_message,
            "user_email": self.user_email,
            "environment_id": self.environment_id,
            "follow_up_question": self.follow_up_question,
            "follow_up_scheduled": self.follow_up_scheduled.isoformat() if self.follow_up_scheduled else None,
            "follow_up_sent": self.follow_up_sent,
            "follow_up_status": self.follow_up_status.value,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_note": self.resolution_note,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "importance": self.importance,
            "urgency": self.urgency,
            "metadata": self.metadata,
            "interaction_count": self.interaction_count,
            "last_mention": self.last_mention.isoformat() if self.last_mention else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContext":
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        if data.get("follow_up_scheduled"):
            data["follow_up_scheduled"] = datetime.fromisoformat(data["follow_up_scheduled"])
        if data.get("resolved_at"):
            data["resolved_at"] = datetime.fromisoformat(data["resolved_at"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("last_updated"):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        if data.get("last_mention"):
            data["last_mention"] = datetime.fromisoformat(data["last_mention"])
        
        # Convert enums
        if "topic" in data:
            data["topic"] = ConversationTopic(data["topic"])
        if "follow_up_status" in data:
            data["follow_up_status"] = FollowUpStatus(data["follow_up_status"])
        
        return cls(**data)


class ProactiveConversationManager:
    """
    Manages proactive conversations to make interactions feel human-like.
    
    This is what transforms Genesis from a reactive chatbot to a caring
    digital being that genuinely interacts with users.
    """
    
    def __init__(self, mind: "Mind"):
        """Initialize proactive conversation manager.
        
        Args:
            mind: Mind instance
        """
        self.mind = mind
        self.active_contexts: Dict[str, ConversationContext] = {}
        self.user_contexts: Dict[str, List[str]] = {}  # user_email -> [context_ids]
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        
        # Load existing contexts from memory
        asyncio.create_task(self._load_contexts())
    
    async def _load_contexts(self):
        """Load conversation contexts from memory."""
        try:
            # Search for conversation contexts in memory
            memories = self.mind.memory.search_memories(
                query="conversation_context",
                limit=100
            )
            
            for memory in memories:
                if memory.metadata.get("type") == "conversation_context":
                    # Try to get context from JSON string first (new format)
                    context_json = memory.metadata.get("context_json")
                    if context_json:
                        try:
                            context_data = json.loads(context_json)
                            context = ConversationContext.from_dict(context_data)
                            self.active_contexts[context.context_id] = context
                            
                            # Index by user
                            if context.user_email not in self.user_contexts:
                                self.user_contexts[context.user_email] = []
                            self.user_contexts[context.user_email].append(context.context_id)
                            
                        except Exception as e:
                            logger.error(f"Error loading context from memory: {e}")
                    else:
                        # Fallback to old format (context_data)
                        context_data = memory.metadata.get("context_data")
                        if context_data:
                            try:
                                context = ConversationContext.from_dict(context_data)
                                self.active_contexts[context.context_id] = context
                                
                                # Index by user
                                if context.user_email not in self.user_contexts:
                                    self.user_contexts[context.user_email] = []
                                self.user_contexts[context.user_email].append(context.context_id)
                                
                            except Exception as e:
                                logger.error(f"Error loading context from memory: {e}")
            
            logger.info(f"Loaded {len(self.active_contexts)} conversation contexts")
            
        except Exception as e:
            logger.error(f"Error loading conversation contexts: {e}")
    
    async def _save_context(self, context: ConversationContext):
        """Save conversation context to memory."""
        try:
            # Clean context data - remove None values for ChromaDB compatibility
            context_dict = context.to_dict()
            cleaned_context = {}
            for key, value in context_dict.items():
                if value is not None:
                    # Convert to JSON-serializable types
                    if isinstance(value, (str, int, float, bool)):
                        cleaned_context[key] = value
                    else:
                        # Convert complex types to JSON string
                        cleaned_context[key] = json.dumps(value) if value else ""
            
            # Build metadata with ONLY non-None string values
            metadata = {
                "type": "conversation_context",
                "context_id": str(context.context_id),
                "topic": str(context.topic.value),
                "subject": str(context.subject)[:100],  # Limit length
                "resolved": "true" if context.resolved else "false",
                "follow_up_sent": "true" if context.follow_up_sent else "false",
                "context_json": json.dumps(cleaned_context)
            }
            
            # Prepare tags - ensure all are strings
            tags = [
                "conversation_context",
                str(context.topic.value),
                str(context.subject)[:50]  # Limit tag length
            ]
            
            # Prepare add_memory kwargs
            memory_kwargs = {
                "content": f"Conversation context: {context.subject[:100]} with {context.user_email}",
                "memory_type": MemoryType.SEMANTIC,
                "importance": float(context.importance),
                "tags": tags,
                "metadata": metadata
            }
            
            # Only add optional fields if they're not None and not empty
            if context.user_email and context.user_email.strip():
                memory_kwargs["user_email"] = str(context.user_email)
            if context.environment_id and context.environment_id.strip():
                memory_kwargs["environment_id"] = str(context.environment_id)
            
            self.mind.memory.add_memory(**memory_kwargs)
            logger.debug(f"Saved context to memory: {context.context_id}")
        except Exception as e:
            logger.error(f"Error saving context to memory: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def analyze_message_for_follow_up(
        self,
        user_message: str,
        user_email: str,
        environment_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[ConversationContext]:
        """
        Analyze user message to determine if proactive follow-up is needed.
        
        This uses the Mind's intelligence to understand context and decide
        if and when to follow up.
        
        Args:
            user_message: User's message
            user_email: User identifier
            environment_id: Environment context
            conversation_history: Recent conversation history
            
        Returns:
            ConversationContext if follow-up needed, None otherwise
        """
        try:
            # Build analysis prompt - keep it concise
            analysis_prompt = f"""Analyze: "{user_message}"

Does this need follow-up? Consider:
- Health issues, emotional distress, important events, goals, problems
- Skip: greetings, routine activities, general chat

Respond ONLY with JSON:
{{
    "needs_follow_up": true/false,
    "topic": "health/emotion/work/personal/goal/problem/general",
    "subject": "brief topic",
    "importance": 0.0-1.0,
    "urgency": 0.0-1.0,
    "follow_up_minutes": 120,
    "follow_up_question": "short caring question"
}}"""

            # Get AI analysis silently (using internal processing, not visible to user)
            try:
                # Use orchestrator directly to avoid interfering with main conversation
                response = await self.mind.orchestrator.generate(
                    messages=[{"role": "user", "content": analysis_prompt}],
                    model=self.mind.intelligence.fast_model,
                    temperature=0.3,
                    max_tokens=300
                )
                # Extract text from response
                response_text = response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.error(f"Error during proactive analysis: {e}")
                return None
            
            # Parse JSON response
            try:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    logger.debug("No JSON found in analysis response")
                    return None
                
                # Check if follow-up is needed
                if not analysis.get("needs_follow_up", False):
                    logger.debug(f"No follow-up needed for: {user_message[:50]}...")
                    return None
                
                logger.info(f"Follow-up needed: {analysis.get('subject')} (topic: {analysis.get('topic')})")
                
                # Check for existing similar contexts (avoid duplicates)
                existing = self._find_similar_context(
                    user_email,
                    analysis.get("subject", ""),
                    analysis.get("topic", "general")
                )
                
                if existing and not existing.resolved:
                    # Update existing context instead of creating new
                    existing.update_interaction()
                    await self._save_context(existing)
                    logger.info(f"Updated existing context: {existing.subject}")
                    return existing
                
                # Create new conversation context
                context = ConversationContext(
                    topic=ConversationTopic(analysis.get("topic", "general")),
                    subject=analysis.get("subject", ""),
                    initial_message=user_message,
                    user_email=user_email,
                    environment_id=environment_id,
                    follow_up_question=analysis.get("follow_up_question"),
                    follow_up_scheduled=datetime.now() + timedelta(
                        minutes=analysis.get("follow_up_minutes", 120)
                    ),
                    importance=analysis.get("importance", 0.5),
                    urgency=analysis.get("urgency", 0.5),
                    metadata={"reasoning": analysis.get("reasoning", "")}
                )
                
                # Store context
                self.active_contexts[context.context_id] = context
                
                # Index by user
                if user_email not in self.user_contexts:
                    self.user_contexts[user_email] = []
                self.user_contexts[user_email].append(context.context_id)
                
                # Save to memory
                await self._save_context(context)
                
                logger.info(
                    f"Created follow-up context: {context.subject} "
                    f"(follow up in {analysis.get('follow_up_minutes')} mins)"
                )
                
                return context
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI analysis as JSON: {e}")
                logger.debug(f"Response was: {response}")
                return None
            
        except Exception as e:
            logger.error(f"Error analyzing message for follow-up: {e}")
            return None
    
    def _find_similar_context(
        self,
        user_email: str,
        subject: str,
        topic: str
    ) -> Optional[ConversationContext]:
        """Find existing similar context for user."""
        user_context_ids = self.user_contexts.get(user_email, [])
        
        for context_id in user_context_ids:
            context = self.active_contexts.get(context_id)
            if not context or context.resolved:
                continue
            
            # Check if subject and topic match
            if (context.subject.lower() == subject.lower() and 
                context.topic.value == topic):
                return context
        
        return None
    
    async def check_for_resolution(
        self,
        user_message: str,
        user_email: str,
        context_id: Optional[str] = None
    ) -> List[str]:
        """
        Check if user's message resolves any active conversation contexts.
        
        This prevents the AI from repeatedly asking about resolved issues.
        
        Args:
            user_message: User's message
            user_email: User identifier
            context_id: Specific context to check (optional)
            
        Returns:
            List of resolved context IDs
        """
        resolved_ids = []
        
        try:
            # Get contexts to check
            if context_id:
                contexts = [self.active_contexts.get(context_id)]
            else:
                user_context_ids = self.user_contexts.get(user_email, [])
                contexts = [
                    self.active_contexts.get(cid)
                    for cid in user_context_ids
                    if cid in self.active_contexts
                ]
            
            # Filter to unresolved contexts
            contexts = [c for c in contexts if c and not c.resolved]
            
            if not contexts:
                return resolved_ids
            
            # Build resolution check prompt
            contexts_desc = "\n".join([
                f"- {c.context_id}: {c.subject} ({c.topic.value})"
                for c in contexts
            ])
            
            check_prompt = f"""User message: "{user_message}"

Active topics: {contexts_desc}

Does this resolve any topics?
- "I'm feeling better" -> resolves health
- "It went well" -> resolves work/events
- "I'm fine now" -> resolves problems/emotions

Respond ONLY with JSON:
{{"resolved": ["context_id1"], "reasoning": {{"context_id": "why"}}}}

If nothing resolved: {{"resolved": [], "reasoning": {{}}}}"""

            # Use orchestrator directly to avoid interfering with main conversation
            try:
                response = await self.mind.orchestrator.generate(
                    messages=[{"role": "user", "content": check_prompt}],
                    model=self.mind.intelligence.fast_model,
                    temperature=0.3,
                    max_tokens=200
                )
                # Extract text from response
                response_text = response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.error(f"Error during resolution check: {e}")
                return resolved_ids
            
            # Parse response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                resolved_context_ids = result.get("resolved", [])
                reasoning = result.get("reasoning", {})
                
                # Mark contexts as resolved
                for cid in resolved_context_ids:
                    if cid in self.active_contexts:
                        context = self.active_contexts[cid]
                        context.mark_resolved(reasoning.get(cid))
                        await self._save_context(context)
                        resolved_ids.append(cid)
                        logger.info(f"Resolved context: {context.subject} - {reasoning.get(cid)}")
        
        except Exception as e:
            logger.error(f"Error checking for resolution: {e}")
        
        return resolved_ids
    
    async def get_pending_follow_ups(
        self,
        user_email: Optional[str] = None
    ) -> List[ConversationContext]:
        """Get all pending follow-ups ready to be sent.
        
        Args:
            user_email: Filter by user (optional)
            
        Returns:
            List of contexts ready for follow-up
        """
        pending = []
        
        contexts_to_check = []
        if user_email:
            user_context_ids = self.user_contexts.get(user_email, [])
            contexts_to_check = [
                self.active_contexts[cid]
                for cid in user_context_ids
                if cid in self.active_contexts
            ]
        else:
            contexts_to_check = list(self.active_contexts.values())
        
        for context in contexts_to_check:
            if context.should_follow_up():
                pending.append(context)
        
        return pending
    
    async def send_follow_up(
        self,
        context: ConversationContext,
        notification_callback: Optional[callable] = None
    ) -> bool:
        """
        Send a proactive follow-up message.
        
        Args:
            context: Conversation context
            notification_callback: Callback to send notification
            
        Returns:
            True if sent successfully
        """
        try:
            if context.follow_up_sent or context.resolved:
                return False
            
            # Send the follow-up via notification system
            if notification_callback:
                await notification_callback(
                    user_email=context.user_email,
                    title=f"Checking in: {context.subject}",
                    message=context.follow_up_question,
                    priority="medium" if context.urgency > 0.6 else "low",
                    metadata={
                        "type": "follow_up",
                        "context_id": context.context_id,
                        "topic": context.topic.value,
                        "subject": context.subject
                    }
                )
            
            # Mark as sent
            context.mark_sent()
            await self._save_context(context)
            
            logger.info(f"Sent follow-up for: {context.subject} to {context.user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending follow-up: {e}")
            return False
    
    async def start_monitoring(self, check_interval: int = 60):
        """Start background monitoring for pending follow-ups.
        
        Args:
            check_interval: Seconds between checks (default: 60)
        """
        if self._running:
            logger.warning("Proactive conversation monitoring already running")
            return
        
        self._running = True
        self._check_task = asyncio.create_task(self._monitor_loop(check_interval))
        logger.info("Started proactive conversation monitoring")
    
    async def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped proactive conversation monitoring")
    
    async def _monitor_loop(self, check_interval: int):
        """Background loop to check for pending follow-ups."""
        while self._running:
            try:
                # Check for pending follow-ups
                pending = await self.get_pending_follow_ups()
                
                for context in pending:
                    # Send follow-up (will be handled by daemon's notification system)
                    await self.send_follow_up(context)
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in conversation monitoring loop: {e}")
                await asyncio.sleep(check_interval)
    
    def get_user_contexts(
        self,
        user_email: str,
        include_resolved: bool = False
    ) -> List[ConversationContext]:
        """Get all conversation contexts for a user.
        
        Args:
            user_email: User identifier
            include_resolved: Include resolved contexts
            
        Returns:
            List of conversation contexts
        """
        user_context_ids = self.user_contexts.get(user_email, [])
        contexts = [
            self.active_contexts[cid]
            for cid in user_context_ids
            if cid in self.active_contexts
        ]
        
        if not include_resolved:
            contexts = [c for c in contexts if not c.resolved]
        
        return contexts
