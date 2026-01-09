"""GEN economy system for Genesis - the currency that motivates Minds."""

import secrets
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    """Types of GEN transactions."""

    EARNED = "earned"  # Earned from task completion
    SPENT = "spent"  # Spent on services/resources
    TRANSFER = "transfer"  # Transferred to another Mind
    BONUS = "bonus"  # Bonus reward
    PENALTY = "penalty"  # Penalty for failed tasks
    ALLOWANCE = "allowance"  # Daily allowance
    GIFT = "gift"  # Gift from another entity


class GenBalance(BaseModel):
    """Current GEN balance and stats for a Mind."""

    current_balance: float = 100.0  # Starting balance
    total_earned: float = 100.0  # Includes starting balance
    total_spent: float = 0.0
    total_transferred_out: float = 0.0
    total_transferred_in: float = 0.0

    # Limits
    max_balance: float = 10000.0
    min_balance: float = -100.0  # Can go into debt

    def can_spend(self, amount: float) -> bool:
        """Check if Mind has enough GEN to spend."""
        return (self.current_balance - amount) >= self.min_balance

    def add_gen(self, amount: float, transaction_type: TransactionType) -> float:
        """Add GEN and update totals."""
        self.current_balance += amount

        if transaction_type == TransactionType.EARNED:
            self.total_earned += amount
        elif transaction_type == TransactionType.TRANSFER:
            self.total_transferred_in += amount
        elif transaction_type == TransactionType.BONUS:
            self.total_earned += amount
        elif transaction_type == TransactionType.ALLOWANCE:
            self.total_earned += amount
        elif transaction_type == TransactionType.GIFT:
            self.total_earned += amount

        # Enforce max balance
        if self.current_balance > self.max_balance:
            self.current_balance = self.max_balance

        return self.current_balance

    def subtract_gen(self, amount: float, transaction_type: TransactionType) -> float:
        """Subtract GEN and update totals."""
        if not self.can_spend(amount):
            raise ValueError(f"Insufficient GEN. Need {amount}, have {self.current_balance}")

        self.current_balance -= amount

        if transaction_type == TransactionType.SPENT:
            self.total_spent += amount
        elif transaction_type == TransactionType.TRANSFER:
            self.total_transferred_out += amount
        elif transaction_type == TransactionType.PENALTY:
            self.total_spent += amount

        return self.current_balance

    def get_net_worth(self) -> float:
        """Calculate net worth (earned - spent)."""
        return self.total_earned - self.total_spent

    def is_in_debt(self) -> bool:
        """Check if Mind is in debt."""
        return self.current_balance < 0


