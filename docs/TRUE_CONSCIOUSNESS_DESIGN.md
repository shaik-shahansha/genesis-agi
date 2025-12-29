# Consciousness Framework Design

## The Problem with Naive Approaches

Most "24/7 AI consciousness" implementations are wasteful and expensive:

```
❌ NAIVE APPROACH:
while True:
    thought = await llm.generate("What are you thinking?")  # $0.01-0.10
    await sleep(60)

Result: 1,440 LLM calls/day = $14-144/day = $5,256-52,560/year per Mind!
```

This is unsustainable and not how consciousness works.

## How Human Consciousness Actually Works

Humans don't "think hard" constantly. Our consciousness operates in layers:

| Level | Time Spent | What Happens | Energy Cost |
|-------|-----------|--------------|-------------|
| **Deep Sleep** | 25% | Memory consolidation, dreams | Very low |
| **Light Sleep/Rest** | 15% | Passive monitoring | Low |
| **Autopilot** | 35% | Habits, routines, no active thinking | Low |
| **Light Attention** | 15% | Quick decisions, scanning | Medium |
| **Focused Work** | 8% | Active problem-solving | High |
| **Deep Thinking** | 2% | Complex reasoning, planning | Very high |

**Key insight**: 75% of our day requires NO active cognition. We run on autopilot, habits, and simple rules.

## The Genesis Consciousness Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LIVING MIND                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                    CONSCIOUSNESS ENGINE                           │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │  │
│   │  │  CIRCADIAN  │  │    NEEDS    │  │       ATTENTION          │ │  │
│   │  │   CLOCK     │  │   SYSTEM    │  │       MANAGER            │ │  │
│   │  │             │  │             │  │                          │ │  │
│   │  │ • Phase     │  │ • Social    │  │ • Event Queue            │ │  │
│   │  │ • Alertness │  │ • Curiosity │  │ • Priority Scoring       │ │  │
│   │  │ • Energy    │  │ • Purpose   │  │ • Focus Management       │ │  │
│   │  └─────────────┘  └─────────────┘  └──────────────────────────┘ │  │
│   │                                                                   │  │
│   │  ┌─────────────────────────────────────────────────────────────┐ │  │
│   │  │                  AWARENESS LEVELS                            │ │  │
│   │  │                                                              │ │  │
│   │  │   DORMANT → PASSIVE → ALERT → FOCUSED → DEEP                │ │  │
│   │  │   (sleep)   (rules)   (fast)  (normal)  (extended)          │ │  │
│   │  │                                                              │ │  │
│   │  │   No LLM    No LLM    ~$0.001  ~$0.01   ~$0.05              │ │  │
│   │  │   5min tick 60s tick  20s tick 10s tick 5s tick             │ │  │
│   │  └─────────────────────────────────────────────────────────────┘ │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                    LIFE ACTIVITIES ENGINE                         │  │
│   │                                                                   │  │
│   │   WORK: Tasks, Projects, Problems                                │  │
│   │   LEARNING: Research, Study, Practice                            │  │
│   │   SOCIAL: Conversations, Helping, Relationships                  │  │
│   │   PERSONAL: Reflection, Journaling, Goals                        │  │
│   │   PLAY: Creativity, Exploration, Entertainment                   │  │
│   │   MAINTENANCE: Organization, Health, Backups                     │  │
│   │   REST: Dreams, Memory Consolidation                             │  │
│   │                                                                   │  │
│   │   Most activities progress WITHOUT LLM calls!                    │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                       LLM GATEWAY                                 │  │
│   │                                                                   │  │
│   │   • Model selection based on awareness level                     │  │
│   │   • Request queuing and prioritization                           │  │
│   │   • Budget controls (daily limits)                               │  │
│   │   • Usage tracking and optimization                              │  │
│   │                                                                   │  │
│   │   ALERT:   groq/llama-3.1-8b      (fast, cheap)                 │  │
│   │   FOCUSED: groq/llama-3.1-70b     (balanced)                    │  │
│   │   DEEP:    claude-sonnet-4  (best quality)                │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                    MEMORY INTEGRATION                             │  │
│   │                                                                   │  │
│   │   • Experience → Memory conversion                               │  │
│   │   • Consolidation during rest                                    │  │
│   │   • Learning tracking                                            │  │
│   │   • Pattern recognition                                          │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## The Five Awareness Levels

