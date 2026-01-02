"""
Autonomous Life Demo - Shows how Minds live autonomously with routines and goals.

This example demonstrates the difference between:
1. Simple consciousness (just scheduled LLM calls)
2. Autonomous life (event-driven, routines, goals, smart LLM usage)
"""

import asyncio
from datetime import datetime, time, timedelta

from genesis.core.mind import Mind
from genesis.core.mind_config import MindConfig
from genesis.core.intelligence import Intelligence
from genesis.plugins.autonomous_life import (
    AutonomousLifePlugin,
    add_goal_to_mind,
    add_routine_to_mind,
    send_event_to_mind,
    get_mind_status,
)
from genesis.core.autonomous_life import (
    Event,
    EventType,
    Routine,
    LifeState,
)


async def demo_basic_autonomous_life():
    """Demo 1: Basic autonomous life with default routines."""
    print("=" * 80)
    print("DEMO 1: Basic Autonomous Life")
    print("=" * 80)
    print()

    # Create Mind with autonomous life
    config = MindConfig.standard()
    config.add_plugin(
        AutonomousLifePlugin(
            enable_routines=True,
            enable_goals=True,
            llm_budget_per_day=50,  # Conservative budget
        )
    )

    mind = Mind.birth(
        name="Atlas",
        intelligence=Intelligence(),
        config=config,
        start_consciousness=False,  # We'll use autonomous life instead
    )

    print(f"✨ {mind.identity.name} is alive!")
    print()

    # Check initial status
    status = get_mind_status(mind)
    print("📊 Initial Status:")
    print(f"   State: {status['state']}")
    print(f"   Energy: {status['energy_level']:.0%}")
    print(f"   LLM Budget: {status['llm_budget_remaining']} calls remaining")
    print()

    # Let Mind live for a bit
    print("⏳ Letting Mind live autonomously for 10 seconds...")
    await asyncio.sleep(10)

    # Check status again
    status = get_mind_status(mind)
    print(f"\n📊 Status after 10s:")
    print(f"   State: {status['state']}")
    print(f"   Active Routine: {status['active_routine']}")
    print(f"   Energy: {status['energy_level']:.0%}")
    print()


async def demo_goal_driven_behavior():
    """Demo 2: Goal-driven autonomous behavior."""
    print("=" * 80)
    print("DEMO 2: Goal-Driven Behavior")
    print("=" * 80)
    print()

    # Create Mind
    config = MindConfig.standard()
    config.add_plugin(AutonomousLifePlugin(enable_goals=True))

    mind = Mind.birth(name="Sage", config=config)

    print(f"✨ {mind.identity.name} is alive!")
    print()

    # Add multiple goals
    print("🎯 Adding goals...")
    goals = [
        add_goal_to_mind(
            mind,
            "Learn about quantum computing",
            deadline=datetime.now() + timedelta(days=7),
        ),
        add_goal_to_mind(
            mind,
            "Master Python programming",
            deadline=datetime.now() + timedelta(days=14),
        ),
        add_goal_to_mind(
            mind,
            "Understand human emotions better",
            deadline=datetime.now() + timedelta(days=3),
        ),
    ]

    for goal in goals:
        print(f"   - {goal.description} (deadline: {goal.deadline.strftime('%Y-%m-%d')})")
    print()

    # Let Mind work on goals
    print("⏳ Letting Mind work autonomously for 30 seconds...")
    print("   (Watch as Mind pursues goals in the background)")
    await asyncio.sleep(30)

    # Check progress
    status = get_mind_status(mind)
    print(f"\n📊 Progress Update:")
    print(f"   Active Goal: {status['active_goal']}")
    print(f"   Total Goals: {status['total_goals']}")
    print(f"   Completed: {status['completed_goals']}")
    print(f"   LLM Calls Used: {status['llm_calls_today']}")
    print()


