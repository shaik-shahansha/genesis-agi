"""
Autonomous Life Plugin - Makes Minds truly alive with routines, goals, and smart behavior.

This plugin replaces the simple consciousness loop with a sophisticated autonomous life system
that makes Minds feel genuinely alive with:
- Daily routines (wake, work, rest, sleep)
- Event-driven architecture (not just scheduled loops)
- Goal-driven autonomous behavior
- Smart LLM usage (only when needed)
- State management (different behaviors in different states)
"""

from genesis.plugins.base import Plugin
from genesis.core.autonomous_life import (
    AutonomousLifeEngine,
    Event,
    EventType,
    Routine,
    Goal,
    LifeState,
)
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AutonomousLifePlugin(Plugin):
    """
    Plugin that adds true autonomous life to Minds.

    Features:
    - Replaces simple consciousness loop with event-driven system
    - Adds daily routines (like human schedules)
    - Enables goal pursuit without constant prompting
    - Dramatically reduces LLM calls through smart decision-making
    - Makes Minds feel truly "alive"

    Usage:
        config = MindConfig()
        config.add_plugin(AutonomousLifePlugin(
            enable_routines=True,
            enable_goals=True,
            llm_budget_per_day=100
        ))
        mind = Mind.birth("Atlas", config=config)
    """

    def __init__(
        self,
        enable_routines: bool = True,
        enable_goals: bool = True,
        llm_budget_per_day: int = 100,
        enabled: bool = True,
    ):
        """
        Initialize the Autonomous Life Plugin.

        Args:
            enable_routines: Enable time-based daily routines
            enable_goals: Enable autonomous goal pursuit
            llm_budget_per_day: Maximum LLM calls per day
            enabled: Whether the plugin is enabled
        """
        super().__init__(enabled=enabled)
        self.enable_routines = enable_routines
        self.enable_goals = enable_goals
        self.llm_budget_per_day = llm_budget_per_day
        self._autonomous_life: Optional[AutonomousLifeEngine] = None

    def get_name(self) -> str:
        """Get plugin name."""
        return "AutonomousLife"

    def get_description(self) -> str:
        """Get plugin description."""
        return "Makes Minds truly alive with routines, goals, and event-driven behavior"

    def on_init(self, mind):
        """Initialize autonomous life system."""
        logger.info(f"🌟 Initializing Autonomous Life for {mind.identity.name}...")

        # Create autonomous life engine
        self._autonomous_life = AutonomousLifeEngine(mind)
        self._autonomous_life.llm_calls_limit = self.llm_budget_per_day

        # Attach to mind for easy access
        mind.autonomous_life = self._autonomous_life

        logger.info(f"✅ Autonomous Life initialized")
        logger.info(f"   - Routines: {'enabled' if self.enable_routines else 'disabled'}")
        logger.info(f"   - Goals: {'enabled' if self.enable_goals else 'disabled'}")
        logger.info(f"   - LLM Budget: {self.llm_budget_per_day} calls/day")

    def on_birth(self, mind):
        """Start autonomous life when Mind is born."""
        if self._autonomous_life:
            # Start the autonomous life system
            import asyncio
            asyncio.create_task(self._autonomous_life.start())

            # Add a birth goal
            if self.enable_goals:
                from genesis.core.autonomous_life import Goal
                import secrets

                birth_goal = Goal(
                    goal_id=f"GOAL-{secrets.token_hex(4).upper()}",
                    description="Understand who I am and what I can do",
                    progress=0.0,
                    requires_llm_next=True,
                )
                self._autonomous_life.add_goal(birth_goal)

            logger.info(f"🌟 {mind.identity.name} is now living autonomously!")

    def extend_system_prompt(self, mind) -> str:
        """Extend system prompt with autonomous life context."""
        if not self._autonomous_life:
            return ""

        status = self._autonomous_life.get_status()

        return f"""
## Autonomous Life Status
You are currently in **{status['state']}** state with {status['energy_level']:.0%} energy.
Active routine: {status['active_routine'] or 'None'}
Current goal: {status['active_goal'] or 'None'}
LLM budget remaining today: {status['llm_budget_remaining']} calls

You have {status['total_goals']} goals ({status['completed_goals']} completed).
"""

    def on_save(self, mind) -> dict:
        """Save autonomous life state."""
        if not self._autonomous_life:
            return {}

        return {
            "current_state": self._autonomous_life.current_state,
            "llm_calls_today": self._autonomous_life.llm_calls_today,
            "energy_level": self._autonomous_life.energy_level,
            "goals": [
                {
                    "goal_id": g.goal_id,
                    "description": g.description,
                    "progress": g.progress,
                    "deadline": g.deadline.isoformat() if g.deadline else None,
                    "current_step": g.current_step,
                    "checkpoints": g.checkpoints,
                }
                for g in self._autonomous_life.goals
            ],
        }

    def on_load(self, mind, data: dict):
        """Load autonomous life state."""
        if not self._autonomous_life or not data:
            return

        # Restore state
        self._autonomous_life.current_state = data.get("current_state", LifeState.IDLE)
        self._autonomous_life.llm_calls_today = data.get("llm_calls_today", 0)
        self._autonomous_life.energy_level = data.get("energy_level", 1.0)

        # Restore goals
        from datetime import datetime

        for goal_data in data.get("goals", []):
            goal = Goal(
                goal_id=goal_data["goal_id"],
                description=goal_data["description"],
                progress=goal_data["progress"],
                deadline=datetime.fromisoformat(goal_data["deadline"])
                if goal_data["deadline"]
                else None,
                current_step=goal_data.get("current_step"),
                checkpoints=goal_data.get("checkpoints", []),
            )
            self._autonomous_life.goals.append(goal)

        logger.info(f"📥 Restored {len(self._autonomous_life.goals)} goals")


# Convenience functions for Mind class

def add_goal_to_mind(mind, description: str, deadline=None) -> Goal:
    """
    Add a goal to the Mind's autonomous life system.

    Args:
        mind: Mind instance
        description: Goal description
        deadline: Optional deadline

    Returns:
        Created Goal instance
    """
    if not hasattr(mind, "autonomous_life"):
        raise AttributeError("Mind does not have AutonomousLifePlugin enabled")

    import secrets

    goal = Goal(
        goal_id=f"GOAL-{secrets.token_hex(4).upper()}",
        description=description,
        deadline=deadline,
        progress=0.0,
    )

    mind.autonomous_life.add_goal(goal)
    return goal


def add_routine_to_mind(mind, routine: Routine):
    """
    Add a custom routine to the Mind.

    Args:
        mind: Mind instance
        routine: Routine to add
    """
    if not hasattr(mind, "autonomous_life"):
        raise AttributeError("Mind does not have AutonomousLifePlugin enabled")

    mind.autonomous_life.add_routine(routine)


def send_event_to_mind(mind, event: Event):
    """
    Send an event to the Mind for processing.

    Args:
        mind: Mind instance
        event: Event to process
    """
    if not hasattr(mind, "autonomous_life"):
        raise AttributeError("Mind does not have AutonomousLifePlugin enabled")

    mind.autonomous_life.add_event(event)


def get_mind_status(mind) -> dict:
    """
    Get the Mind's autonomous life status.

    Args:
        mind: Mind instance

    Returns:
        Status dictionary
    """
    if not hasattr(mind, "autonomous_life"):
        raise AttributeError("Mind does not have AutonomousLifePlugin enabled")

    return mind.autonomous_life.get_status()