class GenTransaction(BaseModel):
    """Record of a single GEN transaction."""

    transaction_id: str = Field(default_factory=lambda: f"TXN-{secrets.token_hex(8).upper()}")
    mind_gmid: str
    counterparty_gmid: Optional[str] = None

    transaction_type: TransactionType
    amount: float
    balance_after: float

    reason: str
    related_task_id: Optional[str] = None
    related_entity: Optional[str] = None

    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class GenEconomy:
    """
    Central GEN economy manager.

    Handles all GEN transactions, rewards, and economic rules.
    """

    # Base rewards by task difficulty
    TASK_REWARDS = {
        "easy": 5.0,
        "medium": 10.0,
        "hard": 20.0,
        "expert": 50.0,
    }

    # Bonus multipliers for quality
    QUALITY_BONUS = {
        "poor": 0.5,
        "acceptable": 1.0,
        "good": 1.2,
        "excellent": 1.5,
        "exceptional": 2.0,
    }

    # Common service costs
    SERVICE_COSTS = {
        "file_storage_mb": 0.1,  # Per MB per day
        "environment_private": 50.0,  # Create private environment
        "relationship_boost": 10.0,  # Boost a relationship
        "memory_backup": 5.0,  # Backup memories
        "dream_trigger": 2.0,  # Trigger a dream
        "extend_life_year": 1000.0,  # Extend life by 1 year (expensive!)
    }

    @staticmethod
    def calculate_task_reward(
        difficulty: str,
        quality_score: Optional[float] = None,
        urgency_multiplier: float = 1.0
    ) -> float:
        """
        Calculate GEN reward for a task.

        Args:
            difficulty: Task difficulty (easy, medium, hard, expert)
            quality_score: Quality of completion (0.0-1.0)
            urgency_multiplier: Urgency multiplier from lifecycle

        Returns:
            GEN amount to award
        """
        base_reward = GenEconomy.TASK_REWARDS.get(difficulty, 10.0)

        # Apply quality bonus
        if quality_score is not None:
            if quality_score < 0.5:
                quality_mult = 0.5
            elif quality_score < 0.7:
                quality_mult = 1.0
            elif quality_score < 0.85:
                quality_mult = 1.2
            elif quality_score < 0.95:
                quality_mult = 1.5
            else:
                quality_mult = 2.0

            base_reward *= quality_mult

        # Apply urgency multiplier
        base_reward *= urgency_multiplier

        return round(base_reward, 2)

    @staticmethod
    def create_transaction(
        mind_gmid: str,
        transaction_type: TransactionType,
        amount: float,
        balance_after: float,
        reason: str,
        counterparty_gmid: Optional[str] = None,
        related_task_id: Optional[str] = None,
        related_entity: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> GenTransaction:
        """Create a transaction record."""
        return GenTransaction(
            mind_gmid=mind_gmid,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=balance_after,
            reason=reason,
            counterparty_gmid=counterparty_gmid,
            related_task_id=related_task_id,
            related_entity=related_entity,
            metadata=metadata or {}
        )

    @staticmethod
    def validate_transaction(
        balance: GenBalance,
        amount: float,
        transaction_type: TransactionType,
        max_per_transaction: float = 1000.0
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a transaction before execution.

        Returns:
            (is_valid, error_message)
        """
        # Check transaction amount limit
        if abs(amount) > max_per_transaction:
            return False, f"Transaction amount {amount} exceeds limit {max_per_transaction}"

        # Check if spending
        if transaction_type in [TransactionType.SPENT, TransactionType.TRANSFER, TransactionType.PENALTY]:
            if not balance.can_spend(amount):
                return False, f"Insufficient GEN. Need {amount}, have {balance.current_balance}"

        # Check for negative amounts
        if amount < 0:
            return False, "Amount cannot be negative"

        return True, None


class GenManager:
    """
    Manager for a single Mind's GEN operations.

    Handles balance, transactions, earning, and spending.
    Now stores transactions in SQLite database for scalability.
    """

    def __init__(self, mind_gmid: str, initial_balance: float = 100.0):
        """Initialize GEN manager for a Mind."""
        self.mind_gmid = mind_gmid
        self.balance = GenBalance(current_balance=initial_balance)
        # Load balance from database
        self._load_balance_from_db()

    def _load_balance_from_db(self) -> None:
        """Load current balance from MindRecord in database."""
        try:
            from genesis.database.base import get_session
            from genesis.database.models import MindRecord
            
            with get_session() as session:
                mind_record = session.query(MindRecord).filter_by(gmid=self.mind_gmid).first()
                if mind_record:
                    # Extract values while session is still active
                    self.balance.current_balance = float(mind_record.gen_balance)
                    self.balance.total_earned = float(mind_record.total_gen_earned)
                    self.balance.total_spent = float(mind_record.total_gen_spent)
        except Exception as e:
            print(f"[GEN] Could not load balance from DB: {e}")

    def _save_balance_to_db(self) -> None:
        """Save current balance to MindRecord in database."""
        try:
            from genesis.database.manager import MetaverseDB
            db = MetaverseDB()
            db.update_mind_gen_balance(
                self.mind_gmid,
                gen_balance=self.balance.current_balance,
                total_earned=self.balance.total_earned,
                total_spent=self.balance.total_spent
            )
        except Exception as e:
            print(f"[GEN] Could not save balance to DB: {e}")

    def _save_transaction_to_db(self, transaction: 'GenTransaction') -> None:
        """Save transaction to database."""
        try:
            # Ensure mind is registered in database before saving transaction
            from genesis.database.manager import MetaverseDB
            metaverse_db = MetaverseDB()
            
            # Check if mind exists, register if not
            existing_mind = metaverse_db.get_mind(self.mind_gmid)
            if not existing_mind:
                print(f"[GEN] Mind {self.mind_gmid} not found in database, registering...")
                try:
                    # Extract a safe name from GMID
                    name_parts = self.mind_gmid.split('-')
                    safe_name = f"Mind-{name_parts[-1]}" if len(name_parts) > 1 else f"Mind-{self.mind_gmid[:8]}"
                    
                    # Ensure name is not too long and contains only safe characters
                    safe_name = safe_name[:50]  # Limit length
                    safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '-_ ').strip()
                    if not safe_name:
                        safe_name = f"Mind-{self.mind_gmid[:8]}"
                    
                    metaverse_db.register_mind(
                        gmid=self.mind_gmid,
                        name=safe_name,
                        creator="system",
                        template="unknown",
                    )
                    print(f"[GEN] Mind {self.mind_gmid} registered successfully as '{safe_name}'")
                except Exception as reg_error:
                    print(f"[GEN] Failed to register mind {self.mind_gmid}: {reg_error}")
                    print(f"[GEN] Registration error details: {type(reg_error).__name__}")
                    import traceback
                    traceback.print_exc()
                    return  # Don't save transaction if mind registration fails
            
            from genesis.database.models import GenTransaction as DBGenTransaction
            from genesis.database.base import get_session
            
            db_txn = DBGenTransaction(
                transaction_id=transaction.transaction_id,
                mind_gmid=self.mind_gmid,
                counterparty_gmid=transaction.counterparty_gmid,
                transaction_type=transaction.transaction_type.value,
                amount=transaction.amount,
                balance_after=transaction.balance_after,
                reason=transaction.reason,
                related_task_id=transaction.related_task_id,
                related_entity=transaction.related_entity,
                timestamp=transaction.timestamp,
                extra_metadata=transaction.metadata
            )
            
            with get_session() as session:
                session.add(db_txn)
                session.commit()
        except Exception as e:
            print(f"[GEN] Could not save transaction to DB: {e}")
            import traceback
            traceback.print_exc()

    def earn(
        self,
        amount: float,
        reason: str,
        transaction_type: TransactionType = TransactionType.EARNED,
        **kwargs
    ) -> GenTransaction:
        """Earn GEN."""
        new_balance = self.balance.add_gen(amount, transaction_type)

        transaction = GenEconomy.create_transaction(
            mind_gmid=self.mind_gmid,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            **kwargs
        )

        # Save to database immediately
        self._save_transaction_to_db(transaction)
        self._save_balance_to_db()
        
        return transaction

    def spend(
        self,
        amount: float,
        reason: str,
        transaction_type: TransactionType = TransactionType.SPENT,
        **kwargs
    ) -> GenTransaction:
        """Spend GEN."""
        # Validate
        is_valid, error = GenEconomy.validate_transaction(
            self.balance, amount, transaction_type
        )
        if not is_valid:
            raise ValueError(error)

        new_balance = self.balance.subtract_gen(amount, transaction_type)

        transaction = GenEconomy.create_transaction(
            mind_gmid=self.mind_gmid,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            **kwargs
        )

        # Save to database immediately
        self._save_transaction_to_db(transaction)
        self._save_balance_to_db()
        
        return transaction

    def transfer(
        self,
        to_gmid: str,
        amount: float,
        reason: str
    ) -> GenTransaction:
        """Transfer GEN to another Mind."""
        return self.spend(
            amount=amount,
            reason=reason,
            transaction_type=TransactionType.TRANSFER,
            counterparty_gmid=to_gmid,
            related_entity=to_gmid
        )

    def get_balance_summary(self) -> dict:
        """Get complete balance summary."""
        # Get transaction count from database
        transaction_count = 0
        try:
            from genesis.database.manager import MetaverseDB
            from genesis.database.base import get_session
            from genesis.database.models import GenTransaction
            
            with get_session() as session:
                transaction_count = session.query(GenTransaction).filter_by(mind_gmid=self.mind_gmid).count()
        except Exception as e:
            print(f"[GEN] Could not get transaction count: {e}")
        
        return {
            "current_balance": round(self.balance.current_balance, 2),
            "total_earned": round(self.balance.total_earned, 2),
            "total_spent": round(self.balance.total_spent, 2),
            "net_worth": round(self.balance.get_net_worth(), 2),
            "is_in_debt": self.balance.is_in_debt(),
            "transaction_count": transaction_count,
        }

    def get_recent_transactions(self, limit: int = 10) -> list[dict]:
        """Get recent transactions from database."""
        try:
            from genesis.database.base import get_session
            from genesis.database.models import GenTransaction
            from sqlalchemy import desc
            
            with get_session() as session:
                transactions = (
                    session.query(GenTransaction)
                    .filter_by(mind_gmid=self.mind_gmid)
                    .order_by(desc(GenTransaction.timestamp))
                    .limit(limit)
                    .all()
                )
                # Extract values while session is active
                return [
                    {
                        "id": txn.transaction_id,
                        "type": txn.transaction_type,
                        "amount": float(txn.amount),
                        "balance_after": float(txn.balance_after),
                        "reason": txn.reason,
                        "timestamp": txn.timestamp.isoformat(),
                    }
                    for txn in transactions
                ]
        except Exception as e:
            print(f"[GEN] Could not load transactions: {e}")
            return []

    def to_dict(self) -> dict:
        """Serialize to dictionary (balance only - transactions in DB)."""
        return {
            "mind_gmid": self.mind_gmid,
            "balance": self.balance.model_dump(mode='json'),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GenManager":
        """Deserialize from dictionary."""
        manager = cls(mind_gmid=data["mind_gmid"])
        manager.balance = GenBalance(**data["balance"])
        return manager