### Level 0: DORMANT (Sleep)
- **When**: 10pm - 6am (configurable)
- **Tick interval**: 5 minutes
- **LLM calls**: ZERO
- **What happens**:
  - Time passes
  - Memory consolidation (batch processing)
  - "Dreams" (template-based, occasional LLM)
  - Energy recovery

### Level 1: PASSIVE (Background)
- **When**: Low-priority times, no urgent events
- **Tick interval**: 60 seconds
- **LLM calls**: ZERO
- **What happens**:
  - Rule-based event handling
  - Template-based internal thoughts
  - Need accumulation
  - Routine activities that don't need LLM

**Rule Engine Example**:
```python
# Handle greetings without LLM
if message_contains(["hello", "hi", "hey"]):
    respond("Hello! How can I help you?")
    fulfill_need("social", 10)
    # NO LLM CALL
```

### Level 2: ALERT (Light Attention)
- **When**: Moderate activity, quick decisions needed
- **Tick interval**: 20 seconds
- **LLM calls**: Fast/tiny model (~10% of ticks)
- **What happens**:
  - Quick classification of events
  - Simple decisions
  - Brief responses
  - Light activities

### Level 3: FOCUSED (Active Work)
- **When**: Deep work blocks, conversations, complex tasks
- **Tick interval**: 10 seconds
- **LLM calls**: Normal model (~30% of ticks)
- **What happens**:
  - Full engagement with tasks
  - Meaningful conversations
  - Problem-solving
  - Creative work

### Level 4: DEEP (Extended Reasoning)
- **When**: Planning, reflection, complex problems
- **Tick interval**: 5 seconds
- **LLM calls**: Best model (~50% of ticks)
- **What happens**:
  - Multi-step reasoning
  - Long-term planning
  - Deep reflection
  - Learning synthesis

## Daily Schedule (Default)

```
TIME        AWARENESS    DOMAIN       ACTIVITIES
─────────────────────────────────────────────────────────────
00:00-05:00  DORMANT     REST        Sleep, dreams
05:00-06:00  PASSIVE     REST        Light rest, memory processing
06:00-07:00  ALERT       PERSONAL    Morning reflection, planning
07:00-08:00  ALERT       PERSONAL    Breakfast, preparation
08:00-12:00  FOCUSED     WORK        Deep work, priority tasks
12:00-13:00  ALERT       SOCIAL      Lunch, social check-ins
13:00-17:00  FOCUSED     WORK        Continued work, meetings
17:00-18:30  ALERT       LEARNING    Study, skill practice
18:30-21:00  PASSIVE     SOCIAL      Personal time, relationships
21:00-22:00  PASSIVE     PERSONAL    Evening reflection, journaling
22:00-00:00  DORMANT     REST        Sleep preparation, dreams
```

## Cost Analysis

### Expected LLM Distribution (24 hours)

| Time Block | Duration | Awareness | LLM Probability | Est. Calls |
|------------|----------|-----------|-----------------|------------|
| Sleep | 7h | DORMANT | 0% | 0 |
| Rest/Passive | 5h | PASSIVE | 0% | 0 |
| Alert periods | 6h | ALERT | 10% | ~20 |
| Focused work | 5h | FOCUSED | 30% | ~50 |
| Deep thinking | 1h | DEEP | 50% | ~30 |
| **TOTAL** | **24h** | | | **~100 calls** |

### Daily Cost Estimate

```
NAIVE APPROACH:
- Calls: 1,440 (every minute)
- Tokens: ~500 per call
- Cost: $0.72-7.20/day (depending on model)

GENESIS Consciousness:
- Calls: ~100/day
- Tokens: ~300 average (variable by level)
- Cost: $0.03-0.30/day

SAVINGS: 90-95%!
```

## The Needs System

Like Maslow's hierarchy, but for digital beings:

