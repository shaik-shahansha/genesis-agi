"""Action receipt construction (ADR-0008 §2).

A receipt is produced for **every** action attempt - allowed, blocked, failed,
cancelled, or rolled back. The blocked ones matter most, so the builder has no
"skip" path: if an action was considered, it gets a receipt.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from genesis.governance.audit import new_correlation_id, new_id
from genesis.governance.models import (
    ActionReceipt,
    ActorType,
    ReceiptOutcome,
    utcnow,
)
from genesis.governance.policy import Decision, PolicyDecision
from genesis.governance.redact import stable_hash

__all__ = [
    "build_receipt",
    "classify_error",
    "outcome_for_decision",
    "ERROR_CLASSES",
]

#: Stable error taxonomy so receipts are groupable in an incident review.
ERROR_CLASSES = (
    "timeout",
    "permission",
    "not_found",
    "validation",
    "sandbox",
    "dependency",
    "external_service",
    "budget",
    "cancelled",
    "runtime",
    "unknown",
)

_ERROR_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("timeout", ("timeout", "timed out", "deadline exceeded")),
    ("budget", ("budget", "quota", "rate limit", "insufficient")),
    ("permission", ("permission", "denied", "forbidden", "unauthor", "not allowed")),
    ("not_found", ("not found", "no such", "unknown action", "missing")),
    ("validation", ("invalid", "validation", "unsafe", "malformed", "schema")),
    ("sandbox", ("sandbox", "rlimit", "seccomp", "isolat")),
    ("dependency", ("importerror", "modulenotfound", "no module named")),
    ("external_service", ("connection", "http", "socket", "dns", "502", "503", "504")),
    ("cancelled", ("cancel", "aborted")),
)


def classify_error(error: Any) -> str:
    """Map an exception or message to a stable error class."""
    if error is None:
        return "unknown"
    if isinstance(error, BaseException):
        name = type(error).__name__.lower()
        text = f"{name}: {error}".lower()
    else:
        text = str(error).lower()

    for label, needles in _ERROR_PATTERNS:
        if any(needle in text for needle in needles):
            return label
    if "error" in text or "exception" in text:
        return "runtime"
    return "unknown"


def outcome_for_decision(decision: Optional[PolicyDecision]) -> str:
    """Default receipt outcome for a policy decision that did not execute."""
    if decision is None:
        return ReceiptOutcome.REQUIRES_APPROVAL.value
    return {
        Decision.ALLOW: ReceiptOutcome.ALLOWED.value,
        Decision.ALLOW_WITH_RECEIPT: ReceiptOutcome.ALLOWED.value,
        Decision.REQUIRE_APPROVAL: ReceiptOutcome.REQUIRES_APPROVAL.value,
        Decision.DENY: ReceiptOutcome.BLOCKED.value,
        Decision.EMERGENCY_STOP: ReceiptOutcome.EMERGENCY_STOP.value,
    }.get(decision.decision, ReceiptOutcome.BLOCKED.value)


def build_receipt(
    *,
    action_id: str,
    action_name: str,
    mind_id: str,
    outcome: str,
    parameters: Optional[Mapping[str, Any]] = None,
    policy_decision: Optional[PolicyDecision] = None,
    policy_decision_dict: Optional[Mapping[str, Any]] = None,
    requested_by: str = "",
    actor_type: str = ActorType.MIND.value,
    intent: str = "",
    selected_skill: Optional[str] = None,
    tenant_id: Optional[str] = None,
    objective_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    approval_id: Optional[str] = None,
    approver_id: Optional[str] = None,
    approved_at: Optional[datetime] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    affected_resources: Iterable[str] = (),
    artifacts: Sequence[Mapping[str, Any]] = (),
    evidence: Optional[Mapping[str, Any]] = None,
    model_invocations: int = 0,
    cost_essence: int = 0,
    error: Any = None,
    rollback: Optional[Mapping[str, Any]] = None,
    receipt_id: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> ActionReceipt:
    """Assemble a receipt. Redaction happens in :class:`AuditService` on write."""
    decision_dict: Dict[str, Any] = dict(policy_decision_dict or {})
    matched: Tuple[str, ...] = ()
    resolved_risk = risk_level or ""

    if policy_decision is not None:
        decision_dict = decision_dict or policy_decision.to_dict()
        matched = policy_decision.matched_rules
        resolved_risk = resolved_risk or policy_decision.risk_level.value

    duration_ms: Optional[float] = None
    if started_at and completed_at:
        duration_ms = (completed_at - started_at).total_seconds() * 1000.0

    receipt = ActionReceipt(
        receipt_id=receipt_id or new_id("rcp"),
        action_id=action_id,
        action_name=action_name,
        mind_id=mind_id,
        tenant_id=tenant_id,
        objective_id=objective_id,
        outcome=str(outcome),
        created_at=created_at or utcnow(),
        requested_by=requested_by or "",
        actor_type=actor_type,
        intent=intent or "",
        selected_skill=selected_skill,
        arguments=dict(parameters or {}),
        arguments_hash=stable_hash(dict(parameters or {})),
        risk_level=resolved_risk,
        policy_decision=decision_dict,
        matched_rules=matched,
        approval_id=approval_id,
        approver_id=approver_id,
        approved_at=approved_at,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        affected_resources=tuple(str(item) for item in affected_resources),
        artifacts=tuple(dict(item) for item in artifacts),
        evidence=dict(evidence or {}),
        model_invocations=int(model_invocations or 0),
        cost_essence=int(cost_essence or 0),
        error_class=classify_error(error) if error is not None else None,
        error_message=(str(error)[:2000] if error is not None else None),
        rollback=dict(rollback) if rollback else None,
        correlation_id=correlation_id or new_correlation_id(),
    )
    return receipt
