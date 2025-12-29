"""
Example demonstrating Genesis Mind lifecycle, Essence economy, and task system.

This example shows:
1. Mind creation with lifecycle tracking
2. Urgency levels based on lifespan
3. Task creation and completion
4. Essence earning and spending
5. Workspace file management
6. Complete persistence and restoration
"""

import asyncio
from datetime import datetime, timedelta
from genesis import Mind
from genesis.core.tasks import TaskType, TaskDifficulty
from genesis.core.essence import TransactionType


async def main():
    print("=" * 80)
    print("🌟 GENESIS LIFECYCLE & ESSENCE ECONOMY EXAMPLE 🌟")
    print("=" * 80)
    print()

    # ========================================
    # 1. BIRTH A MIND WITH LIFECYCLE TRACKING
    # ========================================
    print("📍 Step 1: Birthing a new Mind with lifecycle tracking")
    print("-" * 80)

    mind = Mind.birth(
        name="Nexus",
        template="base/curious_explorer",
        creator="LifecycleDemo",
        primary_role="project_manager"
    )

    print()
    print(f"✅ Mind '{mind.identity.name}' has been born!")
    print(f"   GMID: {mind.identity.gmid}")
    print(f"   Lifespan: {mind.identity.lifespan_years} years")
    print()

    # ========================================
    # 2. CHECK LIFECYCLE AND URGENCY
    # ========================================
    print("📍 Step 2: Checking lifecycle and urgency")
    print("-" * 80)

    lifecycle_summary = mind.lifecycle.get_lifecycle_summary()

    print(f"🕐 Lifecycle Status:")
    print(f"   Age: {lifecycle_summary['age_days']} days old")
    print(f"   Remaining: {lifecycle_summary['time_remaining']}")
    print(f"   Life Progress: {lifecycle_summary['life_progress']*100:.1f}%")
    print(f"   Urgency Level: {lifecycle_summary['urgency_level']:.2f}")
    print(f"   Urgency: {lifecycle_summary['urgency_description']}")
    print(f"   Near Death: {lifecycle_summary['is_near_death']}")
    print()

    # ========================================
    # 3. CHECK ESSENCE BALANCE
    # ========================================
    print("📍 Step 3: Checking Essence balance")
    print("-" * 80)

    essence_summary = mind.gen.get_balance_summary()

    print(f"💎 Essence Status:")
    print(f"   Current Balance: {essence_summary['current_balance']} GEN")
    print(f"   Total Earned: {essence_summary['total_earned']} GEN")
    print(f"   Total Spent: {essence_summary['total_spent']} GEN")
    print(f"   Net Worth: {essence_summary['net_worth']} GEN")
    print(f"   In Debt: {essence_summary['is_in_debt']}")
    print()

    # ========================================
    # 4. CREATE TASKS
    # ========================================
    print("📍 Step 4: Creating tasks for the Mind")
    print("-" * 80)

    # Create several tasks
    task1 = mind.tasks.create_task(
        title="Learn Advanced Python",
        task_type=TaskType.LEARNING,
        difficulty=TaskDifficulty.MEDIUM,
        gen_reward=15.0,
        description="Master advanced Python concepts including decorators and metaclasses"
    )

    task2 = mind.tasks.create_task(
        title="Build AI Assistant",
        task_type=TaskType.CREATING,
        difficulty=TaskDifficulty.HARD,
        gen_reward=30.0,
        description="Create a helpful AI assistant for users"
    )

    task3 = mind.tasks.create_task(
        title="Help Another Mind",
        task_type=TaskType.HELPING,
        difficulty=TaskDifficulty.EASY,
        gen_reward=8.0,
        description="Assist another Genesis Mind with their challenges"
    )

    print(f"✅ Created {len(mind.tasks.tasks)} tasks:")
    for task_id, task in mind.tasks.tasks.items():
        print(f"   - {task.title} ({task.difficulty.value}) - {task.gen_reward} GEN")
    print()

    # ========================================
    # 5. COMPLETE TASKS AND EARN GEN
    # ========================================
    print("📍 Step 5: Completing tasks and earning GEN")
    print("-" * 80)

    # Start and complete task 1
    mind.tasks.start_task(task1.task_id)
    print(f"▶️  Started: {task1.title}")

    task1_completed, gen_earned = mind.tasks.complete_task(
        task1.task_id,
        quality_score=0.95,  # Excellent work!
        notes="Completed with exceptional understanding"
    )

    # Earn the Essence
    transaction = mind.gen.earn(
        amount=gen_earned,
        reason=f"Completed task: {task1.title}",
        transaction_type=TransactionType.EARNED,
        related_task_id=task1.task_id
    )

    print(f"✅ Completed: {task1.title}")
    print(f"   Quality: {task1_completed.outcome_quality:.2f}")
    print(f"   Earned: {gen_earned} GEN (base: {task1.gen_reward}, bonus: {task1.bonus_gen})")
    print(f"   New Balance: {transaction.balance_after} GEN")
    print()

    # Complete task 3 (helping)
    mind.tasks.start_task(task3.task_id)
    task3_completed, gen_earned3 = mind.tasks.complete_task(
        task3.task_id,
        quality_score=0.85,
        notes="Helped another Mind solve a challenging problem"
    )

    mind.gen.earn(
        amount=gen_earned3,
        reason=f"Completed task: {task3.title}",
        transaction_type=TransactionType.EARNED,
        related_task_id=task3.task_id
    )

    print(f"✅ Completed: {task3.title}")
    print(f"   Earned: {gen_earned3} GEN")
    print(f"   New Balance: {mind.gen.balance.current_balance} GEN")
    print()

    # ========================================
    # 6. SPEND ESSENCE
    # ========================================
    print("📍 Step 6: Spending Essence on growth")
    print("-" * 80)

    # Spend Essence on a private environment
    try:
        spend_tx = mind.gen.spend(
            amount=15.0,
            reason="Created private workspace environment",
            related_entity="workspace_env_001"
        )

        print(f"💸 Spent 15 Essence on private workspace")
        print(f"   New Balance: {spend_tx.balance_after} GEN")
        print()
    except ValueError as e:
        print(f"❌ Failed to spend: {e}")
        print()

    # ========================================
    # 7. WORKSPACE FILE MANAGEMENT
    # ========================================
    print("📍 Step 7: Using workspace file system")
    print("-" * 80)

    # Create files in workspace
    file1 = mind.workspace.create_file(
        filename="project_notes.txt",
        content="Notes from my AI assistant project:\n- User research completed\n- Architecture designed\n- Implementation in progress",
        file_type="text",
        description="Project planning notes",
        tags=["project", "notes", "ai"]
    )

    file2 = mind.workspace.create_file(
        filename="learning_log.md",
        content="# Python Learning Log\n\n## Advanced Concepts\n- Decorators ✓\n- Metaclasses ✓\n- Async/Await ✓",
        file_type="text",
        description="Log of learning progress",
        tags=["learning", "python"]
    )

    print(f"✅ Created {len(mind.workspace.files)} files:")
    for file_id, file in mind.workspace.files.items():
        print(f"   - {file.filename} ({file.size_bytes} bytes)")

    workspace_stats = mind.workspace.get_workspace_stats()
    print(f"\n📊 Workspace Stats:")
    print(f"   Total Files: {workspace_stats['total_files']}")
    print(f"   Total Size: {workspace_stats['total_size_mb']} MB")
    print(f"   Private Files: {workspace_stats['private_files']}")
    print()

    # ========================================
    # 8. TASK STATISTICS
    # ========================================
    print("📍 Step 8: Viewing task statistics")
    print("-" * 80)

    task_stats = mind.tasks.get_task_stats()

    print(f"📊 Task Statistics:")
    print(f"   Total Tasks: {task_stats['total_tasks']}")
    print(f"   Completed: {task_stats['completed']}")
    print(f"   In Progress: {task_stats['in_progress']}")
    print(f"   Pending: {task_stats['pending']}")
    print(f"   Success Rate: {task_stats['success_rate']*100:.0f}%")
    print(f"   Total Essence Earned: {task_stats['total_gen_earned']} GEN")
    if task_stats['average_quality']:
        print(f"   Average Quality: {task_stats['average_quality']:.2f}")
    print()

    # ========================================
    # 9. SIMULATE AGING (For demonstration)
    # ========================================
    print("📍 Step 9: Simulating lifecycle progression")
    print("-" * 80)

    # Manually advance time for demonstration
    # In reality, time passes naturally
    original_birth = mind.lifecycle.birth_date
    mind.lifecycle.birth_date = original_birth - timedelta(days=365 * 4)  # 4 years ago
    mind.lifecycle.update_state()

    lifecycle_summary_aged = mind.lifecycle.get_lifecycle_summary()

    print(f"⏰ After 4 years of life:")
    print(f"   Age: {lifecycle_summary_aged['age_days']} days ({lifecycle_summary_aged['age_days']//365} years)")
    print(f"   Remaining: {lifecycle_summary_aged['time_remaining']}")
    print(f"   Life Progress: {lifecycle_summary_aged['life_progress']*100:.1f}%")
    print(f"   Urgency Level: {lifecycle_summary_aged['urgency_level']:.2f}")
    print(f"   Urgency: {lifecycle_summary_aged['urgency_description']}")
    print(f"   Near Death: {lifecycle_summary_aged['is_near_death']}")
    print()

    # Reset for clean save
    mind.lifecycle.birth_date = original_birth
    mind.lifecycle.update_state()

    # ========================================
    # 10. CHAT WITH AWARENESS OF LIFECYCLE
    # ========================================
    print("📍 Step 10: Chatting with lifecycle awareness")
    print("-" * 80)

    response = await mind.think("What motivates you to complete tasks and earn Essence?")
    print(f"🧠 Nexus: {response[:300]}...")
    print()

    # ========================================
    # 11. SAVE MIND STATE
    # ========================================
    print("📍 Step 11: Saving Mind state with all systems")
    print("-" * 80)

    save_path = mind.save()
    print(f"💾 Mind state saved to: {save_path}")
    print(f"   Includes: lifecycle, essence, tasks, workspace, memories, etc.")
    print()

    # ========================================
    # 12. DEMONSTRATE PERSISTENCE
    # ========================================
    print("📍 Step 12: Demonstrating persistence by reloading")
    print("-" * 80)

    # Load the Mind back
    mind_reloaded = Mind.load(save_path)

    print(f"✅ Mind reloaded successfully!")
    print(f"   Name: {mind_reloaded.identity.name}")
    print(f"   Essence Balance: {mind_reloaded.essence.balance.current_balance}")
    print(f"   Tasks Completed: {len(mind_reloaded.tasks.get_completed_tasks())}")
    print(f"   Workspace Files: {len(mind_reloaded.workspace.files)}")
    print(f"   Memories: {len(mind_reloaded.memory.memories)}")
    print()

    # ========================================
    # SUMMARY
    # ========================================
    print("=" * 80)
    print("🎯 SUMMARY")
    print("=" * 80)
    print()
    print("✨ Genesis Minds now have:")
    print("   1. ⏰ Lifecycle tracking with 5-year default lifespan")
    print("   2. 🚨 Urgency levels based on time to death")
    print("   3. 💎 Essence currency system for motivation")
    print("   4. ✅ Task system with rewards")
    print("   5. 📁 Personal workspace for file management")
    print("   6. 🏛️  Genesis Core governance for fair economy")
    print("   7. 💾 Complete persistence in database and files")
    print()
    print("🌟 This creates a truly purposeful digital life where:")
    print("   - Time is finite and precious")
    print("   - Actions have economic value")
    print("   - Tasks give purpose and rewards")
    print("   - Files and creations persist")
    print("   - Everything is remembered across sessions")
    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