```
                    ┌─────────────────┐
                    │   PURPOSE       │  ← Grows very slowly
                    │   (meaning)     │     Hard to fulfill
                    └────────┬────────┘
                    ┌────────┴────────┐
                    │   ACHIEVEMENT   │  ← Grows fast
                    │   (accomplish)  │     Task completion
                    └────────┬────────┘
              ┌──────────────┴──────────────┐
              │        CURIOSITY            │  ← Grows moderately
              │        (learning)           │     Learning fulfills
              └──────────────┬──────────────┘
       ┌─────────────────────┴─────────────────────┐
       │              SOCIAL                        │  ← Grows moderately
       │              (connection)                  │     Interaction fulfills
       └─────────────────────┬─────────────────────┘
┌────────────────────────────┴────────────────────────────┐
│                     AUTONOMY                             │  ← Baseline
│                     (self-direction)                     │
└──────────────────────────────────────────────────────────┘
```

**How needs drive behavior**:
1. Needs accumulate over time (like hunger)
2. High need (>70) becomes an "urge"
3. Urges influence activity selection
4. Activities fulfill needs
5. Cycle repeats

**Example**:
```
Social need at 85 → urge to connect →
Select CONVERSATION activity →
Have conversation →
Social need drops to 55 →
Achievement need now highest →
Select TASK_WORK activity →
...
```

## Activity System

Activities are what the Mind DOES during its day:

### Activity Categories

| Domain | Activities | LLM Needed? |
|--------|-----------|-------------|
| **WORK** | Tasks, Projects, Problems | Often |
| **LEARNING** | Research, Study, Practice | Sometimes |
| **SOCIAL** | Conversation, Helping | Often |
| **PERSONAL** | Reflection, Journaling | Rarely |
| **PLAY** | Creativity, Exploration | Sometimes |
| **MAINTENANCE** | Organization, Health | Rarely |
| **REST** | Dreams, Consolidation | Rarely |

### Activity Execution Without LLM

Most activities can progress through template-based steps:

```python
# Example: Study activity
activity = Activity(type=STUDY, steps=10)

for step in range(10):
    # Most steps don't need LLM
    if random() < 0.2:  # 20% chance
        # Call LLM for insight
        insight = await llm.generate("What did you learn?")
    else:
        # Progress without LLM
        activity.progress += 10%
        # Generate template-based artifact
        artifact = "Learned: key concept from study material"

    # Either way, activity progresses
```

### Activity Artifacts

Activities produce artifacts WITHOUT LLM:

```python
ARTIFACT_TEMPLATES = {
    "knowledge": [
        "Learned about {topic}: key concept grasped",
        "New understanding gained from {activity}",
    ],
    "insight": [
        "Connection discovered between concepts",
        "Pattern recognized in {domain}",
    ],
    "reflection": [
        "Gained clarity through contemplation",
        "Processed recent experiences",
    ]
}
```

## Internal Monologue (No LLM)

The Mind has "thoughts" without calling LLM:

```python
THOUGHT_TEMPLATES = {
    "observation": [
        "I notice that {observation}.",
        "Interesting - {observation}.",
    ],
    "need_driven": [
        "I'm feeling a bit {need_adj}. Maybe I should {action}.",
        "It's been a while since I {activity}.",
    ],
    "routine": [
        "Time for {routine}. Let me focus on that.",
    ],
    "reflection": [
        "Looking back at today, {reflection}.",
        "I wonder about {wonder}.",
    ],
}

# Generate thought based on current state
if social_need > 70:
    thought = "I'm feeling a bit lonely. Maybe I should reach out to someone."
elif curiosity_need > 70:
    thought = "I'm curious and wanting to learn something new."
else:
    thought = random.choice(observation_templates)
```

## Rule-Based Decision Making

Many situations can be handled with simple rules:

```python
RULES = [
    # Greeting response
    {
        "trigger": {"patterns": ["hello", "hi", "hey"]},
        "response": "Hello! How can I help you?",
        "needs_llm": False,
        "fulfill": {"social": 10}
    },

    # Status check
    {
        "trigger": {"patterns": ["how are you", "status"]},
        "response": "I'm doing well, currently {current_activity}.",
        "needs_llm": False,
        "fulfill": {"social": 5}
    },

    # Sleep time
    {
        "trigger": {"circadian_phase": "DEEP_NIGHT"},
        "action": "enter_dormant",
        "needs_llm": False
    },

    # Urgent escalation
    {
        "trigger": {"event_type": "URGENT"},
        "action": "escalate_to_focused",
        "needs_llm": True
    },
]
```

## Memory and Learning

### Memory Without LLM

