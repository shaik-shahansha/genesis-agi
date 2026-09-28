"""The governance gate: one call that authorizes an action.

:class:`GovernanceGate` is the single entry point the action executor uses. It
composes the four services so callers cannot accidentally use only part of the
control plane:

``PolicyEngine`` → decides, ``ApprovalService`` → authorizes, ``AuditService``
→ records, ``EmergencyStopService`` → halts.

Every path through :meth:`authorize` produces an :class:`~genesis.governance.models.ActionReceipt`,
including the blocked paths, because the blocked paths are the interesting ones.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Tuple

from genesis.governance.approval import ApprovalService, Redemption
from genesis.governance.audit import AuditService
from genesis.governance.estop import EmergencyStopService, get_emergency_stop_service
from genesis.governance.models import (
    ActionReceipt,
    ActorType,
    ApprovalRequest,
    EventType,
    PermissionGrant,
    ReceiptOutcome,
)
from genesis.governance.policy import (
    Decision,
    PolicyContext,
    PolicyDecision,
    PolicyEngine,
    get_policy_engine,
)
from genesis.governance.receipts import build_receipt, outcome_for_decision
from genesis.governance.risk import RiskLevel

logger = logging.getLogger(__name__)

__all__ = ["AuthorizationResult", "GovernanceGate", "get_governance_gate"]


@dataclass(frozen=True)
class AuthorizationResult:
    """The outcome of one authorization attempt."""

    allowed: bool
    decision: PolicyDecision
    reason: str
    approval: Optional[ApprovalRequest] = None
    grant: Optional[PermissionGrant] = None
    receipt: Optional[ActionReceipt] = None

    @property
    def requires_approval(self) -> bool:
        return self.decision.requires_approval and not self.allowed

    @property
    def blocked(self) -> bool:
        return self.decision.blocked

    @property
    def risk_level(self) -> RiskLevel:
        return self.decision.risk_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "decision": self.decision.to_dict(),
            "approval": self.approval.to_dict() if self.approval else None,
            "grant": self.grant.to_dict() if self.grant else None,
            "receipt_id": self.receipt.receipt_id if self.receipt else None,
        }


@dataclass
class GovernanceGate:
    """Authorize, record, and explain action attempts."""

    engine: PolicyEngine = field(default_factory=get_policy_engine)
    approvals: ApprovalService = field(default_factory=ApprovalService)
    audit: AuditService = field(default_factory=AuditService)
    emergency_stop: EmergencyStopService = field(
        default_factory=get_emergency_stop_service
    )

    # ------------------------------------------------------------------ #
    def build_context(
        self,
        *,
        action_name: str,
        parameters: Mapping[str, Any],
        mind_id: str,
        category: Optional[str] = None,
        actor_type: str = ActorType.MIND.value,
        actor_id: str = "",
        requester: str = "mind",
        objective_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        granted_scopes: Optional[Tuple[str, ...]] = None,
        tenant_policy: Optional[Mapping[str, Any]] = None,
        autonomy: Any = None,
        lifecycle_state: str = "active",
        budget_remaining_essence: Optional[int] = None,
        advisory_level: Optional[RiskLevel] = None,
        advisory_note: Optional[str] = None,
    ) -> PolicyContext:
        """Assemble a :class:`PolicyContext` from available runtime facts.

        Missing facts stay uninformative, which raises the required control
        rather than lowering it (fail closed).
        """
        profile = self.engine.assess_capability(action_name, category)
        scopes = granted_scopes
        if scopes is None:
            scopes = _scopes_from_autonomy(autonomy, action_name, profile.required_scopes)

        return PolicyContext(
            action_name=action_name,
            parameters=dict(parameters or {}),
            mind_id=mind_id,
            tenant_id=tenant_id,
            actor_type=actor_type,
            actor_id=actor_id or mind_id,
            requester=requester,
            category=category or profile.category,
            objective_id=objective_id,
            correlation_id=correlation_id,
            granted_scopes=frozenset(scopes or ()),
            ownership="owner",
            data_sensitivity=profile.data_sensitivity,
            external=profile.external,
            reversible=profile.reversible,
            physical=profile.physical,
            destructive=profile.destructive,
            cost_essence=0,
            budget_remaining_essence=budget_remaining_essence,
            lifecycle_state=lifecycle_state,
            emergency_stop=self.emergency_stop.is_engaged(mind_id),
            trust_level="trusted",
            tenant_policy=dict(tenant_policy or _policy_from_autonomy(autonomy)),
            advisory_level=advisory_level,
            advisory_note=advisory_note,
        )

    # ------------------------------------------------------------------ #
    def authorize(
        self,
        context: PolicyContext,
        *,
        action_id: str,
        requested_by: str = "",
        actor_type: str = ActorType.MIND.value,
        intent: str = "",
        grant_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> AuthorizationResult:
        """Evaluate policy and either allow, queue for approval, or refuse."""
        decision = self.engine.evaluate(context)
        action_name = context.action_name
        mind_id = context.mind_id

        self._record_event(
            EventType.ACTION_POLICY_EVALUATED,
            mind_id=mind_id,
            tenant_id=context.tenant_id,
            actor_type=actor_type,
            actor_id=requested_by or context.actor_id,
            correlation_id=context.correlation_id,
            causation_id=action_id,
            payload={
                "action_name": action_name,
                "action_id": action_id,
                "decision": decision.decision.value,
                "reason_code": decision.reason_code,
                "risk_level": decision.risk_level.value,
                "matched_rules": list(decision.matched_rules),
                "policy_version": decision.policy_version,
            },
        )

        # ---- allowed -------------------------------------------------- #
        if decision.permits_execution:
            receipt = None
            if decision.decision is Decision.ALLOW_WITH_RECEIPT:
                receipt = self._receipt(
                    context,
                    decision,
                    action_id=action_id,
                    outcome=ReceiptOutcome.ALLOWED.value,
                    requested_by=requested_by,
                    actor_type=actor_type,
                    intent=intent,
                    grant_id=grant_id,
                    started_at=started_at,
                    metadata=metadata,
                )
            return AuthorizationResult(
                allowed=True,
                decision=decision,
                reason=decision.reason_code,
                receipt=receipt,
            )

        # ---- requires approval ---------------------------------------- #
        if decision.requires_approval:
            if grant_id:
                redemption = self._redeem(grant_id, context)
                if redemption.granted:
                    receipt = self._receipt(
                        context,
                        decision,
                        action_id=action_id,
                        outcome=ReceiptOutcome.ALLOWED.value,
                        requested_by=requested_by,
                        actor_type=actor_type,
                        intent=intent,
                        grant_id=grant_id,
                        started_at=started_at,
                        metadata=metadata,
                        approval_id=redemption.grant.approval_id if redemption.grant else None,
                        approver_id=redemption.grant.issued_by if redemption.grant else None,
                    )
                    return AuthorizationResult(
                        allowed=True,
                        decision=decision,
                        reason="grant_redeemed",
                        grant=redemption.grant,
                        receipt=receipt,
                    )
                reason = redemption.reason
            else:
                reason = decision.reason_code

            approval = self.approvals.submit(
                context=context,
                decision=decision,
                action_id=action_id,
                requested_by=requested_by,
                actor_type=actor_type,
            )
            receipt = self._receipt(
                context,
                decision,
                action_id=action_id,
                outcome=ReceiptOutcome.REQUIRES_APPROVAL.value,
                requested_by=requested_by,
                actor_type=actor_type,
                intent=intent,
                started_at=started_at,
                metadata=metadata,
                approval_id=approval.approval_id,
            )
            return AuthorizationResult(
                allowed=False,
                decision=decision,
                reason=reason,
                approval=approval,
                receipt=receipt,
            )

        # ---- blocked --------------------------------------------------- #
        event_type = (
            EventType.ACTION_EMERGENCY_STOP
            if decision.decision is Decision.EMERGENCY_STOP
            else EventType.ACTION_BLOCKED
        )
        self._record_event(
            event_type,
            mind_id=mind_id,
            tenant_id=context.tenant_id,
            actor_type=actor_type,
            actor_id=requested_by or context.actor_id,
            correlation_id=context.correlation_id,
            causation_id=action_id,
            payload={
                "action_name": action_name,
                "action_id": action_id,
                "reason_code": decision.reason_code,
                "explanation": decision.explanation,
                "risk_level": decision.risk_level.value,
                "matched_rules": list(decision.matched_rules),
            },
        )
        if decision.decision is Decision.EMERGENCY_STOP and not self.emergency_stop.is_engaged(
            mind_id
        ):
            # R5 catastrophic capability: latch the stop so the Mind cannot keep
            # probing. A human must release it.
            self.emergency_stop.engage(
                mind_id,
                actor_id="policy_engine",
                actor_type=ActorType.SYSTEM.value,
                reason="policy: prohibited capability attempted",
            )

        receipt = self._receipt(
            context,
            decision,
            action_id=action_id,
            outcome=outcome_for_decision(decision),
            requested_by=requested_by,
            actor_type=actor_type,
            intent=intent,
            started_at=started_at,
            metadata=metadata,
        )
        return AuthorizationResult(
            allowed=False,
            decision=decision,
            reason=decision.reason_code,
            receipt=receipt,
        )

    # ------------------------------------------------------------------ #
    def record_outcome(
        self,
        context: PolicyContext,
        decision: PolicyDecision,
        *,
        action_id: str,
        outcome: str,
        requested_by: str = "",
        actor_type: str = ActorType.MIND.value,
        intent: str = "",
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result_summary: Optional[str] = None,
        error: Any = None,
        affected_resources: Tuple[str, ...] = (),
        artifacts: Tuple[Mapping[str, Any], ...] = (),
        evidence: Optional[Mapping[str, Any]] = None,
        approval_id: Optional[str] = None,
        approver_id: Optional[str] = None,
        cost_essence: int = 0,
        model_invocations: int = 0,
        rollback: Optional[Mapping[str, Any]] = None,
    ) -> ActionReceipt:
        """Write the terminal receipt for an executed (or failed) action."""
        event_type = {
            ReceiptOutcome.EXECUTED.value: EventType.ACTION_EXECUTED,
            ReceiptOutcome.FAILED.value: EventType.ACTION_FAILED,
            ReceiptOutcome.CANCELLED.value: EventType.ACTION_BLOCKED,
            ReceiptOutcome.ROLLED_BACK.value: EventType.ACTION_ROLLED_BACK,
        }.get(outcome, EventType.ACTION_EXECUTED)

        self._record_event(
            event_type,
            mind_id=context.mind_id,
            tenant_id=context.tenant_id,
            actor_type=actor_type,
            actor_id=requested_by or context.actor_id,
            correlation_id=context.correlation_id,
            causation_id=action_id,
            payload={
                "action_name": context.action_name,
                "action_id": action_id,
                "outcome": outcome,
                "result_summary": result_summary,
                "error": str(error)[:500] if error is not None else None,
            },
        )

        return self._receipt(
            context,
            decision,
            action_id=action_id,
            outcome=outcome,
            requested_by=requested_by,
            actor_type=actor_type,
            intent=intent,
            started_at=started_at,
            completed_at=completed_at,
            result_summary=result_summary,
            error=error,
            affected_resources=affected_resources,
            artifacts=artifacts,
            evidence=evidence,
            approval_id=approval_id,
            approver_id=approver_id,
            cost_essence=cost_essence,
            model_invocations=model_invocations,
            rollback=rollback,
        )

    # ------------------------------------------------------------------ #
    def _redeem(self, grant_id: str, context: PolicyContext) -> Redemption:
        return self.approvals.redeem(
            grant_id,
            parameters=context.parameters,
            mind_id=context.mind_id,
            action_name=context.action_name,
        )

    def _receipt(
        self,
        context: PolicyContext,
        decision: PolicyDecision,
        *,
        action_id: str,
        outcome: str,
        requested_by: str,
        actor_type: str,
        intent: str,
        grant_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result_summary: Optional[str] = None,
        error: Any = None,
        affected_resources: Tuple[str, ...] = (),
        artifacts: Tuple[Mapping[str, Any], ...] = (),
        evidence: Optional[Mapping[str, Any]] = None,
        approval_id: Optional[str] = None,
        approver_id: Optional[str] = None,
        cost_essence: int = 0,
        model_invocations: int = 0,
        rollback: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ActionReceipt:
        merged_evidence: Dict[str, Any] = dict(evidence or {})
        if result_summary:
            merged_evidence.setdefault("result_summary", str(result_summary)[:1000])
        if metadata:
            merged_evidence.setdefault("metadata", dict(metadata))
        if grant_id:
            merged_evidence.setdefault("grant_id", grant_id)

        receipt = build_receipt(
            action_id=action_id,
            action_name=context.action_name,
            mind_id=context.mind_id,
            outcome=outcome,
            parameters=context.parameters,
            policy_decision=decision,
            requested_by=requested_by or context.actor_id,
            actor_type=actor_type,
            intent=intent,
            tenant_id=context.tenant_id,
            objective_id=context.objective_id,
            correlation_id=context.correlation_id,
            risk_level=decision.risk_level.value,
            approval_id=approval_id,
            approver_id=approver_id,
            started_at=started_at,
            completed_at=completed_at or (started_at if started_at else None),
            affected_resources=affected_resources,
            artifacts=artifacts,
            evidence=merged_evidence,
            cost_essence=cost_essence,
            model_invocations=model_invocations,
            error=error,
            rollback=rollback,
        )
        return self.audit.record_receipt(receipt)

    def _record_event(
        self,
        event_type: str,
        *,
        mind_id: str,
        tenant_id: Optional[str],
        actor_type: str,
        actor_id: str,
        correlation_id: Optional[str],
        causation_id: Optional[str],
        payload: Mapping[str, Any],
    ) -> None:
        try:
            self.audit.record(
                event_type,
                mind_id=mind_id,
                tenant_id=tenant_id,
                actor_type=actor_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                causation_id=causation_id,
                payload=payload,
            )
        except Exception:  # pragma: no cover - governance must not crash a request
            logger.exception("failed to record governance event %s", event_type)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _scopes_from_autonomy(
    autonomy: Any, action_name: str, required_scopes: Tuple[str, ...] = ()
) -> Tuple[str, ...]:
    """Derive granted scopes from the Mind's autonomy configuration.

    ``autonomy.autonomous_permissions`` is the existing repository concept. An
    entry grants a capability when it names the action (``send_email``) or one of
    the scopes that capability declares (``comms.email.send``). Wildcards are
    deliberately **not** honoured: a broad grant in the autonomy config cannot
    become a blanket policy bypass.
    """
    if autonomy is None:
        return ()
    granted = getattr(autonomy, "autonomous_permissions", None) or ()
    try:
        entries = {str(item).strip() for item in granted}
    except TypeError:
        return ()
    scopes: list = []
    if action_name in entries:
        scopes.append(action_name)
    for scope in required_scopes:
        if scope in entries:
            scopes.append(scope)
    return tuple(dict.fromkeys(scopes))


def _policy_from_autonomy(autonomy: Any) -> Dict[str, Any]:
    """Translate existing autonomy settings into tenant-policy shape.

    Note what is *not* honoured: ``autonomy.proactive_actions`` cannot lift an
    action above R2. That ceiling lives in the policy engine, not here.
    """
    if autonomy is None:
        return {}
    policy: Dict[str, Any] = {}
    initiative = getattr(autonomy, "initiative_level", None)
    if initiative is not None:
        policy["initiative_level"] = getattr(initiative, "value", str(initiative))
    return policy


_gate: Optional[GovernanceGate] = None


def get_governance_gate() -> GovernanceGate:
    """Process-wide governance gate."""
    global _gate
    if _gate is None:
        _gate = GovernanceGate()
    return _gate


def set_governance_gate(gate: Optional[GovernanceGate]) -> Optional[GovernanceGate]:
    """Install a specific gate (tests)."""
    global _gate
    _gate = gate
    return _gate
