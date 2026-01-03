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
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['created_at'] = self.created_at.isoformat()
        data['follow_up_at'] = self.follow_up_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProactiveConcern':
        """Create from dictionary."""
        # Convert ISO format strings back to datetime objects
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['follow_up_at'] = datetime.fromisoformat(data['follow_up_at'])
        return cls(**data)


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
        self.active_concerns: List[ProactiveConcern] = []  # In-memory cache
        self.resolved_concerns: List[ProactiveConcern] = []  # In-memory cache
        
        # Initialize LLM-based concern analyzer
        from genesis.core.concern_analyzer import LLMConcernAnalyzer
        self.concern_analyzer = LLMConcernAnalyzer(mind)
        
        # Initialize intelligent timing engine
        from genesis.core.intelligent_timing import IntelligentTimingEngine
        self.timing_engine = IntelligentTimingEngine(mind)
        
        # Initialize scenario handlers
        from genesis.core.scenario_handlers import (
            HealthScenarioHandler,
            ExamScenarioHandler,
            TaskScenarioHandler,
            ConversationScenarioHandler,
            ScenarioState
        )
        self.health_handler = HealthScenarioHandler(mind)
        self.exam_handler = ExamScenarioHandler(mind)
        self.task_handler = TaskScenarioHandler(mind)
        self.conversation_handler = ConversationScenarioHandler(mind)
        self.active_scenarios: Dict[str, ScenarioState] = {}  # concern_id -> scenario
        
        # Configuration
        self.check_interval = 300  # Check every 5 minutes
        self.health_followup_hours = 6  # Check on health after 6 hours
        self.emotion_followup_hours = 3  # Check on emotions after 3 hours
        self.task_followup_hours = 12   # Check on tasks after 12 hours
        
        # State
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.last_memory_check: Optional[datetime] = None
        
        # Load persisted concerns from SQLite
        self._load_concerns()
        
        logger.info(f"[PROACTIVE] Initialized with LLM-based concern analyzer, intelligent timing, and scenario handlers ({len(self.active_concerns)} active concerns loaded)")
    
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
        
        # USE INTELLIGENT TIMING ENGINE for better timing decisions
        timing_decision = self.timing_engine.decide_timing(
            concern_type=concern_type,
            severity=severity,
            urgency=urgency,
            user_email=user_email,
            context={
                "deadline": deadline.isoformat() if deadline else None,
                "description": description
            }
        )
        
        # Calculate follow-up time from timing decision
        if timing_decision.send_at:
            follow_up_at = timing_decision.send_at
        else:
            # Fallback to hours-based calculation
            follow_up_at = datetime.now() + timedelta(hours=follow_up_hours)
        
        logger.info(f"[TIMING] {timing_decision.reason}")
        logger.info(f"[TIMING] Will follow up at: {follow_up_at.strftime('%Y-%m-%d %I:%M %p')}")
        
        concern_id = str(uuid.uuid4())
        
        concern = ProactiveConcern(
            concern_id=concern_id,
            concern_type=concern_type,
            user_email=user_email,
            description=description,
            severity=severity,
            created_at=datetime.now(),
            follow_up_at=follow_up_at,  # Use timing engine decision
            memory_id=memory_id,
            metadata={
                "memory_content": memory_content,
                "llm_followup_message": llm_followup_message,
                "timing_reason": timing_decision.reason,
                "timing_type": timing_decision.timing.value
            } if memory_content or llm_followup_message else {"timing_reason": timing_decision.reason, "timing_type": timing_decision.timing.value},
            urgency=urgency
        )
        
        self.active_concerns.append(concern)
        
        # INITIALIZE SCENARIO HANDLER for specialized follow-ups
        try:
            scenario_context = {
                "severity": severity,
                "urgency": urgency,
                "deadline": deadline,
                "description": description
            }
            
            if concern_type == "health":
                scenario_context["symptom"] = description.split()[0] if description else "illness"
                scenario = await self.health_handler.initialize(
                    user_message=memory_content or description,
                    user_email=user_email,
                    context=scenario_context
                )
                self.active_scenarios[concern_id] = scenario
                
                # Generate and store initial response
                initial_response = await self.health_handler.generate_initial_response(scenario)
                concern.metadata["scenario_initial_response"] = initial_response
                logger.info(f"[SCENARIO] Health scenario initialized for concern {concern_id[:8]}")
                
            elif concern_type == "task" and "exam" in description.lower():
                # Exam scenario
                scenario = await self.exam_handler.initialize(
                    user_message=memory_content or description,
                    user_email=user_email,
                    context=scenario_context
                )
                self.active_scenarios[concern_id] = scenario
                
                initial_response = await self.exam_handler.generate_initial_response(scenario)
                concern.metadata["scenario_initial_response"] = initial_response
                logger.info(f"[SCENARIO] Exam scenario initialized for concern {concern_id[:8]}")
                
            elif concern_type == "task":
                # General task scenario
                scenario = await self.task_handler.initialize(
                    user_message=memory_content or description,
                    user_email=user_email,
                    context=scenario_context
                )
                self.active_scenarios[concern_id] = scenario
                
                initial_response = await self.task_handler.generate_initial_response(scenario)
                concern.metadata["scenario_initial_response"] = initial_response
                logger.info(f"[SCENARIO] Task scenario initialized for concern {concern_id[:8]}")
                
        except Exception as e:
            logger.warning(f"[SCENARIO] Could not initialize scenario handler: {e}")
        
        # Save to disk
        self._save_concerns()
        
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
            follow_up_message = None
            
            # TRY SCENARIO HANDLER FIRST for specialized follow-ups
            if concern.concern_id in self.active_scenarios:
                scenario = self.active_scenarios[concern.concern_id]
                
                try:
                    # Get scenario-specific follow-up
                    if concern.concern_type == "health":
                        follow_up_message = await self.health_handler.generate_followup(scenario)
                    elif concern.concern_type == "task" and "exam" in concern.description.lower():
                        follow_up_message = await self.exam_handler.generate_followup(scenario)
                    elif concern.concern_type == "task":
                        follow_up_message = await self.task_handler.generate_followup(scenario)
                    
                    if follow_up_message:
                        logger.info(f"[SCENARIO] Using scenario handler for follow-up")
                except Exception as e:
                    logger.warning(f"[SCENARIO] Scenario handler failed, falling back: {e}")
            
            # FALLBACK: Use LLM-generated message if available
            if not follow_up_message:
                follow_up_message = concern.metadata.get("llm_followup_message")
            
            # FALLBACK: Generate contextual follow-up message using LLM
            if not follow_up_message:
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
            
            # FINAL FALLBACK: Template-based message
            if not follow_up_message:
                follow_up_message = self._generate_template_follow_up(concern)
            
            # Record message sent for timing engine
            self.timing_engine.record_message_sent(concern.user_email)
            
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
                # Save to disk
                self._save_concerns()
            else:
                # Schedule next follow-up
                multiplier = 2 ** concern.follow_up_count  # Exponential backoff
                if concern.concern_type == "health":
                    concern.follow_up_at = datetime.now() + timedelta(hours=self.health_followup_hours * multiplier)
                elif concern.concern_type == "emotion":
                    concern.follow_up_at = datetime.now() + timedelta(hours=self.emotion_followup_hours * multiplier)
                else:
                    concern.follow_up_at = datetime.now() + timedelta(hours=self.task_followup_hours * multiplier)
                
                # Save updated concern state
                self._save_concerns()
            
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
        # Find active concerns for this user
        user_concerns = [c for c in self.active_concerns if c.user_email == user_email and not c.resolved]
        
        if not user_concerns:
            return False
        
        # Get the most recent concern (assume user is responding to latest)
        concern = user_concerns[-1]
        
        # USE SCENARIO HANDLER to process response if available
        if concern.concern_id in self.active_scenarios:
            scenario = self.active_scenarios[concern.concern_id]
            
            try:
                # Update scenario with user response
                if concern.concern_type == "health":
                    scenario = await self.health_handler.process_response(scenario, user_message)
                    should_continue = self.health_handler.should_continue(scenario)
                elif concern.concern_type == "task" and "exam" in concern.description.lower():
                    scenario = await self.exam_handler.process_response(scenario, user_message)
                    should_continue = self.exam_handler.should_continue(scenario)
                elif concern.concern_type == "task":
                    scenario = await self.task_handler.process_response(scenario, user_message)
                    should_continue = self.task_handler.should_continue(scenario)
                else:
                    should_continue = True
                
                # Update scenario state
                self.active_scenarios[concern.concern_id] = scenario
                
                # If scenario says we're done, resolve the concern
                if scenario.state == "resolved" or not should_continue:
                    concern.resolved = True
                    self.active_concerns.remove(concern)
                    self.resolved_concerns.append(concern)
                    self._save_concerns()
                    
                    # Remove scenario
                    del self.active_scenarios[concern.concern_id]
                    
                    logger.info(f"[SCENARIO] ✅ Concern resolved via scenario handler: {concern.concern_type}")
                    
                    # Send positive acknowledgment
                    if hasattr(self.mind, 'notification_manager'):
                        from genesis.core.notification_manager import NotificationChannel, NotificationPriority
                        
                        await self.mind.notification_manager.send_notification(
                            recipient=user_email,
                            title="Glad to hear that! 💚",
                            message="I'm happy things are better! I'll keep an eye out for you.",
                            channel=NotificationChannel.WEBSOCKET,
                            priority=NotificationPriority.LOW,
                            metadata={"concern_resolved": concern.concern_id}
                        )
                    
                    return True
                
                return False
                
            except Exception as e:
                logger.warning(f"[SCENARIO] Error processing response with scenario handler: {e}")
                # Fall through to pattern matching
        
        # FALLBACK: Pattern-based resolution detection
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
        
        # Save to disk
        self._save_concerns()
        
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
    
    def _get_concerns_file(self) -> Path:
        """Get path to concerns persistence file."""
        from genesis.config.settings import get_settings
        settings = get_settings()
        concerns_dir = settings.data_dir / "concerns" / self.mind.identity.gmid
        concerns_dir.mkdir(parents=True, exist_ok=True)
        return concerns_dir / "concerns.json"
    
    def _save_concerns(self):
        """
        Save concerns to SQLite (replaces JSON file storage).
        
        ARCHITECTURE CHANGE:
        - Concerns now stored in SQLite for better querying and scalability
        - No longer using JSON files
        """
        from genesis.database.base import get_session
        from genesis.database.models import ConcernRecord
        
        try:
            with get_session() as session:
                # Save/update all active concerns
                for concern in self.active_concerns:
                    # Check if concern already exists
                    existing = session.query(ConcernRecord).filter(
                        ConcernRecord.concern_id == concern.concern_id
                    ).first()
                    
                    if existing:
                        # Update existing
                        existing.status = "active" if not concern.resolved else "resolved"
                        existing.last_checked_at = datetime.now()
                        existing.check_count = concern.follow_up_count
                        if concern.resolved:
                            existing.resolved_at = datetime.now()
                    else:
                        # Create new
                        record = ConcernRecord(
                            concern_id=concern.concern_id,
                            mind_gmid=self.mind.identity.gmid,
                            user_email=concern.user_email,
                            concern_type=concern.concern_type,
                            content=concern.description,
                            priority=concern.severity,
                            confidence=concern.metadata.get('confidence', 0.5),
                            status="active" if not concern.resolved else "resolved",
                            created_at=concern.created_at,
                            next_check_at=concern.follow_up_at,
                            check_count=concern.follow_up_count,
                            extra_data=concern.metadata or {}
                        )
                        session.add(record)
                
                # Mark resolved concerns
                for concern in self.resolved_concerns:
                    existing = session.query(ConcernRecord).filter(
                        ConcernRecord.concern_id == concern.concern_id
                    ).first()
                    
                    if existing and existing.status != "resolved":
                        existing.status = "resolved"
                        existing.resolved_at = datetime.now()
                
                session.commit()
            
            logger.debug(f"[PROACTIVE] Saved {len(self.active_concerns)} concerns to SQLite")
        except Exception as e:
            logger.error(f"[PROACTIVE] Error saving concerns to SQLite: {e}")
    
    def _load_concerns(self):
        """
        Load concerns from SQLite (replaces JSON file storage).
        
        ARCHITECTURE CHANGE:
        - Concerns loaded from SQLite instead of JSON files
        - Better querying and scalability
        """
        from genesis.database.base import get_session
        from genesis.database.models import ConcernRecord
        
        try:
            with get_session() as session:
                # Load active concerns
                active_records = session.query(ConcernRecord).filter(
                    ConcernRecord.mind_gmid == self.mind.identity.gmid,
                    ConcernRecord.status == "active"
                ).all()
                
                self.active_concerns = [
                    ProactiveConcern(
                        concern_id=record.concern_id,
                        concern_type=record.concern_type,
                        user_email=record.user_email,
                        description=record.content,
                        severity=record.priority,
                        created_at=record.created_at,
                        follow_up_at=record.next_check_at or datetime.now(),
                        memory_id=record.extra_data.get('memory_id'),
                        resolved=False,
                        follow_up_count=record.check_count,
                        metadata=record.extra_data or {}
                    )
                    for record in active_records
                ]
                
                # Load resolved concerns (last 100 for history)
                resolved_records = session.query(ConcernRecord).filter(
                    ConcernRecord.mind_gmid == self.mind.identity.gmid,
                    ConcernRecord.status == "resolved"
                ).order_by(ConcernRecord.resolved_at.desc()).limit(100).all()
                
                self.resolved_concerns = [
                    ProactiveConcern(
                        concern_id=record.concern_id,
                        concern_type=record.concern_type,
                        user_email=record.user_email,
                        description=record.content,
                        severity=record.priority,
                        created_at=record.created_at,
                        follow_up_at=record.next_check_at or datetime.now(),
                        memory_id=record.extra_data.get('memory_id'),
                        resolved=True,
                        follow_up_count=record.check_count,
                        metadata=record.extra_data or {}
                    )
                    for record in resolved_records
                ]
            
            logger.info(f"[PROACTIVE] Loaded {len(self.active_concerns)} active concerns from SQLite")
        except Exception as e:
            logger.error(f"[PROACTIVE] Error loading concerns from SQLite: {e}")
            # Initialize empty if database isn't ready
            self.active_concerns = []
            self.resolved_concerns = []
    
    def get_all_concerns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all concerns (for API/debugging)."""
        return {
            "active": [c.to_dict() for c in self.active_concerns],
            "resolved": [c.to_dict() for c in self.resolved_concerns]
        }
