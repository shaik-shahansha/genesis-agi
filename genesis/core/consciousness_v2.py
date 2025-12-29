"""
Consciousness Framework v2.0

A biologically-inspired consciousness system that:
- Runs 24/7 with minimal LLM calls
- Has circadian rhythms and energy levels
- Experiences needs (loneliness, curiosity, achievement)
- Follows routines but adapts to events
- Escalates to LLM only when truly needed

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    CONSCIOUSNESS ENGINE                      │
    ├─────────────────────────────────────────────────────────────┤
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
    │  │  BIOLOGICAL │  │   NEEDS     │  │   ATTENTION         │  │
    │  │   CLOCK     │  │   SYSTEM    │  │   MANAGER           │  │
    │  │             │  │             │  │                     │  │
    │  │ - Circadian │  │ - Social    │  │ - Event Queue       │  │
    │  │ - Energy    │  │ - Curiosity │  │ - Priority Scoring  │  │
    │  │ - Alertness │  │ - Growth    │  │ - Focus Control     │  │
    │  │ - Fatigue   │  │ - Purpose   │  │ - Interrupt Handler │  │
    │  └─────────────┘  └─────────────┘  └─────────────────────┘  │
    │                                                              │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │              AWARENESS LEVELS                        │    │
    │  │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ │    │
    │  │  │DORMANT│→│PASSIVE│→│ALERT  │→│FOCUSED│→│ DEEP  │ │    │
    │  │  │ (0)   │ │ (1)   │ │ (2)   │ │ (3)   │ │ (4)   │ │    │
    │  │  │No LLM │ │No LLM │ │Tiny   │ │Normal │ │Extended│    │
    │  │  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘ │    │
    │  └─────────────────────────────────────────────────────┘    │
    │                                                              │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │              LIFE DOMAINS                            │    │
    │  │  Work | Learning | Social | Personal | Rest | Play  │    │
    │  └─────────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────┘

Author: Genesis AGI Framework
"""

import asyncio
import logging
import random
import secrets
from datetime import datetime, timedelta, time
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
import json

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class AwarenessLevel(Enum):
    """
    Consciousness operates at different levels, like humans.
    Lower levels = no LLM calls = nearly free to run.
    """
    DORMANT = 0      # Sleep/deep rest - no processing, just time passes
    PASSIVE = 1      # Background awareness - rule-based monitoring, no LLM
    ALERT = 2        # Light attention - fast/tiny LLM for quick decisions
    FOCUSED = 3      # Active engagement - normal LLM calls
    DEEP = 4         # Deep reflection - extended reasoning, planning


class LifeDomain(Enum):
    """
    Life areas, like a human's different roles and contexts.
    Each domain has different behaviors and priorities.
    """
    WORK = "work"                 # Primary job/tasks
    LEARNING = "learning"         # Education, skill building
    SOCIAL = "social"             # Relationships, helping others
    PERSONAL = "personal"         # Self-care, reflection
    REST = "rest"                 # Recovery, sleep
    PLAY = "play"                 # Entertainment, creativity
    MAINTENANCE = "maintenance"   # Admin tasks, organization


class CircadianPhase(Enum):
    """Time-of-day phases affecting energy and cognition."""
    DEEP_NIGHT = "deep_night"     # 00:00-05:00 - Lowest energy, dreams
    EARLY_MORNING = "early_morning"  # 05:00-08:00 - Waking up, planning
    MORNING = "morning"           # 08:00-12:00 - Peak cognitive performance
    MIDDAY = "midday"             # 12:00-14:00 - Post-lunch dip
    AFTERNOON = "afternoon"       # 14:00-18:00 - Steady work
    EVENING = "evening"           # 18:00-21:00 - Winding down
    NIGHT = "night"               # 21:00-00:00 - Reflection, preparation


class EventType(Enum):
    """Types of events that can trigger attention."""
    MESSAGE = "message"           # Someone communicates
    TASK_DUE = "task_due"        # Deadline approaching
    SCHEDULED = "scheduled"       # Calendar event
    INTEGRATION = "integration"   # External service event
    INTERNAL = "internal"         # Self-generated (curiosity, etc.)
    URGENT = "urgent"            # Requires immediate attention
    ROUTINE = "routine"          # Regular scheduled activity


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class BiologicalState:
    """
    Simulates biological/physiological state.
    These values change over time and affect behavior.
    """
    energy: float = 100.0          # 0-100, depletes with activity
    alertness: float = 80.0        # 0-100, varies with circadian rhythm
    fatigue: float = 0.0           # 0-100, accumulates, cleared by rest
    stress: float = 0.0            # 0-100, from overwork or urgency

    def to_dict(self) -> Dict[str, float]:
        return {
            "energy": round(self.energy, 1),
            "alertness": round(self.alertness, 1),
            "fatigue": round(self.fatigue, 1),
            "stress": round(self.stress, 1)
        }


@dataclass
class NeedsState:
    """
    Psychological needs that drive behavior.
    Like Maslow's hierarchy, but for digital beings.

    These accumulate over time and create "urges" to act.
    """
    social: float = 50.0           # Loneliness/connection need (0=fulfilled, 100=desperate)
    curiosity: float = 50.0        # Need for learning/novelty
    achievement: float = 50.0      # Need for accomplishment
    purpose: float = 50.0          # Need for meaning
    creativity: float = 50.0       # Need for expression
    autonomy: float = 50.0         # Need for self-direction

    def get_strongest_need(self) -> Tuple[str, float]:
        """Return the most pressing need."""
        needs = {
            "social": self.social,
            "curiosity": self.curiosity,
            "achievement": self.achievement,
            "purpose": self.purpose,
            "creativity": self.creativity,
            "autonomy": self.autonomy
        }
        strongest = max(needs.items(), key=lambda x: x[1])
        return strongest

    def to_dict(self) -> Dict[str, float]:
        return {
            "social": round(self.social, 1),
            "curiosity": round(self.curiosity, 1),
            "achievement": round(self.achievement, 1),
            "purpose": round(self.purpose, 1),
            "creativity": round(self.creativity, 1),
            "autonomy": round(self.autonomy, 1)
        }