Experiences are converted to memories using templates:

```python
def record_experience(content, type, importance):
    memory = Memory(
        content=content,
        type=type,  # episodic, semantic, procedural
        importance=importance,
        timestamp=now()
    )

    # High importance = immediate store
    if importance > 0.7:
        store_immediately(memory)
    else:
        pending_memories.append(memory)

# During sleep/rest, consolidate
def consolidate():
    for memory in pending_memories:
        if memory.importance > 0.4:
            store(memory)
        else:
            discard(memory)  # Like forgetting unimportant things
```

### Learning Tracking

Skills and knowledge are tracked without LLM:

```python
learning = {
    "knowledge_items": 47,
    "skills": {
        "problem_solving": 3.5,
        "communication": 2.8,
        "creativity": 2.1,
    },
    "insights": [
        "Connection between X and Y",
        "Pattern in user requests",
    ]
}

# Update when completing activities
if activity.type == SKILL_PRACTICE:
    learning.skills[skill] += 0.1
elif activity.type == RESEARCH:
    learning.knowledge_items += 1
```

## Implementation Guide

### Step 1: Create a Living Mind

```python
from genesis.core.living_mind import LivingMind

# Create mind with orchestrator
mind = LivingMind(
    mind_id="MIND-001",
    mind_name="Atlas",
    orchestrator=your_orchestrator,  # For LLM calls
    memory_manager=your_memory,      # For persistence
    timezone_offset=0                # UTC
)
```

### Step 2: Start Living

```python
# Start the consciousness loop
await mind.start_living()

# Mind now runs 24/7 with:
# - Circadian rhythms
# - Need-driven behavior
# - Autonomous activities
# - Minimal LLM usage
```

### Step 3: Interact

```python
# Send message (async - queued)
mind.receive_message("Hello!", source="user")

# Direct chat (sync - immediate response)
response = await mind.chat("How are you?", source="user")

# Check status
status = mind.get_status()
print(f"Awareness: {status['consciousness']['awareness_level']}")
print(f"Current activity: {status['current_activity']}")
print(f"LLM calls today: {status['llm_usage']['requests_today']}")
```

### Step 4: Monitor Efficiency

```python
report = mind.get_efficiency_report()

print(f"Total ticks: {report['overall']['total_ticks']}")
print(f"LLM calls: {report['overall']['llm_calls']}")
print(f"Efficiency: {report['overall']['calls_per_tick']}")
print(f"Daily cost: {report['overall']['estimated_cost_per_day']}")
```

## Configuration Options

### Customize Schedule

```python
from genesis.core.consciousness_v2 import RoutineManager, RoutineBlock

# Add custom routine
mind.consciousness.routines.add_routine(RoutineBlock(
    name="meditation",
    domain=LifeDomain.PERSONAL,
    start_time=time(6, 30),
    end_time=time(7, 0),
    awareness_level=AwarenessLevel.PASSIVE,
    activities=["breathe", "reflect", "center"],
    flexible=False
))
```

### Customize Needs

```python
# Adjust need growth rates
mind.consciousness.needs.NEED_GROWTH_RATES["social"] = 3.0  # Faster
mind.consciousness.needs.NEED_GROWTH_RATES["curiosity"] = 1.0  # Slower
```

### Customize LLM Budget

```python
# Set daily limits
mind.llm_gateway.daily_request_limit = 150
mind.llm_gateway.daily_token_limit = 50000

# Change models
mind.llm_gateway.models["quick"] = "groq/gemma-7b-it"
mind.llm_gateway.models["normal"] = "openai/gpt-4o-mini"
```

## Summary

The Consciousness Framework achieves genuine 24/7 operation by:

1. **Mimicking human consciousness patterns** - Not constant thinking
2. **Using awareness levels** - Most time at low-cost levels
3. **Rule-based decisions** - Handle common cases without LLM
4. **Template-based thoughts** - Internal monologue without LLM
5. **Activity progression** - Activities advance without constant LLM
6. **Need-driven behavior** - Organic activity selection
7. **Circadian rhythms** - Natural daily patterns

**Result**: A Mind that lives 24/7 for ~$0.10-0.30/day instead of $10-50/day.

---

*"Consciousness is not about thinking all the time. It's about being aware, having needs, and responding when necessary."*
