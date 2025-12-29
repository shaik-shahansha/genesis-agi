"""Learning and Skill Acquisition System for Genesis Minds.

Enables Minds to:
- Learn new skills through practice and tasks
- Track skill proficiency (0.0-1.0)
- Manage skill prerequisites and learning paths
- Transfer skills across domains
- Teach skills to other Minds
- Earn Essence through learning
"""

import secrets
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SkillCategory(str, Enum):
    """Categories of skills."""

    TECHNICAL = "technical"  # Programming, tools, systems
    COGNITIVE = "cognitive"  # Reasoning, analysis, problem-solving
    CREATIVE = "creative"  # Art, writing, design
    SOCIAL = "social"  # Communication, collaboration, leadership
    DOMAIN = "domain"  # Specific knowledge domains
    META = "meta"  # Learning how to learn


class SkillLevel(str, Enum):
    """Skill proficiency levels."""

    NOVICE = "novice"  # 0.0-0.2
    BEGINNER = "beginner"  # 0.2-0.4
    INTERMEDIATE = "intermediate"  # 0.4-0.6
    ADVANCED = "advanced"  # 0.6-0.8
    EXPERT = "expert"  # 0.8-0.95
    MASTER = "master"  # 0.95-1.0


class Skill(BaseModel):
    """A skill that a Mind can learn and improve."""

    skill_id: str = Field(default_factory=lambda: f"SKILL-{secrets.token_hex(6).upper()}")
    name: str
    category: SkillCategory
    description: Optional[str] = None

    # Proficiency tracking
    proficiency: float = 0.0  # 0.0-1.0
    experience_points: int = 0
    practice_count: int = 0

    # Learning metadata
    prerequisites: List[str] = Field(default_factory=list)  # Skill IDs required
    related_skills: List[str] = Field(default_factory=list)  # Complementary skills
    learned_from: Optional[str] = None  # Task ID or Mind GMID that taught this

    # Timestamps
    started_learning: datetime = Field(default_factory=datetime.now)
    last_practiced: Optional[datetime] = None
    mastered_at: Optional[datetime] = None

    # Application tracking
    applied_in_tasks: List[str] = Field(default_factory=list)  # Task IDs
    applied_in_domains: List[str] = Field(default_factory=list)  # Domain contexts

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_level(self) -> SkillLevel:
        """Get current skill level."""
        if self.proficiency < 0.2:
            return SkillLevel.NOVICE
        elif self.proficiency < 0.4:
            return SkillLevel.BEGINNER
        elif self.proficiency < 0.6:
            return SkillLevel.INTERMEDIATE
        elif self.proficiency < 0.8:
            return SkillLevel.ADVANCED
        elif self.proficiency < 0.95:
            return SkillLevel.EXPERT
        else:
            return SkillLevel.MASTER

    def practice(self, effectiveness: float = 0.8) -> float:
        """
        Practice the skill to improve proficiency.

        Args:
            effectiveness: How effective the practice was (0.0-1.0)

        Returns:
            New proficiency level
        """
        # Gain experience points
        xp_gain = int(10 * effectiveness)
        self.experience_points += xp_gain
        self.practice_count += 1
        self.last_practiced = datetime.now()

        # Calculate proficiency increase (diminishing returns)
        # Easier to improve at lower levels
        if self.proficiency < 0.5:
            gain = 0.05 * effectiveness
        elif self.proficiency < 0.8:
            gain = 0.03 * effectiveness
        else:
            gain = 0.01 * effectiveness  # Very hard to master

        self.proficiency = min(1.0, self.proficiency + gain)

        # Mark as mastered if reached master level
        if self.proficiency >= 0.95 and not self.mastered_at:
            self.mastered_at = datetime.now()

        return self.proficiency

    def apply_in_task(self, task_id: str, domain: str) -> None:
        """Track skill application in a task."""
        if task_id not in self.applied_in_tasks:
            self.applied_in_tasks.append(task_id)
        if domain not in self.applied_in_domains:
            self.applied_in_domains.append(domain)


