"""
Proactive Consciousness Module - World-class empathetic awareness.

This module makes Genesis Minds truly proactive and empathetic by:
- Using LLM to intelligently detect concerns (not regex patterns)
- Monitoring user health mentions in memories
- Tracking time-sensitive concerns (e.g., "I have fever", "finish work in 5 mins")
- Proactively checking in on users
- Using context from relationships, emotions, and recent interactions
- Integrating with plugins (notifications, browser, etc.)

Example Flow:
1. User says "I have a fever" → Memory stores this
2. LLM analyzes memory and detects health concern
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
        r'\b(?:i have|i\'ve got|i got)\s+(?:a\s+)?(?:fever|sick|headache|cold|flu|pain|nausea|cough|dizzy|migraine|stomachache)\b',
        r'\b(?:i feel|i\'m feeling|feeling)\s+(?:sick|ill|unwell|nauseous|dizzy|faint|weak)\b',
        r'\b(?:not feeling well|feeling unwell|under the weather|really sick|very sick|quite sick)\b',
        r'\b(?:my head|my stomach|my back|my throat)\s+(?:hurts|aches|is aching|is sore|is killing me)\b',
        r'\b(?:bad fever|high fever|terrible headache|awful headache|bad headache)\b',
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
        
        # Initialize LLM-based concern analyzer
        from genesis.core.concern_analyzer import LLMConcernAnalyzer
        self.concern_analyzer = LLMConcernAnalyzer(mind)
        
        # Configuration
        self.check_interval = 300  # Check every 5 minutes
        self.health_followup_hours = 6  # Check on health after 6 hours
        self.emotion_followup_hours = 3  # Check on emotions after 3 hours
        self.task_followup_hours = 12   # Check on tasks after 12 hours
        
        # State
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.last_memory_check: Optional[datetime] = None
        
        logger.info("[PROACTIVE] Initialized with LLM-based concern analyzer")
    
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
        """Scan recent memories for concerns requiring follow-up using LLM analysis."""
        try:
            # Get memories since last check (or last 24 hours)
            cutoff_time = self.last_memory_check or (datetime.now() - timedelta(hours=24))
            recent_memories = self.mind.memory.get_recent_memories(limit=50)
            
            logger.info(f"[PROACTIVE] Scanning {len(recent_memories)} recent memories using LLM...")
            
            scanned_count = 0
            for memory in recent_memories:
                # Skip if too old
                if memory.timestamp < cutoff_time:
                    continue
                
                scanned_count += 1
                
                # Skip if already tracked
                if any(c.memory_id == memory.id for c in self.active_concerns):
                    continue
                
                # Use LLM to analyze this memory for concerns
                logger.info(f"[PROACTIVE] Analyzing: {memory.content[:80]}...")
                
                analysis = await self.concern_analyzer.analyze_conversation(
                    conversation_text=memory.content,
                    user_email=memory.user_email
                )
                
                # If concern detected with sufficient confidence
                if analysis.has_concern and analysis.confidence >= 0.7 and analysis.requires_followup:
                    logger.info(f"[PROACTIVE] ✅ {analysis.concern_type.upper()} concern detected!")
                    logger.info(f"[PROACTIVE]    Confidence: {analysis.confidence:.2f}")
                    logger.info(f"[PROACTIVE]    Severity: {analysis.severity}")
                    logger.info(f"[PROACTIVE]    Urgency: {analysis.urgency}")
                    
                    # Parse deadline if present
                    deadline = None
                    if analysis.has_deadline and analysis.deadline_datetime:
                        try:
                            deadline = datetime.fromisoformat(analysis.deadline_datetime)
                            logger.info(f"[PROACTIVE]    Deadline: {deadline.strftime('%Y-%m-%d %H:%M')}")
                        except:
                            pass
                    
                    # Map severity to numeric value
                    severity_map = {'low': 0.4, 'moderate': 0.6, 'high': 0.8, 'critical': 0.95}
                    severity = severity_map.get(analysis.severity, 0.6)
                    
                    await self._create_concern(
                        concern_type=analysis.concern_type,
                        user_email=memory.user_email or "unknown",
                        description=analysis.description,
                        severity=severity,
                        follow_up_hours=analysis.suggested_followup_hours,
                        memory_id=memory.id,
                        memory_content=memory.content,
                        deadline=deadline,
                        urgency=analysis.urgency,
                        llm_followup_message=analysis.followup_message
                    )
            
            logger.info(f"[PROACTIVE] Scanned {scanned_count} memories, found {len([c for c in self.active_concerns if c.created_at > cutoff_time])} new concerns")
            self.last_memory_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Error scanning memories: {e}", exc_info=True)
    
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
        memory_content: Optional[str] = None,
        deadline: Optional[datetime] = None,
        urgency: str = "normal",
        llm_followup_message: Optional[str] = None
    ):
        """Create a new concern to track."""
        import uuid
        
        # For tasks with deadlines, adjust follow-up time based on urgency
        if concern_type == "task" and deadline:
            time_until_deadline = (deadline - datetime.now()).total_seconds() / 3600
            
            if urgency == 'critical':
                # Check in halfway to deadline or in 2 minutes (whichever is sooner)
                follow_up_hours = min(0.03, time_until_deadline / 2)  # 0.03 hours = ~2 minutes
            elif urgency == 'high':
                # Check in at 75% of time to deadline
                follow_up_hours = max(0.5, time_until_deadline * 0.75)
            else:
                # Normal tasks: check in at 50% of time or 6 hours
                follow_up_hours = min(6, time_until_deadline * 0.5)
        
        concern = ProactiveConcern(
            concern_id=str(uuid.uuid4()),
            concern_type=concern_type,
            user_email=user_email,
            description=description,
            severity=severity,
            created_at=datetime.now(),
            follow_up_at=datetime.now() + timedelta(hours=follow_up_hours),
            memory_id=memory_id,
            metadata={
                "memory_content": memory_content,
                "llm_followup_message": llm_followup_message
            } if memory_content or llm_followup_message else {},
            deadline=deadline,
            task_status="pending" if concern_type == "task" else "pending",
            urgency=urgency
        )
        
        self.active_concerns.append(concern)
        
        urgency_emoji = {"critical": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}
        emoji = urgency_emoji.get(urgency, "⚪")
        
        logger.info(f"{emoji} New {concern_type} tracked: {description[:50]}... (urgency: {urgency})")
        if deadline:
            logger.info(f"   ⏰ Deadline: {deadline.strftime('%Y-%m-%d %H:%M')} (follow-up in {follow_up_hours:.1f}h)")
    
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
            # Use LLM-generated message if available, otherwise generate new one
            follow_up_message = concern.metadata.get("llm_followup_message")
            
            if not follow_up_message:
                # Generate contextual follow-up message using LLM
                context = self._build_follow_up_context(concern)
                
                follow_up_prompt = f"""Based on our previous conversation, I noticed: {concern.description}

