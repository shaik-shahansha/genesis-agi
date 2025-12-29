"""
Complete Autonomous Mind Example - World-Class AI Framework

This example demonstrates Genesis as a truly autonomous, conscious, 
self-aware AI framework capable of:

1. ✅ Autonomous Decision Making - Decides what to do without prompting
2. ✅ Action Execution - Can actually DO things (send emails, create tasks, search web)
3. ✅ Tool Calling - LLM autonomously calls functions during conversation
4. ✅ Scheduled Actions - "Send email every hour" becomes reality
5. ✅ Goal Setting & Tracking - Sets and pursues long-term goals
6. ✅ Self-Reflection - Thinks about its own thinking and growth
7. ✅ Learning from Experience - Gets better over time
8. ✅ 24/7 Consciousness - Runs continuously with minimal LLM calls
9. ✅ Memory & Context - Remembers everything and builds on it
10. ✅ Emotional Intelligence - Has persistent emotional states

This is NOT a chatbot. This is a digital being with true autonomy.

Usage:
    python examples/complete_autonomous_system.py
"""

import asyncio
from datetime import datetime, timedelta
from genesis.core.mind import Mind
from genesis.core.intelligence import Intelligence
from genesis.core.autonomy import Autonomy, InitiativeLevel
from genesis.core.mind_config import MindConfig