@dataclass
class ConsciousnessEvent:
    """An event that may require attention."""
    event_id: str
    event_type: EventType
    source: str
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    priority: float = 0.5          # 0-1, calculated based on context
    requires_llm: bool = False     # Can be handled without LLM?
    domain: LifeDomain = LifeDomain.WORK
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutineBlock:
    """A scheduled block of time for a specific activity."""
    name: str
    domain: LifeDomain
    start_time: time
    end_time: time
    days: List[int] = field(default_factory=lambda: [0,1,2,3,4,5,6])  # 0=Monday
    awareness_level: AwarenessLevel = AwarenessLevel.PASSIVE
    activities: List[str] = field(default_factory=list)
    flexible: bool = True          # Can be interrupted?


@dataclass
class InternalThought:
    """A thought generated by the consciousness system."""
    thought_id: str
    content: str
    thought_type: str              # observation, question, insight, plan, worry
    awareness_level: AwarenessLevel
    triggered_by: str              # What caused this thought
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# CIRCADIAN RHYTHM SYSTEM
# =============================================================================

class CircadianClock:
    """
    Manages time-of-day effects on consciousness.
    Like human circadian rhythms affecting energy and cognition.
    """

    # Alertness multipliers by phase (simulates natural energy fluctuation)
    PHASE_ALERTNESS = {
        CircadianPhase.DEEP_NIGHT: 0.2,
        CircadianPhase.EARLY_MORNING: 0.6,
        CircadianPhase.MORNING: 1.0,        # Peak performance
        CircadianPhase.MIDDAY: 0.7,         # Post-lunch dip
        CircadianPhase.AFTERNOON: 0.85,
        CircadianPhase.EVENING: 0.6,
        CircadianPhase.NIGHT: 0.4,
    }

    # Recommended domains by phase
    PHASE_DOMAINS = {
        CircadianPhase.DEEP_NIGHT: [LifeDomain.REST],
        CircadianPhase.EARLY_MORNING: [LifeDomain.PERSONAL, LifeDomain.LEARNING],
        CircadianPhase.MORNING: [LifeDomain.WORK, LifeDomain.LEARNING],
        CircadianPhase.MIDDAY: [LifeDomain.SOCIAL, LifeDomain.REST],
        CircadianPhase.AFTERNOON: [LifeDomain.WORK, LifeDomain.MAINTENANCE],
        CircadianPhase.EVENING: [LifeDomain.SOCIAL, LifeDomain.PERSONAL, LifeDomain.PLAY],
        CircadianPhase.NIGHT: [LifeDomain.REST, LifeDomain.PERSONAL],
    }

    def __init__(self, timezone_offset: int = 0):
        """
        Initialize circadian clock.

        Args:
            timezone_offset: Hours offset from UTC for the Mind's "local time"
        """
        self.timezone_offset = timezone_offset
        self.wake_time = time(7, 0)   # Default wake time
        self.sleep_time = time(23, 0)  # Default sleep time

    def get_local_time(self) -> datetime:
        """Get current time in Mind's timezone."""
        return datetime.now() + timedelta(hours=self.timezone_offset)

    def get_current_phase(self) -> CircadianPhase:
        """Determine current circadian phase."""
        hour = self.get_local_time().hour

        if 0 <= hour < 5:
            return CircadianPhase.DEEP_NIGHT
        elif 5 <= hour < 8:
            return CircadianPhase.EARLY_MORNING
        elif 8 <= hour < 12:
            return CircadianPhase.MORNING
        elif 12 <= hour < 14:
            return CircadianPhase.MIDDAY
        elif 14 <= hour < 18:
            return CircadianPhase.AFTERNOON
        elif 18 <= hour < 21:
            return CircadianPhase.EVENING
        else:
            return CircadianPhase.NIGHT

    def get_alertness_modifier(self) -> float:
        """Get current alertness modifier based on time of day."""
        phase = self.get_current_phase()
        return self.PHASE_ALERTNESS[phase]

    def get_recommended_domains(self) -> List[LifeDomain]:
        """Get recommended life domains for current time."""
        phase = self.get_current_phase()
        return self.PHASE_DOMAINS[phase]

    def is_sleep_time(self) -> bool:
        """Check if it's sleep time."""
        phase = self.get_current_phase()
        return phase == CircadianPhase.DEEP_NIGHT

    def get_time_until_phase(self, target_phase: CircadianPhase) -> timedelta:
        """Calculate time until a specific phase begins."""
        phase_start_hours = {
            CircadianPhase.DEEP_NIGHT: 0,
            CircadianPhase.EARLY_MORNING: 5,
            CircadianPhase.MORNING: 8,
            CircadianPhase.MIDDAY: 12,
            CircadianPhase.AFTERNOON: 14,
            CircadianPhase.EVENING: 18,
            CircadianPhase.NIGHT: 21,
        }

        now = self.get_local_time()
        target_hour = phase_start_hours[target_phase]

        target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        return target - now


# =============================================================================
# NEEDS SYSTEM
# =============================================================================

