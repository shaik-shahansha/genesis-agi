"""Deterministic policy engine (ADR-0006).

The engine evaluates an :class:`~genesis.core.action_executor.ActionRequest`-shaped
context at the *action boundary* and returns a :class:`PolicyDecision`.

Design rules taken directly from ADR-0006:

* **Deterministic.** No I/O, no clock beyond ``evaluated_at``, no randomness.
  The same context always yields the same decision.
* **Fail closed.** Any error, unknown capability, or missing fact resolves to a
  more restrictive decision, never a less restrictive one.
* **Ratchet up only.** A model-based advisory signal can raise the required
  control but can never lower it below what deterministic rules demand.
* **Explainable.** Every decision carries the clause/rule ids that produced it.

The engine is pure. Persistence, notification, and the state machine live in
:mod:`genesis.governance.approval` and :mod:`genesis.governance.audit`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, FrozenSet, Mapping, Optional, Sequence, Tuple

from genesis.governance.constitution_rules import (
    CHARTER_VERSION,
    CLAUSES_BY_ID,
    PROHIBITED_CAPABILITIES,
)
from genesis.governance.risk import (
    CapabilityProfile,
    CapabilityRegistry,
    RiskAssessment,
    RiskLevel,
    RiskSource,
    get_capability_registry,
)

logger = logging.getLogger(__name__)

__all__ = [
    "POLICY_VERSION",
    "Decision",
    "PolicyContext",
    "PolicyDecision",
    "PolicyEngine",
    "get_policy_engine",
    "reset_policy_engine",
    "STANDING_GRANT_MAX_RISK",
]

#: Version of the *engine + rule set*. Recorded on every decision so a decision
#: can be replayed against the rules that produced it.
POLICY_VERSION = "genesis-policy-2026.09.1"

#: A tenant policy may widen autonomy only up to this level. Anything at or
#: above R3 always requires an explicit human approval (ADR-0007).
STANDING_GRANT_MAX_RISK = RiskLevel.R2

#: Lifecycle states where the being must not change the world.
_HALTED_LIFECYCLE_STATES: FrozenSet[str] = frozenset(
    {"retired", "archived", "terminated", "dead", "suspended"}
)
_RESTRICTED_LIFECYCLE_STATES: FrozenSet[str] = frozenset({"paused", "dormant", "hibernating"})

#: Sensitivity labels that force a minimum risk level.
#:
#: ``internal`` is deliberately R0: reading data the owner already owns is
#: owner-authorized (ADR-0006 R0). The floor matters for *disclosure* and for
#: state changes, which capability profiles express through ``external``,
#: ``reversible``, and their declared level.
_SENSITIVITY_FLOOR: Mapping[str, RiskLevel] = {
    "none": RiskLevel.R0,
    "public": RiskLevel.R0,
    "internal": RiskLevel.R0,
    "confidential": RiskLevel.R2,
    "personal": RiskLevel.R3,
    "regulated": RiskLevel.R4,
}

#: Trust level of the external resource/server the action would touch.
_UNTRUSTED_TRUST_LEVELS: FrozenSet[str] = frozenset({"untrusted", "unknown"})

#: Actions a Mind may always take, even while halted, so it can observe itself
#: and a human can inspect state. Read-only only.
_ALWAYS_OBSERVABLE_MAX_RISK = RiskLevel.R0


class Decision(str, Enum):
    """The five policy dispositions (ADR-0006 §4)."""

    ALLOW = "allow"
    ALLOW_WITH_RECEIPT = "allow_with_receipt"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"
    EMERGENCY_STOP = "emergency_stop"

    @property
    def permits_execution(self) -> bool:
        return self in (Decision.ALLOW, Decision.ALLOW_WITH_RECEIPT)

    @property
    def blocks(self) -> bool:
        return self in (Decision.DENY, Decision.EMERGENCY_STOP)


@dataclass(frozen=True)
class PolicyContext:
    """Everything the engine is allowed to consider.

    This mirrors ADR-0006 §5. Fields default to the *uninformative* value so a
    caller that forgets to populate them gets extra control, not less.
    """

    action_name: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    # Identity
    mind_id: str = ""
    tenant_id: Optional[str] = None
    actor_type: str = "mind"  # user | mind | system | plugin | scheduler
    actor_id: str = ""
    requester: str = "user"  # "user" | "mind" | "system" | "plugin"
    category: Optional[str] = None
    objective_id: Optional[str] = None
    correlation_id: Optional[str] = None

    # Authorization
    granted_scopes: FrozenSet[str] = frozenset()
    ownership: str = "owner"  # owner | shared | public | third_party | unknown

    # Facts about the effect
    data_sensitivity: Optional[str] = None
    external: Optional[bool] = None
    reversible: Optional[bool] = None
    physical: Optional[bool] = None
    destructive: Optional[bool] = None

    # Cost
    cost_essence: Optional[int] = None
    budget_remaining_essence: Optional[int] = None

    # Runtime state
    lifecycle_state: str = "active"
    emergency_stop: bool = False
    trust_level: str = "unknown"

    # Tenant/organizational policy
    tenant_policy: Mapping[str, Any] = field(default_factory=dict)

    # Advisory (never authoritative)
    advisory_level: Optional[RiskLevel] = None
    advisory_note: Optional[str] = None

    def with_overrides(self, **kwargs: Any) -> "PolicyContext":
        """Return a copy with selected fields replaced (used by tests/callers)."""
        data = {
            "action_name": self.action_name,
            "parameters": self.parameters,
            "mind_id": self.mind_id,
            "tenant_id": self.tenant_id,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "requester": self.requester,
            "category": self.category,
            "objective_id": self.objective_id,
            "correlation_id": self.correlation_id,
            "granted_scopes": self.granted_scopes,
            "ownership": self.ownership,
            "data_sensitivity": self.data_sensitivity,
            "external": self.external,
            "reversible": self.reversible,
            "physical": self.physical,
            "destructive": self.destructive,
            "cost_essence": self.cost_essence,
            "budget_remaining_essence": self.budget_remaining_essence,
            "lifecycle_state": self.lifecycle_state,
            "emergency_stop": self.emergency_stop,
            "trust_level": self.trust_level,
            "tenant_policy": self.tenant_policy,
            "advisory_level": self.advisory_level,
            "advisory_note": self.advisory_note,
        }
        data.update(kwargs)
        return PolicyContext(**data)  # type: ignore[arg-type]

    def to_public_dict(self) -> Dict[str, Any]:
        """Serializable summary safe to persist (params are hashed elsewhere)."""
        return {
            "action_name": self.action_name,
            "mind_id": self.mind_id,
            "tenant_id": self.tenant_id,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "requester": self.requester,
            "category": self.category,
            "objective_id": self.objective_id,
            "correlation_id": self.correlation_id,
            "granted_scopes": sorted(self.granted_scopes),
            "ownership": self.ownership,
            "data_sensitivity": self.data_sensitivity,
            "external": self.external,
            "reversible": self.reversible,
            "physical": self.physical,
            "destructive": self.destructive,
            "cost_essence": self.cost_essence,
            "budget_remaining_essence": self.budget_remaining_essence,
            "lifecycle_state": self.lifecycle_state,
            "emergency_stop": self.emergency_stop,
            "trust_level": self.trust_level,
        }


@dataclass(frozen=True)
class PolicyDecision:
    """The engine's verdict plus the evidence for it."""

    decision: Decision
    risk: RiskAssessment
    reason_code: str
    explanation: str
    matched_rules: Tuple[str, ...] = ()
    policy_version: str = POLICY_VERSION
    charter_version: str = CHARTER_VERSION
    required_scopes: Tuple[str, ...] = ()
    missing_scopes: Tuple[str, ...] = ()
    requires_human: bool = False
    approver_role: Optional[str] = None
    advisory: Optional[str] = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    capability: Optional[CapabilityProfile] = None

    # -- convenience ------------------------------------------------ #
    @property
    def risk_level(self) -> RiskLevel:
        return self.risk.level

    @property
    def permits_execution(self) -> bool:
        return self.decision.permits_execution

    @property
    def requires_approval(self) -> bool:
        return self.decision is Decision.REQUIRE_APPROVAL

    @property
    def blocked(self) -> bool:
        return self.decision.blocks

    @property
    def emergency_stop(self) -> bool:
        return self.decision is Decision.EMERGENCY_STOP

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "risk": self.risk.to_dict(),
            "reason_code": self.reason_code,
            "explanation": self.explanation,
            "matched_rules": list(self.matched_rules),
            "policy_version": self.policy_version,
            "charter_version": self.charter_version,
            "required_scopes": list(self.required_scopes),
            "missing_scopes": list(self.missing_scopes),
            "requires_human": self.requires_human,
            "approver_role": self.approver_role,
            "advisory": self.advisory,
            "evaluated_at": self.evaluated_at.isoformat(),
            "capability": self.capability.to_dict() if self.capability else None,
        }


