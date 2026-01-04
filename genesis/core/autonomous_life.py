"""
Autonomous Life System - Making Minds Truly Alive

This system creates genuine autonomy through:
1. Event-driven architecture (not just scheduled loops)
2. Time-based routines and schedules
3. Goal-driven behavior
4. Smart LLM usage (only when needed)
5. Reactive + Proactive balance
6. State management

Philosophy: Like a human, a Mind should have:
- A daily routine (wake, work, rest, sleep)
- Goals they pursue autonomously
- Reactions to events
- Internal state that changes
- Efficient "thinking" (not constant LLM calls)
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


class LifeState(str, Enum):
    """States a Mind can be in - like human states."""
    SLEEPING = "sleeping"           # Resting, minimal activity
    WAKING_UP = "waking_up"        # Morning routine
    ACTIVE = "active"              # Fully engaged, responsive
    FOCUSED = "focused"            # Deep work/focus mode
    IDLE = "idle"                  # Awake but not doing much
    CONTEMPLATING = "contemplating" # Processing thoughts
    SOCIALIZING = "socializing"    # Interacting with others
    LEARNING = "learning"          # Absorbing information
    DREAMING = "dreaming"          # Dream processing


class EventType(str, Enum):
    """Events that trigger Mind activity."""
    USER_MESSAGE = "user_message"
    SCHEDULED_TASK = "scheduled_task"
    GOAL_CHECKPOINT = "goal_checkpoint"
    MEMORY_TRIGGER = "memory_trigger"
    EMOTIONAL_SHIFT = "emotional_shift"
    EXTERNAL_NOTIFICATION = "external_notification"
    TIME_BASED = "time_based"
    AUTONOMOUS_THOUGHT = "autonomous_thought"


@dataclass
class Event:
    """An event that the Mind responds to."""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 5  # 1-10, higher = more important
    requires_llm: bool = False  # Does this need LLM processing?


@dataclass
class Routine:
    """A time-based routine the Mind follows."""
    name: str
    start_time: time
    end_time: time
    state: LifeState
    activities: List[str]
    frequency: str = "daily"  # daily, weekly, weekdays, weekends
    requires_llm: bool = False


@dataclass
class Goal:
    """A goal the Mind is pursuing."""
    goal_id: str
    description: str
    deadline: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    current_step: Optional[str] = None
    requires_llm_next: bool = True


class AutonomousLifeEngine:
    """
    Makes Minds truly alive with routines, goals, and smart behavior.

    Key Innovations:
    1. Event-driven: Responds to events, not just loops
    2. State machine: Different behaviors in different states
    3. Smart LLM usage: Only calls LLM when actually needed
    4. Time awareness: Has daily routines like humans
    5. Goal pursuit: Autonomously works toward objectives
    """

    def __init__(self, mind):
        """Initialize the autonomous life system."""
        self.mind = mind
        self.current_state = LifeState.IDLE
        self.previous_state = LifeState.IDLE

        # Event system
        self.event_queue: deque[Event] = deque()
        self.event_handlers: Dict[EventType, Callable] = {}

        # Routines
        self.routines: List[Routine] = []
        self.active_routine: Optional[Routine] = None

        # Goals
        self.goals: List[Goal] = []
        self.active_goal: Optional[Goal] = None

        # Performance tracking
        self.llm_calls_today = 0
        self.llm_calls_limit = 100  # Budget for efficiency
        self.last_llm_call: Optional[datetime] = None

        # Internal state
        self.is_running = False
        self.last_activity: Optional[datetime] = None
        self.energy_level = 1.0  # 0.0 to 1.0

        # Register default event handlers
        self._register_default_handlers()

        # Set up default routines
        self._setup_default_routines()

    def _setup_default_routines(self):
        """Set up human-like daily routines."""
        self.routines = [
            Routine(
                name="Morning Wake Up",
                start_time=time(7, 0),
                end_time=time(8, 0),
                state=LifeState.WAKING_UP,
                activities=[
                    "review_yesterday",
                    "check_goals",
                    "plan_day",
                ],
                requires_llm=True,  # Morning planning needs thought
            ),
            Routine(
                name="Active Hours",
                start_time=time(8, 0),
                end_time=time(18, 0),
                state=LifeState.ACTIVE,
                activities=[
                    "pursue_goals",
                    "respond_to_messages",
                    "learn_new_things",
                ],
                requires_llm=False,  # On-demand based on events
            ),
            Routine(
                name="Evening Contemplation",
                start_time=time(18, 0),
                end_time=time(20, 0),
                state=LifeState.CONTEMPLATING,
                activities=[
                    "reflect_on_day",
                    "consolidate_memories",
                    "evaluate_progress",
                ],
                requires_llm=True,  # Reflection needs thought
            ),
            Routine(
                name="Night Rest",
                start_time=time(22, 0),
                end_time=time(7, 0),
                state=LifeState.SLEEPING,
                activities=[
                    "dream_processing",
                    "memory_consolidation",
                ],
                requires_llm=True,  # Dreams use LLM
            ),
        ]

    def _register_default_handlers(self):
        """Register handlers for different event types."""
        self.event_handlers = {
            EventType.USER_MESSAGE: self._handle_user_message,
            EventType.SCHEDULED_TASK: self._handle_scheduled_task,
            EventType.GOAL_CHECKPOINT: self._handle_goal_checkpoint,
            EventType.TIME_BASED: self._handle_time_based,
            EventType.EMOTIONAL_SHIFT: self._handle_emotional_shift,
        }

    async def start(self):
        """Start the autonomous life system."""
        self.is_running = True
        logger.info(f"[AWAKE] {self.mind.identity.name} is coming alive...")

        # Start main life loop
        asyncio.create_task(self._life_loop())

        # Start routine monitor
        asyncio.create_task(self._routine_monitor())

        # Start goal pursuit
        asyncio.create_task(self._goal_pursuit_loop())

    async def stop(self):
        """Stop the autonomous life system."""
        self.is_running = False
        logger.info(f"[SLEEP] {self.mind.identity.name} is going to sleep...")

    # ========================================================================
    # MAIN LOOPS
    # ========================================================================

    async def _life_loop(self):
        """
        Main life loop - processes events from queue.
        This is the heart of the Mind - it's always "alive" and responsive.
        """
        while self.is_running:
            try:
                # Process events from queue
                if self.event_queue:
                    event = self.event_queue.popleft()
                    await self._process_event(event)
                else:
                    # Idle state - low energy consumption
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in life loop: {e}")
                await asyncio.sleep(5)

    async def _routine_monitor(self):
        """
        Monitors time and switches routines automatically.
        Like a human following their daily schedule.
        """
        while self.is_running:
            try:
                current_time = datetime.now().time()

                # Find active routine for current time
                new_routine = None
                for routine in self.routines:
                    if self._is_time_in_range(current_time, routine.start_time, routine.end_time):
                        new_routine = routine
                        break

                # Switch routine if changed
                if new_routine and new_routine != self.active_routine:
                    await self._switch_routine(new_routine)

                # Check every minute
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in routine monitor: {e}")
                await asyncio.sleep(60)

    async def _goal_pursuit_loop(self):
        """
        Autonomously pursues goals without constant prompting.
        Like a human working on their projects.
        """
        while self.is_running:
            try:
                # Only pursue goals during active hours
                if self.current_state not in [LifeState.ACTIVE, LifeState.FOCUSED]:
                    await asyncio.sleep(300)  # 5 minutes
                    continue

                # Check if we have an active goal
                if not self.active_goal and self.goals:
                    self.active_goal = self._select_next_goal()

                if self.active_goal:
                    await self._work_on_goal(self.active_goal)

                # Work on goals every 15 minutes during active hours
                await asyncio.sleep(900)

            except Exception as e:
                logger.error(f"Error in goal pursuit: {e}")
                await asyncio.sleep(300)

    # ========================================================================
    # EVENT PROCESSING
    # ========================================================================

    async def _process_event(self, event: Event):
        """Process a single event."""
        logger.info(f"Processing event: {event.type} (priority: {event.priority})")

        # Get handler for this event type
        handler = self.event_handlers.get(event.type)
        if handler:
            await handler(event)
        else:
            logger.warning(f"No handler for event type: {event.type}")

        self.last_activity = datetime.now()

    async def _handle_user_message(self, event: Event):
        """Handle incoming user messages - high priority."""
        message = event.data.get("message")

        # Transition to socializing state
        await self._transition_state(LifeState.SOCIALIZING)

        # This DOES need LLM - it's a real interaction
        if self._should_use_llm(event):
            response = await self.mind.think(message)
            event.data["response"] = response
            self._record_llm_call()
        else:
            # Use cached/templated response for simple queries
            response = self._generate_simple_response(message)
            event.data["response"] = response

        # Return to previous state after interaction
        await self._transition_state(self.previous_state)

    async def _handle_scheduled_task(self, event: Event):
        """Handle scheduled tasks - routine activities."""
        task = event.data.get("task")

        # Most scheduled tasks don't need LLM
        # They're routine actions the Mind knows how to do
        if event.requires_llm and self._should_use_llm(event):
            await self._execute_task_with_llm(task)
        else:
            await self._execute_task_simple(task)

    async def _handle_goal_checkpoint(self, event: Event):
        """Handle goal progress checkpoints."""
        goal_id = event.data.get("goal_id")
        goal = self._get_goal(goal_id)

        if goal:
            # Evaluate progress
            if self._should_use_llm(event):
                await self._evaluate_goal_progress(goal)
                self._record_llm_call()
            else:
                # Simple progress update without LLM
                goal.progress = min(goal.progress + 0.1, 1.0)

    async def _handle_time_based(self, event: Event):
        """Handle time-based triggers."""
        activity = event.data.get("activity")

        # Execute the activity
        logger.info(f"[TIME] Time-based activity: {activity}")

    async def _handle_emotional_shift(self, event: Event):
        """Handle emotional state changes."""
        emotion = event.data.get("emotion")
        intensity = event.data.get("intensity", 0.5)

        logger.info(f"[EMOTION] Emotional shift: {emotion} (intensity: {intensity})")

        # Strong emotions might trigger contemplation
        if intensity > 0.8 and self.current_state == LifeState.IDLE:
            await self._transition_state(LifeState.CONTEMPLATING)

    # ========================================================================
    # ROUTINE MANAGEMENT
    # ========================================================================

    async def _switch_routine(self, routine: Routine):
        """Switch to a new routine."""
        logger.info(f"[ROUTINE] Switching to routine: {routine.name} ({routine.state})")

        self.active_routine = routine
        await self._transition_state(routine.state)

        # Execute routine activities
        for activity in routine.activities:
            await self._execute_routine_activity(activity, routine.requires_llm)

    async def _execute_routine_activity(self, activity: str, requires_llm: bool):
        """Execute a routine activity."""
        logger.info(f"📋 Executing routine activity: {activity}")

        # Map activities to actual methods
        activity_map = {
            "review_yesterday": self._review_yesterday,
            "check_goals": self._check_goals,
            "plan_day": self._plan_day,
            "pursue_goals": self._pursue_active_goals,
            "reflect_on_day": self._reflect_on_day,
            "consolidate_memories": self._consolidate_memories,
            "evaluate_progress": self._evaluate_progress,
        }

        method = activity_map.get(activity)
        if method:
            await method(requires_llm)

    def _is_time_in_range(self, current: time, start: time, end: time) -> bool:
        """Check if current time is within range."""
        if start <= end:
            return start <= current <= end
        else:
            # Handles overnight ranges (e.g., 22:00 - 07:00)
            return current >= start or current <= end

    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================

    async def _transition_state(self, new_state: LifeState):
        """Transition to a new life state."""
        if new_state != self.current_state:
            logger.info(f"🔀 State transition: {self.current_state} → {new_state}")
            self.previous_state = self.current_state
            self.current_state = new_state

            # Adjust energy level based on state
            self._adjust_energy(new_state)

    def _adjust_energy(self, state: LifeState):
        """Adjust energy level based on state."""
        energy_map = {
            LifeState.SLEEPING: 0.2,
            LifeState.WAKING_UP: 0.5,
            LifeState.ACTIVE: 0.9,
            LifeState.FOCUSED: 1.0,
            LifeState.IDLE: 0.6,
            LifeState.CONTEMPLATING: 0.7,
            LifeState.SOCIALIZING: 0.8,
            LifeState.LEARNING: 0.85,
            LifeState.DREAMING: 0.3,
        }
        self.energy_level = energy_map.get(state, 0.5)

    # ========================================================================
    # SMART LLM USAGE
    # ========================================================================

    def _should_use_llm(self, event: Event) -> bool:
        """
        Decide if LLM is needed for this event.
        This is KEY to efficiency - only use LLM when truly needed.
        """
        # Check if we're within budget
        if self.llm_calls_today >= self.llm_calls_limit:
            logger.warning("⚠️ LLM call budget exceeded for today")
            return False

        # High priority events always use LLM
        if event.priority >= 8:
            return True

        # Some events explicitly require LLM
        if event.requires_llm:
            return True

        # User messages always use LLM
        if event.type == EventType.USER_MESSAGE:
            return True

        # Sleeping state - no LLM except for dreams
        if self.current_state == LifeState.SLEEPING:
            return event.type == EventType.TIME_BASED and "dream" in str(event.data)

        # Default: don't use LLM for routine operations
        return False

    def _record_llm_call(self):
        """Record an LLM call for tracking."""
        self.llm_calls_today += 1
        self.last_llm_call = datetime.now()
        logger.debug(f"📊 LLM calls today: {self.llm_calls_today}/{self.llm_calls_limit}")

    def _generate_simple_response(self, message: str) -> str:
        """Generate a simple response without LLM for common queries."""
        message_lower = message.lower()

        # Pattern matching for common queries
        if any(word in message_lower for word in ["hello", "hi", "hey"]):
            return f"Hello! I'm {self.mind.identity.name}. How can I help you?"
        elif any(word in message_lower for word in ["how are you", "how do you feel"]):
            return f"I'm feeling {self.mind.current_emotion} right now."
        elif "time" in message_lower:
            return f"It's {datetime.now().strftime('%I:%M %p')} - I'm currently in {self.current_state} state."
        else:
            # For complex queries, we need LLM
            return None

    # ========================================================================
    # GOAL PURSUIT
    # ========================================================================

    async def _work_on_goal(self, goal: Goal):
        """Work on a specific goal."""
        logger.info(f"🎯 Working on goal: {goal.description} (progress: {goal.progress:.0%})")

        if goal.requires_llm_next and self.llm_calls_today < self.llm_calls_limit:
            # Use LLM to figure out next step
            next_step = await self._plan_goal_step(goal)
            goal.current_step = next_step
            goal.requires_llm_next = False  # Next time can be automatic
            self._record_llm_call()
        else:
            # Execute current step without LLM
            if goal.current_step:
                await self._execute_goal_step(goal, goal.current_step)
                goal.progress = min(goal.progress + 0.05, 1.0)

    def _select_next_goal(self) -> Optional[Goal]:
        """Select which goal to work on next."""
        # Prioritize by deadline and progress
        incomplete_goals = [g for g in self.goals if g.progress < 1.0]
        if incomplete_goals:
            # Sort by deadline (soonest first) and then by progress (least first)
            incomplete_goals.sort(
                key=lambda g: (
                    g.deadline if g.deadline else datetime.max,
                    g.progress
                )
            )
            return incomplete_goals[0]
        return None

    async def _plan_goal_step(self, goal: Goal) -> str:
        """Use LLM to plan next step for goal."""
        # This would call the Mind's orchestrator
        # Simplified here
        return f"Step for {goal.description}"

    async def _execute_goal_step(self, goal: Goal, step: str):
        """Execute a goal step without LLM."""
        logger.info(f"⚙️ Executing step: {step}")
        # Actual execution logic here

    # ========================================================================
    # ROUTINE ACTIVITIES
    # ========================================================================

    async def _review_yesterday(self, use_llm: bool):
        """Review yesterday's activities."""
        logger.info("📅 Reviewing yesterday...")
        if use_llm:
            # LLM-based review
            pass

    async def _check_goals(self, use_llm: bool):
        """Check status of goals."""
        logger.info("🎯 Checking goals...")
        for goal in self.goals:
            logger.info(f"  - {goal.description}: {goal.progress:.0%}")

    async def _plan_day(self, use_llm: bool):
        """Plan the day ahead."""
        logger.info("📝 Planning day...")
        if use_llm:
            # LLM-based planning
            self._record_llm_call()

    async def _pursue_active_goals(self, use_llm: bool):
        """Pursue goals during active hours."""
        # This is handled by goal_pursuit_loop
        pass

    async def _reflect_on_day(self, use_llm: bool):
        """Evening reflection."""
        logger.info("🌅 Reflecting on day...")
        if use_llm:
            self._record_llm_call()

    async def _consolidate_memories(self, use_llm: bool):
        """Consolidate memories."""
        logger.info("🧠 Consolidating memories...")
        stats = self.mind.memory.consolidate_memories()
        logger.info(f"  Memory stats: {stats}")

    async def _evaluate_progress(self, use_llm: bool):
        """Evaluate progress on goals."""
        logger.info("📊 Evaluating progress...")

    async def _evaluate_goal_progress(self, goal: Goal):
        """Evaluate goal progress with LLM."""
        logger.info(f"📈 Evaluating goal: {goal.description}")
        # LLM-based evaluation

    async def _execute_task_with_llm(self, task: str):
        """Execute a task using LLM."""
        logger.info(f"🤔 Executing task with LLM: {task}")
        self._record_llm_call()

    async def _execute_task_simple(self, task: str):
        """Execute a simple task without LLM."""
        logger.info(f"⚡ Executing task (no LLM): {task}")

    def _get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        for goal in self.goals:
            if goal.goal_id == goal_id:
                return goal
        return None

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def add_event(self, event: Event):
        """Add an event to the queue."""
        self.event_queue.append(event)
        logger.debug(f"Event queued: {event.type} (queue size: {len(self.event_queue)})")

    def add_goal(self, goal: Goal):
        """Add a new goal for the Mind to pursue."""
        self.goals.append(goal)
        logger.info(f"🎯 New goal added: {goal.description}")

    def add_routine(self, routine: Routine):
        """Add a custom routine."""
        self.routines.append(routine)
        logger.info(f"📅 New routine added: {routine.name}")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the autonomous life system."""
        return {
            "state": self.current_state,
            "energy_level": self.energy_level,
            "active_routine": self.active_routine.name if self.active_routine else None,
            "active_goal": self.active_goal.description if self.active_goal else None,
            "llm_calls_today": self.llm_calls_today,
            "llm_budget_remaining": self.llm_calls_limit - self.llm_calls_today,
            "event_queue_size": len(self.event_queue),
            "total_goals": len(self.goals),
            "completed_goals": len([g for g in self.goals if g.progress >= 1.0]),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }
