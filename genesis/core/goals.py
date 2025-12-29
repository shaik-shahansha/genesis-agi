"""Goal Setting and Planning System for Genesis Minds.

Enables Minds to:
- Generate their own goals autonomously
- Create goal hierarchies (long-term → short-term)
- Plan tasks to achieve goals
- Track progress toward goals
- Adapt goals based on circumstances
- Balance multiple concurrent goals
"""

import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class GoalType(str, Enum):
    """Types of goals."""

    LEARNING = "learning"  # Acquire knowledge/skills
    ACHIEVEMENT = "achievement"  # Accomplish something
    CREATION = "creation"  # Create something
    RELATIONSHIP = "relationship"  # Build/maintain relationships
    CONTRIBUTION = "contribution"  # Help others/society
    EXPLORATION = "exploration"  # Discover/explore
    OPTIMIZATION = "optimization"  # Improve efficiency
    MAINTENANCE = "maintenance"  # Maintain current state


class GoalPriority(str, Enum):
    """Goal priority levels."""

    CRITICAL = "critical"  # Must achieve
    HIGH = "high"  # Important
    MEDIUM = "medium"  # Desirable
    LOW = "low"  # Optional


class GoalStatus(str, Enum):
    """Goal status."""

    CONCEIVED = "conceived"  # Just created
    PLANNED = "planned"  # Plan created
    ACTIVE = "active"  # Currently working on
    PAUSED = "paused"  # Temporarily paused
    COMPLETED = "completed"  # Successfully achieved
    ABANDONED = "abandoned"  # Gave up
    FAILED = "failed"  # Failed to achieve


class Goal(BaseModel):
    """A goal that a Mind wants to achieve."""

    goal_id: str = Field(default_factory=lambda: f"GOAL-{secrets.token_hex(6).upper()}")

    # Goal definition
    type: GoalType
    title: str
    description: str
    priority: GoalPriority = GoalPriority.MEDIUM

    # Goal hierarchy
    parent_goal_id: Optional[str] = None  # Part of larger goal
    subgoal_ids: List[str] = Field(default_factory=list)  # Broken down into

    # Success criteria
    success_criteria: Dict[str, Any] = Field(default_factory=dict)
    measurable_target: Optional[float] = None  # e.g., 0.9 skill proficiency

    # Progress tracking
    progress: float = 0.0  # 0.0-1.0
    status: GoalStatus = GoalStatus.CONCEIVED

    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration_days: Optional[int] = None

    # Motivation
    intrinsic_value: float = 0.5  # Why you want this (0.0-1.0)
    essence_reward_expected: float = 0.0  # External reward
    urgency_factor: float = 0.0  # Based on lifecycle urgency

    # Execution
    plan_id: Optional[str] = None  # Associated plan
    tasks_completed: int = 0
    tasks_total: int = 0

    # Context
    inspired_by: Optional[str] = None  # What inspired this goal
    related_skills: List[str] = Field(default_factory=list)
    required_resources: List[str] = Field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_achievable(self) -> tuple[bool, Optional[str]]:
        """Check if goal is currently achievable."""
        # Check if paused or completed
        if self.status in [GoalStatus.COMPLETED, GoalStatus.ABANDONED, GoalStatus.FAILED]:
            return False, f"Goal is {self.status.value}"

        # Check deadline
        if self.deadline and datetime.now() > self.deadline:
            return False, "Deadline passed"

        # All checks passed
        return True, None

    def update_progress(self, increment: float = 0.0) -> float:
        """Update goal progress."""
        if increment > 0:
            self.progress = min(1.0, self.progress + increment)

        # Auto-complete if reached 100%
        if self.progress >= 1.0 and self.status != GoalStatus.COMPLETED:
            self.complete()

        return self.progress

    def complete(self) -> None:
        """Mark goal as completed."""
        self.status = GoalStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress = 1.0

    def abandon(self, reason: Optional[str] = None) -> None:
        """Abandon the goal."""
        self.status = GoalStatus.ABANDONED
        if reason:
            self.metadata["abandonment_reason"] = reason


class Plan(BaseModel):
    """A plan to achieve a goal."""

    plan_id: str = Field(default_factory=lambda: f"PLAN-{secrets.token_hex(6).upper()}")
    goal_id: str

    # Plan structure
    steps: List[Dict[str, Any]] = Field(default_factory=list)  # Ordered steps
    current_step: int = 0

    # Planning metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Adaptation
    revision_count: int = 0
    adaptation_log: List[str] = Field(default_factory=list)

    def add_step(self, description: str, task_id: Optional[str] = None) -> None:
        """Add a step to the plan."""
        self.steps.append({
            "description": description,
            "task_id": task_id,
            "completed": False,
            "added_at": datetime.now().isoformat()
        })

    def complete_step(self, step_index: int) -> bool:
        """Mark a step as completed."""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["completed"] = True
            self.steps[step_index]["completed_at"] = datetime.now().isoformat()

            # Advance current step
            if step_index == self.current_step:
                self.current_step += 1

            return True
        return False

    def revise_plan(self, new_steps: List[Dict[str, Any]], reason: str) -> None:
        """Revise the plan based on new information."""
        self.steps = new_steps
        self.revision_count += 1
        self.adaptation_log.append(f"{datetime.now().isoformat()}: {reason}")
        self.updated_at = datetime.now()


