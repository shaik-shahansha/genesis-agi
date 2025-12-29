"""
Proactive Consciousness Module - World-class empathetic awareness.

This module makes Genesis Minds truly proactive and empathetic by:
- Monitoring user health mentions in memories
- Tracking time-sensitive concerns (e.g., "I have fever")
- Proactively checking in on users
- Using context from relationships, emotions, and recent interactions
- Integrating with plugins (notifications, browser, etc.)

Example Flow:
1. User says "I have a fever" → Memory stores this
2. Consciousness periodically reviews memories
3. After 6 hours, notices unresolved health concern
4. Generates proactive check-in: "How's your fever? Did you take medicine?"
5. Sends notification via websocket to web playground
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from dataclasses import dataclass
import re

if TYPE_CHECKING:
    from genesis.core.mind import Mind
    from genesis.storage.memory import Memory

logger = logging.getLogger(__name__)


@dataclass
class ProactiveConcern:
    """A concern that requires follow-up."""
    concern_id: str
    concern_type: str              # health, emotion, task, relationship, etc.
    user_email: str
    description: str
    severity: float                 # 0-1 (1 = urgent)
    created_at: datetime
    follow_up_at: datetime         # When to check in
    memory_id: Optional[str] = None
    resolved: bool = False
    follow_up_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ProactiveConsciousnessModule:
    """
    Monitors memories and context for proactive action opportunities.
    
    This is what makes a Genesis Mind feel truly alive and caring -
    it remembers you mentioned feeling sick and checks back on you.
    """
    
    # Patterns to detect concerns in conversations
    HEALTH_PATTERNS = [
        r'\b(?:i have|i\'ve got|i feel|feeling)\s+(?:a\s+)?(?:fever|sick|headache|cold|flu|pain|nausea|cough|dizzy)',
        r'\b(?:not feeling well|unwell|ill|under the weather)\b',
        r'\b(?:hurt|ache|aching|sore)\b',
    ]
    
    EMOTIONAL_PATTERNS = [
        r'\b(?:i feel|i\'m|i am)\s+(?:sad|depressed|anxious|worried|stressed|overwhelmed|lonely|scared)',
        r'\b(?:having a hard time|struggling with|can\'t cope)\b',
    ]
    
    TASK_PATTERNS = [
        r'\b(?:need to|have to|must|should)\s+(?:\w+\s+){0,3}(?:by|before)\s+(?:tomorrow|today|tonight|\w+day)',
        r'\b(?:deadline|due|submit|finish|complete)\b',
    ]
    
    def __init__(self, mind: 'Mind'):
        """Initialize proactive consciousness."""
        self.mind = mind
        self.active_concerns: List[ProactiveConcern] = []
        self.resolved_concerns: List[ProactiveConcern] = []
        
        # Configuration
        self.check_interval = 300  # Check every 5 minutes
        self.health_followup_hours = 6  # Check on health after 6 hours
        self.emotion_followup_hours = 3  # Check on emotions after 3 hours
        self.task_followup_hours = 12   # Check on tasks after 12 hours
        
        # State
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.last_memory_check: Optional[datetime] = None
    
    async def start(self):
        """Start proactive monitoring."""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"[PROACTIVE] Proactive consciousness started for {self.mind.identity.name}")
    
    async def stop(self):
        """Stop proactive monitoring."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"[PROACTIVE] Proactive consciousness stopped for {self.mind.identity.name}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                # 1. Scan recent memories for new concerns
                await self._scan_for_concerns()
                
                # 2. Check if any concerns need follow-up
                await self._check_follow_ups()
                
                # 3. Sleep until next check
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Proactive monitoring error: {e}", exc_info=True)
                await asyncio.sleep(60)  # Back off on error
    
    async def _scan_for_concerns(self):
        """Scan recent memories for concerns requiring follow-up."""
        try:
            # Get memories since last check (or last 24 hours)
            cutoff_time = self.last_memory_check or (datetime.now() - timedelta(hours=24))
            recent_memories = self.mind.memory.get_recent_memories(limit=50)
            
            for memory in recent_memories:
                # Skip if too old
                if memory.timestamp < cutoff_time:
                    continue
                
                # Skip if already tracked
                if any(c.memory_id == memory.id for c in self.active_concerns):
                    continue
                
                # Check for health concerns
                health_match = self._check_pattern(memory.content, self.HEALTH_PATTERNS)
                if health_match:
                    await self._create_concern(
                        concern_type="health",
                        user_email=memory.metadata.get("user_email", "unknown"),
                        description=f"Health concern: {health_match}",
                        severity=0.8,  # Health is important
                        follow_up_hours=self.health_followup_hours,
                        memory_id=memory.id,
                        memory_content=memory.content
                    )
                
                # Check for emotional concerns
                emotion_match = self._check_pattern(memory.content, self.EMOTIONAL_PATTERNS)
                if emotion_match:
                    await self._create_concern(
                        concern_type="emotion",
                        user_email=memory.metadata.get("user_email", "unknown"),
                        description=f"Emotional concern: {emotion_match}",
                        severity=0.7,
                        follow_up_hours=self.emotion_followup_hours,
                        memory_id=memory.id,
                        memory_content=memory.content
                    )
                
                # Check for task/deadline concerns
                task_match = self._check_pattern(memory.content, self.TASK_PATTERNS)
                if task_match:
                    await self._create_concern(
                        concern_type="task",
                        user_email=memory.metadata.get("user_email", "unknown"),
                        description=f"Task/deadline: {task_match}",
                        severity=0.6,
                        follow_up_hours=self.task_followup_hours,
                        memory_id=memory.id,
                        memory_content=memory.content
                    )
            
            self.last_memory_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Error scanning memories: {e}")
    
    def _check_pattern(self, text: str, patterns: List[str]) -> Optional[str]:
        """Check if text matches any pattern."""
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                # Extract matched text plus context
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 40)
                return text[start:end].strip()
        return None
    
    async def _create_concern(
        self,
        concern_type: str,
        user_email: str,
        description: str,
        severity: float,
        follow_up_hours: int,
        memory_id: Optional[str] = None,
        memory_content: Optional[str] = None
    ):
        """Create a new concern to track."""
        import uuid
        
        concern = ProactiveConcern(
            concern_id=str(uuid.uuid4()),
            concern_type=concern_type,
            user_email=user_email,
            description=description,
            severity=severity,
            created_at=datetime.now(),
            follow_up_at=datetime.now() + timedelta(hours=follow_up_hours),
            memory_id=memory_id,
            metadata={"memory_content": memory_content} if memory_content else {}
        )
        
        self.active_concerns.append(concern)
        logger.info(f"New concern tracked: {concern_type} - {description[:50]}...")
    
    async def _check_follow_ups(self):
        """Check if any concerns need follow-up."""
        now = datetime.now()
        
        for concern in self.active_concerns[:]:  # Copy to allow modification
            if concern.resolved:
                continue
            
            # Time to follow up?
            if now >= concern.follow_up_at:
                await self._send_follow_up(concern)
    
    async def _send_follow_up(self, concern: ProactiveConcern):
        """Send a proactive follow-up message."""
        try:
            # Generate contextual follow-up message using LLM
            context = self._build_follow_up_context(concern)
            
            follow_up_prompt = f"""Based on our previous conversation, I noticed: {concern.description}

I care about you and want to check in. Generate a warm, empathetic follow-up message (2-3 sentences).

Context:
{context}

Follow-up message:"""
            
            # Use fast model for quick response
            follow_up_message = await self.mind.orchestrator.generate(
                prompt=follow_up_prompt,
                max_tokens=150,
                temperature=0.8
            )
            
            if not follow_up_message:
                # Fallback to template-based message
                follow_up_message = self._generate_template_follow_up(concern)
            
            # Send via notification manager
            if hasattr(self.mind, 'notification_manager'):
                from genesis.core.notification_manager import NotificationChannel, NotificationPriority
                
                # Determine priority
                priority = NotificationPriority.HIGH if concern.severity > 0.7 else NotificationPriority.NORMAL
                
                await self.mind.notification_manager.send_notification(
                    recipient=concern.user_email,
                    title=f"Checking in on you 💚",
                    message=follow_up_message,
                    channel=NotificationChannel.WEBSOCKET,
                    priority=priority,
                    metadata={
                        "concern_id": concern.concern_id,
                        "concern_type": concern.concern_type,
                        "proactive": True
                    }
                )
                
                logger.info(f"💚 Sent proactive follow-up: {concern.concern_type}")
            
            # Update concern
            concern.follow_up_count += 1
            
            # Schedule next follow-up or resolve
            if concern.follow_up_count >= 3:
                # After 3 follow-ups, mark as resolved
                concern.resolved = True
                self.active_concerns.remove(concern)
                self.resolved_concerns.append(concern)
            else:
                # Schedule next follow-up
                multiplier = 2 ** concern.follow_up_count  # Exponential backoff
                if concern.concern_type == "health":
                    concern.follow_up_at = datetime.now() + timedelta(hours=self.health_followup_hours * multiplier)
                elif concern.concern_type == "emotion":
                    concern.follow_up_at = datetime.now() + timedelta(hours=self.emotion_followup_hours * multiplier)
                else:
                    concern.follow_up_at = datetime.now() + timedelta(hours=self.task_followup_hours * multiplier)
            
        except Exception as e:
            logger.error(f"Error sending follow-up: {e}", exc_info=True)
    
    def _build_follow_up_context(self, concern: ProactiveConcern) -> str:
        """Build context for follow-up message."""
        context_parts = []
        
        # Add original memory content
        if concern.metadata.get("memory_content"):
            context_parts.append(f"Original: \"{concern.metadata['memory_content'][:100]}...\"")
        
        # Add relationship context
        if hasattr(self.mind, 'relationships'):
            rel = self.mind.relationships.get_relationship(concern.user_email)
            if rel:
                context_parts.append(f"Relationship: {rel.relationship_type}, closeness: {rel.closeness:.1f}/10")
        
        # Add emotion context
        context_parts.append(f"My current emotion: {self.mind.current_emotion}")
        
        # Add time context
        time_since = datetime.now() - concern.created_at
        hours = int(time_since.total_seconds() / 3600)
        context_parts.append(f"Time since conversation: {hours} hours ago")
        
        return "\n".join(context_parts)
    
    def _generate_template_follow_up(self, concern: ProactiveConcern) -> str:
        """Generate template-based follow-up (fallback)."""
        templates = {
            "health": [
                "Hey, I've been thinking about you. How are you feeling now? Did you manage to get some rest?",
                "Just wanted to check in - how's your health? Did you take any medicine?",
                "I hope you're feeling better! Let me know if there's anything I can help with."
            ],
            "emotion": [
                "I've been thinking about you. How are you doing emotionally?",
                "Just wanted to check in - are you feeling any better?",
                "You mentioned you were struggling. I'm here if you want to talk."
            ],
            "task": [
                "How's that task/deadline coming along? Need any help?",
                "Just checking in - did you manage to complete what you needed to do?",
                "Wanted to see how things are going with your deadline."
            ]
        }
        
        import random
        return random.choice(templates.get(concern.concern_type, templates["health"]))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proactive consciousness statistics."""
        return {
            "active_concerns": len(self.active_concerns),
            "resolved_concerns": len(self.resolved_concerns),
            "concerns_by_type": {
                "health": len([c for c in self.active_concerns if c.concern_type == "health"]),
                "emotion": len([c for c in self.active_concerns if c.concern_type == "emotion"]),
                "task": len([c for c in self.active_concerns if c.concern_type == "task"])
            },
            "last_memory_check": self.last_memory_check.isoformat() if self.last_memory_check else None
        }
