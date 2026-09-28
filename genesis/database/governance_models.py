"""SQLAlchemy models for the governance control plane (ADR-0006/0007/0008).

Four tables:

* ``governance_events`` - append-only, hash-chained event journal.
* ``action_receipts`` - immutable record of every action attempt.
* ``approval_requests`` - the persistence layer of the approval state machine.
* ``permission_grants`` - single-use, parameter-bound, expiring authorizations.

These are deliberately *not* wired into ``MindRecord`` with ORM relationships:
the journal must be appendable even when the Mind row is gone (a retired mind's
history still has to be auditable), and receipts must not be deletable via a
cascade.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)

from genesis.database.base import Base


class GovernanceEventRecord(Base):
    """Append-only journal entry. Never updated in place after insert."""

    __tablename__ = "governance_events"

    event_id = Column(String(64), primary_key=True)
    stream_key = Column(String(200), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    type = Column(String(64), nullable=False, index=True)
    schema_version = Column(Integer, nullable=False, default=1)
    timestamp = Column(DateTime, nullable=False, index=True)

    tenant_id = Column(String(100), nullable=True, index=True)
    mind_id = Column(String(50), nullable=True, index=True)
    actor_type = Column(String(32), nullable=False, default="system")
    actor_id = Column(String(200), nullable=False, default="")
    correlation_id = Column(String(64), nullable=False, default="", index=True)
    causation_id = Column(String(64), nullable=True)

    payload = Column(JSON, nullable=False, default=dict)
    payload_hash = Column(String(64), nullable=False, default="")
    prev_hash = Column(String(64), nullable=False, default="")
    integrity_hash = Column(String(64), nullable=False, default="")

    __table_args__ = (
        Index("ix_gov_events_stream_seq", "stream_key", "sequence", unique=True),
        Index("ix_gov_events_mind_ts", "mind_id", "timestamp"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<GovernanceEvent {self.type} seq={self.sequence}>"


class ActionReceiptRecord(Base):
    """Immutable receipt for one action attempt (allowed, blocked, or failed)."""

    __tablename__ = "action_receipts"

    receipt_id = Column(String(64), primary_key=True)
    action_id = Column(String(64), nullable=False, index=True)
    action_name = Column(String(120), nullable=False, index=True)
    mind_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=True, index=True)
    objective_id = Column(String(64), nullable=True, index=True)

    outcome = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
    requested_by = Column(String(200), nullable=False, default="")
    actor_type = Column(String(32), nullable=False, default="mind")

    intent = Column(Text, nullable=False, default="")
    selected_skill = Column(String(120), nullable=True)
    arguments = Column(JSON, nullable=False, default=dict)
    arguments_hash = Column(String(64), nullable=False, default="")

    risk_level = Column(String(4), nullable=False, default="")
    policy_decision = Column(JSON, nullable=False, default=dict)
    matched_rules = Column(JSON, nullable=False, default=list)

    approval_id = Column(String(64), nullable=True, index=True)
    approver_id = Column(String(200), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)

    affected_resources = Column(JSON, nullable=False, default=list)
    artifacts = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=dict)

    model_invocations = Column(Integer, nullable=False, default=0)
    cost_essence = Column(Integer, nullable=False, default=0)

    error_class = Column(String(120), nullable=True)
    error_message = Column(Text, nullable=True)
    rollback = Column(JSON, nullable=True)

    correlation_id = Column(String(64), nullable=False, default="", index=True)
    payload_hash = Column(String(64), nullable=False, default="")
    prev_hash = Column(String(64), nullable=False, default="")
    integrity_hash = Column(String(64), nullable=False, default="")
    sequence = Column(Integer, nullable=False, default=0)
    schema_version = Column(Integer, nullable=False, default=1)

    __table_args__ = (Index("ix_receipts_mind_created", "mind_id", "created_at"),)


class ApprovalRequestRecord(Base):
    """Persistent approval state machine (ADR-0007)."""

    __tablename__ = "approval_requests"

    approval_id = Column(String(64), primary_key=True)
    action_id = Column(String(64), nullable=False, index=True)
    action_name = Column(String(120), nullable=False, index=True)
    mind_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=True, index=True)
    objective_id = Column(String(64), nullable=True, index=True)

    status = Column(String(32), nullable=False, index=True)
    risk_level = Column(String(4), nullable=False, default="R3")
    requested_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    resolved_at = Column(DateTime, nullable=True)

    parameters = Column(JSON, nullable=False, default=dict)
    parameters_hash = Column(String(64), nullable=False, default="")

    summary = Column(Text, nullable=False, default="")
    reason = Column(Text, nullable=False, default="")
    expected_impact = Column(Text, nullable=False, default="")
    data_accessed = Column(JSON, nullable=False, default=list)
    recipient = Column(String(300), nullable=True)
    financial_cost_essence = Column(Integer, nullable=False, default=0)
    reversibility = Column(String(32), nullable=False, default="unknown")
    requested_duration = Column(String(64), nullable=False, default="one-off")
    scope = Column(Text, nullable=False, default="")
    proposed_rollback = Column(Text, nullable=False, default="")
    evidence = Column(JSON, nullable=False, default=dict)

    policy_decision = Column(JSON, nullable=False, default=dict)
    matched_rules = Column(JSON, nullable=False, default=list)
    policy_version = Column(String(64), nullable=False, default="")
    requires_human = Column(Boolean, nullable=False, default=False)
    approver_role = Column(String(64), nullable=True)

    requested_by = Column(String(200), nullable=False, default="")
    actor_type = Column(String(32), nullable=False, default="mind")
    approver_id = Column(String(200), nullable=True)
    resolution_note = Column(Text, nullable=True)
    correlation_id = Column(String(64), nullable=False, default="", index=True)
    transition_log = Column(JSON, nullable=False, default=list)


class PermissionGrantRecord(Base):
    """Single-use, parameter-bound, expiring authorization (ADR-0007)."""

    __tablename__ = "permission_grants"

    grant_id = Column(String(64), primary_key=True)
    approval_id = Column(String(64), nullable=False, index=True)
    mind_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=True, index=True)
    objective_id = Column(String(64), nullable=True)
    action_name = Column(String(120), nullable=False, index=True)
    parameters_hash = Column(String(64), nullable=False, index=True)
    scope = Column(Text, nullable=False, default="")

    issued_by = Column(String(200), nullable=False, default="")
    issued_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)

    single_use = Column(Boolean, nullable=False, default=True)
    max_uses = Column(Integer, nullable=False, default=1)
    consumed_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(200), nullable=True)

    __table_args__ = (Index("ix_grants_mind_action", "mind_id", "action_name"),)
