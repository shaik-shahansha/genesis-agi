"""Goals Plugin - EXPERIMENTAL (no autonomous pursuit)."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.goals import GoalManager

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class GoalsPlugin(Plugin):
    """
    Adds goal setting and planning system.

    ⚠️ EXPERIMENTAL WARNING:
    - Goals exist but don't drive behavior
    - No autonomous goal pursuit
    - Plans aren't auto-executed
    - This is DATA TRACKING, not autonomy

    Use only for:
    - Goal tracking and organization
    - Planning assistance
    - Understanding future autonomy architecture

    For REAL goal-driven behavior, we need:
    - Autonomous goal pursuit loops
    - Goal-based task generation
    - Plan execution engine
    - Success/failure learning
    """

    def __init__(self, **config):
        super().__init__(**config)
        self.goals: Optional[GoalManager] = None

    def get_name(self) -> str:
        return "goals"

    def get_version(self) -> str:
        return "0.1.1-experimental"

    def get_description(self) -> str:
        return "⚠️ EXPERIMENTAL: Goal tracking (no autonomy)"

    def on_init(self, mind: "Mind") -> None:
        self.goals = GoalManager(mind_gmid=mind.identity.gmid)
        mind.goals = self.goals

    def extend_system_prompt(self, mind: "Mind") -> str:
        if not self.goals:
            return ""

        stats = self.goals.get_goal_stats()

        return f"""
⚠️ EXPERIMENTAL GOALS (tracking only):
- Active goals: {stats.get('active', 0)}
- Completed goals: {stats.get('completed', 0)}

Note: Goals are tracked but don't drive autonomous behavior yet.
"""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        if not self.goals:
            return {}
        return {"goals": self.goals.to_dict()}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        if "goals" in data:
            self.goals = GoalManager.from_dict(data["goals"])
            mind.goals = self.goals
