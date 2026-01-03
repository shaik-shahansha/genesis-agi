"""
Intelligent Message Timing System

Determines WHEN to send proactive messages based on:
- Urgency and severity
- User's likely availability
- Conversation flow and context
- Time-appropriate responses
- Message pacing to avoid overwhelm

This is what makes Genesis feel human - knowing when to speak up vs when to wait.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MessageTiming(Enum):
    """When to send a message"""
    IMMEDIATE = "immediate"  # Send right now (critical/urgent)
    NEXT_AVAILABLE = "next_available"  # Within next 5-30 minutes
    SCHEDULED = "scheduled"  # At a specific calculated time
    NEXT_INTERACTION = "next_interaction"  # Wait for user to initiate
    BATCHED = "batched"  # Group with other messages


@dataclass
class TimingDecision:
    """Decision about when to send a message"""
    timing: MessageTiming
    send_at: Optional[datetime]  # When to send (if scheduled)
    reason: str  # Why this timing was chosen
    confidence: float  # 0-1, how confident in this decision
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class IntelligentTimingEngine:
    """
    World-class timing engine that knows WHEN to send messages.
    
    This is the secret sauce that makes Genesis feel human.
    """
    
    # Time windows for different activities
    MORNING_START = time(6, 0)
    MORNING_END = time(9, 0)
    WORK_START = time(9, 0)
    WORK_END = time(17, 0)
    EVENING_START = time(17, 0)
    EVENING_END = time(22, 0)
    SLEEP_START = time(22, 0)
    SLEEP_END = time(6, 0)
    
    def __init__(self, mind: 'Mind'):
        """Initialize timing engine"""
        self.mind = mind
        self.user_interaction_history: Dict[str, List[datetime]] = {}
        self.last_message_sent: Dict[str, datetime] = {}
    
    def decide_timing(
        self,
        concern_type: str,
        severity: float,
        urgency: str,
        user_email: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TimingDecision:
        """
        Decide when to send a proactive message.
        
        This is the core intelligence that differentiates Genesis from ChatGPT.
        
        Args:
            concern_type: Type of concern (health, task, emotion, etc.)
            severity: 0-1 how serious
            urgency: critical, high, normal, low
            user_email: Who to send to
            context: Additional context
            
        Returns:
            TimingDecision with when and why
        """
        context = context or {}
        now = datetime.now()
        current_time = now.time()
        
        # 1. CRITICAL = IMMEDIATE (no matter what)
        if urgency == "critical" or severity >= 0.9:
            return TimingDecision(
                timing=MessageTiming.IMMEDIATE,
                send_at=now,
                reason="Critical urgency requires immediate response",
                confidence=1.0,
                metadata={"override": "critical"}
            )
        
        # 2. Check if user is likely asleep
        if self._is_sleep_time(current_time):
            # Health concerns during sleep = wait till morning
            if concern_type == "health" and urgency == "high":
                wake_time = self._get_next_wake_time(now)
                return TimingDecision(
                    timing=MessageTiming.SCHEDULED,
                    send_at=wake_time,
                    reason=f"User likely asleep. Will check in at {wake_time.strftime('%I:%M %p')}",
                    confidence=0.9,
                    metadata={"sleep_override": True}
                )
            
            # Non-urgent = wait till morning
            if urgency in ["normal", "low"]:
                wake_time = self._get_next_wake_time(now)
                return TimingDecision(
                    timing=MessageTiming.SCHEDULED,
                    send_at=wake_time,
                    reason=f"Not urgent and user asleep. Scheduled for {wake_time.strftime('%I:%M %p')}",
                    confidence=0.95
                )
        
        # 3. Check message pacing (don't overwhelm user)
        if user_email in self.last_message_sent:
            last_sent = self.last_message_sent[user_email]
            time_since = (now - last_sent).total_seconds() / 60  # minutes
            
            # If we sent a message in last 30 minutes, batch unless urgent
            if time_since < 30 and urgency not in ["critical", "high"]:
                next_send = last_sent + timedelta(minutes=30)
                return TimingDecision(
                    timing=MessageTiming.BATCHED,
                    send_at=next_send,
                    reason=f"Pacing messages. Last sent {int(time_since)} min ago. Will batch.",
                    confidence=0.8,
                    metadata={"last_sent_minutes_ago": time_since}
                )
        
        # 4. HIGH urgency during waking hours = next available slot
        if urgency == "high" and not self._is_sleep_time(current_time):
            # Find next good time (5-15 minutes)
            next_slot = self._find_next_available_slot(now, user_email)
            return TimingDecision(
                timing=MessageTiming.NEXT_AVAILABLE,
                send_at=next_slot,
                reason=f"High urgency. Sending at next good time: {next_slot.strftime('%I:%M %p')}",
                confidence=0.85,
                metadata={"slot_type": "next_available"}
            )
        
        # 5. Task with upcoming deadline
        if concern_type == "task" and context.get("deadline"):
            deadline = context["deadline"]
            if isinstance(deadline, str):
                deadline = datetime.fromisoformat(deadline)
            
            time_until = (deadline - now).total_seconds() / 3600  # hours
            
            # Exam tomorrow morning = check in evening before
            if "exam" in context.get("task_description", "").lower() and time_until < 24:
                evening_checkin = self._get_next_evening_time(now)
                if evening_checkin < deadline:
                    return TimingDecision(
                        timing=MessageTiming.SCHEDULED,
                        send_at=evening_checkin,
                        reason=f"Exam prep: Check readiness evening before at {evening_checkin.strftime('%I:%M %p')}",
                        confidence=0.9,
                        metadata={"scenario": "exam_prep"}
                    )
            
            # Deadline within 2 hours = immediate check
            if time_until <= 2:
                return TimingDecision(
                    timing=MessageTiming.IMMEDIATE,
                    send_at=now,
                    reason="Deadline very close. Checking in now.",
                    confidence=0.95
                )
        
        # 6. Health concern = context-aware timing
        if concern_type == "health":
            # Morning health issue = check in afternoon
            if self._is_morning_time(current_time):
                afternoon_time = self._get_afternoon_time(now)
                return TimingDecision(
                    timing=MessageTiming.SCHEDULED,
                    send_at=afternoon_time,
                    reason=f"Morning health concern. Will check progress at {afternoon_time.strftime('%I:%M %p')}",
                    confidence=0.85,
                    metadata={"health_timing": "morning_to_afternoon"}
                )
            
            # Default health follow-up = 6 hours
            followup_time = now + timedelta(hours=6)
            # But not during sleep
            if self._is_sleep_time(followup_time.time()):
                followup_time = self._get_next_wake_time(followup_time)
            
            return TimingDecision(
                timing=MessageTiming.SCHEDULED,
                send_at=followup_time,
                reason=f"Health check-in scheduled for {followup_time.strftime('%I:%M %p')}",
                confidence=0.8,
                metadata={"health_timing": "standard_6h"}
            )
        
        # 7. Emotional concern = sooner, but not immediate
        if concern_type == "emotion":
            # Check in 2-3 hours, but at a good time
            preferred_time = now + timedelta(hours=2.5)
            if self._is_sleep_time(preferred_time.time()):
                preferred_time = self._get_next_wake_time(preferred_time)
            
            return TimingDecision(
                timing=MessageTiming.SCHEDULED,
                send_at=preferred_time,
                reason=f"Emotional check-in at {preferred_time.strftime('%I:%M %p')}",
                confidence=0.8,
                metadata={"emotion_timing": "2_5_hours"}
            )
        
        # 8. Intelligent conversation follow-up = wait for natural moment
        if concern_type == "conversation" or urgency == "low":
            # Wait for user to come back, or next morning
            if self._is_evening_time(current_time):
                next_morning = self._get_next_morning_time(now)
                return TimingDecision(
                    timing=MessageTiming.SCHEDULED,
                    send_at=next_morning,
                    reason=f"Casual follow-up. Will continue conversation {next_morning.strftime('%I:%M %p')}",
                    confidence=0.75,
                    metadata={"conversation_timing": "next_morning"}
                )
            else:
                return TimingDecision(
                    timing=MessageTiming.NEXT_INTERACTION,
                    send_at=None,
                    reason="Low urgency. Will respond when user next interacts.",
                    confidence=0.9,
                    metadata={"wait_for": "user_interaction"}
                )
        
        # 9. Default = schedule for appropriate time
        next_good_time = self._get_next_appropriate_time(now, concern_type)
        return TimingDecision(
            timing=MessageTiming.SCHEDULED,
            send_at=next_good_time,
            reason=f"Scheduled for appropriate time: {next_good_time.strftime('%I:%M %p')}",
            confidence=0.7,
            metadata={"default_scheduling": True}
        )
    
    def _is_sleep_time(self, t: time) -> bool:
        """Check if time is in sleep hours (10 PM - 6 AM)"""
        return t >= self.SLEEP_START or t < self.SLEEP_END
    
    def _is_morning_time(self, t: time) -> bool:
        """Check if morning (6 AM - 9 AM)"""
        return self.MORNING_START <= t < self.MORNING_END
    
    def _is_work_time(self, t: time) -> bool:
        """Check if work hours (9 AM - 5 PM)"""
        return self.WORK_START <= t < self.WORK_END
    
    def _is_evening_time(self, t: time) -> bool:
        """Check if evening (5 PM - 10 PM)"""
        return self.EVENING_START <= t < self.SLEEP_START
    
    def _get_next_wake_time(self, from_time: datetime) -> datetime:
        """Get next wake time (6:30 AM)"""
        next_day = from_time + timedelta(days=1)
        wake_time = next_day.replace(hour=6, minute=30, second=0, microsecond=0)
        
        # If it's before 6 AM, wake time is today
        if from_time.time() < self.SLEEP_END:
            wake_time = from_time.replace(hour=6, minute=30, second=0, microsecond=0)
        
        return wake_time
    
    def _get_afternoon_time(self, from_time: datetime) -> datetime:
        """Get afternoon time (2-3 PM)"""
        afternoon = from_time.replace(hour=14, minute=30, second=0, microsecond=0)
        if afternoon <= from_time:
            afternoon += timedelta(days=1)
        return afternoon
    
    def _get_next_evening_time(self, from_time: datetime) -> datetime:
        """Get evening time (7-8 PM)"""
        evening = from_time.replace(hour=19, minute=30, second=0, microsecond=0)
        if evening <= from_time:
            evening += timedelta(days=1)
        return evening
    
    def _get_next_morning_time(self, from_time: datetime) -> datetime:
        """Get next morning time (8-9 AM)"""
        morning = from_time.replace(hour=8, minute=30, second=0, microsecond=0)
        if morning <= from_time:
            morning += timedelta(days=1)
        return morning
    
    def _find_next_available_slot(self, from_time: datetime, user_email: str) -> datetime:
        """Find next good time slot (5-15 minutes from now)"""
        # Simple implementation: 10 minutes from now
        # Could be enhanced with user interaction patterns
        return from_time + timedelta(minutes=10)
    
    def _get_next_appropriate_time(self, from_time: datetime, concern_type: str) -> datetime:
        """Get next contextually appropriate time"""
        current = from_time.time()
        
        # If in sleep hours, wait till morning
        if self._is_sleep_time(current):
            return self._get_next_wake_time(from_time)
        
        # Otherwise, 3 hours from now (standard follow-up)
        next_time = from_time + timedelta(hours=3)
        
        # If that puts us in sleep time, schedule for morning
        if self._is_sleep_time(next_time.time()):
            return self._get_next_wake_time(next_time)
        
        return next_time
    
    def record_message_sent(self, user_email: str, sent_at: Optional[datetime] = None):
        """Record that we sent a message to user"""
        self.last_message_sent[user_email] = sent_at or datetime.now()
    
    def record_user_interaction(self, user_email: str, interaction_time: Optional[datetime] = None):
        """Record user interaction for pattern learning"""
        interaction_time = interaction_time or datetime.now()
        
        if user_email not in self.user_interaction_history:
            self.user_interaction_history[user_email] = []
        
        self.user_interaction_history[user_email].append(interaction_time)
        
        # Keep only last 100 interactions
        if len(self.user_interaction_history[user_email]) > 100:
            self.user_interaction_history[user_email] = self.user_interaction_history[user_email][-100:]
    
    def get_user_active_hours(self, user_email: str) -> List[int]:
        """
        Get hours of day when user is typically active.
        
        Returns list of hours (0-23) when user is most active.
        """
        if user_email not in self.user_interaction_history:
            # Default active hours
            return list(range(8, 23))  # 8 AM - 11 PM
        
        interactions = self.user_interaction_history[user_email]
        hour_counts = {}
        
        for interaction in interactions:
            hour = interaction.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Return hours with activity (sorted by frequency)
        active_hours = sorted(hour_counts.keys(), key=lambda h: hour_counts[h], reverse=True)
        return active_hours or list(range(8, 23))