I care about you and want to check in. Generate a warm, empathetic follow-up message (2-3 sentences).

Context:
{context}

Follow-up message:"""
                
                # Use fast model for quick response
                response = await self.mind.orchestrator.generate(
                    messages=[{"role": "user", "content": follow_up_prompt}],
                    model=self.mind.intelligence.fast_model,
                    max_tokens=150,
                    temperature=0.8
                )
                
                follow_up_message = response.content if response else None
            
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
    
    async def process_user_response(self, user_message: str, user_email: str) -> bool:
        """Process user response to check if any concerns should be resolved.
        
        Returns True if a concern was resolved.
        """
        # Patterns indicating user is fine/concern resolved
        RESOLUTION_PATTERNS = [
            r'\b(?:i\'m|i am|im)\s+(?:fine|good|better|ok|okay|alright|well|much better|feeling better)\b',
            r'\b(?:feel|feeling)\s+(?:better|good|fine|great|much better|so much better|a lot better)\b',
            r'\b(?:all good|all better|recovered|feeling great|doing better|doing fine|doing great|doing well)\b',
            r'\b(?:don\'t worry|no worries|thanks for checking|thank you for checking|glad you asked)\b',
            r'\b(?:much better now|doing better now|feeling much better|feeling way better)\b',
            r'\b(?:i\'m okay now|i\'m fine now|i\'m good now|all fine now)\b',
        ]
        
        text_lower = user_message.lower()
        is_resolution = any(re.search(pattern, text_lower) for pattern in RESOLUTION_PATTERNS)
        
        if not is_resolution:
            return False
        
        # Find active concerns for this user
        user_concerns = [c for c in self.active_concerns if c.user_email == user_email and not c.resolved]
        
        if not user_concerns:
            return False
        
        # Resolve the most recent concern (assume user is responding to latest follow-up)
        concern = user_concerns[-1]
        concern.resolved = True
        self.active_concerns.remove(concern)
        self.resolved_concerns.append(concern)
        
        logger.info(f"✅ Resolved concern: {concern.concern_type} for {user_email}")
        
        # Send positive acknowledgment notification
        if hasattr(self.mind, 'notification_manager'):
            from genesis.core.notification_manager import NotificationChannel, NotificationPriority
            
            await self.mind.notification_manager.send_notification(
                recipient=user_email,
                title="Glad you're doing better! 💚",
                message="I'm happy to hear that! I'll keep an eye out for you.",
                channel=NotificationChannel.WEBSOCKET,
                priority=NotificationPriority.LOW,
                metadata={"concern_resolved": concern.concern_id}
            )
        
        return True
    
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