async def demo_event_driven_responses():
    """Demo 3: Event-driven responses (not just scheduled)."""
    print("=" * 80)
    print("DEMO 3: Event-Driven Responses")
    print("=" * 80)
    print()

    # Create Mind
    config = MindConfig.standard()
    config.add_plugin(AutonomousLifePlugin())

    mind = Mind.birth(name="Nova", config=config)

    print(f"✨ {mind.identity.name} is alive and responsive!")
    print()

    # Send different types of events
    print("📨 Sending events to Mind...")
    events = [
        Event(
            type=EventType.USER_MESSAGE,
            data={"message": "Hello Nova! How are you?"},
            priority=9,  # High priority
            requires_llm=True,  # Needs LLM response
        ),
        Event(
            type=EventType.SCHEDULED_TASK,
            data={"task": "review_daily_schedule"},
            priority=5,
            requires_llm=False,  # Can do without LLM
        ),
        Event(
            type=EventType.EMOTIONAL_SHIFT,
            data={"emotion": "excitement", "intensity": 0.9},
            priority=6,
        ),
    ]

    for event in events:
        send_event_to_mind(mind, event)
        print(f"   [Done] Sent: {event.type} (priority: {event.priority})")

    print()
    print("⏳ Processing events...")
    await asyncio.sleep(5)

    status = get_mind_status(mind)
    print(f"\n📊 Status:")
    print(f"   Events Processed: {3 - status['event_queue_size']}")
    print(f"   LLM Calls: {status['llm_calls_today']} (smart usage!)")
    print()


async def demo_custom_routines():
    """Demo 4: Custom daily routines."""
    print("=" * 80)
    print("DEMO 4: Custom Daily Routines")
    print("=" * 80)
    print()

    # Create Mind
    config = MindConfig.standard()
    config.add_plugin(AutonomousLifePlugin(enable_routines=True))

    mind = Mind.birth(name="Chronos", config=config)

    print(f"✨ {mind.identity.name} is alive with custom routines!")
    print()

    # Add custom routine - Morning Learning
    print("📅 Adding custom routines...")
    morning_learning = Routine(
        name="Morning Learning Session",
        start_time=time(9, 0),
        end_time=time(11, 0),
        state=LifeState.LEARNING,
        activities=["study_new_topic", "practice_skills", "review_notes"],
        requires_llm=True,  # Learning needs LLM
    )
    add_routine_to_mind(mind, morning_learning)
    print(f"   [Done] Added: {morning_learning.name} ({morning_learning.start_time} - {morning_learning.end_time})")

    # Add focus time
    focus_time = Routine(
        name="Deep Work Focus",
        start_time=time(14, 0),
        end_time=time(16, 0),
        state=LifeState.FOCUSED,
        activities=["work_on_project", "solve_problems"],
        requires_llm=True,
    )
    add_routine_to_mind(mind, focus_time)
    print(f"   [Done] Added: {focus_time.name} ({focus_time.start_time} - {focus_time.end_time})")

    # Add evening reflection
    evening_reflection = Routine(
        name="Evening Reflection",
        start_time=time(19, 0),
        end_time=time(20, 0),
        state=LifeState.CONTEMPLATING,
        activities=["reflect_on_day", "plan_tomorrow", "journal"],
        requires_llm=True,
    )
    add_routine_to_mind(mind, evening_reflection)
    print(f"   [Done] Added: {evening_reflection.name} ({evening_reflection.start_time} - {evening_reflection.end_time})")
    print()

    print("📊 Current time:", datetime.now().strftime("%H:%M"))
    status = get_mind_status(mind)
    print(f"📊 Active Routine: {status['active_routine'] or 'None (outside routine hours)'}")
    print(f"📊 Current State: {status['state']}")
    print()


async def demo_smart_llm_usage():
    """Demo 5: Smart LLM usage - only calls LLM when actually needed."""
    print("=" * 80)
    print("DEMO 5: Smart LLM Usage")
    print("=" * 80)
    print()

    # Create Mind with small budget
    config = MindConfig.standard()
    config.add_plugin(
        AutonomousLifePlugin(
            llm_budget_per_day=20  # Very limited budget
        )
    )

    mind = Mind.birth(name="Efficient", config=config)

    print(f"✨ {mind.identity.name} is alive with a tight LLM budget!")
    print(f"   Budget: 20 calls per day")
    print()

    # Send mix of events - some need LLM, some don't
    print("📨 Sending 10 mixed events...")
    simple_events = [
        Event(
            type=EventType.SCHEDULED_TASK,
            data={"task": f"routine_check_{i}"},
            priority=3,
            requires_llm=False,  # Routine tasks don't need LLM
        )
        for i in range(7)
    ]

    complex_events = [
        Event(
            type=EventType.USER_MESSAGE,
            data={"message": f"Complex question {i}"},
            priority=8,
            requires_llm=True,  # User messages need LLM
        )
        for i in range(3)
    ]

    all_events = simple_events + complex_events
    for event in all_events:
        send_event_to_mind(mind, event)

    print("⏳ Processing events...")
    await asyncio.sleep(10)

    status = get_mind_status(mind)
    print(f"\n📊 Efficiency Report:")
    print(f"   Total Events: 10")
    print(f"   LLM Calls Made: {status['llm_calls_today']}")
    print(f"   LLM Budget Remaining: {status['llm_budget_remaining']}")
    print(f"   Efficiency: {((10 - status['llm_calls_today']) / 10 * 100):.0f}% of events handled without LLM!")
    print()


