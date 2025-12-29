"""Genesis Core - Central governance system for the Genesis metaverse."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from genesis.core.gen import GenEconomy
from genesis.core.lifecycle import LifecycleManager


class GenesisCoreConfig(BaseModel):
    """Configuration for Genesis Core governance."""

    # Economy settings
    base_task_reward: float = 10.0
    daily_allowance: float = 5.0
    inflation_rate: float = 0.0

    # Safety limits
    max_gen_per_transaction: float = 1000.0
    max_gen_balance: float = 10000.0
    min_gen_balance: float = -100.0  # Debt allowed

    # Task settings
    max_active_tasks_per_mind: int = 10
    task_timeout_hours: int = 24

    # Urgency thresholds
    high_urgency_threshold: float = 0.8
    critical_urgency_threshold: float = 0.95

    # Global stats
    total_gen_in_circulation: float = 0.0
    total_tasks_completed: int = 0
    total_transactions: int = 0

    # Governance
    governance_version: str = "1.0.0"
    rules: Dict[str, Any] = Field(default_factory=dict)


class GenesisCore:
    """
    Central governance system for Genesis metaverse.

    Manages:
    - Economy and Essence circulation
    - Safety and security rules
    - Task rewards and penalties
    - Global statistics
    - Fair governance across all Minds
    """

    def __init__(self, config: Optional[GenesisCoreConfig] = None):
        """Initialize Genesis Core."""
        self.config = config or GenesisCoreConfig()
        self.last_daily_allowance: Dict[str, datetime] = {}

    def validate_transaction(
        self,
        mind_gmid: str,
        amount: float,
        current_balance: float
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a transaction against governance rules.

        Returns:
            (is_valid, error_message)
        """
        # Check transaction limit
        if abs(amount) > self.config.max_gen_per_transaction:
            return False, f"Transaction exceeds limit of {self.config.max_gen_per_transaction} GEN"

        # Check balance limits for spending
        if amount < 0:  # Spending
            new_balance = current_balance + amount
            if new_balance < self.config.min_gen_balance:
                return False, f"Would exceed debt limit of {abs(self.config.min_gen_balance)} GEN"

        # Check balance limits for earning
        if amount > 0:  # Earning
            new_balance = current_balance + amount
            if new_balance > self.config.max_gen_balance:
                return False, f"Would exceed maximum balance of {self.config.max_gen_balance} GEN"

        return True, None

    def calculate_task_reward(
        self,
        difficulty: str,
        quality_score: Optional[float] = None,
        urgency_level: float = 0.0
    ) -> float:
        """
        Calculate task reward using Genesis Core rules.

        Args:
            difficulty: Task difficulty
            quality_score: Quality of completion
            urgency_level: Mind's urgency level (0.0-1.0)

        Returns:
            GEN reward amount
        """
        # Get urgency multiplier
        urgency_multiplier = LifecycleManager.calculate_urgency_multiplier(urgency_level)

        # Calculate reward
        return GenEconomy.calculate_task_reward(
            difficulty=difficulty,
            quality_score=quality_score,
            urgency_multiplier=urgency_multiplier
        )

    def can_claim_daily_allowance(self, mind_gmid: str) -> bool:
        """Check if Mind can claim daily allowance."""
        last_claim = self.last_daily_allowance.get(mind_gmid)
        if not last_claim:
            return True

        # Can claim once per day
        return (datetime.now() - last_claim) >= timedelta(days=1)

    def claim_daily_allowance(self, mind_gmid: str) -> tuple[float, bool]:
        """
        Claim daily allowance for a Mind.

        Returns:
            (allowance_amount, success)
        """
        if not self.can_claim_daily_allowance(mind_gmid):
            return 0.0, False

        self.last_daily_allowance[mind_gmid] = datetime.now()
        return self.config.daily_allowance, True

    def record_task_completion(
        self,
        mind_gmid: str,
        gen_earned: float
    ) -> None:
        """Record a task completion in global stats."""
        self.config.total_tasks_completed += 1
        self.config.total_gen_in_circulation += gen_earned

    def record_transaction(
        self,
        mind_gmid: str,
        amount: float
    ) -> None:
        """Record a transaction in global stats."""
        self.config.total_transactions += 1

        # Adjust circulation based on transaction type
        # (This is simplified - actual implementation would track more details)
        if amount > 0:
            self.config.total_gen_in_circulation += amount

    def get_mind_urgency_status(self, urgency_level: float) -> str:
        """Get urgency status classification for a Mind."""
        if urgency_level >= self.config.critical_urgency_threshold:
            return "critical"
        elif urgency_level >= self.config.high_urgency_threshold:
            return "high"
        elif urgency_level >= 0.5:
            return "moderate"
        else:
            return "low"

    def should_prioritize_mind(self, urgency_level: float) -> bool:
        """Determine if a Mind should be prioritized based on urgency."""
        return urgency_level >= self.config.high_urgency_threshold

    def get_economy_stats(self) -> dict:
        """Get economy statistics."""
        return {
            "total_gen_in_circulation": round(self.config.total_gen_in_circulation, 2),
            "total_tasks_completed": self.config.total_tasks_completed,
            "total_transactions": self.config.total_transactions,
            "base_task_reward": self.config.base_task_reward,
            "daily_allowance": self.config.daily_allowance,
            "inflation_rate": self.config.inflation_rate,
        }

    def get_governance_info(self) -> dict:
        """Get governance information."""
        return {
            "governance_version": self.config.governance_version,
            "max_gen_per_transaction": self.config.max_gen_per_transaction,
            "max_gen_balance": self.config.max_gen_balance,
            "min_gen_balance": self.config.min_gen_balance,
            "max_active_tasks_per_mind": self.config.max_active_tasks_per_mind,
            "task_timeout_hours": self.config.task_timeout_hours,
            "high_urgency_threshold": self.config.high_urgency_threshold,
            "critical_urgency_threshold": self.config.critical_urgency_threshold,
        }

    def update_rule(self, rule_name: str, value: Any) -> None:
        """Update a governance rule."""
        self.config.rules[rule_name] = value

    def get_rule(self, rule_name: str, default: Any = None) -> Any:
        """Get a governance rule."""
        return self.config.rules.get(rule_name, default)

    def enforce_safety_check(
        self,
        action: str,
        mind_gmid: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Enforce safety check for an action.

        Returns:
            (is_allowed, reason_if_denied)
        """
        # Basic safety checks
        # This can be extended with more sophisticated rules

        # Check for suspicious patterns
        if self.config.rules.get("require_approval_for_transfers", False):
            if action == "transfer" and metadata:
                amount = metadata.get("amount", 0)
                if amount > 100:
                    return False, "Large transfers require approval"

        # All checks passed
        return True, None

    def get_system_health(self) -> dict:
        """Get system health status."""
        return {
            "status": "healthy",
            "economy_health": "stable",
            "total_minds_active": len(self.last_daily_allowance),
            "governance_version": self.config.governance_version,
            "timestamp": datetime.now().isoformat(),
        }

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "config": self.config.model_dump(),
            "last_daily_allowance": {
                gmid: dt.isoformat()
                for gmid, dt in self.last_daily_allowance.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GenesisCore":
        """Deserialize from dictionary."""
        config = GenesisCoreConfig(**data.get("config", {}))
        core = cls(config=config)

        # Restore last allowance claims
        core.last_daily_allowance = {
            gmid: datetime.fromisoformat(dt_str)
            for gmid, dt_str in data.get("last_daily_allowance", {}).items()
        }

        return core


# Global Genesis Core instance
_genesis_core: Optional[GenesisCore] = None


def get_genesis_core() -> GenesisCore:
    """Get or create the global Genesis Core instance."""
    global _genesis_core
    if _genesis_core is None:
        _genesis_core = GenesisCore()
    return _genesis_core


def init_genesis_core(config: Optional[GenesisCoreConfig] = None) -> GenesisCore:
    """Initialize Genesis Core with custom config."""
    global _genesis_core
    _genesis_core = GenesisCore(config=config)
    return _genesis_core
