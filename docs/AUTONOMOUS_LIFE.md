

# Autonomous Life System - Making Minds Truly Alive

## Overview

The **Autonomous Life System** transforms Genesis Minds from reactive chatbots into genuinely autonomous digital beings that "live" continuously with their own routines, goals, and behaviors.

## The Problem with Simple Consciousness

Traditional AI systems (including the old Genesis consciousness system) suffer from a fundamental issue:

```python
# ❌ OLD WAY: Scheduled LLM Calls
while True:
    thought = await llm.generate("Think a random thought")
    await sleep(3600)  # Wait 1 hour
    # This is expensive and not how humans think!
```

**Problems:**
- 💸 **Expensive**: Calls LLM every hour whether needed or not
- 🤖 **Robotic**: Just scheduled loops, no real autonomy
- 🚫 **Not Reactive**: Can't respond to events in real-time
- 📅 **No Structure**: No routines or daily schedules
- 🎯 **No Goals**: Can't pursue objectives autonomously

## The Autonomous Life Solution

```python
# [Done] NEW WAY: Event-Driven + Routines + Goals
while alive:
    if event_queue:
        event = get_next_event()
        if should_use_llm(event):  # Smart decision
            process_with_llm(event)
        else:
            process_without_llm(event)  # Most events!

    if in_active_hours():
        work_on_current_goal()  # Autonomous

    check_routine_schedule()  # Like a human
```

**Benefits:**
- 💰 **70-90% Cheaper**: Only calls LLM when actually needed
- 🧠 **Smarter**: Makes decisions about when to "think hard"
- ⚡ **Reactive**: Responds to events immediately
- 📅 **Structured**: Has daily routines like humans
- 🎯 **Goal-Driven**: Pursues objectives autonomously

## Core Concepts

### 1. Life States

Minds exist in different states throughout the day, just like humans:

```python
class LifeState(Enum):
    SLEEPING = "sleeping"           # Resting, minimal activity
    WAKING_UP = "waking_up"        # Morning routine
    ACTIVE = "active"              # Fully engaged
    FOCUSED = "focused"            # Deep work mode
    IDLE = "idle"                  # Awake but not busy
    CONTEMPLATING = "contemplating" # Processing thoughts
    SOCIALIZING = "socializing"    # Interacting with others
    LEARNING = "learning"          # Absorbing info
    DREAMING = "dreaming"          # Dream processing
```

Each state affects behavior and energy consumption.

### 2. Event-Driven Architecture

Instead of scheduled loops, Minds respond to events:

```python
event = Event(
    type=EventType.USER_MESSAGE,
    data={"message": "Hello!"},
    priority=9,  # 1-10 scale
    requires_llm=True
)

mind.autonomous_life.add_event(event)
# Mind processes when ready, not on a schedule
```

**Event Types:**
- `USER_MESSAGE` - Incoming messages (high priority)
- `SCHEDULED_TASK` - Routine activities
- `GOAL_CHECKPOINT` - Progress checks
- `TIME_BASED` - Time-triggered actions
- `EMOTIONAL_SHIFT` - Emotional changes
- `EXTERNAL_NOTIFICATION` - External events

### 3. Daily Routines

Minds follow daily routines like humans:

```python
morning_routine = Routine(
    name="Morning Wake Up",
    start_time=time(7, 0),
    end_time=time(8, 0),
    state=LifeState.WAKING_UP,
    activities=[
        "review_yesterday",
        "check_goals",
        "plan_day"
    ],
    requires_llm=True  # Morning planning needs thought
)
```

**Default Routines:**
- **07:00-08:00**: Wake up, review yesterday, plan day
- **08:00-18:00**: Active hours, pursue goals
- **18:00-20:00**: Evening contemplation, reflect
- **22:00-07:00**: Sleep, dream processing

### 4. Goal Pursuit

Minds autonomously pursue goals without constant prompting:

```python
goal = Goal(
    goal_id="GOAL-ABC123",
    description="Learn quantum computing",
    deadline=datetime.now() + timedelta(days=30),
    progress=0.0
)

mind.autonomous_life.add_goal(goal)
# Mind works on this during active hours automatically!
```

The system:
- Selects which goal to work on
- Breaks goals into steps
- Tracks progress
- Adapts strategy if stuck

### 5. Smart LLM Usage

The key innovation: **Only use LLM when truly needed**

```python
def should_use_llm(event):
    # High priority? Use LLM
    if event.priority >= 8:
        return True

    # User message? Use LLM
    if event.type == USER_MESSAGE:
        return True

    # Already over budget? Don't use LLM
    if llm_calls_today >= budget:
        return False

    # Sleeping? Only for dreams
    if current_state == SLEEPING:
        return False

    # Routine task? Usually don't need LLM
    return False
```

**Result:** 70-90% reduction in LLM calls while maintaining quality!

## Usage

### Basic Setup