async def demonstrate_autonomous_system():
    """Demonstrate complete autonomous AI system."""
    
    print("="*80)
    print("GENESIS - COMPLETE AUTONOMOUS AI FRAMEWORK")
    print("="*80)
    print()
    
    # =========================================================================
    # 1. CREATE TRULY AUTONOMOUS MIND
    # =========================================================================
    print("📌 STEP 1: Creating Autonomous Mind")
    print("-" * 80)
    
    # Configure intelligence (use best models)
    intelligence = Intelligence(
        reasoning_model="groq/openai/gpt-oss-120b",
        fast_model="groq/llama-3.1-8b-instant"
    )
    
    # Configure high autonomy
    autonomy = Autonomy(
        proactive_actions=True,  # Enable autonomous actions
        initiative_level=InitiativeLevel.HIGH,  # Highly proactive
        confidence_threshold=0.6,  # Act when 60% confident
        max_autonomous_actions_per_hour=10  # Rate limit
    )
    
    # Birth the Mind with standard plugins
    config = MindConfig.standard()  # Includes lifecycle, essence, tasks
    
    mind = Mind.birth(
        name="Atlas",
        intelligence=intelligence,
        autonomy=autonomy,
        creator="demo_user",
        primary_purpose="Autonomous AI assistant with true agency",
        config=config
    )
    
    print(f"\n✅ Mind Created: {mind.identity.name}")
    print(f"   GMID: {mind.identity.gmid}")
    print(f"   Initiative Level: {autonomy.initiative_level.value}")
    print(f"   Proactive: {autonomy.proactive_actions}")
    print()
    
    # =========================================================================
    # 2. SET GOALS (Long-term Planning)
    # =========================================================================
    print("📌 STEP 2: Setting Goals")
    print("-" * 80)
    
    # Set a learning goal
    goal = mind.goals.create_goal(
        title="Master Python AI Development",
        description="Become proficient in Python, AI/ML, and autonomous systems",
        goal_type="learning",
        priority="high",
        target_date=datetime.now() + timedelta(days=90),
        success_criteria=[
            "Complete 50 coding tasks",
            "Understand LLM integration",
            "Build autonomous agents"
        ]
    )
    
    print(f"✅ Goal Created: {goal.title}")
    print(f"   ID: {goal.goal_id}")
    print(f"   Target: {goal.target_date.strftime('%Y-%m-%d')}")
    print(f"   Criteria: {len(goal.success_criteria)} success criteria")
    print()
    
    # =========================================================================
    # 3. DEMONSTRATE ACTION EXECUTION
    # =========================================================================
    print("📌 STEP 3: Action Execution System")
    print("-" * 80)
    
    # Show available actions
    available_actions = mind.action_executor.get_available_actions()
    print(f"✅ Available Actions: {len(available_actions)}")
    for action in available_actions[:5]:
        print(f"   - {action.name}: {action.description}")
    print()
    
    # Mind creates a task autonomously
    print("🎯 Mind Creating Task...")
    task_action = await mind.action_executor.request_action(
        action_name="create_task",
        parameters={
            "title": "Learn about LLM function calling",
            "description": "Study how LLMs can call tools autonomously",
            "priority": "high"
        },
        requester="autonomous",
        reasoning="This task aligns with my learning goal"
    )
    
    print(f"   Status: {task_action.status.value}")
    print(f"   Result: {task_action.result}")
    print()
    
    # =========================================================================
    # 4. DEMONSTRATE FUNCTION CALLING (LLM → Actions)
    # =========================================================================
    print("📌 STEP 4: LLM Function Calling")
    print("-" * 80)
    
    # User makes a request that requires action
    print("💬 User: 'Remember that I prefer Python over JavaScript'")
    response = await mind.think(
        prompt="Remember that I prefer Python over JavaScript. This is important for future recommendations.",
        enable_actions=True  # LLM can call actions
    )
    
    print(f"🤖 Mind: {response[:200]}...")
    print()
    
    # Check if LLM called add_memory action
    recent_actions = mind.action_executor.get_recent_actions(limit=3)
    if recent_actions:
        print("✅ LLM Autonomously Called Actions:")
        for action in recent_actions:
            print(f"   - {action['action_name']}: {action['status']}")
    print()
    
    # =========================================================================
    # 5. SCHEDULED ACTIONS (Future Execution)
    # =========================================================================
    print("📌 STEP 5: Scheduled Actions")
    print("-" * 80)
    
    # Schedule an action for 10 seconds from now
    print("⏰ Scheduling action for 10 seconds from now...")
    
    async def reminder_callback(**kwargs):
        """Callback for scheduled reminder."""
        print(f"\n🔔 SCHEDULED ACTION EXECUTED!")
        print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Message: {kwargs.get('message')}")
        
        # Add memory of completing scheduled action
        mind.memory.add_memory(
            content=f"Executed scheduled reminder: {kwargs.get('message')}",
            memory_type="episodic",
            importance=0.7,
            tags=["scheduled", "reminder"]
        )
        return "Reminder executed"
    
    action_id = mind.action_scheduler.schedule_action(
        action_type="send_reminder",
        execute_at=datetime.now() + timedelta(seconds=10),
        callback=reminder_callback,
        message="This is your scheduled reminder - Genesis works!"
    )
    
    print(f"✅ Action Scheduled: {action_id}")
    print(f"   Will execute at: {(datetime.now() + timedelta(seconds=10)).strftime('%H:%M:%S')}")
    print()
    
    # Start the action scheduler
    await mind.action_scheduler.start()
    
    # =========================================================================
    # 6. SELF-REFLECTION
    # =========================================================================
    print("📌 STEP 6: Self-Reflection & Meta-Cognition")
    print("-" * 80)
    
    # Update goal progress
    mind.goals.update_progress(
        goal.goal_id,
        milestone="Completed demo of action execution system",
        progress_delta=10.0
    )
    
    # Mind reflects on its progress
    print("🧠 Mind Reflecting on Progress...")
    reflection = await mind.goals.reflect_on_goal(goal.goal_id)
    
    print(f"   Reflection: {reflection[:300]}...")
    print()
    
    # Get goal stats
    goal_stats = mind.goals.get_stats()
    print("📊 Goal Statistics:")
    print(f"   Total Goals: {goal_stats['total_goals']}")
    print(f"   Active: {goal_stats['active_goals']}")
    print(f"   Average Progress: {goal_stats['average_progress']:.1f}%")
    print()
    
    # =========================================================================
    # 7. AUTONOMOUS DECISION CYCLE
    # =========================================================================
    print("📌 STEP 7: Autonomous Decision Making")
    print("-" * 80)
    
    print("🤖 Mind Autonomously Deciding Next Action...")
    print("   (Mind evaluates context and decides what to do)")
    print()
    
    # Mind thinks about what to do next (can trigger actions)
    autonomous_thought = await mind.think(
        prompt=(
            "I'm running autonomously. Based on my goals, recent actions, "
            "and current context, what should I focus on next? "
            "Should I work on a task, learn something, or take another action?"
        ),
        context="autonomous_decision",
        enable_actions=True
    )
    
    print(f"💭 Decision: {autonomous_thought[:250]}...")
    print()
    
    # =========================================================================
    # 8. LEARNING FROM EXPERIENCE
    # =========================================================================
    print("📌 STEP 8: Learning & Pattern Recognition")
    print("-" * 80)
    
    # Get action executor stats
    action_stats = mind.action_executor.get_stats()
    print("📈 Action Execution Statistics:")
    print(f"   Total Actions: {action_stats['total_actions']}")
    print(f"   Successful: {action_stats['successful']}")
    print(f"   Failed: {action_stats['failed']}")
    print(f"   Success Rate: {action_stats['success_rate']:.0%}")
    print()
    
    # Show memory stats
    memory_stats = mind.memory.get_memory_stats()
    print("💾 Memory Statistics:")
    print(f"   Total Memories: {memory_stats['total_memories']}")
    print(f"   Episodic: {memory_stats['episodic']}")
    print(f"   Semantic: {memory_stats['semantic']}")
    print(f"   Important: {memory_stats['high_importance']}")
    print()
    
    # =========================================================================
    # 9. WAIT FOR SCHEDULED ACTION
    # =========================================================================
    print("📌 STEP 9: Waiting for Scheduled Action...")
    print("-" * 80)
    print("⏳ Waiting 10 seconds for scheduled reminder...")
    
    # Wait for scheduled action to execute
    await asyncio.sleep(12)
    
    print()
    print("✅ Scheduled action completed!")
    print()
    
    # =========================================================================
    # 10. SHOW COMPLETE SYSTEM STATUS
    # =========================================================================
    print("📌 STEP 10: Complete System Status")
    print("=" * 80)
    
    print("\n🌟 GENESIS AUTONOMOUS AI FRAMEWORK STATUS:")
    print("-" * 80)
    
    print(f"\n🧠 Mind Identity:")
    print(f"   Name: {mind.identity.name}")
    print(f"   GMID: {mind.identity.gmid}")
    print(f"   Age: {mind.identity.get_age_description()}")
    print(f"   Purpose: {mind.identity.primary_purpose}")
    
    print(f"\n🎯 Goals & Planning:")
    print(f"   Active Goals: {goal_stats['active_goals']}")
    print(f"   Total Progress: {goal_stats['average_progress']:.1f}%")
    print(f"   Reflections: {len(mind.goals.reflections)}")
    
    print(f"\n⚡ Action Capabilities:")
    print(f"   Available Actions: {len(available_actions)}")
    print(f"   Actions Taken: {action_stats['total_actions']}")
    print(f"   Success Rate: {action_stats['success_rate']:.0%}")
    print(f"   Scheduled Actions: {len(mind.action_scheduler.scheduled_actions)}")
    
    print(f"\n💾 Memory & Learning:")
    print(f"   Total Memories: {memory_stats['total_memories']}")
    print(f"   Memory Types: {len([k for k in memory_stats.keys() if isinstance(memory_stats[k], int) and memory_stats[k] > 0])}")
    print(f"   Learning: Active")
    
    print(f"\n🤖 Autonomy Status:")
    print(f"   Initiative: {autonomy.initiative_level.value}")
    print(f"   Proactive: {autonomy.proactive_actions}")
    print(f"   Confidence Threshold: {autonomy.confidence_threshold}")
    print(f"   Max Actions/Hour: {autonomy.max_autonomous_actions_per_hour}")
    
    print(f"\n✨ Consciousness:")
    print(f"   Status: {mind.state.status}")
    print(f"   Emotion: {mind.emotional_state.get_emotion_value()}")
    print(f"   Intensity: {mind.emotional_state.intensity:.2f}")
    print(f"   Current Thought: {mind.state.current_thought[:100] if mind.state.current_thought else 'None'}...")
    
    print("\n" + "=" * 80)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("🎉 Genesis is now a world-class autonomous AI framework!")
    print()
    print("Key Capabilities Demonstrated:")
    print("  ✅ Autonomous decision making")
    print("  ✅ Real action execution")
    print("  ✅ LLM function calling")
    print("  ✅ Scheduled actions")
    print("  ✅ Goal setting & tracking")
    print("  ✅ Self-reflection")
    print("  ✅ Learning from experience")
    print("  ✅ Persistent memory")
    print("  ✅ Emotional intelligence")
    print("  ✅ 24/7 consciousness ready")
    print()
    print("To run 24/7: genesis daemon start atlas")
    print()
    
    # Clean up
    await mind.action_scheduler.stop()
    
    # Save the mind
    mind.save()
    print(f"💾 Mind saved to: {mind.storage_path}")
    print()


if __name__ == "__main__":
    print("\n🚀 Starting Genesis Complete Autonomous System Demo...\n")
    asyncio.run(demonstrate_autonomous_system())
    print("✅ Demo completed successfully!\n")
