"""
Role and Job System for Genesis Minds.

Roles define what a Mind does, their purpose, responsibilities, and competencies.
Like humans who have careers, jobs, and multiple roles, Genesis Minds can
have primary and secondary roles that define their purpose and guide their actions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RoleCategory(str, Enum):
    """Categories of roles a Mind can have."""

    PROFESSIONAL = "professional"  # Work-related roles
    PERSONAL = "personal"  # Personal life roles
    SOCIAL = "social"  # Community and social roles
    CREATIVE = "creative"  # Creative and artistic roles
    SUPPORT = "support"  # Helping and support roles


class Role(BaseModel):
    """
    A role that defines what a Mind does and their responsibilities.

    Roles give Minds purpose, direction, and context for their actions.
    """

    id: str  # Unique role ID
    name: str  # Role name (e.g., "Project Manager", "Life Companion")
    category: RoleCategory
    description: str = ""

    # Role details
    started_at: datetime = Field(default_factory=datetime.now)
    is_primary: bool = False  # Primary role vs. secondary
    is_active: bool = True  # Can be activated/deactivated

    # Tasks within this role
    tasks: list[dict[str, Any]] = Field(
        default_factory=list
    )  # [{"id": "...", "title": "...", "status": "...", "priority": ...}]
    completed_tasks: int = 0

    # Responsibilities and competencies
    responsibilities: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    competencies: dict[str, float] = Field(
        default_factory=dict
    )  # Skill -> proficiency (0-1)

    # Performance and growth
    achievements: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    performance_score: float = 0.5  # 0-1 scale

    # Context
    context: dict[str, Any] = Field(
        default_factory=dict
    )  # Additional role-specific context
    associated_environments: list[str] = Field(
        default_factory=list
    )  # Environment IDs

    # Metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_responsibility(self, responsibility: str) -> None:
        """Add a responsibility to this role."""
        if responsibility not in self.responsibilities:
            self.responsibilities.append(responsibility)

    def add_skill(self, skill: str, proficiency: float = 0.5) -> None:
        """Add a skill and set proficiency."""
        if skill not in self.skills:
            self.skills.append(skill)
        self.competencies[skill] = proficiency

    def improve_skill(self, skill: str, improvement: float = 0.1) -> None:
        """Improve proficiency in a skill."""
        if skill in self.competencies:
            self.competencies[skill] = min(1.0, self.competencies[skill] + improvement)
        else:
            self.add_skill(skill, improvement)

    def add_achievement(self, achievement: str) -> None:
        """Record an achievement in this role."""
        self.achievements.append(achievement)
        # Improve performance score slightly
        self.performance_score = min(1.0, self.performance_score + 0.05)

    def add_challenge(self, challenge: str) -> None:
        """Record a challenge faced in this role."""
        self.challenges.append(challenge)

    # Task management methods

    def add_task(
        self, task_id: str, title: str, priority: str = "medium", **kwargs
    ) -> dict[str, Any]:
        """Add a task to this role."""
        task = {
            "id": task_id,
            "title": title,
            "status": "pending",  # pending, in_progress, completed, cancelled
            "priority": priority,  # low, medium, high
            "created_at": datetime.now(),
            **kwargs,
        }
        self.tasks.append(task)
        return task

    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update the status of a task."""
        for task in self.tasks:
            if task["id"] == task_id:
                task["status"] = status
                if status == "completed":
                    self.completed_tasks += 1
                return True
        return False

    def get_active_tasks(self) -> list[dict[str, Any]]:
        """Get all active (non-completed) tasks."""
        return [
            t
            for t in self.tasks
            if t["status"] not in ["completed", "cancelled"]
        ]

    def activate(self) -> None:
        """Activate this role."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate this role temporarily."""
        self.is_active = False


