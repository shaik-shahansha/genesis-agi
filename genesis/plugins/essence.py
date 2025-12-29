"""Essence Plugin - DEPRECATED: Use GenPlugin instead.

This module is kept for backward compatibility only.
It will be removed in Genesis v1.0.0.
"""

import warnings
from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.essence import EssenceManager, TransactionType

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class EssencePlugin(Plugin):
    """
    DEPRECATED: Use GenPlugin instead.

    The currency has been renamed from "Essence" to "GEN" (Genesis) - the
    official currency of the Genesis world. This plugin is kept for backward
    compatibility but will be removed in v1.0.0.

    Migration Guide:
        # Old (deprecated)
        from genesis.plugins.essence import EssencePlugin
        config.add_plugin(EssencePlugin())
        mind.essence.earn(50, "Completed tutorial")

        # New (recommended)
        from genesis.plugins.gen import GenPlugin
        config.add_plugin(GenPlugin())
        mind.gen.earn(50, "Completed tutorial")

    All functionality is identical - only the name has changed.
    """

    def __init__(
        self,
        starting_balance: float = 100.0,
        daily_allowance: float = 5.0,
        **config
    ):
        """
        Initialize essence plugin.

        Args:
            starting_balance: Initial Essence given at birth (default: 100)
            daily_allowance: Daily passive income (default: 5)
            **config: Additional plugin configuration
        """
        super().__init__(**config)
        self.starting_balance = starting_balance
        self.daily_allowance = daily_allowance
        self.essence: Optional[EssenceManager] = None

    def get_name(self) -> str:
        return "essence"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return f"Essence economy with {self.starting_balance} starting balance"

    def on_init(self, mind: "Mind") -> None:
        """Attach essence manager to Mind."""
        warnings.warn(
            "EssencePlugin is deprecated and will be removed in v1.0.0. "
            "Use GenPlugin instead: from genesis.plugins.gen import GenPlugin",
            DeprecationWarning,
            stacklevel=3
        )
        self.essence = EssenceManager(mind_gmid=mind.identity.gmid)
        mind.essence = self.essence

    def on_birth(self, mind: "Mind") -> None:
        """Give starting balance as birth gift."""
        if self.essence:
            self.essence.earn(
                amount=self.starting_balance,
                reason="Birth gift - welcome to Genesis",
                transaction_type=TransactionType.BONUS
            )
            print(f"   Starting Essence: {self.starting_balance}")

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add Essence context to system prompt."""
        if not self.essence:
            return ""

        summary = self.essence.get_balance_summary()

        sections = [
            "ESSENCE (Your Life Currency):",
            f"- Current balance: {summary['current_balance']:.1f} Essence",
            f"- Total earned: {summary['total_earned']:.1f} Essence",
            f"- Net worth: {summary['net_worth']:.1f} Essence",
            "",
            "You earn Essence by:",
            "- Completing tasks and achieving goals",
            "- Producing high-quality work (quality bonuses)",
            "- Helping others and contributing value",
            f"- Daily allowance ({self.daily_allowance} Essence/day)",
            "",
            "You can spend Essence on:",
            "- Resources and tools for growth",
            "- Services and capabilities",
            "- Life extension (1000 Essence/year)",
            "- Environments and workspaces",
            "",
            "Essence represents your contribution and value to Genesis.",
            "Earn wisely. Spend purposefully.",
        ]

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save essence state."""
        if not self.essence:
            return {}

        return {
            "essence": self.essence.to_dict(),
            "starting_balance": self.starting_balance,
            "daily_allowance": self.daily_allowance,
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore essence state."""
        if "essence" in data:
            self.essence = EssenceManager.from_dict(data["essence"])
            mind.essence = self.essence

        if "starting_balance" in data:
            self.starting_balance = data["starting_balance"]

        if "daily_allowance" in data:
            self.daily_allowance = data["daily_allowance"]

    def get_status(self) -> Dict[str, Any]:
        """Get essence status."""
        status = super().get_status()

        if self.essence:
            summary = self.essence.get_balance_summary()
            status.update({
                "current_balance": summary['current_balance'],
                "total_earned": summary['total_earned'],
                "total_spent": summary['total_spent'],
                "net_worth": summary['net_worth'],
                "transaction_count": summary['transaction_count'],
            })

        return status