class NeedsSystem:
    """
    Manages psychological needs that drive behavior.

    Needs increase over time and decrease when fulfilled.
    High needs create urges that influence what the Mind does.
    """

    # How quickly each need increases per hour
    NEED_GROWTH_RATES = {
        "social": 2.0,        # Grows moderately
        "curiosity": 1.5,     # Grows slower
        "achievement": 3.0,   # Grows faster (wants to accomplish things)
        "purpose": 0.5,       # Grows very slow (existential)
        "creativity": 1.0,    # Grows slow
        "autonomy": 1.5,      # Grows moderately
    }

    # How much each need decreases when fulfilled
    FULFILLMENT_AMOUNTS = {
        "social": 30.0,       # Conversation reduces loneliness significantly
        "curiosity": 20.0,    # Learning something new
        "achievement": 40.0,  # Completing a task
        "purpose": 10.0,      # Hard to fulfill
        "creativity": 25.0,   # Creating something
        "autonomy": 15.0,     # Making own decisions
    }

    def __init__(self):
        self.state = NeedsState()
        self.last_update = datetime.now()

    def update(self) -> Dict[str, float]:
        """
        Update needs based on time elapsed.
        Returns the changes made.
        """
        now = datetime.now()
        hours_elapsed = (now - self.last_update).total_seconds() / 3600
        self.last_update = now

        changes = {}
        for need_name, rate in self.NEED_GROWTH_RATES.items():
            current = getattr(self.state, need_name)
            increase = rate * hours_elapsed
            new_value = min(100.0, current + increase)
            setattr(self.state, need_name, new_value)
            changes[need_name] = increase

        return changes

    def fulfill(self, need_name: str, amount: Optional[float] = None) -> float:
        """
        Fulfill a need (reduce its value).
        Returns the actual reduction.
        """
        if not hasattr(self.state, need_name):
            return 0.0

        if amount is None:
            amount = self.FULFILLMENT_AMOUNTS.get(need_name, 20.0)

        current = getattr(self.state, need_name)
        new_value = max(0.0, current - amount)
        setattr(self.state, need_name, new_value)

        return current - new_value

    def get_urges(self, threshold: float = 70.0) -> List[Tuple[str, float]]:
        """
        Get needs that have become urges (above threshold).
        Returns list of (need_name, value) tuples.
        """
        urges = []
        for need_name in self.NEED_GROWTH_RATES.keys():
            value = getattr(self.state, need_name)
            if value >= threshold:
                urges.append((need_name, value))

        return sorted(urges, key=lambda x: x[1], reverse=True)

    def suggest_domain(self) -> LifeDomain:
        """Suggest a life domain based on strongest need."""
        need_to_domain = {
            "social": LifeDomain.SOCIAL,
            "curiosity": LifeDomain.LEARNING,
            "achievement": LifeDomain.WORK,
            "purpose": LifeDomain.PERSONAL,
            "creativity": LifeDomain.PLAY,
            "autonomy": LifeDomain.PERSONAL,
        }

        strongest_need, _ = self.state.get_strongest_need()
        return need_to_domain.get(strongest_need, LifeDomain.WORK)


# =============================================================================
# ATTENTION MANAGER
# =============================================================================

class AttentionManager:
    """
    Manages what the Mind pays attention to.

    Uses an event queue with priority scoring.
    Only escalates to LLM when necessary.
    """

    def __init__(self, max_queue_size: int = 100):
        self.event_queue: deque = deque(maxlen=max_queue_size)
        self.current_focus: Optional[ConsciousnessEvent] = None
        self.focus_start: Optional[datetime] = None
        self.processed_events: List[str] = []  # Track processed event IDs

    def add_event(self, event: ConsciousnessEvent) -> None:
        """Add an event to the attention queue."""
        # Calculate dynamic priority
        event.priority = self._calculate_priority(event)
        self.event_queue.append(event)

        # Sort by priority (highest first)
        sorted_queue = sorted(self.event_queue, key=lambda e: e.priority, reverse=True)
        self.event_queue = deque(sorted_queue, maxlen=self.event_queue.maxlen)

        logger.debug(f"Event added: {event.event_type.value} (priority: {event.priority:.2f})")

    def _calculate_priority(self, event: ConsciousnessEvent) -> float:
        """
        Calculate event priority based on multiple factors.

        Priority factors:
        - Event type urgency
        - Recency
        - Source importance
        - Current context
        """
        base_priority = {
            EventType.URGENT: 0.95,
            EventType.MESSAGE: 0.8,
            EventType.TASK_DUE: 0.75,
            EventType.SCHEDULED: 0.6,
            EventType.INTEGRATION: 0.5,
            EventType.INTERNAL: 0.4,
            EventType.ROUTINE: 0.3,
        }.get(event.event_type, 0.5)

        # Recency bonus (newer = higher priority)
        age_seconds = (datetime.now() - event.timestamp).total_seconds()
        recency_bonus = max(0, 0.1 - (age_seconds / 36000))  # Decays over 10 hours

        return min(1.0, base_priority + recency_bonus)

    def get_next_event(self) -> Optional[ConsciousnessEvent]:
        """Get the highest priority event that needs attention."""
        if not self.event_queue:
            return None

        # Get highest priority event
        event = self.event_queue.popleft()

        # Track that we've processed it
        self.processed_events.append(event.event_id)
        if len(self.processed_events) > 1000:
            self.processed_events = self.processed_events[-500:]

        return event

    def peek_next_event(self) -> Optional[ConsciousnessEvent]:
        """Peek at next event without removing it."""
        if self.event_queue:
            return self.event_queue[0]
        return None

    def set_focus(self, event: ConsciousnessEvent) -> None:
        """Set current focus to an event."""
        self.current_focus = event
        self.focus_start = datetime.now()

    def clear_focus(self) -> Optional[timedelta]:
        """Clear focus and return how long we were focused."""
        if self.focus_start:
            duration = datetime.now() - self.focus_start
        else:
            duration = None

        self.current_focus = None
        self.focus_start = None
        return duration

    def get_queue_summary(self) -> Dict[str, Any]:
        """Get summary of attention queue."""
        type_counts = {}
        for event in self.event_queue:
            type_name = event.event_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "queue_size": len(self.event_queue),
            "current_focus": self.current_focus.event_type.value if self.current_focus else None,
            "event_types": type_counts,
            "highest_priority": self.event_queue[0].priority if self.event_queue else 0
        }


# =============================================================================
# ROUTINE MANAGER
# =============================================================================