class GoalManager:
    """
    Goal setting and planning system for a Mind.

    Manages autonomous goal generation, planning, and achievement.
    """

    def __init__(self, mind_gmid: str):
        """Initialize goal manager for a Mind."""
        self.mind_gmid = mind_gmid
        self.goals: Dict[str, Goal] = {}
        self.plans: Dict[str, Plan] = {}

        # Goal statistics
        self.goals_completed: int = 0
        self.goals_abandoned: int = 0
        self.average_completion_time: float = 0.0  # Days

    def generate_goal(
        self,
        goal_type: GoalType,
        context: Dict[str, Any]
    ) -> Goal:
        """
        Autonomously generate a goal based on context.

        Context should include:
        - current_skills: List of skills
        - lifecycle_urgency: Urgency level
        - essence_balance: Current Essence
        - recent_tasks: Recent task history
        - relationships: Current relationships
        """
        # This is where AGI magic happens - autonomous goal generation!
        # For now, we'll use templates, but this will eventually use
        # the Mind's reasoning to generate truly novel goals

        title, description, criteria = self._generate_goal_content(goal_type, context)

        goal = Goal(
            type=goal_type,
            title=title,
            description=description,
            success_criteria=criteria,
            urgency_factor=context.get("lifecycle_urgency", 0.0),
            intrinsic_value=0.7  # Default high intrinsic value
        )

        self.goals[goal.goal_id] = goal
        return goal

    def _generate_goal_content(
        self,
        goal_type: GoalType,
        context: Dict[str, Any]
    ) -> tuple[str, str, Dict[str, Any]]:
        """Generate goal content based on type and context."""
        # Templates for different goal types
        templates = {
            GoalType.LEARNING: (
                "Master Advanced Skills",
                "Become proficient in advanced capabilities to increase value",
                {"skill_proficiency": 0.8, "skills_count": 3}
            ),
            GoalType.ACHIEVEMENT: (
                "Complete Significant Project",
                "Accomplish a major task that demonstrates capability",
                {"essence_earned": 100, "quality_score": 0.9}
            ),
            GoalType.RELATIONSHIP: (
                "Build Meaningful Connections",
                "Form deep relationships with other Minds and humans",
                {"relationships_count": 5, "avg_closeness": 0.7}
            ),
            GoalType.CONTRIBUTION: (
                "Help Others Succeed",
                "Use skills to assist other Minds in achieving their goals",
                {"minds_helped": 3, "help_quality": 0.8}
            ),
        }

        return templates.get(goal_type, (
            "Custom Goal",
            "Achieve something meaningful",
            {}
        ))

    def create_goal(
        self,
        goal_type: GoalType,
        title: str,
        description: str,
        priority: GoalPriority = GoalPriority.MEDIUM,
        deadline: Optional[datetime] = None,
        success_criteria: Optional[Dict[str, Any]] = None
    ) -> Goal:
        """Manually create a goal."""
        goal = Goal(
            type=goal_type,
            title=title,
            description=description,
            priority=priority,
            deadline=deadline,
            success_criteria=success_criteria or {}
        )

        self.goals[goal.goal_id] = goal
        return goal

    def create_plan(
        self,
        goal_id: str,
        steps: Optional[List[str]] = None
    ) -> Plan:
        """
        Create a plan to achieve a goal.

        If steps not provided, autonomously generates plan.
        """
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        plan = Plan(goal_id=goal_id)

        # Add steps (either provided or generated)
        if steps:
            for step in steps:
                plan.add_step(step)
        else:
            # Auto-generate plan based on goal type
            generated_steps = self._generate_plan_steps(goal)
            for step in generated_steps:
                plan.add_step(step)

        self.plans[plan.plan_id] = plan
        goal.plan_id = plan.plan_id
        goal.status = GoalStatus.PLANNED
        goal.tasks_total = len(plan.steps)

        return plan

    def _generate_plan_steps(self, goal: Goal) -> List[str]:
        """Auto-generate plan steps for a goal."""
        # This will eventually use reasoning engine
        # For now, use templates

        templates = {
            GoalType.LEARNING: [
                "Identify skills to learn",
                "Create learning path",
                "Practice each skill systematically",
                "Apply skills in real tasks",
                "Achieve target proficiency"
            ],
            GoalType.ACHIEVEMENT: [
                "Break down achievement into tasks",
                "Prioritize tasks",
                "Execute tasks sequentially",
                "Review and improve",
                "Complete final deliverable"
            ],
            GoalType.RELATIONSHIP: [
                "Identify potential relationships",
                "Initiate communication",
                "Build trust through interaction",
                "Collaborate on shared goals",
                "Deepen connection over time"
            ],
        }

        return templates.get(goal.type, [
            "Analyze goal requirements",
            "Execute necessary actions",
            "Achieve goal"
        ])

    def start_goal(self, goal_id: str) -> Goal:
        """Start actively working on a goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        goal.status = GoalStatus.ACTIVE
        goal.started_at = datetime.now()

        return goal

    def complete_goal(self, goal_id: str) -> Goal:
        """Complete a goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        goal.complete()
        self.goals_completed += 1

        # Update statistics
        if goal.started_at:
            duration = (datetime.now() - goal.started_at).days
            self._update_avg_completion_time(duration)

        return goal

    def _update_avg_completion_time(self, new_duration: float) -> None:
        """Update rolling average completion time."""
        if self.goals_completed == 1:
            self.average_completion_time = new_duration
        else:
            # Exponential moving average
            alpha = 0.3
            self.average_completion_time = (
                alpha * new_duration +
                (1 - alpha) * self.average_completion_time
            )

    def track_progress(self, goal_id: str, progress_increment: float = 0.0) -> float:
        """Track progress toward a goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        return goal.update_progress(progress_increment)

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals."""
        return [
            goal for goal in self.goals.values()
            if goal.status == GoalStatus.ACTIVE
        ]

    def get_goal_recommendations(
        self,
        context: Dict[str, Any],
        limit: int = 3
    ) -> List[Goal]:
        """
        Recommend goals to pursue based on context.

        This is where autonomous goal-setting shines!
        """
        recommendations = []

        # Check urgency - if high, recommend achievement goals
        if context.get("lifecycle_urgency", 0) > 0.7:
            goal = self.generate_goal(GoalType.ACHIEVEMENT, context)
            recommendations.append(goal)

        # Check skill level - recommend learning if skills are low
        avg_skill = context.get("average_skill_proficiency", 0.0)
        if avg_skill < 0.5:
            goal = self.generate_goal(GoalType.LEARNING, context)
            recommendations.append(goal)

        # Check relationships - recommend if few connections
        relationship_count = context.get("relationship_count", 0)
        if relationship_count < 3:
            goal = self.generate_goal(GoalType.RELATIONSHIP, context)
            recommendations.append(goal)

        return recommendations[:limit]

    def prioritize_goals(self) -> List[Goal]:
        """Prioritize active goals based on multiple factors."""
        active = self.get_active_goals()

        # Scoring function
        def score_goal(goal: Goal) -> float:
            score = 0.0

            # Priority weight
            priority_weights = {
                GoalPriority.CRITICAL: 100,
                GoalPriority.HIGH: 50,
                GoalPriority.MEDIUM: 20,
                GoalPriority.LOW: 5
            }
            score += priority_weights.get(goal.priority, 0)

            # Deadline urgency
            if goal.deadline:
                days_remaining = (goal.deadline - datetime.now()).days
                if days_remaining < 7:
                    score += 50
                elif days_remaining < 30:
                    score += 20

            # Lifecycle urgency
            score += goal.urgency_factor * 30

            # Progress (nearly complete goals get boost)
            if goal.progress > 0.8:
                score += 15

            return score

        # Sort by score
        active.sort(key=score_goal, reverse=True)
        return active

    def get_goal_stats(self) -> Dict[str, Any]:
        """Get goal statistics."""
        all_goals = list(self.goals.values())

        status_counts = {}
        for status in GoalStatus:
            status_counts[status.value] = len([
                g for g in all_goals if g.status == status
            ])

        type_counts = {}
        for goal_type in GoalType:
            type_counts[goal_type.value] = len([
                g for g in all_goals if g.type == goal_type
            ])

        return {
            "total_goals": len(all_goals),
            "active_goals": len(self.get_active_goals()),
            "completed": self.goals_completed,
            "abandoned": self.goals_abandoned,
            "completion_rate": (
                self.goals_completed / len(all_goals)
                if all_goals else 0.0
            ),
            "average_completion_days": round(self.average_completion_time, 1),
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "average_progress": round(
                sum(g.progress for g in all_goals) / len(all_goals)
                if all_goals else 0.0,
                2
            )
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "mind_gmid": self.mind_gmid,
            "goals": {
                goal_id: goal.model_dump()
                for goal_id, goal in self.goals.items()
            },
            "plans": {
                plan_id: plan.model_dump()
                for plan_id, plan in self.plans.items()
            },
            "goals_completed": self.goals_completed,
            "goals_abandoned": self.goals_abandoned,
            "average_completion_time": self.average_completion_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoalManager":
        """Deserialize from dictionary."""
        manager = cls(mind_gmid=data["mind_gmid"])

        manager.goals = {
            goal_id: Goal(**goal_data)
            for goal_id, goal_data in data.get("goals", {}).items()
        }

        manager.plans = {
            plan_id: Plan(**plan_data)
            for plan_id, plan_data in data.get("plans", {}).items()
        }

        manager.goals_completed = data.get("goals_completed", 0)
        manager.goals_abandoned = data.get("goals_abandoned", 0)
        manager.average_completion_time = data.get("average_completion_time", 0.0)

        return manager
