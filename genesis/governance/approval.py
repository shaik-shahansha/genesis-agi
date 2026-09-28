"""Approval service: a persistent, auditable state machine (ADR-0007).

The state machine is a *control*, not a convention. Illegal transitions are
refused with :class:`ApprovalTransitionError`, and every accepted transition is
journaled.

The security core of this module is the binding of an approval to the exact
action:

1. ``parameters_hash`` covers the **material** parameters only; changing any of
   them invalidates the grant.
2. A grant is bound to one mind, one capability, one scope, and one expiry.
3. Grants are single-use by default; redemption is idempotent-safe because a
   second redemption fails closed.
4. Approval and grant TTLs are short, so a forgotten grant cannot be replayed
   hours later.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from genesis.governance.audit import AuditService, new_correlation_id, new_id
from genesis.governance.models import (
    APPROVAL_TRANSITIONS,
    ActorType,
    ApprovalRequest,
    ApprovalStatus,
    EventType,
    PermissionGrant,
    can_transition,
    utcnow,
)
from genesis.governance.policy import PolicyContext, PolicyDecision
from genesis.governance.redact import canonical_json, redact_payload, stable_hash
from genesis.governance.risk import RiskLevel
from genesis.governance.store import GovernanceStore, get_governance_store

logger = logging.getLogger(__name__)

__all__ = [
    "ApprovalError",
    "ApprovalTransitionError",
    "ApprovalNotFoundError",
    "GrantRedemptionError",
    "Redemption",
    "MATERIAL_PARAMETER_EXCLUSIONS",
    "material_parameters",
    "parameters_fingerprint",
    "describe_action",
    "ApprovalService",
    "DEFAULT_APPROVAL_TTL",
    "DEFAULT_GRANT_TTL",
]

#: How long a request may sit unanswered before it expires.
DEFAULT_APPROVAL_TTL = timedelta(hours=24)
#: How long an approved grant stays redeemable.
DEFAULT_GRANT_TTL = timedelta(minutes=15)

#: Parameters that never change the *meaning* of an action. Excluding them means
#: a re-worded reasoning string does not invalidate an approval, while a changed
#: recipient or amount does.
MATERIAL_PARAMETER_EXCLUSIONS: frozenset = frozenset(
    {
        "reasoning",
        "reason",
        "rationale",
        "justification",
        "explanation",
        "context",
        "note",
        "comment",
        "notes",
        "confidence",
        "request_id",
        "requestid",
        "correlation_id",
        "correlationid",
        "trace_id",
        "traceid",
        "stream",
        "timestamp",
        "think",
        "thought",
        "idempotency_key",
        "idempotencykey",
    }
)

#: Parameter names whose values are surfaced to the approver as "who/what".
_RECIPIENT_KEYS = ("to", "recipient", "recipients", "email", "target", "url", "channel", "address")
_COST_KEYS = ("cost", "amount", "price", "budget", "spend", "cost_essence", "costessence")
_RESOURCE_KEYS = ("path", "file", "resource", "table", "database", "repo", "repository", "bucket")


class ApprovalError(RuntimeError):
    """Base class for approval failures."""


class ApprovalTransitionError(ApprovalError):
    """An illegal state transition was attempted."""


class ApprovalNotFoundError(ApprovalError):
    """No approval exists for the given id."""


class GrantRedemptionError(ApprovalError):
    """A grant could not be redeemed."""


def material_parameters(parameters: Mapping[str, Any]) -> Dict[str, Any]:
    """Strip non-material keys so cosmetic edits do not break a grant."""
    if not parameters:
        return {}
    return {
        str(key): _normalize(value)
        for key, value in parameters.items()
        if str(key).lower() not in MATERIAL_PARAMETER_EXCLUSIONS
    }


def _normalize(value: Any) -> Any:
    """Normalise values that are semantically identical but textually different."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(str(item) for item in value)
    return value


def parameters_fingerprint(parameters: Mapping[str, Any]) -> str:
    """Hash of the material parameters. The binding used by grants."""
    return stable_hash(material_parameters(parameters))