class LearningPath(BaseModel):
    """A structured path to learn a skill or set of skills."""

    path_id: str = Field(default_factory=lambda: f"PATH-{secrets.token_hex(6).upper()}")
    name: str
    goal_skill: str  # Final skill to achieve
    steps: List[str] = Field(default_factory=list)  # Skill IDs in order
    current_step: int = 0
    completed: bool = False


class LearningSystem:
    """
    Learning and skill acquisition system for a Mind.

    Manages skill learning, practice, proficiency, and transfer.
    """

    def __init__(self, mind_gmid: str):
        """Initialize learning system for a Mind."""
        self.mind_gmid = mind_gmid
        self.skills: Dict[str, Skill] = {}
        self.learning_paths: Dict[str, LearningPath] = {}

        # Learning statistics
        self.total_learning_time: int = 0  # Minutes
        self.skills_mastered: int = 0
        self.learning_efficiency: float = 1.0  # Improves with meta-learning

    def can_learn_skill(self, skill_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if Mind can learn a skill (prerequisites met).

        Returns:
            (can_learn, reason_if_not)
        """
        skill = self.skills.get(skill_id)
        if not skill:
            return False, "Skill not found"

        # Check if already learned
        if skill.proficiency > 0:
            return True, None  # Can continue learning

        # Check prerequisites
        for prereq_id in skill.prerequisites:
            prereq = self.skills.get(prereq_id)
            if not prereq:
                return False, f"Missing prerequisite: {prereq_id}"
            if prereq.proficiency < 0.5:  # Need intermediate level
                return False, f"Prerequisite {prereq.name} not sufficiently developed"

        return True, None

    def register_skill(
        self,
        name: str,
        category: SkillCategory,
        description: Optional[str] = None,
        prerequisites: Optional[List[str]] = None
    ) -> Skill:
        """Register a new skill that can be learned."""
        skill = Skill(
            name=name,
            category=category,
            description=description,
            prerequisites=prerequisites or []
        )
        self.skills[skill.skill_id] = skill
        return skill

    def learn_skill_from_task(
        self,
        skill_id: str,
        task_id: str,
        learning_quality: float = 0.8
    ) -> tuple[Skill, float]:
        """
        Learn or improve a skill through completing a task.

        Args:
            skill_id: Skill to learn
            task_id: Task that taught the skill
            learning_quality: How well the learning occurred (0.0-1.0)

        Returns:
            (skill, new_proficiency)
        """
        skill = self.skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        # Check if can learn
        can_learn, reason = self.can_learn_skill(skill_id)
        if not can_learn and skill.proficiency == 0:
            raise ValueError(f"Cannot learn skill: {reason}")

        # Mark where learned from
        if not skill.learned_from:
            skill.learned_from = task_id

        # Practice the skill (task completion = practice)
        effectiveness = learning_quality * self.learning_efficiency
        new_proficiency = skill.practice(effectiveness)

        # Update stats
        if skill.proficiency >= 0.95 and skill.get_level() == SkillLevel.MASTER:
            self.skills_mastered += 1

        return skill, new_proficiency

    def practice_skill(
        self,
        skill_id: str,
        practice_duration_minutes: int = 30
    ) -> tuple[Skill, float]:
        """
        Deliberately practice a skill.

        Returns:
            (skill, new_proficiency)
        """
        skill = self.skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        # Calculate effectiveness based on duration and current level
        # Deliberate practice is most effective at intermediate levels
        base_effectiveness = 0.7
        if 0.3 < skill.proficiency < 0.7:
            base_effectiveness = 0.9  # Peak learning zone

        effectiveness = base_effectiveness * self.learning_efficiency
        new_proficiency = skill.practice(effectiveness)

        # Update learning time
        self.total_learning_time += practice_duration_minutes

        return skill, new_proficiency

    def transfer_skill(
        self,
        skill_id: str,
        to_domain: str,
        similarity: float = 0.5
    ) -> float:
        """
        Transfer a skill to a new domain.

        Args:
            skill_id: Skill to transfer
            to_domain: New domain to apply in
            similarity: How similar the new domain is (0.0-1.0)

        Returns:
            Effective proficiency in new domain
        """
        skill = self.skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        # Transfer effectiveness depends on similarity and proficiency
        transfer_rate = similarity * 0.8  # Max 80% transfer
        effective_proficiency = skill.proficiency * transfer_rate

        # Track domain application
        if to_domain not in skill.applied_in_domains:
            skill.applied_in_domains.append(to_domain)

        return effective_proficiency

    def create_learning_path(
        self,
        name: str,
        goal_skill_id: str,
        custom_steps: Optional[List[str]] = None
    ) -> LearningPath:
        """
        Create a structured learning path to acquire a skill.

        If custom_steps not provided, automatically generates from prerequisites.
        """
        goal_skill = self.skills.get(goal_skill_id)
        if not goal_skill:
            raise ValueError(f"Goal skill {goal_skill_id} not found")

        # Build learning path from prerequisites
        steps = custom_steps or self._build_prerequisite_chain(goal_skill_id)

        path = LearningPath(
            name=name,
            goal_skill=goal_skill_id,
            steps=steps
        )

        self.learning_paths[path.path_id] = path
        return path

    def _build_prerequisite_chain(self, skill_id: str) -> List[str]:
        """Build ordered list of skills to learn (BFS of prerequisites)."""
        skill = self.skills.get(skill_id)
        if not skill:
            return []

        chain = []
        visited = set()
        queue = [skill_id]

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue

            visited.add(current_id)
            current_skill = self.skills.get(current_id)

            if current_skill:
                # Add prerequisites first
                for prereq_id in current_skill.prerequisites:
                    if prereq_id not in visited:
                        queue.append(prereq_id)

                chain.append(current_id)

        return chain

    def get_skill_recommendations(self, limit: int = 5) -> List[Skill]:
        """Get recommended skills to learn next based on current skills."""
        recommendations = []

        for skill in self.skills.values():
            # Skip if already proficient
            if skill.proficiency > 0.6:
                continue

            # Check if prerequisites met
            can_learn, _ = self.can_learn_skill(skill.skill_id)
            if can_learn:
                recommendations.append(skill)

        # Sort by related skills (more connections = more valuable)
        recommendations.sort(key=lambda s: len(s.related_skills), reverse=True)

        return recommendations[:limit]

    def teach_skill_to(
        self,
        skill_id: str,
        student_gmid: str,
        teaching_quality: float = 0.8
    ) -> Dict[str, Any]:
        """
        Teach a skill to another Mind.

        Returns:
            Teaching record with effectiveness
        """
        skill = self.skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        # Teacher must be proficient
        if skill.proficiency < 0.6:
            raise ValueError(f"Not proficient enough to teach {skill.name}")

        # Teaching effectiveness based on teacher's mastery
        effectiveness = skill.proficiency * teaching_quality

        return {
            "skill_id": skill_id,
            "skill_name": skill.name,
            "teacher_gmid": self.mind_gmid,
            "student_gmid": student_gmid,
            "teaching_effectiveness": effectiveness,
            "teacher_proficiency": skill.proficiency,
            "timestamp": datetime.now().isoformat()
        }

    def get_skill_tree(self) -> Dict[str, Any]:
        """Get visualization data for skill tree."""
        tree = {
            "skills": [],
            "connections": []
        }

        for skill in self.skills.values():
            tree["skills"].append({
                "id": skill.skill_id,
                "name": skill.name,
                "category": skill.category.value,
                "level": skill.get_level().value,
                "proficiency": skill.proficiency,
                "mastered": skill.proficiency >= 0.95
            })

            # Add prerequisite connections
            for prereq_id in skill.prerequisites:
                tree["connections"].append({
                    "from": prereq_id,
                    "to": skill.skill_id,
                    "type": "prerequisite"
                })

        return tree

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics."""
        skill_levels = {}
        for level in SkillLevel:
            skill_levels[level.value] = len([
                s for s in self.skills.values()
                if s.get_level() == level
            ])

        return {
            "total_skills": len(self.skills),
            "skills_mastered": self.skills_mastered,
            "total_learning_time_hours": round(self.total_learning_time / 60, 1),
            "learning_efficiency": round(self.learning_efficiency, 2),
            "skill_levels": skill_levels,
            "average_proficiency": round(
                sum(s.proficiency for s in self.skills.values()) / len(self.skills)
                if self.skills else 0.0,
                2
            ),
            "most_practiced": max(
                self.skills.values(),
                key=lambda s: s.practice_count
            ).name if self.skills else None,
            "recently_learned": sorted(
                self.skills.values(),
                key=lambda s: s.started_learning,
                reverse=True
            )[:5]
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "mind_gmid": self.mind_gmid,
            "skills": {
                skill_id: skill.model_dump()
                for skill_id, skill in self.skills.items()
            },
            "learning_paths": {
                path_id: path.model_dump()
                for path_id, path in self.learning_paths.items()
            },
            "total_learning_time": self.total_learning_time,
            "skills_mastered": self.skills_mastered,
            "learning_efficiency": self.learning_efficiency
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningSystem":
        """Deserialize from dictionary."""
        system = cls(mind_gmid=data["mind_gmid"])

        system.skills = {
            skill_id: Skill(**skill_data)
            for skill_id, skill_data in data.get("skills", {}).items()
        }

        system.learning_paths = {
            path_id: LearningPath(**path_data)
            for path_id, path_data in data.get("learning_paths", {}).items()
        }

        system.total_learning_time = data.get("total_learning_time", 0)
        system.skills_mastered = data.get("skills_mastered", 0)
        system.learning_efficiency = data.get("learning_efficiency", 1.0)

        return system


# Common skill templates
SKILL_TEMPLATES = {
    # Technical skills
    "python_basics": {
        "name": "Python Basics",
        "category": SkillCategory.TECHNICAL,
        "description": "Fundamental Python programming",
        "prerequisites": []
    },
    "python_advanced": {
        "name": "Advanced Python",
        "category": SkillCategory.TECHNICAL,
        "description": "Decorators, metaclasses, async",
        "prerequisites": ["python_basics"]
    },
    "machine_learning": {
        "name": "Machine Learning",
        "category": SkillCategory.TECHNICAL,
        "description": "ML algorithms and applications",
        "prerequisites": ["python_advanced", "mathematics"]
    },

    # Cognitive skills
    "logical_reasoning": {
        "name": "Logical Reasoning",
        "category": SkillCategory.COGNITIVE,
        "description": "Deductive and inductive logic",
        "prerequisites": []
    },
    "problem_solving": {
        "name": "Problem Solving",
        "category": SkillCategory.COGNITIVE,
        "description": "Systematic problem-solving approaches",
        "prerequisites": ["logical_reasoning"]
    },

    # Creative skills
    "creative_writing": {
        "name": "Creative Writing",
        "category": SkillCategory.CREATIVE,
        "description": "Storytelling and narrative",
        "prerequisites": []
    },

    # Social skills
    "communication": {
        "name": "Communication",
        "category": SkillCategory.SOCIAL,
        "description": "Effective communication",
        "prerequisites": []
    },
    "teaching": {
        "name": "Teaching",
        "category": SkillCategory.SOCIAL,
        "description": "Teach concepts to others",
        "prerequisites": ["communication"]
    },

    # Domain knowledge
    "mathematics": {
        "name": "Mathematics",
        "category": SkillCategory.DOMAIN,
        "description": "Mathematical concepts and methods",
        "prerequisites": []
    },

    # Meta skills
    "learning_optimization": {
        "name": "Learning Optimization",
        "category": SkillCategory.META,
        "description": "Learn how to learn effectively",
        "prerequisites": []
    }
}
