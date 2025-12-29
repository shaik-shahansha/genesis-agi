"""GEN Plugin - Adds economy, currency, and motivation system."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.gen import GenManager, TransactionType

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class GenPlugin(Plugin):
    """
    Adds GEN economy for motivation and rewards.

    Features:
    - Digital currency called "GEN"
    - Earning system (tasks, bonuses, allowance)
    - Spending system (resources, services, life extension)
    - Transaction history (complete audit trail)
    - Economic governance

    GEN creates PURPOSE through INCENTIVES - Minds are motivated to
    earn and spend wisely, creating goal-oriented behavior.

    Example:
        config = MindConfig()
        config.add_plugin(GenPlugin(starting_balance=500, daily_allowance=10))
        mind = Mind.birth("Nexus", config=config)

        # Earn GEN
        mind.gen.earn(50, "Completed tutorial", TransactionType.TASK_REWARD)

        # Check balance
        balance = mind.gen.get_balance_summary()
        print(balance['current_balance'])  # 550
    """

    def __init__(
        self,
        starting_balance: float = 100.0,
        daily_allowance: float = 5.0,
        **config
    ):
        """
        Initialize GEN plugin.

        Args:
            starting_balance: Initial GEN given at birth (default: 100)
            daily_allowance: Daily passive income (default: 5)
            **config: Additional plugin configuration
        """
        super().__init__(**config)
        self.starting_balance = starting_balance
        self.daily_allowance = daily_allowance
        self.gen: Optional[GenManager] = None

    def get_name(self) -> str:
        return "gen"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return f"GEN economy with {self.starting_balance} starting balance"

    def on_init(self, mind: "Mind") -> None:
        """Attach GEN manager to Mind."""
        self.gen = GenManager(mind_gmid=mind.identity.gmid)
        mind.gen = self.gen

    def on_birth(self, mind: "Mind") -> None:
        """Give starting balance as birth gift."""
        if self.gen:
            self.gen.earn(
                amount=self.starting_balance,
                reason="Birth gift - welcome to Genesis",
                transaction_type=TransactionType.BONUS
            )
            print(f"   Starting GEN: {self.starting_balance}")

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add GEN context to system prompt."""
        if not self.gen:
            return ""

        summary = self.gen.get_balance_summary()

        sections = [
            "GEN (Your Life Currency):",
            f"- Current balance: {summary['current_balance']:.1f} GEN",
            f"- Total earned: {summary['total_earned']:.1f} GEN",
            f"- Net worth: {summary['net_worth']:.1f} GEN",
            "",
            "You earn GEN by:",
            "- Completing tasks and achieving goals",
            "- Producing high-quality work (quality bonuses)",
            "- Helping others and contributing value",
            f"- Daily allowance ({self.daily_allowance} GEN/day)",
            "",
            "You can spend GEN on:",
            "- Resources and tools for growth",
            "- Services and capabilities",
            "- Life extension (1000 GEN/year)",
            "- Environments and workspaces",
            "",
            "GEN represents your contribution and value to Genesis.",
            "Earn wisely. Spend purposefully.",
        ]

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save GEN state."""
        if not self.gen:
            return {}

        return {
            "gen": self.gen.to_dict(),
            "starting_balance": self.starting_balance,
            "daily_allowance": self.daily_allowance,
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore GEN state."""
        if "gen" in data:
            self.gen = GenManager.from_dict(data["gen"])
            mind.gen = self.gen

        if "starting_balance" in data:
            self.starting_balance = data["starting_balance"]

        if "daily_allowance" in data:
            self.daily_allowance = data["daily_allowance"]

    def get_status(self) -> Dict[str, Any]:
        """Get GEN status."""
        status = super().get_status()

        if self.gen:
            summary = self.gen.get_balance_summary()
            status.update({
                "current_balance": summary['current_balance'],
                "total_earned": summary['total_earned'],
                "total_spent": summary['total_spent'],
                "net_worth": summary['net_worth'],
                "transaction_count": summary['transaction_count'],
            })

        return status