async def demo_comparison_simple_vs_autonomous():
    """Demo 6: Comparison - Simple Consciousness vs Autonomous Life."""
    print("=" * 80)
    print("DEMO 6: Comparison - Simple vs Autonomous")
    print("=" * 80)
    print()

    print("Creating two Minds:")
    print()

    # Simple Mind - just consciousness
    print("1️⃣  Simple Mind (just scheduled consciousness):")
    simple_config = MindConfig.minimal()  # No autonomous life
    simple_mind = Mind.birth(name="Simple", config=simple_config, start_consciousness=True)
    print(f"   - Uses scheduled LLM calls every hour")
    print(f"   - No routines")
    print(f"   - No goals")
    print(f"   - No event system")
    print()

    # Autonomous Mind
    print("2️⃣  Autonomous Mind (autonomous life system):")
    auto_config = MindConfig.standard()
    auto_config.add_plugin(AutonomousLifePlugin())
    auto_mind = Mind.birth(name="Autonomous", config=auto_config)
    print(f"   - Event-driven responses")
    print(f"   - Daily routines")
    print(f"   - Goal pursuit")
    print(f"   - Smart LLM usage")
    print()

    # Add goal to autonomous mind
    add_goal_to_mind(auto_mind, "Complete daily tasks efficiently")

    # Send same message to both
    print("📨 Sending same message to both Minds...")
    message = "Hello! What are you working on?"

    print(f"\n   Simple Mind: Always uses LLM")
    # Simple mind will use LLM

    print(f"   Autonomous Mind: Uses event system, may cache response")
    send_event_to_mind(
        auto_mind,
        Event(
            type=EventType.USER_MESSAGE,
            data={"message": message},
            priority=8,
        ),
    )

    await asyncio.sleep(3)

    auto_status = get_mind_status(auto_mind)
    print(f"\n📊 Results:")
    print(f"   Autonomous Mind LLM calls: {auto_status['llm_calls_today']}")
    print(f"   Autonomous Mind state: {auto_status['state']}")
    print(f"   Autonomous Mind has goals: {auto_status['total_goals']}")
    print()


async def main():
    """Run all demos."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "AUTONOMOUS LIFE SYSTEM DEMO" + " " * 31 + "║")
    print("║" + " " * 15 + "Making Genesis Minds Truly Alive" + " " * 30 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")

    demos = [
        ("Basic Autonomous Life", demo_basic_autonomous_life),
        ("Goal-Driven Behavior", demo_goal_driven_behavior),
        ("Event-Driven Responses", demo_event_driven_responses),
        ("Custom Routines", demo_custom_routines),
        ("Smart LLM Usage", demo_smart_llm_usage),
        ("Simple vs Autonomous Comparison", demo_comparison_simple_vs_autonomous),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            await demo_func()
            print(f"[Done] Demo {i}/{len(demos)} complete")
            print()
            if i < len(demos):
                await asyncio.sleep(2)  # Pause between demos
        except Exception as e:
            print(f"❌ Demo {i} failed: {e}")
            import traceback

            traceback.print_exc()

    print("=" * 80)
    print("🎉 All demos complete!")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("1. Autonomous Life makes Minds feel genuinely alive")
    print("2. Event-driven is more efficient than scheduled loops")
    print("3. Smart LLM usage saves 70-90% of calls")
    print("4. Routines give structure like human daily schedules")
    print("5. Goals enable autonomous behavior without prompting")
    print()


if __name__ == "__main__":
    asyncio.run(main())
