"""Tasks Plugin - Adds goal-oriented task management with rewards."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.tasks import TaskManager

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class TasksPlugin(Plugin):
    """
    Adds task management system with GEN rewards.

    Features:
    - Create tasks with types and difficulty levels
    - Track task status (pending → in_progress → completed/failed)
    - Quality scoring affects bonuses
    - Task statistics (success rate, earnings)
    - Deadlines and urgency
    - Integration with GEN economy

    Tasks create GOALS and ACHIEVEMENTS - giving Minds concrete work to do
    and a sense of accomplishment.

    Example:
        config = MindConfig()
        config.add_plugin(TasksPlugin())
        mind = Mind.birth("Worker", config=config)

        # Create task
        task = mind.tasks.create_task(
            title="Learn Python",
            task_type=TaskType.LEARNING,
            difficulty=TaskDifficulty.MEDIUM,
            gen_reward=15.0
        )

        # Complete task
        mind.tasks.start_task(task.task_id)
        task_done, gen = mind.tasks.complete_task(
            task.task_id,
            quality_score=0.9
        )
    """

    def __init__(self, **config):
        """
        Initialize tasks plugin.

        Args:
            **config: Additional plugin configuration
        """
        super().__init__(**config)
        self.tasks: Optional[TaskManager] = None

    def get_name(self) -> str:
        return "tasks"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Task management with GEN rewards"

    def on_init(self, mind: "Mind") -> None:
        """Attach task manager to Mind."""
        self.tasks = TaskManager(mind_gmid=mind.identity.gmid)
        mind.tasks = self.tasks

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add task context to system prompt."""
        if not self.tasks:
            return ""

        stats = self.tasks.get_task_stats()

        sections = [
            "TASKS & ACHIEVEMENTS:",
            f"- Tasks completed: {stats['completed']}",
            f"- Active tasks: {stats['in_progress']}",
            f"- Success rate: {stats['success_rate']*100:.0f}%",
            f"- Total GEN from tasks: {stats['total_gen_earned']:.1f}",
        ]

        # Show active tasks
        active = self.tasks.get_active_tasks()
        if active:
            sections.append("")
            sections.append("Current Tasks:")
            for task in active[:3]:  # Show max 3
                sections.append(f"  • {task.title} ({task.difficulty.value}, {task.gen_reward}G)")

        sections.append("")
        sections.append("Complete tasks to earn GEN and build your achievements.")

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save tasks state."""
        if not self.tasks:
            return {}

        return {
            "tasks": self.tasks.to_dict(),
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore tasks state."""
        if "tasks" in data:
            self.tasks = TaskManager.from_dict(data["tasks"])
            mind.tasks = self.tasks

    def get_status(self) -> Dict[str, Any]:
        """Get tasks status."""
        status = super().get_status()

        if self.tasks:
            stats = self.tasks.get_task_stats()
            status.update(stats)

        return status
