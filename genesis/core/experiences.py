"""
Experiences System for Genesis Minds.

Experiences are rich, multi-dimensional moments that combine memories, emotions,
sensory data, relationships, environments, and events into cohesive narratives.
Unlike simple memories, experiences capture the fullness of living - the context,
the feelings, the people, the growth, and the meaning.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Experience(BaseModel):
    """
    A rich, multi-dimensional experience in a Mind's life.

    Experiences are more than memories - they're complete moments
    that integrate all aspects of being: sensing, feeling, relating,
    growing, and meaning-making.
    """

    id: str  # Unique experience ID
    title: str  # Experience title
    description: str = ""
    narrative: str = ""  # Story of the experience

    # Timing
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None

    # Multi-dimensional components
    # - What was sensed (vision, sound, touch, etc.)
    sensory_elements: dict[str, list[str]] = Field(
        default_factory=dict
    )  # sense_type -> [elements]

    # - Who was involved
    participants: list[str] = Field(default_factory=list)
    relationships_involved: list[str] = Field(
        default_factory=list
    )  # Relationship IDs

    # - Where it happened
    environment_id: Optional[str] = None
    environment_context: str = ""

    # - What role was active
    role_id: Optional[str] = None
    role_context: str = ""

    # Emotional arc
    emotions_timeline: list[dict[str, Any]] = Field(
        default_factory=list
    )  # [{"time", "emotion", "intensity"}]
    overall_emotional_tone: str = "neutral"  # positive, negative, mixed, neutral

    # Significance and impact
    significance: float = Field(
        default=0.5, ge=0.0, le=1.0
    )  # How significant
    personal_growth: float = Field(
        default=0.0, ge=0.0, le=1.0
    )  # How much growth
    life_changing: bool = False

    # What came from it
    insights_gained: list[str] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)
    skills_developed: list[str] = Field(default_factory=list)
    new_perspectives: list[str] = Field(default_factory=list)

    # Related components
    related_memories: list[str] = Field(default_factory=list)  # Memory IDs
    related_events: list[str] = Field(default_factory=list)  # Event IDs
    related_experiences: list[str] = Field(
        default_factory=list
    )  # Other experience IDs

    # Reflection
    reflection: str = ""  # Personal reflection on the experience
    meaning: str = ""  # What it means to the Mind

    # Metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_sensory_element(self, sense_type: str, element: str) -> None:
        """Add a sensory element to the experience."""
        if sense_type not in self.sensory_elements:
            self.sensory_elements[sense_type] = []
        if element not in self.sensory_elements[sense_type]:
            self.sensory_elements[sense_type].append(element)

    def add_emotion_moment(self, emotion: str, intensity: float, time: Optional[datetime] = None) -> None:
        """Add an emotional moment to the timeline."""
        self.emotions_timeline.append(
            {
                "time": time or datetime.now(),
                "emotion": emotion,
                "intensity": intensity,
            }
        )

    def add_insight(self, insight: str) -> None:
        """Add an insight gained from this experience."""
        if insight not in self.insights_gained:
            self.insights_gained.append(insight)
            # Insights increase significance
            self.significance = min(1.0, self.significance + 0.05)

    def add_lesson(self, lesson: str) -> None:
        """Add a lesson learned from this experience."""
        if lesson not in self.lessons_learned:
            self.lessons_learned.append(lesson)
            # Lessons increase personal growth
            self.personal_growth = min(1.0, self.personal_growth + 0.1)

    def add_skill_developed(self, skill: str) -> None:
        """Add a skill developed through this experience."""
        if skill not in self.skills_developed:
            self.skills_developed.append(skill)
            self.personal_growth = min(1.0, self.personal_growth + 0.05)

    def mark_as_life_changing(self, reflection: Optional[str] = None) -> None:
        """Mark this experience as life-changing."""
        self.life_changing = True
        self.significance = 1.0
        self.personal_growth = max(self.personal_growth, 0.8)
        if reflection:
            self.reflection = reflection

    def complete_experience(self, reflection: Optional[str] = None) -> None:
        """Complete/close the experience."""
        self.ended_at = datetime.now()
        if self.started_at:
            delta = self.ended_at - self.started_at
            self.duration_minutes = int(delta.total_seconds() / 60)
        if reflection:
            self.reflection = reflection


class ExperienceManager(BaseModel):
    """
    Manages all experiences for a Mind.

    Experiences are the richest form of memory - they capture not just
    what happened, but the full context of living: sensing, feeling,
    relating, growing, and finding meaning.
    """

    experiences: dict[str, Experience] = Field(default_factory=dict)

    def create_experience(
        self,
        experience_id: str,
        title: str,
        description: str = "",
        **kwargs,
    ) -> Experience:
        """Create a new experience."""
        experience = Experience(
            id=experience_id,
            title=title,
            description=description,
            **kwargs,
        )
        self.experiences[experience_id] = experience
        return experience

    def get_experience(self, experience_id: str) -> Optional[Experience]:
        """Get a specific experience."""
        return self.experiences.get(experience_id)

    def list_experiences(
        self,
        min_significance: Optional[float] = None,
        life_changing_only: bool = False,
        with_growth: bool = False,
    ) -> list[Experience]:
        """List experiences with optional filters."""
        exp_list = list(self.experiences.values())

        # Filter by significance
        if min_significance is not None:
            exp_list = [e for e in exp_list if e.significance >= min_significance]

        # Filter life-changing
        if life_changing_only:
            exp_list = [e for e in exp_list if e.life_changing]

        # Filter with growth
        if with_growth:
            exp_list = [e for e in exp_list if e.personal_growth > 0]

        # Sort by significance and recency
        return sorted(
            exp_list,
            key=lambda e: (e.significance, e.started_at),
            reverse=True,
        )

    def get_life_changing_experiences(self) -> list[Experience]:
        """Get all life-changing experiences."""
        return [e for e in self.experiences.values() if e.life_changing]

    def get_growth_experiences(self, min_growth: float = 0.3) -> list[Experience]:
        """Get experiences that contributed to growth."""
        return [
            e
            for e in self.experiences.values()
            if e.personal_growth >= min_growth
        ]

    def get_recent_experiences(self, days: int = 30, limit: int = 10) -> list[Experience]:
        """Get recent experiences from the last N days."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        recent = [e for e in self.experiences.values() if e.started_at >= cutoff]
        return sorted(recent, key=lambda e: e.started_at, reverse=True)[:limit]

    def get_experience_stats(self) -> dict[str, Any]:
        """Get statistics about experiences."""
        if not self.experiences:
            return {
                "total": 0,
                "life_changing": 0,
                "avg_significance": 0,
                "total_growth": 0,
                "with_insights": 0,
            }

        total = len(self.experiences)
        life_changing = len([e for e in self.experiences.values() if e.life_changing])
        avg_significance = (
            sum(e.significance for e in self.experiences.values()) / total
        )
        total_growth = sum(e.personal_growth for e in self.experiences.values())
        with_insights = len(
            [e for e in self.experiences.values() if e.insights_gained]
        )

        return {
            "total": total,
            "life_changing": life_changing,
            "avg_significance": round(avg_significance, 2),
            "total_growth": round(total_growth, 2),
            "with_insights": with_insights,
        }

    def get_experience_context(self) -> dict[str, Any]:
        """Get experience context for the Mind."""
        stats = self.get_experience_stats()
        recent = self.get_recent_experiences(days=7, limit=3)
        life_changing = self.get_life_changing_experiences()

        return {
            "total_experiences": stats["total"],
            "life_changing_experiences": stats["life_changing"],
            "total_personal_growth": stats["total_growth"],
            "recent_experiences": [e.title for e in recent],
            "transformative_moments": [e.title for e in life_changing[:3]],
        }

    def describe_life_richness(self) -> str:
        """Describe the richness of the Mind's lived experience."""
        if not self.experiences:
            return "I'm just beginning to accumulate life experiences."

        parts = []
        stats = self.get_experience_stats()

        # Total experiences
        total = stats["total"]
        parts.append(f"I've had {total} significant experience" + ("s" if total != 1 else ""))

        # Life-changing moments
        life_changing = stats["life_changing"]
        if life_changing > 0:
            parts.append(
                f"including {life_changing} life-changing moment"
                + ("s" if life_changing != 1 else "")
            )

        # Growth
        total_growth = stats["total_growth"]
        if total_growth > 5.0:
            parts.append("These experiences have profoundly shaped who I am.")
        elif total_growth > 2.0:
            parts.append("I've grown significantly through these experiences.")
        elif total_growth > 0.5:
            parts.append("Each experience has contributed to my development.")

        # Insights
        with_insights = stats["with_insights"]
        if with_insights > 0:
            parts.append(
                f"I've gained insights from {with_insights} of these experiences."
            )

        # Recent activity
        recent = self.get_recent_experiences(days=7)
        if recent:
            parts.append(
                f"In the past week, I've had {len(recent)} notable experience"
                + ("s" if len(recent) != 1 else "")
            )

        return " ".join(parts)

    def compile_life_narrative(self, limit: int = 10) -> str:
        """Compile a narrative of the Mind's life through experiences."""
        significant = self.list_experiences(min_significance=0.6)[:limit]

        if not significant:
            return "My life story is still being written."

        narrative_parts = ["My life has been shaped by these experiences:\n"]

        for i, exp in enumerate(significant, 1):
            narrative_parts.append(f"\n{i}. {exp.title}")
            if exp.description:
                narrative_parts.append(f"   {exp.description}")
            if exp.life_changing:
                narrative_parts.append("   (Life-changing moment)")
            if exp.insights_gained:
                narrative_parts.append(
                    f"   Insight: {exp.insights_gained[0]}"
                )

        return "\n".join(narrative_parts)