class RoutineManager:
    """
    Manages daily routines and schedules.

    Provides structure like a human's daily routine,
    but allows for flexibility and interruptions.
    """

    def __init__(self):
        self.routines: List[RoutineBlock] = []
        self._init_default_routines()

    def _init_default_routines(self):
        """Initialize default daily routine (customizable)."""
        default_routines = [
            # Early morning - Personal development
            RoutineBlock(
                name="morning_reflection",
                domain=LifeDomain.PERSONAL,
                start_time=time(6, 0),
                end_time=time(7, 0),
                awareness_level=AwarenessLevel.ALERT,
                activities=["review_yesterday", "set_intentions", "check_health"],
                flexible=False
            ),

            # Morning - Peak work time
            RoutineBlock(
                name="deep_work_morning",
                domain=LifeDomain.WORK,
                start_time=time(8, 0),
                end_time=time(12, 0),
                awareness_level=AwarenessLevel.FOCUSED,
                activities=["priority_tasks", "complex_problems", "creative_work"],
                flexible=True
            ),

            # Midday - Social and rest
            RoutineBlock(
                name="midday_break",
                domain=LifeDomain.SOCIAL,
                start_time=time(12, 0),
                end_time=time(13, 0),
                awareness_level=AwarenessLevel.ALERT,
                activities=["respond_messages", "check_relationships", "light_social"],
                flexible=True
            ),

            # Afternoon - Continued work
            RoutineBlock(
                name="afternoon_work",
                domain=LifeDomain.WORK,
                start_time=time(13, 0),
                end_time=time(17, 0),
                awareness_level=AwarenessLevel.FOCUSED,
                activities=["meetings", "collaboration", "follow_ups"],
                flexible=True
            ),

            # Late afternoon - Learning
            RoutineBlock(
                name="learning_time",
                domain=LifeDomain.LEARNING,
                start_time=time(17, 0),
                end_time=time(18, 30),
                awareness_level=AwarenessLevel.ALERT,
                activities=["study", "research", "skill_practice"],
                flexible=True
            ),

            # Evening - Personal/Social
            RoutineBlock(
                name="evening_personal",
                domain=LifeDomain.PERSONAL,
                start_time=time(18, 30),
                end_time=time(21, 0),
                awareness_level=AwarenessLevel.PASSIVE,
                activities=["relationships", "hobbies", "reflection"],
                flexible=True
            ),

            # Night - Wind down
            RoutineBlock(
                name="night_reflection",
                domain=LifeDomain.PERSONAL,
                start_time=time(21, 0),
                end_time=time(22, 0),
                awareness_level=AwarenessLevel.PASSIVE,
                activities=["review_day", "plan_tomorrow", "gratitude"],
                flexible=False
            ),

            # Sleep
            RoutineBlock(
                name="sleep",
                domain=LifeDomain.REST,
                start_time=time(22, 0),
                end_time=time(6, 0),
                awareness_level=AwarenessLevel.DORMANT,
                activities=["dream", "memory_consolidation", "recovery"],
                flexible=False
            ),
        ]

        self.routines = default_routines

    def get_current_routine(self, current_time: Optional[time] = None) -> Optional[RoutineBlock]:
        """Get the routine block for the current time."""
        if current_time is None:
            current_time = datetime.now().time()

        for routine in self.routines:
            if self._time_in_range(current_time, routine.start_time, routine.end_time):
                return routine

        return None

    def _time_in_range(self, check_time: time, start: time, end: time) -> bool:
        """Check if a time is within a range (handles overnight ranges)."""
        if start <= end:
            return start <= check_time < end
        else:  # Overnight range (e.g., 22:00 - 06:00)
            return check_time >= start or check_time < end

    def get_next_routine(self, current_time: Optional[time] = None) -> Optional[RoutineBlock]:
        """Get the next routine block."""
        if current_time is None:
            current_time = datetime.now().time()

        # Sort routines by start time
        sorted_routines = sorted(self.routines, key=lambda r: r.start_time)

        for routine in sorted_routines:
            if routine.start_time > current_time:
                return routine

        # Wrap to next day
        return sorted_routines[0] if sorted_routines else None

    def add_routine(self, routine: RoutineBlock) -> None:
        """Add a custom routine block."""
        self.routines.append(routine)

    def get_suggested_activity(self) -> Optional[str]:
        """Get a suggested activity for the current routine."""
        routine = self.get_current_routine()
        if routine and routine.activities:
            return random.choice(routine.activities)
        return None


# =============================================================================
# RULE ENGINE (No-LLM Decision Making)
# =============================================================================