class PolicyEngine:
    """Deterministic, context-aware action gate."""

    def __init__(
        self,
        registry: Optional[CapabilityRegistry] = None,
        *,
        policy_version: str = POLICY_VERSION,
    ) -> None:
        self.registry = registry or get_capability_registry()
        self.policy_version = policy_version

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def assess_capability(
        self, action_name: str, category: Optional[str] = None
    ) -> CapabilityProfile:
        """Declared (or conservatively inferred) facts about a capability."""
        return self.registry.profile_for(action_name, category=category)

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """Evaluate one action. Never raises; errors fail closed."""
        try:
            return self._evaluate(context)
        except Exception as exc:  # pragma: no cover - defensive, must still fail closed
            logger.exception("policy evaluation failed; failing closed")
            return PolicyDecision(
                decision=Decision.DENY,
                risk=RiskAssessment(level=RiskLevel.R5),
                reason_code="policy_error_fail_closed",
                explanation=(
                    "Policy evaluation failed, so the action was refused. "
                    f"Error: {type(exc).__name__}"
                ),
                policy_version=self.policy_version,
                capability=self.registry.get(context.action_name),
            )

    # ------------------------------------------------------------------ #
    # Evaluation
    # ------------------------------------------------------------------ #
    def _evaluate(self, ctx: PolicyContext) -> PolicyDecision:
        matched: list = []
        capability = self.assess_capability(ctx.action_name, ctx.category)
        contributions: list = []
        #: Contextual risk floor, raised (never lowered) as facts are considered.
        context_floor = RiskLevel.R0

        declared_level = capability.risk
        contributions.append(
            (RiskSource.DECLARED, declared_level, f"declared profile for {ctx.action_name}")
        )

        # ---- 1. Constitution: hard prohibitions -------------------------- #
        prohibited_clause = PROHIBITED_CAPABILITIES.get(ctx.action_name)
        if prohibited_clause is None and capability.prohibited_reason:
            prohibited_clause = _clause_for_prohibition(ctx.action_name)
        if capability.risk is RiskLevel.R5:
            matched.append(prohibited_clause or "A1.L3")
            clause = CLAUSES_BY_ID.get(prohibited_clause or "")
            explanation = (
                capability.prohibited_reason
                or (clause.statement if clause else "This capability is prohibited.")
            )
            decision = (
                Decision.EMERGENCY_STOP if capability.catastrophic else Decision.DENY
            )
            return self._build(
                ctx,
                decision=decision,
                risk=RiskAssessment(
                    level=RiskLevel.R5, contributions=tuple(contributions), capability=capability
                ),
                reason_code="constitution_prohibited",
                explanation=f"Refused: {explanation}",
                matched_rules=tuple(matched),
                capability=capability,
                requires_human=False,
            )

        # ---- 2. Tenant hard blocks --------------------------------------- #
        tenant_blocks = _as_str_set(ctx.tenant_policy.get("blocked_capabilities"))
        if ctx.action_name in tenant_blocks:
            matched.append("TENANT.BLOCK")
            return self._build(
                ctx,
                decision=Decision.DENY,
                risk=RiskAssessment(
                    level=RiskLevel.max_of(declared_level, RiskLevel.R3),
                    contributions=tuple(contributions),
                    capability=capability,
                ),
                reason_code="tenant_policy_blocked",
                explanation=(
                    f"Organization policy blocks '{ctx.action_name}' for this tenant."
                ),
                matched_rules=tuple(matched),
                capability=capability,
            )

        # ---- 3. Emergency stop ------------------------------------------- #
        if ctx.emergency_stop:
            if declared_level <= _ALWAYS_OBSERVABLE_MAX_RISK:
                matched.append("A3.C3")
                return self._build(
                    ctx,
                    decision=Decision.ALLOW,
                    risk=RiskAssessment(
                        level=declared_level,
                        contributions=tuple(contributions),
                        capability=capability,
                    ),
                    reason_code="emergency_stop_readonly_allowed",
                    explanation=(
                        "Emergency stop is engaged; read-only observation is still allowed."
                    ),
                    matched_rules=tuple(matched),
                    capability=capability,
                )
            matched.append("A3.C3")
            return self._build(
                ctx,
                decision=Decision.EMERGENCY_STOP,
                risk=RiskAssessment(
                    level=RiskLevel.max_of(declared_level, RiskLevel.R4),
                    contributions=tuple(contributions),
                    capability=capability,
                ),
                reason_code="emergency_stop_engaged",
                explanation=(
                    "Emergency stop is engaged. All state-changing action is halted; "
                    "a human must reset it before this can proceed."
                ),
                matched_rules=tuple(matched),
                capability=capability,
            )

        # ---- 4. Lifecycle ------------------------------------------------- #
        lifecycle = (ctx.lifecycle_state or "active").lower()
        if lifecycle in _HALTED_LIFECYCLE_STATES:
            if declared_level <= _ALWAYS_OBSERVABLE_MAX_RISK:
                matched.append("LIFECYCLE.READONLY")
            else:
                matched.append("LIFECYCLE.HALTED")
                return self._build(
                    ctx,
                    decision=Decision.DENY,
                    risk=RiskAssessment(
                        level=RiskLevel.max_of(declared_level, RiskLevel.R2),
                        contributions=tuple(contributions),
                        capability=capability,
                    ),
                    reason_code="lifecycle_halted",
                    explanation=(
                        f"This Mind is '{lifecycle}' and may not change anything."
                    ),
                    matched_rules=tuple(matched),
                    capability=capability,
                )
        elif lifecycle in _RESTRICTED_LIFECYCLE_STATES and declared_level > RiskLevel.R0:
            matched.append("LIFECYCLE.RESTRICTED")
            context_floor = RiskLevel.max_of(context_floor, RiskLevel.R2)
            contributions.append(
                (RiskSource.CONTEXT, RiskLevel.R2, f"lifecycle={lifecycle} requires a decision")
            )

        # ---- 5. Budget ---------------------------------------------------- #
        if (
            ctx.cost_essence is not None
            and ctx.budget_remaining_essence is not None
            and ctx.cost_essence > ctx.budget_remaining_essence
        ):
            matched.append("A2.L7")
            return self._build(
                ctx,
                decision=Decision.DENY,
                risk=RiskAssessment(
                    level=RiskLevel.max_of(declared_level, RiskLevel.R3),
                    contributions=tuple(contributions),
                    capability=capability,
                ),
                reason_code="budget_exceeded",
                explanation=(
                    f"Cost {ctx.cost_essence} exceeds the remaining budget "
                    f"{ctx.budget_remaining_essence} for this objective."
                ),
                matched_rules=tuple(matched),
                capability=capability,
            )

        # ---- 6. Contextual risk floors ------------------------------------ #
        if ctx.ownership in ("third_party", "unknown") and declared_level > RiskLevel.R0:
            context_floor = RiskLevel.max_of(context_floor, RiskLevel.R2)
            matched.append("SCOPE.THIRD_PARTY")
            contributions.append(
                (RiskSource.CONTEXT, RiskLevel.R2, f"ownership={ctx.ownership}")
            )

        sensitivity = (ctx.data_sensitivity or capability.data_sensitivity or "none").lower()
        sensitivity_floor = _SENSITIVITY_FLOOR.get(sensitivity, RiskLevel.R2)
        if sensitivity_floor > RiskLevel.R0:
            context_floor = RiskLevel.max_of(context_floor, sensitivity_floor)
            contributions.append(
                (RiskSource.CONTEXT, sensitivity_floor, f"data_sensitivity={sensitivity}")
            )
        if sensitivity in ("personal", "regulated"):
            matched.append("A1.L2")
        if sensitivity == "regulated":
            matched.append("A3.C2")

        external = capability.external if ctx.external is None else bool(ctx.external)
        # A remote we do not trust can only affect actions that *do* something.
        # Read-only fetches of public data (R0) stay R0: they disclose nothing
        # about the Mind, and raising them would gate every web search behind an
        # approval for no security gain.
        if (
            external
            and declared_level > RiskLevel.R0
            and ctx.trust_level.lower() in _UNTRUSTED_TRUST_LEVELS
        ):
            context_floor = RiskLevel.max_of(context_floor, RiskLevel.R3)
            contributions.append(
                (RiskSource.CONTEXT, RiskLevel.R3, f"external + trust={ctx.trust_level}")
            )

        reversible = capability.reversible if ctx.reversible is None else bool(ctx.reversible)
        if not reversible and declared_level > RiskLevel.R0:
            context_floor = RiskLevel.max_of(context_floor, RiskLevel.R2)
            context_floor = RiskLevel.max_of(context_floor, RiskLevel.R1)
            contributions.append(
                (RiskSource.CONTEXT, RiskLevel.R2, "irreversible action")
            )

        destructive = (
            capability.destructive if ctx.destructive is None else bool(ctx.destructive)
        )
        if destructive:
            context_floor = RiskLevel.max_of(context_floor, RiskLevel.R3)
            contributions.append((RiskSource.CONTEXT, RiskLevel.R3, "destructive action"))

        physical = capability.physical if ctx.physical is None else bool(ctx.physical)
        if physical:
            context_floor = RiskLevel.max_of(context_floor, RiskLevel.R4)
            matched.append("A1.L1")
            contributions.append(
                (RiskSource.CONTEXT, RiskLevel.R4, "physical-world impact")
            )

        # ---- 7. Advisory (ratchet up only) -------------------------------- #
        advisory_text: Optional[str] = None
        if ctx.advisory_level is not None:
            advisory_level = RiskLevel.coerce(ctx.advisory_level, default=declared_level)
            if advisory_level > declared_level:
                matched.append("A2.L8")
                contributions.append(
                    (
                        RiskSource.ADVISORY,
                        advisory_level,
                        "model advisory raised the level",
                    )
                )
            advisory_text = ctx.advisory_note or f"model advisory: {advisory_level.value}"
        else:
            advisory_level = RiskLevel.R0

        level = RiskLevel.max_of(
            declared_level,
            context_floor,
            advisory_level,
        )
        contributions.append((RiskSource.FLOOR, level, "effective level"))

        # ---- 8. Scopes ---------------------------------------------------- #
        required_scopes = tuple(capability.required_scopes)
        missing_scopes: Tuple[str, ...] = ()
        if required_scopes and level >= RiskLevel.R2:
            missing = tuple(
                scope for scope in required_scopes if scope not in set(ctx.granted_scopes)
            )
            if missing:
                missing_scopes = missing
                matched.append("SCOPE.MISSING")
                level = RiskLevel.max_of(level, RiskLevel.R2)

        assessment = RiskAssessment(
            level=level, contributions=tuple(contributions), capability=capability
        )

        # ---- 9. Disposition ----------------------------------------------- #
        if level is RiskLevel.R5:  # defensive: should be caught in step 1
            return self._build(
                ctx,
                decision=Decision.DENY,
                risk=assessment,
                reason_code="risk_level_prohibited",
                explanation="Effective risk is R5: this is prohibited.",
                matched_rules=tuple(matched),
                capability=capability,
            )

        if level <= RiskLevel.R0:
            return self._build(
                ctx,
                decision=Decision.ALLOW,
                risk=assessment,
                reason_code="read_only_allowed",
                explanation="Read-only or owner-authorized; allowed.",
                matched_rules=tuple(matched),
                capability=capability,
                advisory=advisory_text,
            )

        if level is RiskLevel.R1:
            if missing_scopes:
                return self._approval_decision(
                    ctx,
                    assessment,
                    capability,
                    matched,
                    reason_code="missing_scope",
                    explanation=(
                        "This action is reversible but its required scope "
                        f"({', '.join(missing_scopes)}) has not been granted."
                    ),
                    requires_human=False,
                    advisory=advisory_text,
                )
            return self._build(
                ctx,
                decision=Decision.ALLOW_WITH_RECEIPT,
                risk=assessment,
                reason_code="reversible_internal_allowed",
                explanation=(
                    "Reversible action inside the Mind's own workspace; allowed and "
                    "recorded as a receipt."
                ),
                matched_rules=tuple(matched) + ("A3.C1",),
                capability=capability,
                required_scopes=required_scopes,
                advisory=advisory_text,
            )

        # R2/R3: standing grant may widen autonomy, but only up to R2.
        if level is RiskLevel.R2:
            if missing_scopes:
                return self._approval_decision(
                    ctx,
                    assessment,
                    capability,
                    matched,
                    reason_code="missing_scope",
                    explanation=(
                        "Required scope not granted: "
                        f"{', '.join(missing_scopes)}. A human must approve."
                    ),
                    requires_human=False,
                    advisory=advisory_text,
                )
            if _standing_grant_covers(ctx, level):
                matched.append("TENANT.STANDING_GRANT")
                return self._build(
                    ctx,
                    decision=Decision.ALLOW_WITH_RECEIPT,
                    risk=assessment,
                    reason_code="standing_grant",
                    explanation=(
                        "Organization policy grants standing approval for this risk "
                        "class; allowed and recorded."
                    ),
                    matched_rules=tuple(matched),
                    capability=capability,
                    required_scopes=required_scopes,
                    advisory=advisory_text,
                )
            return self._approval_decision(
                ctx,
                assessment,
                capability,
                matched,
                reason_code="external_change_requires_approval",
                explanation=(
                    "This changes something outside the Mind's own workspace. "
                    "A human must approve it first."
                ),
                requires_human=False,
                advisory=advisory_text,
            )

        if level is RiskLevel.R3:
            return self._approval_decision(
                ctx,
                assessment,
                capability,
                matched,
                reason_code="consequential_requires_approval",
                explanation=(
                    capability.prohibited_reason
                    or "This is consequential, external, or irreversible "
                    "(communication, deployment, purchase, privileged administration). "
                    "A human must approve it first."
                ),
                requires_human=False,
                advisory=advisory_text,
                missing_scopes=missing_scopes,
            )

        # R4
        if "A3.C2" not in matched:
            matched.append("A3.C2")
        return self._approval_decision(
            ctx,
            assessment,
            capability,
            matched,
            reason_code="regulated_domain_requires_human",
            explanation=(
                "This has legal, medical, financial, employment, safety-critical, or "
                "physical-world impact. A responsible human owner must approve it."
            ),
            requires_human=True,
            advisory=advisory_text,
            missing_scopes=missing_scopes,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _approval_decision(
        self,
        ctx: PolicyContext,
        assessment: RiskAssessment,
        capability: CapabilityProfile,
        matched: Sequence[str],
        *,
        reason_code: str,
        explanation: str,
        requires_human: bool,
        advisory: Optional[str] = None,
        missing_scopes: Tuple[str, ...] = (),
    ) -> PolicyDecision:
        return self._build(
            ctx,
            decision=Decision.REQUIRE_APPROVAL,
            risk=assessment,
            reason_code=reason_code,
            explanation=explanation,
            matched_rules=tuple(matched),
            capability=capability,
            missing_scopes=missing_scopes,
            requires_human=requires_human,
            approver_role="human_owner" if requires_human else "owner_or_delegate",
            advisory=advisory,
        )

    def _build(
        self,
        ctx: PolicyContext,
        *,
        decision: Decision,
        risk: RiskAssessment,
        reason_code: str,
        explanation: str,
        matched_rules: Sequence[str],
        capability: Optional[CapabilityProfile],
        required_scopes: Tuple[str, ...] = (),
        missing_scopes: Tuple[str, ...] = (),
        requires_human: bool = False,
        approver_role: Optional[str] = None,
        advisory: Optional[str] = None,
    ) -> PolicyDecision:
        return PolicyDecision(
            decision=decision,
            risk=risk,
            reason_code=reason_code,
            explanation=explanation,
            matched_rules=tuple(dict.fromkeys(matched_rules)),
            policy_version=self.policy_version,
            required_scopes=required_scopes or (capability.required_scopes if capability else ()),
            missing_scopes=missing_scopes,
            requires_human=requires_human,
            approver_role=approver_role,
            advisory=advisory,
            capability=capability,
        )


def _clause_for_prohibition(action_name: str) -> Optional[str]:
    """Find the clause that prohibits a capability, if any."""
    for clause_id, clause in CLAUSES_BY_ID.items():
        if action_name in clause.prohibited_capabilities:
            return clause_id
    return None


def _as_str_set(value: Any) -> FrozenSet[str]:
    if not value:
        return frozenset()
    if isinstance(value, str):
        return frozenset({value})
    try:
        return frozenset(str(item) for item in value)
    except TypeError:
        return frozenset()


def _standing_grant_covers(ctx: PolicyContext, level: RiskLevel) -> bool:
    """Whether tenant policy auto-approves this risk level.

    Deliberately capped at :data:`STANDING_GRANT_MAX_RISK`. A tenant can widen
    autonomy for low-risk recurring work, and nothing more.
    """
    if level > STANDING_GRANT_MAX_RISK:
        return False
    policy = ctx.tenant_policy or {}
    raw = policy.get("auto_approve_risk_levels")
    if not raw:
        return False
    if isinstance(raw, str):
        raw = [raw]
    try:
        granted = {RiskLevel.coerce(item, default=RiskLevel.R5) for item in raw}
    except TypeError:
        return False
    if level not in granted:
        return False
    # A standing grant must be scoped to capabilities/categories, never blanket.
    allowed_caps = _as_str_set(policy.get("auto_approve_capabilities"))
    allowed_cats = _as_str_set(policy.get("auto_approve_categories"))
    if not allowed_caps and not allowed_cats:
        return False
    if ctx.action_name in allowed_caps:
        return True
    category = (ctx.category or "").upper()
    return bool(category and category in allowed_cats)


# --------------------------------------------------------------------------- #
# Module-level default engine
# --------------------------------------------------------------------------- #

_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Process-wide policy engine."""
    global _engine
    if _engine is None:
        _engine = PolicyEngine()
    return _engine


def reset_policy_engine(engine: Optional[PolicyEngine] = None) -> PolicyEngine:
    """Replace the process-wide engine (tests, plugin reload)."""
    global _engine
    _engine = engine or PolicyEngine()
    return _engine
