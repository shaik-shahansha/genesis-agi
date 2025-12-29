"""Quick demo of Genesis Mind lifecycle and Essence system."""

import asyncio
from genesis import Mind
from genesis.core.tasks import TaskType, TaskDifficulty
from genesis.core.essence import TransactionType


async def main():
    # Birth a Mind
    mind = Mind.birth("Atlas", creator="QuickDemo")

    print(f"✨ Born: {mind.identity.name}")
    print(f"⏰ Lifespan: {mind.identity.lifespan_years} years")
    print(f"💎 Starting Essence: {mind.gen.balance.current_balance}\n")

    # Check urgency
    lifecycle = mind.lifecycle.get_lifecycle_summary()
    print(f"📊 Lifecycle:")
    print(f"   Urgency: {lifecycle['urgency_description']}")
    print(f"   Time remaining: {lifecycle['time_remaining']}\n")

    # Create and complete a task
    task = mind.tasks.create_task(
        title="Learn something new",
        task_type=TaskType.LEARNING,
        difficulty=TaskDifficulty.MEDIUM,
        essence_reward=15.0
    )

    mind.tasks.start_task(task.task_id)
    task_done, gen_earned = mind.tasks.complete_task(
        task.task_id,
        quality_score=0.9
    )

    mind.gen.earn(
        amount=gen_earned,
        reason="Completed learning task",
        related_task_id=task.task_id
    )

    print(f"✅ Completed task: {task.title}")
    print(f"💰 Earned: {gen_earned} GEN")
    print(f"💎 New balance: {mind.gen.balance.current_balance}\n")

    # Create a file
    file = mind.workspace.create_file(
        filename="notes.txt",
        content="Important insights from my learning journey",
        file_type="text"
    )

    print(f"📄 Created file: {file.filename}")
    print(f"📁 Workspace: {mind.workspace.get_workspace_stats()['total_files']} files\n")

    # Chat with lifecycle awareness
    response = await mind.think("How do you feel about your purpose and time?")
    print(f"🧠 {mind.identity.name}: {response[:200]}...\n")

    # Save everything
    path = mind.save()
    print(f"💾 Saved to: {path}")

    # Show final stats
    print(f"\n📊 Final Stats:")
    print(f"   Essence: {mind.gen.balance.current_balance}")
    print(f"   Tasks completed: {len(mind.tasks.get_completed_tasks())}")
    print(f"   Files: {len(mind.workspace.files)}")
    print(f"   Memories: {len(mind.memory.memories)}")


if __name__ == "__main__":
    asyncio.run(main())