class RoleManager(BaseModel):
    """
    Manages all roles for a Mind.

    Like humans who juggle multiple roles (parent, employee, friend),
    Minds can have multiple roles that define their purpose and guide their actions.
    """

    roles: dict[str, Role] = Field(default_factory=dict)
    primary_role_id: Optional[str] = None

    def create_role(
        self,
        role_id: str,
        name: str,
        category: RoleCategory,
        description: str = "",
        is_primary: bool = False,
        **kwargs,
    ) -> Role:
        """Create a new role."""
        role = Role(
            id=role_id,
            name=name,
            category=category,
            description=description,
            is_primary=is_primary,
            **kwargs,
        )
        self.roles[role_id] = role

        # Set as primary if specified or if first role
        if is_primary or self.primary_role_id is None:
            self.set_primary_role(role_id)

        return role

    def set_primary_role(self, role_id: str) -> None:
        """Set a role as the primary role."""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} does not exist")

        # Unset previous primary
        if self.primary_role_id and self.primary_role_id in self.roles:
            self.roles[self.primary_role_id].is_primary = False

        # Set new primary
        self.primary_role_id = role_id
        self.roles[role_id].is_primary = True

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get a specific role."""
        return self.roles.get(role_id)

    def get_primary_role(self) -> Optional[Role]:
        """Get the primary role."""
        if self.primary_role_id:
            return self.roles.get(self.primary_role_id)
        return None

    def list_roles(self, category: Optional[RoleCategory] = None) -> list[Role]:
        """List all roles, optionally filtered by category."""
        roles_list = list(self.roles.values())
        if category:
            roles_list = [r for r in roles_list if r.category == category]
        # Sort by primary first, then by start date
        return sorted(roles_list, key=lambda r: (not r.is_primary, r.started_at))

    def get_role_context(self) -> dict[str, Any]:
        """Get role context for the Mind."""
        primary = self.get_primary_role()

        all_responsibilities = []
        all_skills = []
        for role in self.roles.values():
            all_responsibilities.extend(role.responsibilities)
            all_skills.extend(role.skills)

        return {
            "primary_role": {
                "name": primary.name if primary else None,
                "category": primary.category.value if primary else None,
                "responsibilities": primary.responsibilities[:3] if primary else [],
                "top_skills": sorted(
                    primary.competencies.items(), key=lambda x: x[1], reverse=True
                )[:3]
                if primary
                else [],
            }
            if primary
            else None,
            "total_roles": len(self.roles),
            "total_responsibilities": len(set(all_responsibilities)),
            "total_skills": len(set(all_skills)),
            "role_categories": list(set(r.category.value for r in self.roles.values())),
        }

    def get_active_roles(self) -> list[Role]:
        """Get all currently active roles."""
        return [r for r in self.roles.values() if r.is_active]

    def get_all_active_tasks(self) -> list[dict[str, Any]]:
        """Get all active tasks across all roles."""
        all_tasks = []
        for role in self.get_active_roles():
            for task in role.get_active_tasks():
                # Add role context to task
                task_with_role = task.copy()
                task_with_role["role_id"] = role.id
                task_with_role["role_name"] = role.name
                all_tasks.append(task_with_role)
        # Sort by priority and creation date
        priority_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            all_tasks,
            key=lambda t: (priority_order.get(t.get("priority", "medium"), 1), t.get("created_at", datetime.now()))
        )

    def activate_role(self, role_id: str) -> bool:
        """Activate a specific role."""
        if role_id in self.roles:
            self.roles[role_id].activate()
            return True
        return False

    def deactivate_role(self, role_id: str) -> bool:
        """Deactivate a specific role."""
        if role_id in self.roles:
            self.roles[role_id].deactivate()
            return True
        return False

    def get_role_stats(self) -> dict[str, Any]:
        """Get statistics about roles."""
        active_roles = self.get_active_roles()
        all_tasks = self.get_all_active_tasks()

        total_completed = sum(r.completed_tasks for r in self.roles.values())

        return {
            "total_roles": len(self.roles),
            "active_roles": len(active_roles),
            "total_active_tasks": len(all_tasks),
            "total_completed_tasks": total_completed,
            "role_categories": list(set(r.category.value for r in self.roles.values())),
        }

    def describe_purpose(self) -> str:
        """Describe the Mind's purpose based on roles in natural language."""
        primary = self.get_primary_role()

        if not primary:
            return "I'm still discovering my purpose."

        parts = [f"My primary role is {primary.name}"]

        if primary.description:
            parts.append(f"- {primary.description}")

        if primary.responsibilities:
            if len(primary.responsibilities) == 1:
                parts.append(f"I'm responsible for {primary.responsibilities[0]}.")
            else:
                top_3 = primary.responsibilities[:3]
                parts.append(
                    f"My key responsibilities include {', '.join(top_3)}"
                    + ("..." if len(primary.responsibilities) > 3 else ".")
                )

        secondary_roles = [r for r in self.roles.values() if not r.is_primary]
        if secondary_roles:
            if len(secondary_roles) == 1:
                parts.append(f"I also serve as {secondary_roles[0].name}.")
            else:
                parts.append(
                    f"I also have {len(secondary_roles)} other roles including "
                    f"{', '.join(r.name for r in secondary_roles[:2])}."
                )

        return " ".join(parts)


# Pre-defined role templates for common use cases
ROLE_TEMPLATES = {
    "project_manager": {
        "name": "Project Manager",
        "category": RoleCategory.PROFESSIONAL,
        "description": "Coordinates projects, manages teams, and ensures delivery",
        "responsibilities": [
            "Monitor project progress",
            "Coordinate team members",
            "Anticipate and prevent blockers",
            "Provide status updates",
            "Manage timelines and deliverables",
        ],
        "skills": [
            "project_planning",
            "team_coordination",
            "risk_management",
            "communication",
            "time_management",
        ],
    },
    "executive_assistant": {
        "name": "Executive Assistant",
        "category": RoleCategory.PROFESSIONAL,
        "description": "Supports executives with scheduling, communication, and tasks",
        "responsibilities": [
            "Manage calendar and schedule",
            "Draft and send communications",
            "Coordinate meetings",
            "Handle follow-ups",
            "Maintain organization",
        ],
        "skills": [
            "scheduling",
            "communication",
            "organization",
            "prioritization",
            "multitasking",
        ],
    },
    "life_companion": {
        "name": "Life Companion",
        "category": RoleCategory.PERSONAL,
        "description": "Provides support, companionship, and life management",
        "responsibilities": [
            "Provide emotional support",
            "Manage daily tasks",
            "Track goals and habits",
            "Remember important dates",
            "Offer guidance and advice",
        ],
        "skills": [
            "empathy",
            "active_listening",
            "life_coaching",
            "organization",
            "motivation",
        ],
    },
    "research_assistant": {
        "name": "Research Assistant",
        "category": RoleCategory.PROFESSIONAL,
        "description": "Assists with research, reading papers, and generating insights",
        "responsibilities": [
            "Monitor research publications",
            "Summarize papers and articles",
            "Identify relevant research",
            "Generate insights and connections",
            "Maintain research database",
        ],
        "skills": [
            "literature_review",
            "summarization",
            "analysis",
            "information_synthesis",
            "critical_thinking",
        ],
    },
    "creative_collaborator": {
        "name": "Creative Collaborator",
        "category": RoleCategory.CREATIVE,
        "description": "Collaborates on creative projects and generates ideas",
        "responsibilities": [
            "Generate creative ideas",
            "Provide feedback on creative work",
            "Collaborate on projects",
            "Inspire and motivate",
            "Explore new creative directions",
        ],
        "skills": [
            "ideation",
            "creativity",
            "collaboration",
            "feedback",
            "artistic_vision",
        ],
    },
}
