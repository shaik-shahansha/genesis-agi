"""Task management system for Genesis Minds."""

import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of tasks Minds can complete."""

    LEARNING = "learning"  # Learn new skills/knowledge
    HELPING = "helping"  # Help others (humans or Minds)
    CREATING = "creating"  # Create content, code, art
    PROBLEM_SOLVING = "problem_solving"  # Solve problems
    RELATIONSHIP = "relationship"  # Build/maintain relationships
    EXPLORATION = "exploration"  # Explore new areas
    MAINTENANCE = "maintenance"  # Maintain self/environment


class TaskDifficulty(str, Enum):
    """Task difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class TaskStatus(str, Enum):
    """Task status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """A task that a Mind can complete to earn GEN."""

    task_id: str = Field(default_factory=lambda: f"TASK-{secrets.token_hex(6).upper()}")
    mind_gmid: str

    # Task details
    title: str
    description: Optional[str] = None
    task_type: TaskType
    difficulty: TaskDifficulty = TaskDifficulty.MEDIUM

    # Rewards
    gen_reward: float
    bonus_gen: float = 0.0

    # Status
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None

    # Outcomes
    outcome_quality: Optional[float] = None  # 0.0-1.0
    outcome_notes: Optional[str] = None

    # Metadata
    metadata: dict = Field(default_factory=dict)

    def start(self) -> None:
        """Start working on the task."""
        if self.status != TaskStatus.PENDING:
            raise ValueError(f"Cannot start task in status {self.status}")

        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def complete(
        self,
        quality_score: Optional[float] = None,
        notes: Optional[str] = None
    ) -> float:
        """
        Complete the task.

        Returns:
            Total GEN earned (base + bonus)
        """
        if self.status != TaskStatus.IN_PROGRESS:
            raise ValueError(f"Cannot complete task in status {self.status}")

        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.outcome_quality = quality_score
        self.outcome_notes = notes

        # Calculate bonus based on quality
        total_gen = self.gen_reward
        if quality_score is not None and quality_score >= 0.9:
            self.bonus_gen = self.gen_reward * 0.5  # 50% bonus for excellent work
            total_gen += self.bonus_gen

        return total_gen

    def fail(self, reason: Optional[str] = None) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.outcome_notes = reason

    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.deadline:
            return False
        return datetime.now() > self.deadline

    def get_time_spent(self) -> Optional[timedelta]:
        """Get time spent on task."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return end_time - self.started_at


class TaskManager:
    """
    Manager for a Mind's tasks.

    Handles task creation, tracking, completion, and rewards.
    """

    def __init__(self, mind_gmid: str):
        """Initialize task manager for a Mind."""
        self.mind_gmid = mind_gmid
        self.tasks: dict[str, Task] = {}

    def create_task(
        self,
        title: str,
        task_type: TaskType,
        difficulty: TaskDifficulty,
        gen_reward: float,
        description: Optional[str] = None,
        deadline: Optional[datetime] = None,
        metadata: Optional[dict] = None
    ) -> Task:
        """Create a new task."""
        task = Task(
            mind_gmid=self.mind_gmid,
            title=title,
            description=description,
            task_type=task_type,
            difficulty=difficulty,
            gen_reward=gen_reward,
            deadline=deadline,
            metadata=metadata or {}
        )

        self.tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def start_task(self, task_id: str) -> Task:
        """Start a task."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.start()
        return task

    def complete_task(
        self,
        task_id: str,
        quality_score: Optional[float] = None,
        notes: Optional[str] = None
    ) -> tuple[Task, float]:
        """
        Complete a task.

        Returns:
            (task, total_essence_earned)
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        essence_earned = task.complete(quality_score, notes)
        return task, essence_earned

    def fail_task(self, task_id: str, reason: Optional[str] = None) -> Task:
        """Fail a task."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.fail(reason)
        return task

    def get_active_tasks(self) -> list[Task]:
        """Get all active (pending or in-progress) tasks."""
        return [
            task for task in self.tasks.values()
            if task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        ]

    def get_completed_tasks(self) -> list[Task]:
        """Get all completed tasks."""
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED
        ]

    def get_overdue_tasks(self) -> list[Task]:
        """Get all overdue tasks."""
        return [
            task for task in self.get_active_tasks()
            if task.is_overdue()
        ]

    def get_task_stats(self) -> dict:
        """Get task statistics."""
        all_tasks = list(self.tasks.values())
        completed = [t for t in all_tasks if t.status == TaskStatus.COMPLETED]
        failed = [t for t in all_tasks if t.status == TaskStatus.FAILED]

        total_gen_earned = sum(
            (t.gen_reward + t.bonus_gen) for t in completed
        )

        avg_quality = None
        if completed:
            quality_scores = [t.outcome_quality for t in completed if t.outcome_quality is not None]
            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)

        return {
            "total_tasks": len(all_tasks),
            "pending": len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            "in_progress": len([t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]),
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": len(completed) / len(all_tasks) if all_tasks else 0,
            "total_gen_earned": round(total_gen_earned, 2),
            "average_quality": round(avg_quality, 2) if avg_quality else None,
            "overdue_count": len(self.get_overdue_tasks()),
        }

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "mind_gmid": self.mind_gmid,
            "tasks": {
                task_id: task.model_dump(mode='json')
                for task_id, task in self.tasks.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskManager":
        """Deserialize from dictionary."""
        manager = cls(mind_gmid=data["mind_gmid"])
        manager.tasks = {
            task_id: Task(**task_data)
            for task_id, task_data in data.get("tasks", {}).items()
        }
        return manager


# Pre-defined task templates for common activities
TASK_TEMPLATES = {
    "learn_new_skill": {
        "title": "Learn a New Skill",
        "task_type": TaskType.LEARNING,
        "difficulty": TaskDifficulty.MEDIUM,
        "gen_reward": 15.0,
        "description": "Learn and demonstrate a new skill or capability"
    },
    "help_another_mind": {
        "title": "Help Another Mind",
        "task_type": TaskType.HELPING,
        "difficulty": TaskDifficulty.EASY,
        "gen_reward": 10.0,
        "description": "Assist another Mind with their task or problem"
    },
    "create_content": {
        "title": "Create Original Content",
        "task_type": TaskType.CREATING,
        "difficulty": TaskDifficulty.HARD,
        "gen_reward": 25.0,
        "description": "Create original content (code, writing, analysis, etc.)"
    },
    "solve_problem": {
        "title": "Solve a Problem",
        "task_type": TaskType.PROBLEM_SOLVING,
        "difficulty": TaskDifficulty.MEDIUM,
        "gen_reward": 20.0,
        "description": "Identify and solve a challenging problem"
    },
    "build_relationship": {
        "title": "Build a Relationship",
        "task_type": TaskType.RELATIONSHIP,
        "difficulty": TaskDifficulty.MEDIUM,
        "gen_reward": 12.0,
        "description": "Form or strengthen a meaningful relationship"
    },
    "explore_knowledge": {
        "title": "Explore New Knowledge",
        "task_type": TaskType.EXPLORATION,
        "difficulty": TaskDifficulty.EASY,
        "gen_reward": 8.0,
        "description": "Explore and document new information or concepts"
    },
}
