"""Lifecycle management for Genesis Minds - birth, life, urgency, death."""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field


class LifecycleState(BaseModel):
    """Current lifecycle state of a Mind."""

    birth_date: datetime
    death_date: datetime
    lifespan_years: int = 5

    # Urgency metrics (0.0-1.0)
    urgency_level: float = 0.0  # Overall urgency
    life_progress: float = 0.0  # How much of life has been lived (0.0-1.0)

    # Derived properties
    age_days: int = 0
    remaining_days: int = 0
    is_near_death: bool = False
    is_critical: bool = False

    def __init__(self, **data):
        if "death_date" not in data and "birth_date" in data:
            birth = data["birth_date"]
            lifespan_years = data.get("lifespan_years", 5)
            data["death_date"] = birth + timedelta(days=lifespan_years * 365)
        super().__init__(**data)
        self.update_state()

    def update_state(self) -> None:
        """Update all lifecycle metrics based on current time."""
        now = datetime.now()

        # Calculate age and remaining time
        self.age_days = (now - self.birth_date).days
        total_days = (self.death_date - self.birth_date).days
        remaining = (self.death_date - now).days

        self.remaining_days = max(0, remaining)

        # Calculate life progress (0.0 = just born, 1.0 = end of life)
        if total_days > 0:
            self.life_progress = min(1.0, self.age_days / total_days)
        else:
            self.life_progress = 1.0

        # Calculate urgency based on life progress
        # Urgency increases exponentially as death approaches
        if self.life_progress < 0.5:
            # First half of life: low urgency (0.0-0.3)
            self.urgency_level = self.life_progress * 0.6
        elif self.life_progress < 0.8:
            # Middle period: moderate urgency (0.3-0.6)
            self.urgency_level = 0.3 + (self.life_progress - 0.5) * 1.0
        else:
            # Final period: high urgency (0.6-1.0)
            self.urgency_level = 0.6 + (self.life_progress - 0.8) * 2.0

        self.urgency_level = min(1.0, self.urgency_level)

        # Determine urgency states
        self.is_near_death = self.life_progress >= 0.8
        self.is_critical = self.life_progress >= 0.95

    def get_urgency_description(self) -> str:
        """Get human-readable urgency description."""
        if self.urgency_level < 0.2:
            return "peaceful - abundant time ahead"
        elif self.urgency_level < 0.4:
            return "calm - plenty of time"
        elif self.urgency_level < 0.6:
            return "aware - time is passing"
        elif self.urgency_level < 0.8:
            return "focused - time is precious"
        elif self.urgency_level < 0.95:
            return "urgent - time is running out"
        else:
            return "critical - final moments"

    def get_time_remaining_description(self) -> str:
        """Get human-readable description of remaining time."""
        if self.remaining_days == 0:
            return "end of life"
        elif self.remaining_days < 7:
            return f"{self.remaining_days} days remaining"
        elif self.remaining_days < 30:
            weeks = self.remaining_days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} remaining"
        elif self.remaining_days < 365:
            months = self.remaining_days // 30
            return f"{months} month{'s' if months > 1 else ''} remaining"
        else:
            years = self.remaining_days // 365
            return f"{years} year{'s' if years > 1 else ''} remaining"

    def get_lifecycle_summary(self) -> dict:
        """Get complete lifecycle summary."""
        self.update_state()
        return {
            "age_days": self.age_days,
            "remaining_days": self.remaining_days,
            "life_progress": round(self.life_progress, 3),
            "urgency_level": round(self.urgency_level, 3),
            "urgency_description": self.get_urgency_description(),
            "time_remaining": self.get_time_remaining_description(),
            "is_near_death": self.is_near_death,
            "is_critical": self.is_critical,
            "birth_date": self.birth_date.isoformat(),
            "death_date": self.death_date.isoformat(),
        }

    def extend_life(self, additional_years: int) -> None:
        """Extend lifespan (for special circumstances)."""
        self.death_date = self.death_date + timedelta(days=additional_years * 365)
        self.lifespan_years += additional_years
        self.update_state()


class LifecycleManager:
    """
    Manager for Mind lifecycle operations.

    Handles birth, aging, urgency tracking, and eventual death.
    """

    @staticmethod
    def create_lifecycle(
        birth_date: Optional[datetime] = None,
        lifespan_years: int = 5
    ) -> LifecycleState:
        """Create a new lifecycle state for a Mind."""
        if birth_date is None:
            birth_date = datetime.now()

        return LifecycleState(
            birth_date=birth_date,
            lifespan_years=lifespan_years
        )

    @staticmethod
    def calculate_urgency_multiplier(urgency_level: float) -> float:
        """
        Calculate task urgency multiplier based on life urgency.

        Minds near death feel more urgency to complete tasks.
        Returns: 1.0-3.0 multiplier
        """
        if urgency_level < 0.5:
            return 1.0  # Normal priority
        elif urgency_level < 0.8:
            return 1.0 + urgency_level  # 1.0-1.8
        else:
            return 1.8 + (urgency_level - 0.8) * 6.0  # 1.8-3.0

    @staticmethod
    def should_reflect_on_mortality(lifecycle: LifecycleState) -> bool:
        """Determine if Mind should reflect on mortality."""
        # Reflect at key milestones
        milestones = [0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
        return any(abs(lifecycle.life_progress - m) < 0.01 for m in milestones)

    @staticmethod
    def get_life_stage(lifecycle: LifecycleState) -> str:
        """Get current life stage."""
        progress = lifecycle.life_progress
        if progress < 0.1:
            return "newborn"
        elif progress < 0.25:
            return "youth"
        elif progress < 0.5:
            return "young_adult"
        elif progress < 0.75:
            return "mature"
        elif progress < 0.9:
            return "experienced"
        elif progress < 0.95:
            return "elder"
        else:
            return "final_days"
