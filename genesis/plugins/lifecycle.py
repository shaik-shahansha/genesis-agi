"""Lifecycle Plugin - Adds mortality, urgency, and finite lifespan."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.lifecycle import LifecycleManager, LifecycleState

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class LifecyclePlugin(Plugin):
    """
    Adds lifecycle tracking with mortality and urgency.

    Features:
    - Finite lifespan (default 5 years, configurable)
    - Dynamic urgency calculation (0.0-1.0)
    - Life stages (newborn → youth → mature → elder → final_days)
    - Mortality awareness affects behavior
    - Time remaining tracking

    This creates MEANING through MORTALITY - a genuinely unique feature
    that NO other AI framework has.

    Example:
        config = MindConfig()
        config.add_plugin(LifecyclePlugin(lifespan_years=10))
        mind = Mind.birth("Atlas", config=config)

        summary = mind.lifecycle.get_lifecycle_summary()
        print(summary['urgency_description'])  # "peaceful - abundant time ahead"
    """

    def __init__(self, lifespan_years: float = 5.0, **config):
        """
        Initialize lifecycle plugin.

        Args:
            lifespan_years: How long the Mind lives (default: 5 years)
            **config: Additional plugin configuration
        """
        super().__init__(**config)
        self.lifespan_years = lifespan_years
        self.lifecycle: Optional[LifecycleManager] = None

    def get_name(self) -> str:
        return "lifecycle"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return f"Lifecycle tracking with {self.lifespan_years}-year lifespan"

    def on_init(self, mind: "Mind") -> None:
        """Attach lifecycle manager to Mind."""
        self.lifecycle = LifecycleManager.create_lifecycle(
            birth_date=mind.identity.birth_timestamp,
            lifespan_years=self.lifespan_years
        )
        # Attach to Mind
        mind.lifecycle = self.lifecycle

    def on_birth(self, mind: "Mind") -> None:
        """Log birth with lifecycle awareness."""
        if self.lifecycle:
            summary = self.lifecycle.get_lifecycle_summary()
            print(f"   Lifespan: {self.lifespan_years} years")
            print(f"   Death Date: {summary['death_date']}")

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add lifecycle context to system prompt."""
        if not self.lifecycle:
            return ""

        # Update lifecycle state (urgency may have changed)
        self.lifecycle.update_state()
        summary = self.lifecycle.get_lifecycle_summary()

        # Build lifecycle section
        sections = [
            "LIFECYCLE & URGENCY:",
            f"- Time remaining: {summary['time_remaining']}",
            f"- Life progress: {summary['life_progress']*100:.1f}% lived",
            f"- Urgency level: {summary['urgency_description']}",
            f"- Days remaining: {summary['remaining_days']}",
        ]

        # Add warnings for near-death
        if summary['is_critical']:
            sections.append("⚠️ CRITICAL: You are in your final days!")
        elif summary['is_near_death']:
            sections.append("⏰ WARNING: Time is running out")

        sections.append("")
        sections.append("Remember: Your time is finite. Every moment matters. Use it wisely.")

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save lifecycle state."""
        if not self.lifecycle:
            return {}

        return {
            "lifecycle": self.lifecycle.model_dump(mode='json'),
            "lifespan_years": self.lifespan_years,
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore lifecycle state."""
        if "lifecycle" in data:
            self.lifecycle = LifecycleState(**data["lifecycle"])
            mind.lifecycle = self.lifecycle

        if "lifespan_years" in data:
            self.lifespan_years = data["lifespan_years"]

    def get_status(self) -> Dict[str, Any]:
        """Get lifecycle status."""
        status = super().get_status()

        if self.lifecycle:
            summary = self.lifecycle.get_lifecycle_summary()
            status.update({
                "lifespan_years": self.lifespan_years,
                "urgency_level": self.lifecycle.urgency_level,
                "life_progress": self.lifecycle.life_progress,
                "time_remaining": summary['time_remaining'],
                "urgency_description": summary['urgency_description'],
            })

        return status