def describe_action(
    context: PolicyContext,
    decision: PolicyDecision,
    *,
    capability_reversible: bool = True,
    proposed_rollback: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the plain-language block a non-engineer reads before approving.

    Deliberately derived from *facts*, not from model prose: the summary is
    generated from the capability name, risk level, and the material
    parameters, so a persuasive model cannot write its own approval rationale.
    """
    params = context.parameters or {}
    lowered = {str(key).lower(): value for key, value in params.items()}

    recipient = next(
        (str(lowered[key]) for key in _RECIPIENT_KEYS if lowered.get(key)), None
    )
    cost_value = next(
        (lowered[key] for key in _COST_KEYS if isinstance(lowered.get(key), (int, float))),
        None,
    )
    data_accessed = tuple(
        str(lowered[key]) for key in _RESOURCE_KEYS if lowered.get(key)
    )
    impact = _impact_sentence(context, decision)

    return {
        "summary": _summary_sentence(context, recipient),
        "reason": decision.explanation,
        "expected_impact": impact,
        "data_accessed": data_accessed,
        "recipient": recipient,
        "financial_cost_essence": int(cost_value) if cost_value is not None else 0,
        "reversibility": "reversible" if capability_reversible else "not reversible",
        "scope": _scope_sentence(context),
        "proposed_rollback": proposed_rollback
        or (
            "Undo is possible from the action receipt; the workspace snapshot taken "
            "before execution is the restore point."
            if capability_reversible
            else "This action cannot be undone automatically. Manual remediation required."
        ),
    }


def _summary_sentence(context: PolicyContext, recipient: Optional[str]) -> str:
    human = context.action_name.replace("_", " ")
    if recipient:
        return f"{human} involving {recipient}"
    return human


def _scope_sentence(context: PolicyContext) -> str:
    scope_bits = [f"mind={context.mind_id or 'unknown'}"]
    if context.objective_id:
        scope_bits.append(f"objective={context.objective_id}")
    if context.objective_id is None:
        scope_bits.append("scope=single action")
    return ", ".join(scope_bits)


def _impact_sentence(context: PolicyContext, decision: PolicyDecision) -> str:
    capability = decision.capability
    bits: List[str] = []
    if capability:
        if capability.external:
            bits.append("affects systems outside the Mind's own workspace")
        if capability.physical:
            bits.append("has physical-world effect")
        if capability.destructive:
            bits.append("can destroy data")
        if not capability.reversible:
            bits.append("cannot be automatically undone")
        if capability.data_sensitivity not in ("none", "", None):
            bits.append(f"touches {capability.data_sensitivity} data")
    if not bits:
        bits.append("no external or irreversible effect identified")
    return f"Risk {decision.risk_level.value} ({decision.risk_level.label}): " + "; ".join(bits) + "."


@dataclass(frozen=True)
class Redemption:
    """Result of trying to spend a grant."""

    granted: bool
    reason: str
    grant: Optional[PermissionGrant] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "granted": self.granted,
            "reason": self.reason,
            "grant": self.grant.to_dict() if self.grant else None,
        }


@dataclass
class ApprovalService:
    """Submission, decision, expiry, and redemption of approvals."""

    store: GovernanceStore = None  # type: ignore[assignment]
    audit: Optional[AuditService] = None
    default_tenant_id: Optional[str] = None
    approval_ttl: timedelta = DEFAULT_APPROVAL_TTL
    grant_ttl: timedelta = DEFAULT_GRANT_TTL

    def __post_init__(self) -> None:
        if self.store is None:
            self.store = get_governance_store()
        if self.audit is None:
            self.audit = AuditService(store=self.store, default_tenant_id=self.default_tenant_id)

    # ------------------------------------------------------------------ #
    # Submission
    # ------------------------------------------------------------------ #
    def submit(
        self,
        *,
        context: PolicyContext,
        decision: PolicyDecision,
        action_id: str,
        requested_by: str = "",
        actor_type: str = ActorType.MIND.value,
        ttl: Optional[timedelta] = None,
        proposed_rollback: Optional[str] = None,
    ) -> ApprovalRequest:
        """Create a pending approval for a decision that requires one."""
        now = utcnow()
        capability = decision.capability
        reversible = bool(capability.reversible) if capability else True
        described = describe_action(
            context,
            decision,
            capability_reversible=reversible,
            proposed_rollback=proposed_rollback,
        )

        approval = ApprovalRequest(
            approval_id=new_id("apr"),
            action_id=action_id,
            action_name=context.action_name,
            mind_id=context.mind_id,
            tenant_id=context.tenant_id if context.tenant_id is not None else self.default_tenant_id,
            objective_id=context.objective_id,
            status=ApprovalStatus.WAITING_FOR_APPROVAL.value,
            requested_at=now,
            expires_at=now + (ttl or self.approval_ttl),
            risk_level=decision.risk_level.value,
            parameters=redact_payload(context.parameters),
            parameters_hash=parameters_fingerprint(context.parameters),
            summary=described["summary"],
            reason=described["reason"],
            expected_impact=described["expected_impact"],
            data_accessed=tuple(described["data_accessed"]),
            recipient=described["recipient"],
            financial_cost_essence=int(described["financial_cost_essence"]),
            reversibility=described["reversibility"],
            scope=described["scope"],
            proposed_rollback=described["proposed_rollback"],
            evidence={
                "reason_code": decision.reason_code,
                "risk": decision.risk.to_dict(),
                "capability": capability.to_dict() if capability else None,
                "policy_version": decision.policy_version,
                "charter_version": decision.charter_version,
            },
            policy_decision=decision.to_dict(),
            matched_rules=decision.matched_rules,
            policy_version=decision.policy_version,
            requires_human=decision.requires_human,
            approver_role=decision.approver_role,
            requested_by=requested_by or context.actor_id or context.requester,
            actor_type=actor_type,
            correlation_id=context.correlation_id or new_correlation_id(),
            transition_log=(
                _log_entry(ApprovalStatus.PROPOSED, now, requested_by, "created"),
                _log_entry(
                    ApprovalStatus.POLICY_EVALUATED,
                    now,
                    "policy_engine",
                    f"{decision.reason_code} at {decision.risk_level.value}",
                ),
                _log_entry(
                    ApprovalStatus.WAITING_FOR_APPROVAL,
                    now,
                    "policy_engine",
                    "queued for a human decision",
                ),
            ),
        )

        self.store.save_approval(approval)
        self._event(
            EventType.ACTION_APPROVAL_REQUESTED,
            approval,
            actor_type=ActorType.MIND.value,
            actor_id=approval.requested_by,
            payload={
                "approval_id": approval.approval_id,
                "action_name": approval.action_name,
                "risk_level": approval.risk_level,
                "reason_code": decision.reason_code,
                "requires_human": approval.requires_human,
                "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
            },
        )
        return approval

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    def get(self, approval_id: str) -> ApprovalRequest:
        approval = self.store.get_approval(approval_id)
        if approval is None:
            raise ApprovalNotFoundError(f"unknown approval '{approval_id}'")
        return approval

    def inbox(
        self, *, mind_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Pending approvals as human-readable cards for the approval inbox."""
        pending = self.store.list_approvals(
            mind_id=mind_id, status=ApprovalStatus.WAITING_FOR_APPROVAL.value, limit=limit
        )
        return [approval.plain_language_card() for approval in pending]

    def history(self, *, mind_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self.store.list_approvals(mind_id=mind_id, limit=limit)]

    # ------------------------------------------------------------------ #
    # Decisions
    # ------------------------------------------------------------------ #
    def approve(
        self,
        approval_id: str,
        *,
        approver_id: str,
        note: Optional[str] = None,
        ttl: Optional[timedelta] = None,
        actor_type: str = ActorType.APPROVER.value,
    ) -> PermissionGrant:
        """Approve a pending request and issue a bound, single-use grant."""
        approval = self.get(approval_id)
        now = utcnow()

        if approval.expired_at(now):
            self._transition(
                approval, ApprovalStatus.EXPIRED, actor_id="system", note="expired before decision"
            )
            raise ApprovalError("this approval request has expired")

        if approval.requires_human and actor_type == ActorType.MIND.value:
            raise ApprovalError(
                "this action requires a human approver; a Mind cannot approve it"
            )

        self._transition(
            approval, ApprovalStatus.APPROVED, actor_id=approver_id, note=note or "approved"
        )
        approval.approver_id = approver_id
        approval.resolved_at = now
        approval.resolution_note = note
        self.store.save_approval(approval)

        grant = PermissionGrant(
            grant_id=new_id("grt"),
            approval_id=approval.approval_id,
            mind_id=approval.mind_id,
            tenant_id=approval.tenant_id,
            objective_id=approval.objective_id,
            action_name=approval.action_name,
            parameters_hash=approval.parameters_hash,
            scope=approval.scope,
            issued_by=approver_id,
            issued_at=now,
            expires_at=now + (ttl or self.grant_ttl),
            single_use=True,
            max_uses=1,
        )
        self.store.save_grant(grant)

        self._event(
            EventType.ACTION_APPROVED,
            approval,
            actor_type=actor_type,
            actor_id=approver_id,
            payload={
                "approval_id": approval.approval_id,
                "grant_id": grant.grant_id,
                "parameters_hash": grant.parameters_hash,
                "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
                "note": note,
            },
        )
        self._event(
            EventType.GRANT_ISSUED,
            approval,
            actor_type=actor_type,
            actor_id=approver_id,
            payload={"grant_id": grant.grant_id, "action_name": grant.action_name},
        )
        return grant

    def reject(
        self,
        approval_id: str,
        *,
        approver_id: str,
        note: Optional[str] = None,
        actor_type: str = ActorType.APPROVER.value,
    ) -> ApprovalRequest:
        approval = self.get(approval_id)
        self._transition(
            approval, ApprovalStatus.REJECTED, actor_id=approver_id, note=note or "rejected"
        )
        approval.approver_id = approver_id
        approval.resolved_at = utcnow()
        approval.resolution_note = note
        self.store.save_approval(approval)
        self._event(
            EventType.ACTION_REJECTED,
            approval,
            actor_type=actor_type,
            actor_id=approver_id,
            payload={"approval_id": approval.approval_id, "note": note},
        )
        return approval

    def cancel(
        self,
        approval_id: str,
        *,
        actor_id: str,
        note: Optional[str] = None,
        actor_type: str = ActorType.USER.value,
    ) -> ApprovalRequest:
        """Withdraw a request (the requester withdrew, or policy changed)."""
        approval = self.get(approval_id)
        self._transition(
            approval, ApprovalStatus.CANCELLED, actor_id=actor_id, note=note or "cancelled"
        )
        approval.resolved_at = utcnow()
        approval.resolution_note = note
        self.store.save_approval(approval)
        self._event(
            EventType.ACTION_BLOCKED,
            approval,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"approval_id": approval.approval_id, "disposition": "cancelled", "note": note},
        )
        return approval

    def expire_stale(self, *, now: Optional[datetime] = None) -> List[ApprovalRequest]:
        """Expire unanswered requests. Called by the heartbeat, not by a timer."""
        now = now or utcnow()
        expired: List[ApprovalRequest] = []
        for approval in self.store.list_approvals(
            status=ApprovalStatus.WAITING_FOR_APPROVAL.value, limit=1000
        ):
            if approval.expired_at(now):
                self._transition(
                    approval, ApprovalStatus.EXPIRED, actor_id="system", note="ttl elapsed"
                )
                approval.resolved_at = now
                self.store.save_approval(approval)
                self._event(
                    EventType.ACTION_EXPIRED,
                    approval,
                    actor_id="system",
                    payload={"approval_id": approval.approval_id},
                )
                expired.append(approval)
        return expired

    def revoke_grant(
        self, grant_id: str, *, actor_id: str, note: Optional[str] = None
    ) -> PermissionGrant:
        grant = self.store.get_grant(grant_id)
        if grant is None:
            raise ApprovalError(f"unknown grant '{grant_id}'")
        if grant.is_consumed:
            raise ApprovalError("this grant has already been used; use rollback instead")
        grant.revoked_at = utcnow()
        grant.revoked_by = actor_id
        self.store.save_grant(grant)
        self._event(
            EventType.GRANT_REVOKED,
            _event_stub(grant.mind_id, grant.tenant_id, grant.approval_id),
            actor_type=ActorType.OPERATOR.value,
            actor_id=actor_id,
            payload={"grant_id": grant.grant_id, "note": note},
        )
        return grant

    # ------------------------------------------------------------------ #
    # Redemption & execution lifecycle
    # ------------------------------------------------------------------ #
    def redeem(
        self,
        grant_id: str,
        *,
        parameters: Mapping[str, Any],
        mind_id: Optional[str] = None,
        action_name: Optional[str] = None,
    ) -> Redemption:
        """Spend a grant. Fails closed on any mismatch."""
        now = utcnow()
        grant = self.store.get_grant(grant_id)
        if grant is None:
            return Redemption(False, "unknown grant")
        if grant.is_revoked:
            return Redemption(False, "grant was revoked", grant)
        if grant.is_expired(now):
            return Redemption(False, "grant expired", grant)
        if grant.is_consumed and grant.max_uses <= 1:
            return Redemption(False, "grant already used", grant)
        if mind_id is not None and grant.mind_id != mind_id:
            return Redemption(False, "grant belongs to a different Mind", grant)
        if action_name is not None and grant.action_name != action_name:
            return Redemption(False, "grant is for a different action", grant)
        if parameters_fingerprint(parameters) != grant.parameters_hash:
            return Redemption(False, "action parameters changed since approval", grant)

        grant.consumed_at = now
        self.store.save_grant(grant)
        self._event(
            EventType.GRANT_REDEEMED,
            _event_stub(grant.mind_id, grant.tenant_id, grant.approval_id),
            actor_type=ActorType.MIND.value,
            actor_id=grant.mind_id,
            payload={"grant_id": grant.grant_id, "action_name": grant.action_name},
        )
        return Redemption(True, "grant redeemed", grant)

    def mark_executing(self, approval_id: str, *, actor_id: str = "mind") -> ApprovalRequest:
        approval = self.get(approval_id)
        self._transition(
            approval, ApprovalStatus.EXECUTING, actor_id=actor_id, note="execution started"
        )
        self.store.save_approval(approval)
        self._event(EventType.ACTION_EXECUTING, approval, actor_id=actor_id, payload={})
        return approval

    def complete(
        self,
        approval_id: str,
        *,
        success: bool,
        actor_id: str = "mind",
        detail: Optional[str] = None,
    ) -> ApprovalRequest:
        approval = self.get(approval_id)
        target = ApprovalStatus.COMPLETED if success else ApprovalStatus.FAILED
        self._transition(approval, target, actor_id=actor_id, note=detail or target.value.lower())
        self.store.save_approval(approval)
        self._event(
            EventType.ACTION_EXECUTED if success else EventType.ACTION_FAILED,
            approval,
            actor_id=actor_id,
            payload={"detail": detail},
        )
        return approval

    def mark_rolled_back(
        self, approval_id: str, *, actor_id: str, detail: Optional[str] = None
    ) -> ApprovalRequest:
        approval = self.get(approval_id)
        self._transition(
            approval, ApprovalStatus.ROLLED_BACK, actor_id=actor_id, note=detail or "rolled back"
        )
        self.store.save_approval(approval)
        self._event(
            EventType.ACTION_ROLLED_BACK,
            approval,
            actor_id=actor_id,
            payload={"detail": detail},
        )
        return approval

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _transition(
        self,
        approval: ApprovalRequest,
        target: ApprovalStatus,
        *,
        actor_id: str,
        note: str,
    ) -> None:
        current = approval.status_enum
        if current is target:
            return
        if not can_transition(current, target):
            raise ApprovalTransitionError(
                f"cannot move approval {approval.approval_id} from "
                f"{current.value} to {target.value}"
            )
        approval.status = target.value
        approval.transition_log = approval.transition_log + (
            _log_entry(target, utcnow(), actor_id, note),
        )

    def _event(
        self,
        event_type: str,
        approval: ApprovalRequest,
        *,
        actor_type: str = ActorType.SYSTEM.value,
        actor_id: str = "",
        payload: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if self.audit is None:  # pragma: no cover - __post_init__ guarantees it
            return
        self.audit.record(
            event_type,
            mind_id=approval.mind_id,
            tenant_id=approval.tenant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=approval.correlation_id,
            causation_id=approval.approval_id,
            payload=payload,
        )


def _log_entry(
    status: ApprovalStatus, when: datetime, actor_id: str, note: str
) -> Dict[str, Any]:
    return {
        "status": status.value,
        "at": when.isoformat(),
        "actor_id": actor_id or "",
        "note": note or "",
    }


def _event_stub(mind_id: str, tenant_id: Optional[str], correlation_id: str) -> ApprovalRequest:
    """Minimal ApprovalRequest used only so ``_event`` has a routing target."""
    return ApprovalRequest(
        approval_id="",
        action_id="",
        action_name="",
        mind_id=mind_id,
        status=ApprovalStatus.APPROVED.value,
        requested_at=utcnow(),
        risk_level=RiskLevel.R3.value,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )
