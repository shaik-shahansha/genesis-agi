"""Genesis governance control plane.

Accountable autonomy in four cooperating services, all deterministic at the
boundary that matters - the action, not the prompt:

* :mod:`genesis.governance.policy` - ``PolicyEngine``: risk levels R0-R5 and the
  five dispositions (allow / allow_with_receipt / require_approval / deny /
  emergency_stop).
* :mod:`genesis.governance.approval` - ``ApprovalService``: a persistent state
  machine with parameter-bound, single-use, expiring grants.
* :mod:`genesis.governance.audit` - ``AuditService``: append-only, hash-chained
  event journal and immutable action receipts, redacted in the writer.
* :mod:`genesis.governance.guard` - ``GovernanceGate``: the single entry point
  the action executor calls.

Supporting modules: :mod:`~genesis.governance.risk` (capability registry),
:mod:`~genesis.governance.constitution_rules` (the charter as executable rules),
:mod:`~genesis.governance.redact` (redaction by construction),
:mod:`~genesis.governance.store` (durable persistence),
:mod:`~genesis.governance.estop` (emergency stop).

Architecture decision records: ``docs/architecture/adr/ADR-0006`` to ``ADR-0008``.
"""

from __future__ import annotations

from genesis.governance.approval import (
    DEFAULT_APPROVAL_TTL,
    DEFAULT_GRANT_TTL,
    ApprovalError,
    ApprovalNotFoundError,
    ApprovalService,
    ApprovalTransitionError,
    GrantRedemptionError,
    Redemption,
    material_parameters,
    parameters_fingerprint,
)
from genesis.governance.audit import AuditService, get_audit_service, new_id
from genesis.governance.constitution_rules import (
    CHARTER_VERSION,
    CLAUSES,
    Enforcement,
    unmapped_violations,
)
from genesis.governance.estop import (
    EmergencyStopService,
    EmergencyStopState,
    get_emergency_stop_service,
)
from genesis.governance.guard import (
    AuthorizationResult,
    GovernanceGate,
    get_governance_gate,
    set_governance_gate,
)
from genesis.governance.models import (
    APPROVAL_TRANSITIONS,
    EVENT_SCHEMA_VERSION,
    ActionReceipt,
    ActorType,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    EventType,
    PermissionGrant,
    ReceiptOutcome,
    can_transition,
)
from genesis.governance.policy import (
    POLICY_VERSION,
    STANDING_GRANT_MAX_RISK,
    Decision,
    PolicyContext,
    PolicyDecision,
    PolicyEngine,
    get_policy_engine,
    reset_policy_engine,
)
from genesis.governance.receipts import build_receipt, classify_error
from genesis.governance.redact import redact_payload, stable_hash
from genesis.governance.risk import (
    CapabilityProfile,
    CapabilityRegistry,
    RiskAssessment,
    RiskLevel,
    get_capability_registry,
    register_capability,
)
from genesis.governance.store import (
    GovernanceStoreError,
    InMemoryGovernanceStore,
    JournalVerification,
    SqlAlchemyGovernanceStore,
    get_governance_store,
    set_governance_store,
)

__all__ = [
    # policy
    "Decision",
    "PolicyContext",
    "PolicyDecision",
    "PolicyEngine",
    "POLICY_VERSION",
    "STANDING_GRANT_MAX_RISK",
    "get_policy_engine",
    "reset_policy_engine",
    # risk
    "RiskLevel",
    "RiskAssessment",
    "CapabilityProfile",
    "CapabilityRegistry",
    "get_capability_registry",
    "register_capability",
    # charter
    "CHARTER_VERSION",
    "CLAUSES",
    "Enforcement",
    "unmapped_violations",
    # approval
    "ApprovalService",
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalError",
    "ApprovalNotFoundError",
    "ApprovalTransitionError",
    "GrantRedemptionError",
    "PermissionGrant",
    "Redemption",
    "APPROVAL_TRANSITIONS",
    "can_transition",
    "material_parameters",
    "parameters_fingerprint",
    "DEFAULT_APPROVAL_TTL",
    "DEFAULT_GRANT_TTL",
    # audit
    "AuditService",
    "AuditEvent",
    "ActionReceipt",
    "EventType",
    "ActorType",
    "ReceiptOutcome",
    "EVENT_SCHEMA_VERSION",
    "get_audit_service",
    "build_receipt",
    "classify_error",
    "new_id",
    "redact_payload",
    "stable_hash",
    # store
    "JournalVerification",
    "GovernanceStoreError",
    "InMemoryGovernanceStore",
    "SqlAlchemyGovernanceStore",
    "get_governance_store",
    "set_governance_store",
    # estop
    "EmergencyStopService",
    "EmergencyStopState",
    "get_emergency_stop_service",
    # gate
    "GovernanceGate",
    "AuthorizationResult",
    "get_governance_gate",
    "set_governance_gate",
]