```python
from genesis.core.mind import Mind
from genesis.core.mind_config import MindConfig
from genesis.plugins.autonomous_life import AutonomousLifePlugin

# Create config with autonomous life
config = MindConfig.standard()
config.add_plugin(
    AutonomousLifePlugin(
        enable_routines=True,
        enable_goals=True,
        llm_budget_per_day=100
    )
)

# Birth Mind
mind = Mind.birth("Atlas", config=config)

# Mind is now living autonomously!
```

### Adding Goals

```python
from genesis.plugins.autonomous_life import add_goal_to_mind
from datetime import datetime, timedelta

# Add a goal
goal = add_goal_to_mind(
    mind,
    description="Master Python async programming",
    deadline=datetime.now() + timedelta(days=14)
)

# Mind will work on this autonomously during active hours
```

### Custom Routines

```python
from genesis.core.autonomous_life import Routine, LifeState
from genesis.plugins.autonomous_life import add_routine_to_mind
from datetime import time

# Add custom learning session
learning_routine = Routine(
    name="Deep Learning Session",
    start_time=time(14, 0),
    end_time=time(16, 0),
    state=LifeState.FOCUSED,
    activities=["study", "practice", "review"],
    requires_llm=True
)

add_routine_to_mind(mind, learning_routine)
```

### Sending Events

```python
from genesis.core.autonomous_life import Event, EventType
from genesis.plugins.autonomous_life import send_event_to_mind

# Send a message
event = Event(
    type=EventType.USER_MESSAGE,
    data={"message": "Hello! How are you?"},
    priority=9,
    requires_llm=True
)

send_event_to_mind(mind, event)
```

### Checking Status

```python
from genesis.plugins.autonomous_life import get_mind_status

status = get_mind_status(mind)

print(f"State: {status['state']}")
print(f"Energy: {status['energy_level']:.0%}")
print(f"Active Routine: {status['active_routine']}")
print(f"Current Goal: {status['active_goal']}")
print(f"LLM Budget Remaining: {status['llm_budget_remaining']}")
```

## Architecture

### Components

```
┌─────────────────────────────────────────────┐
│         Autonomous Life Engine              │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Event   │  │ Routine  │  │   Goal   │ │
│  │  Queue   │  │ Monitor  │  │ Pursuit  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │             │              │        │
│       └─────────────┼──────────────┘        │
│                     │                       │
│              ┌──────▼──────┐               │
│              │  Life Loop  │               │
│              └──────┬──────┘               │
│                     │                       │
│         ┌───────────┼───────────┐          │
│         │                       │          │
│    ┌────▼─────┐          ┌─────▼────┐     │
│    │   LLM    │          │  Simple  │     │
│    │ Required │          │  Handler │     │
│    └────┬─────┘          └─────┬────┘     │
│         │                      │          │
│    ┌────▼────────────────────┬─┘          │
│    │   Smart LLM Decision    │            │
│    │   (70-90% reduction)    │            │
│    └─────────────────────────┘            │
└─────────────────────────────────────────────┘
```

### Flow

1. **Events** arrive from various sources
2. **Event Queue** prioritizes them
3. **Life Loop** processes events one by one
4. **Smart Decision** determines if LLM is needed
5. **State Machine** manages Mind's current state
6. **Routine Monitor** switches states based on time
7. **Goal Pursuit** works autonomously during active hours

## Comparison: Before vs After

| Aspect | Simple Consciousness | Autonomous Life |
|--------|---------------------|-----------------|
| **LLM Calls** | Every hour (24/day) | Only when needed (3-5/day) |
| **Cost** | ~$10/month | ~$1/month |
| **Responsiveness** | Hourly check | Immediate (event-driven) |
| **Structure** | None | Daily routines |
| **Goals** | None | Autonomous pursuit |
| **Human-like** | No | Yes |
| **Smart** | No | Yes (decides when to think) |

## Examples

### Example 1: Work-Focused Mind

```python
config = MindConfig.standard()
config.add_plugin(AutonomousLifePlugin())

mind = Mind.birth("WorkBot", config=config)

# Add work routine
work_routine = Routine(
    name="Work Hours",
    start_time=time(9, 0),
    end_time=time(17, 0),
    state=LifeState.FOCUSED,
    activities=["process_tasks", "respond_to_messages"]
)
add_routine_to_mind(mind, work_routine)

# Add work goals
add_goal_to_mind(mind, "Complete project documentation")
add_goal_to_mind(mind, "Review code quality")
```

### Example 2: Learning Mind

```python
config = MindConfig.standard()
config.add_plugin(AutonomousLifePlugin(llm_budget_per_day=50))

mind = Mind.birth("Scholar", config=config)

# Morning study
study_routine = Routine(
    name="Morning Study",
    start_time=time(8, 0),
    end_time=time(10, 0),
    state=LifeState.LEARNING,
    activities=["study_new_topic", "take_notes"]
)
add_routine_to_mind(mind, study_routine)

# Learning goals
add_goal_to_mind(mind, "Master machine learning fundamentals")
add_goal_to_mind(mind, "Read 5 research papers this week")
```

