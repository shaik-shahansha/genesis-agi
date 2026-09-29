"""Governance domain models (pure dataclasses, no ORM, no I/O).

Keeping these separate from :mod:`genesis.governance.store` avoids an import
cycle: the store persists these shapes, the services produce them, and the
policy engine reasons about them.

Everything here is JSON-serializable via ``to_dict()`` so the same shapes serve
the API layer, the audit journal, and the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, FrozenSet, Optional, Tuple

__all__ = [
    "EVENT_SCHEMA_VERSION",
    "GENESIS_EPOCH_HASH",
    "ActorType",
    "EventType",
    "ApprovalStatus",
    "ReceiptOutcome",
    "AuditEvent",
    "ActionReceipt",
    "ApprovalRequest",
    "PermissionGrant",
    "APPROVAL_TRANSITIONS",
    "utcnow",
]

#: Bumped when the event payload shape changes. Readers tolerate older versions
#: (ADR-0008 risk "Schema drift across versions").
EVENT_SCHEMA_VERSION = 1

#: Sentinel ``prev_hash`` for the first event in a stream.
GENESIS_EPOCH_HASH = "0" * 64


def utcnow() -> datetime:
    """Timezone-aware UTC now. All governance timestamps use this."""
    return datetime.now(timezone.utc)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


class ActorType(str, Enum):
    """Who caused an event."""

    USER = "user"
    MIND = "mind"
    SYSTEM = "system"
    PLUGIN = "plugin"
    SCHEDULER = "scheduler"
    APPROVER = "approver"
    OPERATOR = "operator"


class EventType:
    """Event families from ADR-0008 §1.

    Plain strings (not an Enum) so new event types are additive and a reader
    never fails on an unknown value.
    """

    MIND_BORN = "mind.born"
    MIND_STATE_CHANGED = "mind.state_changed"

    CONSTITUTION_RULE_APPLIED = "constitution.rule_applied"
    CONSTITUTION_VIOLATION = "constitution.violation"

    # Domain write paths (plan item D2). Recorded through
    # `governance/domain_events.py`, which carries identity and metadata but
    # never content — see that module for why.
    MEMORY_ACCEPTED = "memory.accepted"
    MEMORY_FORGOTTEN = "memory.forgotten"
    MEMORY_CONSOLIDATED = "memory.consolidated"

    RELATIONSHIP_CREATED = "relationship.created"
    RELATIONSHIP_INTERACTION = "relationship.interaction"

    GOAL_CREATED = "goal.created"
    GOAL_PROGRESS = "goal.progress"
    GOAL_COMPLETED = "goal.completed"
    GOAL_ABANDONED = "goal.abandoned"

    # Digital life state (Phase N). A commitment is an obligation, so its events
    # are the record of what the being promised and whether it kept it.
    COMMITMENT_CREATED = "commitment.created"
    COMMITMENT_UPDATED = "commitment.updated"
    COMMITMENT_FULFILLED = "commitment.fulfilled"
    COMMITMENT_MISSED = "commitment.missed"
    COMMITMENT_RENEGOTIATED = "commitment.renegotiated"
    COMMITMENT_WITHDRAWN = "commitment.withdrawn"

    ACTION_PROPOSED = "action.proposed"
    ACTION_POLICY_EVALUATED = "action.policy_evaluated"
    ACTION_APPROVAL_REQUESTED = "action.approval_requested"
    ACTION_APPROVED = "action.approved"
    ACTION_REJECTED = "action.rejected"
    ACTION_EXPIRED = "action.expired"
    ACTION_EXECUTING = "action.executing"
    ACTION_EXECUTED = "action.executed"
    ACTION_FAILED = "action.failed"
    ACTION_ROLLED_BACK = "action.rolled_back"
    ACTION_BLOCKED = "action.blocked"
    ACTION_EMERGENCY_STOP = "action.emergency_stop"
    EMERGENCY_STOP_RELEASED = "emergency_stop.released"

    # Channels: the Mind's own digital presence (docs/v3/DIGITAL_PRESENCE.md).
    #
    # A separate family rather than reusing `action.*`, because the question an
    # operator asks is "what did this being say to people?" — and answering that
    # should be a query over one prefix, not a filter over action events hoping the
    # channel ones were labelled consistently.
    #
    # Note what these carry: channel, direction, decision, approval id, and the
    # contact's *relationship* id. Not the body. `record` redacts the payload in the
    # writer, so message content does not reach the journal by this path.
    CHANNEL_INBOUND_RECEIVED = "channel.inbound_received"
    CHANNEL_REPLY_SENT = "channel.reply_sent"
    CHANNEL_REPLY_REFUSED = "channel.reply_refused"
    CHANNEL_REPLY_NOT_SENT = "channel.reply_not_sent"
    CHANNEL_CLAIM_ABANDONED = "channel.claim_abandoned"

    GRANT_ISSUED = "grant.issued"
    GRANT_REDEEMED = "grant.redeemed"
    GRANT_REVOKED = "grant.revoked"

    RECEIPT_RECORDED = "receipt.recorded"

    JOURNAL_VERIFIED = "journal.verified"
    JOURNAL_TAMPERED = "journal.tampered"

    ALL_PREFIXES = (
        "mind.",
        "identity.",
        "constitution.",
        "relationship.",
        "goal.",
        "commitment.",
        "experience.",
        "memory.",
        "skill.",
        "action.",
        "channel.",
        "grant.",
        "receipt.",
        "journal.",
        "embodiment.",
    )

    @classmethod
    def is_known_prefix(cls, event_type: str) -> bool:
        return any(str(event_type).startswith(prefix) for prefix in cls.ALL_PREFIXES)


class ApprovalStatus(str, Enum):
    """Approval state machine (ADR-0007)."""

    PROPOSED = "PROPOSED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"

    @property
    def is_terminal(self) -> bool:
        return self in (
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.COMPLETED,
            ApprovalStatus.FAILED,
            ApprovalStatus.ROLLED_BACK,
        )

    @property
    def is_pending(self) -> bool:
        return self in (ApprovalStatus.WAITING_FOR_APPROVAL,)


#: Legal transitions. Anything not listed here is refused, which makes the
#: state machine a *control* rather than a convention.
APPROVAL_TRANSITIONS: Dict[ApprovalStatus, FrozenSet[ApprovalStatus]] = {
    ApprovalStatus.PROPOSED: frozenset(
        {ApprovalStatus.POLICY_EVALUATED, ApprovalStatus.CANCELLED}
    ),
    ApprovalStatus.POLICY_EVALUATED: frozenset(
        {
            ApprovalStatus.WAITING_FOR_APPROVAL,
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
        }
    ),
    ApprovalStatus.WAITING_FOR_APPROVAL: frozenset(
        {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
            ApprovalStatus.CANCELLED,
        }
    ),
    ApprovalStatus.APPROVED: frozenset(
        {
            ApprovalStatus.EXECUTING,
            ApprovalStatus.EXPIRED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.FAILED,
        }
    ),
    ApprovalStatus.EXECUTING: frozenset(
        {
            ApprovalStatus.COMPLETED,
            ApprovalStatus.FAILED,
            ApprovalStatus.ROLLED_BACK,
        }
    ),
    ApprovalStatus.COMPLETED: frozenset({ApprovalStatus.ROLLED_BACK}),
    ApprovalStatus.FAILED: frozenset({ApprovalStatus.ROLLED_BACK}),
    ApprovalStatus.REJECTED: frozenset(),
    ApprovalStatus.EXPIRED: frozenset(),
    ApprovalStatus.CANCELLED: frozenset(),
    ApprovalStatus.ROLLED_BACK: frozenset(),
}


def can_transition(current: ApprovalStatus, target: ApprovalStatus) -> bool:
    """Whether the state machine permits ``current -> target``."""
    return ApprovalStatus(target) in APPROVAL_TRANSITIONS.get(ApprovalStatus(current), frozenset())


class ReceiptOutcome(str, Enum):
    """Outcome recorded on an :class:`ActionReceipt`."""

    ALLOWED = "allowed"
    EXECUTED = "executed"
    BLOCKED = "blocked"
    DENIED = "denied"
    REQUIRES_APPROVAL = "requires_approval"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"
    EMERGENCY_STOP = "emergency_stop"

    @property
    def is_success(self) -> bool:
        return self in (ReceiptOutcome.ALLOWED, ReceiptOutcome.EXECUTED)


@dataclass
class AuditEvent:
    """One append-only journal entry (already redacted)."""

    event_id: str
    type: str
    timestamp: datetime
    mind_id: str
    actor_type: str = ActorType.SYSTEM.value
    actor_id: str = ""
    tenant_id: Optional[str] = None
    correlation_id: str = ""
    causation_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    payload_hash: str = ""
    prev_hash: str = GENESIS_EPOCH_HASH
    integrity_hash: str = ""
    sequence: int = 0
    schema_version: int = EVENT_SCHEMA_VERSION

    @property
    def stream_key(self) -> str:
        """Hash chains are per (tenant, mind) stream."""
        return f"{self.tenant_id or '-'}:{self.mind_id or '-'}"

    def hashable_body(self) -> Dict[str, Any]:
        """The fields covered by ``integrity_hash`` (excludes the hash itself)."""
        return {
            "event_id": self.event_id,
            "type": self.type,
            "schema_version": self.schema_version,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "mind_id": self.mind_id,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "sequence": self.sequence,
            "prev_hash": self.prev_hash,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.hashable_body(),
            "integrity_hash": self.integrity_hash,
            "stream_key": self.stream_key,
        }


@dataclass
class ActionReceipt:
    """Immutable record of one action attempt (ADR-0008 §2).

    A receipt exists for allowed, blocked, failed, cancelled, and rolled-back
    attempts alike - the blocked ones are the highest-interest records.
    """

    receipt_id: str
    action_id: str
    action_name: str
    mind_id: str
    outcome: str
    created_at: datetime
    tenant_id: Optional[str] = None
    objective_id: Optional[str] = None
    requested_by: str = ""
    actor_type: str = ActorType.MIND.value
    intent: str = ""
    selected_skill: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)  # redacted
    arguments_hash: str = ""
    risk_level: str = ""
    policy_decision: Dict[str, Any] = field(default_factory=dict)
    matched_rules: Tuple[str, ...] = ()
    approval_id: Optional[str] = None
    approver_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    affected_resources: Tuple[str, ...] = ()
    artifacts: Tuple[Dict[str, Any], ...] = ()
    evidence: Dict[str, Any] = field(default_factory=dict)
    model_invocations: int = 0
    cost_essence: int = 0
    error_class: Optional[str] = None
    error_message: Optional[str] = None
    rollback: Optional[Dict[str, Any]] = None
    correlation_id: str = ""
    payload_hash: str = ""
    prev_hash: str = GENESIS_EPOCH_HASH
    integrity_hash: str = ""
    sequence: int = 0
    schema_version: int = EVENT_SCHEMA_VERSION

    @property
    def success(self) -> bool:
        return ReceiptOutcome(self.outcome).is_success

    @property
    def stream_key(self) -> str:
        return f"{self.tenant_id or '-'}:{self.mind_id or '-'}"

    def hashable_body(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "action_id": self.action_id,
            "action_name": self.action_name,
            "mind_id": self.mind_id,
            "tenant_id": self.tenant_id,
            "objective_id": self.objective_id,
            "outcome": self.outcome,
            "created_at": self.created_at.isoformat(),
            "requested_by": self.requested_by,
            "actor_type": self.actor_type,
            "intent": self.intent,
            "selected_skill": self.selected_skill,
            "arguments": self.arguments,
            "arguments_hash": self.arguments_hash,
            "risk_level": self.risk_level,
            "policy_decision": self.policy_decision,
            "matched_rules": list(self.matched_rules),
            "approval_id": self.approval_id,
            "approver_id": self.approver_id,
            "approved_at": _iso(self.approved_at),
            "started_at": _iso(self.started_at),
            "completed_at": _iso(self.completed_at),
            "duration_ms": self.duration_ms,
            "affected_resources": list(self.affected_resources),
            "artifacts": [dict(item) for item in self.artifacts],
            "evidence": self.evidence,
            "model_invocations": self.model_invocations,
            "cost_essence": self.cost_essence,
            "error_class": self.error_class,
            "error_message": self.error_message,
            "rollback": self.rollback,
            "correlation_id": self.correlation_id,
            "sequence": self.sequence,
            "prev_hash": self.prev_hash,
            "payload_hash": self.payload_hash,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {**self.hashable_body(), "integrity_hash": self.integrity_hash}


@dataclass
class ApprovalRequest:
    """A human decision that is pending, resolved, or expired (ADR-0007).

    Fields are grouped the way the UI needs them: *what needs approval, why,
    what it costs, and what can be reversed*.
    """

    approval_id: str
    action_id: str
    action_name: str
    mind_id: str
    status: str
    requested_at: datetime
    risk_level: str
    parameters: Dict[str, Any] = field(default_factory=dict)  # redacted
    parameters_hash: str = ""
    tenant_id: Optional[str] = None
    objective_id: Optional[str] = None
    # Plain-language block (non-engineer readable)
    summary: str = ""
    reason: str = ""
    expected_impact: str = ""
    data_accessed: Tuple[str, ...] = ()
    recipient: Optional[str] = None
    financial_cost_essence: int = 0
    reversibility: str = "unknown"
    requested_duration: str = "one-off"
    scope: str = ""
    proposed_rollback: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    # Policy provenance
    policy_decision: Dict[str, Any] = field(default_factory=dict)
    matched_rules: Tuple[str, ...] = ()
    policy_version: str = ""
    requires_human: bool = False
    approver_role: Optional[str] = None
    # People
    requested_by: str = ""
    actor_type: str = ActorType.MIND.value
    approver_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    # Durability
    expires_at: Optional[datetime] = None
    correlation_id: str = ""
    transition_log: Tuple[Dict[str, Any], ...] = ()

    @property
    def status_enum(self) -> ApprovalStatus:
        return ApprovalStatus(self.status)

    @property
    def is_pending(self) -> bool:
        return self.status_enum.is_pending

    @property
    def is_expired(self) -> bool:
        return self.status_enum is ApprovalStatus.EXPIRED

    @property
    def is_terminal(self) -> bool:
        """No further transition is possible from here."""
        return self.status_enum.is_terminal

    def expired_at(self, now: datetime) -> bool:
        return bool(self.expires_at and now >= self.expires_at)

    def plain_language_card(self) -> Dict[str, Any]:
        """The approval-inbox card. Explicitly human-facing."""
        return {
            "approval_id": self.approval_id,
            "status": self.status,
            "action": self.summary or self.action_name,
            "why": self.reason,
            "risk_level": self.risk_level,
            "expected_impact": self.expected_impact,
            "data_accessed": list(self.data_accessed),
            "recipient": self.recipient,
            "cost_essence": self.financial_cost_essence,
            "reversibility": self.reversibility,
            "rollback": self.proposed_rollback,
            "scope": self.scope,
            "duration": self.requested_duration,
            "expires_at": _iso(self.expires_at),
            "requires_human": self.requires_human,
            "approver_role": self.approver_role,
            "requested_by": self.requested_by,
            "requested_at": _iso(self.requested_at),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "action_id": self.action_id,
            "action_name": self.action_name,
            "mind_id": self.mind_id,
            "tenant_id": self.tenant_id,
            "objective_id": self.objective_id,
            "status": self.status,
            "risk_level": self.risk_level,
            "parameters": self.parameters,
            "parameters_hash": self.parameters_hash,
            "summary": self.summary,
            "reason": self.reason,
            "expected_impact": self.expected_impact,
            "data_accessed": list(self.data_accessed),
            "recipient": self.recipient,
            "financial_cost_essence": self.financial_cost_essence,
            "reversibility": self.reversibility,
            "requested_duration": self.requested_duration,
            "scope": self.scope,
            "proposed_rollback": self.proposed_rollback,
            "evidence": self.evidence,
            "policy_decision": self.policy_decision,
            "matched_rules": list(self.matched_rules),
            "policy_version": self.policy_version,
            "requires_human": self.requires_human,
            "approver_role": self.approver_role,
            "requested_by": self.requested_by,
            "actor_type": self.actor_type,
            "approver_id": self.approver_id,
            "resolved_at": _iso(self.resolved_at),
            "resolution_note": self.resolution_note,
            "expires_at": _iso(self.expires_at),
            "correlation_id": self.correlation_id,
            "transition_log": [dict(item) for item in self.transition_log],
        }


@dataclass
class PermissionGrant:
    """Single-use, parameter-bound, expiring authorization (ADR-0007 §Binding rules).

    ``parameters_hash`` binds the grant to the *exact* material parameters. If
    the Mind changes anything material, redemption fails and the action returns
    to the approval queue.
    """

    grant_id: str
    approval_id: str
    mind_id: str
    action_name: str
    parameters_hash: str
    issued_at: datetime
    expires_at: Optional[datetime]
    issued_by: str = ""
    tenant_id: Optional[str] = None
    scope: str = ""
    objective_id: Optional[str] = None
    single_use: bool = True
    consumed_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    max_uses: int = 1

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return bool(self.expires_at and now >= self.expires_at)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "approval_id": self.approval_id,
            "mind_id": self.mind_id,
            "tenant_id": self.tenant_id,
            "action_name": self.action_name,
            "parameters_hash": self.parameters_hash,
            "scope": self.scope,
            "objective_id": self.objective_id,
            "issued_by": self.issued_by,
            "issued_at": _iso(self.issued_at),
            "expires_at": _iso(self.expires_at),
            "single_use": self.single_use,
            "max_uses": self.max_uses,
            "consumed_at": _iso(self.consumed_at),
            "revoked_at": _iso(self.revoked_at),
            "revoked_by": self.revoked_by,
        }