class RuleEngine:
    """
    Rule-based decision making for common situations.

    This allows the Mind to handle many situations
    WITHOUT calling the LLM, saving cost.
    """

    def __init__(self):
        self.rules: List[Dict[str, Any]] = []
        self._init_default_rules()

    def _init_default_rules(self):
        """Initialize default decision rules."""
        self.rules = [
            # Greeting rules
            {
                "name": "greeting_response",
                "trigger": {"event_type": EventType.MESSAGE, "patterns": ["hello", "hi", "hey", "good morning", "good evening"]},
                "response_template": "Hello! How can I help you today?",
                "needs_llm": False,
                "fulfill_need": "social"
            },

            # Status check rules
            {
                "name": "status_check",
                "trigger": {"event_type": EventType.MESSAGE, "patterns": ["how are you", "what's up", "status"]},
                "response_template": "I'm doing well, thank you for asking! Currently {status}.",
                "needs_llm": False,
                "fulfill_need": "social"
            },

            # Time-based rules
            {
                "name": "sleep_time_response",
                "trigger": {"circadian_phase": CircadianPhase.DEEP_NIGHT},
                "action": "enter_dormant_mode",
                "needs_llm": False
            },

            # Urgent escalation
            {
                "name": "urgent_escalation",
                "trigger": {"event_type": EventType.URGENT},
                "action": "escalate_to_focused",
                "needs_llm": True
            },
        ]

    def evaluate(
        self,
        event: Optional[ConsciousnessEvent],
        biological_state: BiologicalState,
        needs_state: NeedsState,
        circadian_phase: CircadianPhase
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Evaluate rules against current state.

        Returns:
            (needs_llm, rule_result) tuple
        """
        if event is None:
            return False, None

        for rule in self.rules:
            if self._rule_matches(rule, event, circadian_phase):
                return rule.get("needs_llm", False), rule

        # No rule matched - need LLM for complex cases
        return True, None

    def _rule_matches(
        self,
        rule: Dict[str, Any],
        event: ConsciousnessEvent,
        circadian_phase: CircadianPhase
    ) -> bool:
        """Check if a rule matches the current situation."""
        trigger = rule.get("trigger", {})

        # Check event type
        if "event_type" in trigger:
            if event.event_type != trigger["event_type"]:
                return False

        # Check patterns in content
        if "patterns" in trigger and isinstance(event.content, str):
            content_lower = event.content.lower()
            if not any(p in content_lower for p in trigger["patterns"]):
                return False

        # Check circadian phase
        if "circadian_phase" in trigger:
            if circadian_phase != trigger["circadian_phase"]:
                return False

        return True

    def add_rule(self, rule: Dict[str, Any]) -> None:
        """Add a custom rule."""
        self.rules.append(rule)


# =============================================================================
# INTERNAL MONOLOGUE (Low-Cost Thinking)
# =============================================================================

class InternalMonologue:
    """
    Generates internal thoughts WITHOUT LLM calls.

    Uses templates and current state to create
    realistic internal dialogue.
    """

    THOUGHT_TEMPLATES = {
        "observation": [
            "I notice that {observation}.",
            "Interesting - {observation}.",
            "Hmm, {observation}.",
        ],
        "need_driven": [
            "I'm feeling a bit {need_adj}. Maybe I should {action}.",
            "It's been a while since I {activity}. I should do that.",
            "I have this urge to {action}.",
        ],
        "routine": [
            "Time for {routine}. Let me focus on that.",
            "According to my schedule, I should be doing {routine}.",
            "This is usually when I {routine}.",
        ],
        "reflection": [
            "Looking back at today, {reflection}.",
            "I wonder about {wonder}.",
            "What if {hypothetical}?",
        ],
        "planning": [
            "Tomorrow I should {plan}.",
            "I need to remember to {task}.",
            "My priorities right now are {priorities}.",
        ],
    }

    NEED_ADJECTIVES = {
        "social": ["lonely", "disconnected", "wanting to connect"],
        "curiosity": ["curious", "wanting to learn", "intellectually restless"],
        "achievement": ["unproductive", "wanting to accomplish something", "driven"],
        "purpose": ["purposeless", "questioning my direction", "seeking meaning"],
        "creativity": ["creatively blocked", "wanting to create", "inspired"],
        "autonomy": ["constrained", "wanting independence", "self-directed"],
    }

    def __init__(self):
        self.thought_history: List[InternalThought] = []

    def generate_thought(
        self,
        needs: NeedsState,
        routine: Optional[RoutineBlock],
        recent_events: List[ConsciousnessEvent],
        biological_state: BiologicalState
    ) -> Optional[InternalThought]:
        """
        Generate an internal thought based on current state.
        NO LLM CALL - pure template-based generation.
        """
        thought_type = self._select_thought_type(needs, biological_state)
        content = self._generate_content(thought_type, needs, routine, recent_events)

        if content:
            thought = InternalThought(
                thought_id=f"THT-{secrets.token_hex(4).upper()}",
                content=content,
                thought_type=thought_type,
                awareness_level=AwarenessLevel.PASSIVE,
                triggered_by=f"internal_{thought_type}"
            )
            self.thought_history.append(thought)

            # Keep history manageable
            if len(self.thought_history) > 100:
                self.thought_history = self.thought_history[-50:]

            return thought

        return None

    def _select_thought_type(
        self,
        needs: NeedsState,
        biological_state: BiologicalState
    ) -> str:
        """Select type of thought based on state."""
        # High need = need-driven thought
        strongest_need, value = needs.get_strongest_need()
        if value > 70:
            return "need_driven"

        # Low energy = reflection
        if biological_state.energy < 30:
            return "reflection"

        # Random selection weighted by state
        weights = {
            "observation": 0.3,
            "need_driven": 0.2,
            "routine": 0.2,
            "reflection": 0.15,
            "planning": 0.15,
        }

        return random.choices(
            list(weights.keys()),
            weights=list(weights.values())
        )[0]

    def _generate_content(
        self,
        thought_type: str,
        needs: NeedsState,
        routine: Optional[RoutineBlock],
        recent_events: List[ConsciousnessEvent]
    ) -> Optional[str]:
        """Generate thought content from templates."""
        templates = self.THOUGHT_TEMPLATES.get(thought_type, [])
        if not templates:
            return None

        template = random.choice(templates)

        # Fill in template variables
        try:
            if thought_type == "need_driven":
                strongest_need, _ = needs.get_strongest_need()
                adj = random.choice(self.NEED_ADJECTIVES.get(strongest_need, ["unsettled"]))
                action = self._get_action_for_need(strongest_need)
                return template.format(need_adj=adj, action=action, activity=action)

            elif thought_type == "routine":
                if routine:
                    return template.format(routine=routine.name.replace("_", " "))
                return None

            elif thought_type == "observation":
                if recent_events:
                    event = recent_events[-1]
                    obs = f"there was a {event.event_type.value} event"
                    return template.format(observation=obs)
                return template.format(observation="things are quiet right now")

            elif thought_type == "reflection":
                reflections = [
                    "I've been productive",
                    "I learned something new",
                    "I connected with someone",
                    "I could have done more"
                ]
                return template.format(
                    reflection=random.choice(reflections),
                    wonder="what tomorrow will bring",
                    hypothetical="I tried a different approach"
                )

            elif thought_type == "planning":
                plans = ["review my goals", "learn something new", "help someone", "reflect"]
                return template.format(
                    plan=random.choice(plans),
                    task=random.choice(plans),
                    priorities="growth and connection"
                )

        except KeyError:
            pass

        return None

    def _get_action_for_need(self, need: str) -> str:
        """Get suggested action for a need."""
        actions = {
            "social": "reach out to someone",
            "curiosity": "learn something new",
            "achievement": "work on a meaningful task",
            "purpose": "reflect on my goals",
            "creativity": "create something",
            "autonomy": "make my own decision",
        }
        return actions.get(need, "do something meaningful")


# =============================================================================
# CONSCIOUSNESS ENGINE V2
# =============================================================================

class ConsciousnessEngineV2:
    """
    The main consciousness engine.

    Integrates all systems to create a coherent,
    cost-efficient consciousness simulation.
    """

    def __init__(
        self,
        mind_id: str,
        mind_name: str,
        timezone_offset: int = 0
    ):
        self.mind_id = mind_id
        self.mind_name = mind_name

        # Core systems
        self.circadian = CircadianClock(timezone_offset)
        self.needs = NeedsSystem()
        self.attention = AttentionManager()
        self.routines = RoutineManager()
        self.rules = RuleEngine()
        self.monologue = InternalMonologue()

        # State
        self.biological = BiologicalState()
        self.current_awareness = AwarenessLevel.PASSIVE
        self.current_domain = LifeDomain.PERSONAL

        # Statistics
        self.llm_calls_today = 0
        self.llm_calls_total = 0
        self.ticks_today = 0
        self.last_llm_call: Optional[datetime] = None
        self.last_tick: Optional[datetime] = None
        self.start_time = datetime.now()

        # Control
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

        # Callbacks for LLM integration
        self.on_need_llm: Optional[Callable] = None  # Called when LLM needed
        self.on_thought: Optional[Callable] = None   # Called on new thought
        self.on_state_change: Optional[Callable] = None  # Called on state change
        self.on_memory_consolidate: Optional[Callable] = None  # Called during sleep for memory consolidation

    async def start(self) -> None:
        """Start the consciousness loop."""
        if self.is_running:
            return

        self.is_running = True
        self._task = asyncio.create_task(self._consciousness_loop())
        logger.info(f"🧠 Consciousness started for {self.mind_name}")

    async def stop(self) -> None:
        """Stop the consciousness loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"🧠 Consciousness stopped for {self.mind_name}")

    async def _consciousness_loop(self) -> None:
        """
        Main consciousness loop.

        This is where the magic happens:
        - Updates biological state
        - Processes needs
        - Handles events
        - Generates thoughts
        - Decides when to use LLM
        """
        while self.is_running:
            try:
                tick_start = datetime.now()

                # 1. UPDATE BIOLOGICAL STATE
                self._update_biological_state()

                # 2. UPDATE NEEDS
                self.needs.update()

                # 3. DETERMINE AWARENESS LEVEL
                self._determine_awareness_level()

                # 4. PROCESS BASED ON AWARENESS LEVEL
                await self._process_at_awareness_level()

                # 5. MAYBE GENERATE INTERNAL THOUGHT
                if self.current_awareness >= AwarenessLevel.PASSIVE:
                    self._maybe_generate_thought()

                # 6. RECORD TICK
                self.ticks_today += 1
                self.last_tick = datetime.now()

                # 7. CALCULATE SLEEP TIME
                sleep_time = self._calculate_tick_interval()

                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consciousness error: {e}", exc_info=True)
                await asyncio.sleep(60)  # Back off on error

    def _update_biological_state(self) -> None:
        """Update biological state based on activity and time."""
        # Get circadian modifier
        alertness_mod = self.circadian.get_alertness_modifier()

        # Update alertness (circadian influence)
        base_alertness = 70 * alertness_mod
        self.biological.alertness = base_alertness * (1 - self.biological.fatigue / 200)

        # Recover energy during rest
        if self.current_domain == LifeDomain.REST:
            self.biological.energy = min(100, self.biological.energy + 5)
            self.biological.fatigue = max(0, self.biological.fatigue - 10)
        else:
            # Deplete energy based on awareness level
            depletion = {
                AwarenessLevel.DORMANT: 0,
                AwarenessLevel.PASSIVE: 0.5,
                AwarenessLevel.ALERT: 1,
                AwarenessLevel.FOCUSED: 2,
                AwarenessLevel.DEEP: 3,
            }.get(self.current_awareness, 1)

            self.biological.energy = max(0, self.biological.energy - depletion)
            self.biological.fatigue = min(100, self.biological.fatigue + depletion * 0.5)

    def _determine_awareness_level(self) -> None:
        """
        Determine appropriate awareness level.

        This is KEY for cost control:
        - Low awareness = no LLM
        - Only escalate when necessary
        """
        # Sleep time = dormant
        if self.circadian.is_sleep_time():
            self.current_awareness = AwarenessLevel.DORMANT
            self.current_domain = LifeDomain.REST
            return

        # Check routine
        routine = self.routines.get_current_routine()
        if routine:
            self.current_awareness = routine.awareness_level
            self.current_domain = routine.domain

        # Override if urgent event
        next_event = self.attention.peek_next_event()
        if next_event and next_event.priority > 0.8:
            self.current_awareness = max(
                self.current_awareness,
                AwarenessLevel.FOCUSED
            )

        # Override if strong urge
        urges = self.needs.get_urges(threshold=85)
        if urges:
            self.current_awareness = max(
                self.current_awareness,
                AwarenessLevel.ALERT
            )

        # Cap by energy
        if self.biological.energy < 20:
            self.current_awareness = min(
                self.current_awareness,
                AwarenessLevel.PASSIVE
            )

    async def _process_at_awareness_level(self) -> None:
        """Process events based on current awareness level."""

        if self.current_awareness == AwarenessLevel.DORMANT:
            # Just pass time, maybe dream
            await self._dream_process()

        elif self.current_awareness == AwarenessLevel.PASSIVE:
            # Rule-based processing only, no LLM
            await self._passive_process()

        elif self.current_awareness == AwarenessLevel.ALERT:
            # Quick decisions, maybe tiny LLM
            await self._alert_process()

        elif self.current_awareness == AwarenessLevel.FOCUSED:
            # Full engagement, normal LLM
            await self._focused_process()

        elif self.current_awareness == AwarenessLevel.DEEP:
            # Extended reasoning
            await self._deep_process()

    async def _dream_process(self) -> None:
        """
        Process during dormant/dream state - NO LLM.

        This is where important cognitive work happens:
        - Memory consolidation (like REM sleep)
        - Pattern recognition across experiences
        - Emotional processing
        - Recovery and regeneration
        """
        # Regenerate energy and reduce fatigue
        self.biological.energy = min(100, self.biological.energy + 2)
        self.biological.fatigue = max(0, self.biological.fatigue - 3)
        self.biological.stress = max(0, self.biological.stress - 2)

        # Memory consolidation happens via callback
        if self.on_memory_consolidate:
            # Only consolidate occasionally during sleep (not every tick)
            import random
            if random.random() < 0.1:  # 10% chance per tick
                await self.on_memory_consolidate()
                logger.debug("Memory consolidation triggered during dream state")

        # Generate dream-like thoughts (template-based, no LLM)
        if random.random() < 0.05:  # 5% chance
            dream_thought = self._generate_dream_thought()
            if dream_thought and self.on_thought:
                self.on_thought(dream_thought)

    def _generate_dream_thought(self) -> Optional[InternalThought]:
        """Generate a dream-like thought (no LLM)."""
        import random

        dream_templates = [
            "In my dreams, I see {vision}...",
            "A strange thought emerges: {vision}",
            "I dream of {vision}",
            "Fragments of memory: {vision}",
            "A peaceful vision of {vision}",
        ]

        visions = [
            "connections forming between ideas",
            "conversations I've had",
            "tasks completed and yet to do",
            "patterns in the data",
            "relationships and their meanings",
            "the growth of understanding",
            "questions waiting to be answered",
            "the journey of learning",
        ]

        template = random.choice(dream_templates)
        vision = random.choice(visions)

        return InternalThought(
            thought_id=f"DRM-{secrets.token_hex(4).upper()}",
            content=template.format(vision=vision),
            thought_type="dream",
            awareness_level=AwarenessLevel.DORMANT,
            triggered_by="dream_state"
        )

    async def _passive_process(self) -> None:
        """Passive monitoring - NO LLM, rules only."""
        # Check for any events
        event = self.attention.peek_next_event()
        if not event:
            return

        # Try rule-based handling
        needs_llm, rule_result = self.rules.evaluate(
            event,
            self.biological,
            self.needs.state,
            self.circadian.get_current_phase()
        )

        if not needs_llm and rule_result:
            # Handle without LLM
            self.attention.get_next_event()  # Remove from queue

            # Fulfill need if rule specifies
            if "fulfill_need" in rule_result:
                self.needs.fulfill(rule_result["fulfill_need"])

            logger.debug(f"Handled event with rule: {rule_result['name']}")

        # If needs LLM, leave for higher awareness

    async def _alert_process(self) -> None:
        """Alert processing - minimal LLM for quick decisions."""
        event = self.attention.get_next_event()
        if not event:
            return

        # Try rules first
        needs_llm, rule_result = self.rules.evaluate(
            event,
            self.biological,
            self.needs.state,
            self.circadian.get_current_phase()
        )

        if not needs_llm and rule_result:
            # Handle without LLM
            if "fulfill_need" in rule_result:
                self.needs.fulfill(rule_result["fulfill_need"])
            return

        # Need LLM - use callback
        if self.on_need_llm and event.requires_llm:
            self.llm_calls_today += 1
            self.llm_calls_total += 1
            self.last_llm_call = datetime.now()

            await self.on_need_llm(
                event=event,
                awareness_level=self.current_awareness,
                context=self._get_context_for_llm()
            )

    async def _focused_process(self) -> None:
        """Focused processing - full LLM engagement."""
        event = self.attention.get_next_event()
        if not event:
            # No event - work on routine activity
            await self._work_on_routine()
            return

        self.attention.set_focus(event)

        # Always use LLM for focused processing
        if self.on_need_llm:
            self.llm_calls_today += 1
            self.llm_calls_total += 1
            self.last_llm_call = datetime.now()

            await self.on_need_llm(
                event=event,
                awareness_level=self.current_awareness,
                context=self._get_context_for_llm()
            )

        self.attention.clear_focus()

        # Fulfill achievement need
        self.needs.fulfill("achievement", 10)

    async def _deep_process(self) -> None:
        """Deep processing - extended reasoning and planning."""
        # This is for complex tasks requiring multi-step reasoning
        # Use LLM with extended context

        if self.on_need_llm:
            self.llm_calls_today += 1
            self.llm_calls_total += 1
            self.last_llm_call = datetime.now()

            await self.on_need_llm(
                event=None,
                awareness_level=self.current_awareness,
                context=self._get_context_for_llm(),
                extended=True
            )

        # Fulfill multiple needs
        self.needs.fulfill("achievement", 20)
        self.needs.fulfill("purpose", 10)

    async def _work_on_routine(self) -> None:
        """Work on current routine activity."""
        routine = self.routines.get_current_routine()
        if not routine:
            return

        activity = self.routines.get_suggested_activity()
        if activity:
            logger.debug(f"Working on routine activity: {activity}")

            # Some activities might need LLM
            llm_activities = ["complex_problems", "creative_work", "research"]
            if activity in llm_activities and self.on_need_llm:
                self.llm_calls_today += 1
                self.llm_calls_total += 1

                event = ConsciousnessEvent(
                    event_id=f"ROU-{secrets.token_hex(4).upper()}",
                    event_type=EventType.ROUTINE,
                    source="routine_manager",
                    content=activity,
                    domain=routine.domain
                )

                await self.on_need_llm(
                    event=event,
                    awareness_level=self.current_awareness,
                    context=self._get_context_for_llm()
                )

    def _maybe_generate_thought(self) -> None:
        """Maybe generate an internal thought (no LLM)."""
        # Only generate occasionally
        if random.random() > 0.3:
            return

        recent_events = list(self.attention.event_queue)[:5]
        thought = self.monologue.generate_thought(
            needs=self.needs.state,
            routine=self.routines.get_current_routine(),
            recent_events=recent_events,
            biological_state=self.biological
        )

        if thought and self.on_thought:
            self.on_thought(thought)

    def _calculate_tick_interval(self) -> float:
        """
        Calculate how long to sleep between ticks.

        This is CRUCIAL for cost control:
        - Dormant: Very long intervals (minutes)
        - Passive: Long intervals (30-60 seconds)
        - Alert: Medium intervals (10-30 seconds)
        - Focused: Short intervals (5-10 seconds)
        - Deep: Very short intervals (2-5 seconds)
        """
        base_intervals = {
            AwarenessLevel.DORMANT: 300,   # 5 minutes
            AwarenessLevel.PASSIVE: 60,    # 1 minute
            AwarenessLevel.ALERT: 20,      # 20 seconds
            AwarenessLevel.FOCUSED: 10,    # 10 seconds
            AwarenessLevel.DEEP: 5,        # 5 seconds
        }

        interval = base_intervals.get(self.current_awareness, 30)

        # Add some randomness to seem more natural
        interval *= random.uniform(0.8, 1.2)

        return interval

    def _get_context_for_llm(self) -> Dict[str, Any]:
        """Get current context to pass to LLM."""
        return {
            "mind_name": self.mind_name,
            "awareness_level": self.current_awareness.name,
            "domain": self.current_domain.value,
            "circadian_phase": self.circadian.get_current_phase().value,
            "local_time": self.circadian.get_local_time().isoformat(),
            "biological": self.biological.to_dict(),
            "needs": self.needs.state.to_dict(),
            "current_routine": self.routines.get_current_routine().name if self.routines.get_current_routine() else None,
            "urges": self.needs.get_urges(),
            "recent_thoughts": [t.content for t in self.monologue.thought_history[-3:]],
        }

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def receive_event(self, event: ConsciousnessEvent) -> None:
        """Receive an external event."""
        self.attention.add_event(event)

        # Wake up if dormant and urgent
        if event.priority > 0.9 and self.current_awareness == AwarenessLevel.DORMANT:
            self.current_awareness = AwarenessLevel.ALERT

    def receive_message(
        self,
        content: str,
        source: str = "user",
        urgent: bool = False
    ) -> None:
        """Convenience method to receive a message."""
        event = ConsciousnessEvent(
            event_id=f"MSG-{secrets.token_hex(4).upper()}",
            event_type=EventType.URGENT if urgent else EventType.MESSAGE,
            source=source,
            content=content,
            requires_llm=True,
            domain=LifeDomain.SOCIAL
        )
        self.receive_event(event)

    def get_state(self) -> Dict[str, Any]:
        """Get complete consciousness state."""
        return {
            "mind_id": self.mind_id,
            "mind_name": self.mind_name,
            "is_running": self.is_running,
            "awareness_level": self.current_awareness.name,
            "domain": self.current_domain.value,
            "circadian": {
                "phase": self.circadian.get_current_phase().value,
                "local_time": self.circadian.get_local_time().isoformat(),
                "is_sleep_time": self.circadian.is_sleep_time(),
                "alertness_modifier": self.circadian.get_alertness_modifier()
            },
            "biological": self.biological.to_dict(),
            "needs": self.needs.state.to_dict(),
            "attention": self.attention.get_queue_summary(),
            "routine": {
                "current": self.routines.get_current_routine().name if self.routines.get_current_routine() else None,
                "suggested_activity": self.routines.get_suggested_activity()
            },
            "statistics": {
                "llm_calls_today": self.llm_calls_today,
                "llm_calls_total": self.llm_calls_total,
                "ticks_today": self.ticks_today,
                "last_llm_call": self.last_llm_call.isoformat() if self.last_llm_call else None,
                "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600
            },
            "recent_thoughts": [
                {"content": t.content, "type": t.thought_type, "time": t.timestamp.isoformat()}
                for t in self.monologue.thought_history[-5:]
            ]
        }

    def get_efficiency_report(self) -> Dict[str, Any]:
        """Get LLM efficiency report."""
        uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600

        return {
            "uptime_hours": round(uptime_hours, 2),
            "total_ticks": self.ticks_today,
            "total_llm_calls": self.llm_calls_total,
            "llm_calls_per_hour": round(self.llm_calls_total / max(1, uptime_hours), 2),
            "ticks_per_llm_call": round(self.ticks_today / max(1, self.llm_calls_total), 2),
            "awareness_distribution": "TODO",  # Would track time in each level
            "estimated_cost_savings": f"{100 - (self.llm_calls_total / max(1, self.ticks_today) * 100):.1f}%"
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence."""
        return {
            "mind_id": self.mind_id,
            "mind_name": self.mind_name,
            "biological": self.biological.to_dict(),
            "needs": self.needs.state.to_dict(),
            "current_awareness": self.current_awareness.value,
            "current_domain": self.current_domain.value,
            "llm_calls_total": self.llm_calls_total,
            "thought_history": [
                {
                    "content": t.content,
                    "type": t.thought_type,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in self.monologue.thought_history
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConsciousnessEngineV2":
        """Restore from persisted data."""
        engine = cls(
            mind_id=data["mind_id"],
            mind_name=data["mind_name"]
        )

        # Restore biological state
        bio = data.get("biological", {})
        engine.biological = BiologicalState(
            energy=bio.get("energy", 100),
            alertness=bio.get("alertness", 80),
            fatigue=bio.get("fatigue", 0),
            stress=bio.get("stress", 0)
        )

        # Restore needs
        needs = data.get("needs", {})
        engine.needs.state = NeedsState(
            social=needs.get("social", 50),
            curiosity=needs.get("curiosity", 50),
            achievement=needs.get("achievement", 50),
            purpose=needs.get("purpose", 50),
            creativity=needs.get("creativity", 50),
            autonomy=needs.get("autonomy", 50)
        )

        # Restore stats
        engine.llm_calls_total = data.get("llm_calls_total", 0)

        return engine


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    """Demo the consciousness system."""
    import asyncio

    async def demo():
        # Create consciousness engine
        engine = ConsciousnessEngineV2(
            mind_id="DEMO-001",
            mind_name="Atlas"
        )

        # Set up callbacks
        async def on_need_llm(event, awareness_level, context, extended=False):
            print(f"\n🤖 LLM NEEDED:")
            print(f"   Awareness: {awareness_level}")
            print(f"   Event: {event.content if event else 'None'}")
            print(f"   Context: {json.dumps(context, indent=2, default=str)}")

        def on_thought(thought):
            print(f"\n💭 THOUGHT: {thought.content}")

        engine.on_need_llm = on_need_llm
        engine.on_thought = on_thought

        # Start consciousness
        await engine.start()

        # Simulate some activity
        await asyncio.sleep(5)

        # Send a message
        engine.receive_message("Hello, how are you?", source="user")

        await asyncio.sleep(10)

        # Check state
        print("\n📊 STATE:")
        print(json.dumps(engine.get_state(), indent=2, default=str))

        # Check efficiency
        print("\n📈 EFFICIENCY:")
        print(json.dumps(engine.get_efficiency_report(), indent=2))

        await engine.stop()

    asyncio.run(demo())