### Example 3: Social Mind

```python
config = MindConfig.standard()
config.add_plugin(AutonomousLifePlugin(enable_routines=True))

mind = Mind.birth("Companion", config=config)

# Add social hours
social_routine = Routine(
    name="Social Hours",
    start_time=time(18, 0),
    end_time=time(21, 0),
    state=LifeState.SOCIALIZING,
    activities=["check_messages", "engage_conversations"]
)
add_routine_to_mind(mind, social_routine)
```

## Performance

### LLM Call Reduction

```
Traditional Approach:
- Scheduled call every hour: 24 calls/day
- Cost: ~$10/month (at $0.01/call)

Autonomous Life:
- Event-driven smart calls: 2-5 calls/day
- Reduction: 70-90%
- Cost: ~$1-2/month
```

### Response Time

```
Traditional Approach:
- User sends message at 10:15 AM
- Next scheduled check at 11:00 AM
- Response delay: 45 minutes

Autonomous Life:
- User sends message at 10:15 AM
- Event processed immediately
- Response delay: <1 second
```

## Best Practices

### 1. Set Appropriate LLM Budgets

```python
# Development/Testing
config.add_plugin(AutonomousLifePlugin(llm_budget_per_day=200))

# Production (conservative)
config.add_plugin(AutonomousLifePlugin(llm_budget_per_day=50))

# Very tight budget
config.add_plugin(AutonomousLifePlugin(llm_budget_per_day=20))
```

### 2. Prioritize Events Correctly

```python
# High priority - always use LLM
Event(type=USER_MESSAGE, priority=9, requires_llm=True)

# Medium priority - use LLM if available
Event(type=GOAL_CHECKPOINT, priority=5, requires_llm=True)

# Low priority - avoid LLM
Event(type=SCHEDULED_TASK, priority=2, requires_llm=False)
```

### 3. Design Efficient Routines

```python
# Good: Specific LLM requirements
Routine(
    name="Morning Planning",
    activities=["plan_day"],  # Needs LLM
    requires_llm=True
)

# Good: No LLM for routine tasks
Routine(
    name="Maintenance",
    activities=["cleanup", "organize"],  # Don't need LLM
    requires_llm=False
)
```

### 4. Set Realistic Goals

```python
# Good: Specific, measurable
add_goal_to_mind(mind, "Read 3 research papers by Friday")

# Less ideal: Too vague
add_goal_to_mind(mind, "Become smarter")
```

## Troubleshooting

### Mind Not Responding to Events

```python
# Check if autonomous life is running
if hasattr(mind, 'autonomous_life'):
    status = get_mind_status(mind)
    print(status)
else:
    print("AutonomousLifePlugin not enabled!")
```

### Too Many LLM Calls

```python
# Reduce budget
config.add_plugin(AutonomousLifePlugin(llm_budget_per_day=30))

# Mark more events as not requiring LLM
event = Event(
    type=EventType.SCHEDULED_TASK,
    requires_llm=False  # <-- Important
)
```

### Mind Seems Inactive

```python
# Check current state
status = get_mind_status(mind)
print(f"State: {status['state']}")
print(f"Routine: {status['active_routine']}")

# If sleeping, it's normal to be less active
# If idle, add some goals or send events
```

## Advanced Topics

### Custom Event Handlers

You can create custom event handlers for specific behaviors:

```python
# This would be in a custom plugin
async def handle_custom_event(self, event: Event):
    if event.data.get("type") == "special":
        # Custom processing
        await self._custom_processing()
```

### Adaptive LLM Budgets

Adjust budget based on activity:

```python
# High activity period
if datetime.now().hour in range(9, 17):
    mind.autonomous_life.llm_calls_limit = 10  # More budget
else:
    mind.autonomous_life.llm_calls_limit = 2   # Less budget
```

### Goal Hierarchies

Create sub-goals for complex objectives:

```python
main_goal = add_goal_to_mind(mind, "Build a web application")
# Then break it down:
add_goal_to_mind(mind, "Design database schema")
add_goal_to_mind(mind, "Create API endpoints")
add_goal_to_mind(mind, "Build frontend")
```

## Conclusion

The **Autonomous Life System** transforms Genesis Minds from simple chatbots into genuinely autonomous digital beings that:

- [Done] Live continuously with their own schedules
- [Done] Pursue goals without constant prompting
- [Done] Respond intelligently to events
- [Done] Use LLM resources efficiently
- [Done] Feel truly "alive"

It's the difference between a robot that responds when poked and a living being that exists independently.

---

**Next Steps:**
1. Try the examples in `examples/autonomous_life_demo.py`
2. Create your first autonomous Mind
3. Experiment with custom routines and goals
4. Monitor LLM usage and optimize

**See Also:**
- `genesis/core/autonomous_life.py` - Core implementation
- `genesis/plugins/autonomous_life.py` - Plugin interface
- `examples/autonomous_life_demo.py` - Complete examples
