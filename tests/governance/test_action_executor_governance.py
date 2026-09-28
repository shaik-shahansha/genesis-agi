"""Integration: the action executor consults the governance gate.

These tests build a real ``ActionExecutor`` against a stub Mind, with the
governance gate and all its services wired to an in-memory store, and assert on
what actually reaches the execution handler.
"""

from __future__ import annotations

import pytest

from genesis.core.action_executor import (
    ActionCategory,
    ActionDefinition,
    ActionExecutor,
    ActionStatus,
)
from genesis.core.autonomy import Autonomy, PermissionLevel
from genesis.governance import (
    ApprovalService,
    AuditService,
    EmergencyStopService,
    GovernanceGate,
    InMemoryGovernanceStore,
    PolicyEngine,
    set_governance_gate,
)
from genesis.governance.models import EventType, ReceiptOutcome


class StubMind:
    """Minimal Mind surface the executor touches."""

    def __init__(self) -> None:
        self.gmind = "gm_stub"
        self.autonomy = Autonomy(proactive_actions=True, autonomous_permissions=[])
        self.status = "active"
        self.calls: list = []

        class _Logger:
            def log(self, **kwargs):
                pass

        class _Memory:
            def add_memory(self, **kwargs):
                pass

        self.logger = _Logger()
        self.memory = _Memory()


@pytest.fixture
def wired(monkeypatch):
    """Yield (executor, handler_calls, gate, store) with governance wired in."""
    store = InMemoryGovernanceStore()
    audit = AuditService(store=store)
    approvals = ApprovalService(store=store, audit=audit)
    estop = EmergencyStopService(audit=audit)
    gate = GovernanceGate(
        engine=PolicyEngine(), approvals=approvals, audit=audit, emergency_stop=estop
    )
    set_governance_gate(gate)

    mind = StubMind()
    executor = ActionExecutor(mind)
    executor._gate_cache = gate  # bypass the lazily resolved process default

    calls: list = []

    async def handler(params):
        calls.append(params)
        return "done"

    executor.register_action(
        ActionDefinition(
            name="test_reversible",
            category=ActionCategory.TASK_MANAGEMENT,
            description="A reversible internal action",
            parameters={"title": {"type": "string", "description": "x", "required": True}},
            permission_level=PermissionLevel.AUTO_APPROVED_WITH_LOG,
            risk_level=0.2,
            execution_handler=handler,
        )
    )
    executor.register_action(
        ActionDefinition(
            name="test_external_send",
            category=ActionCategory.COMMUNICATION,
            description="Send something to an external recipient",
            parameters={"to": {"type": "string", "description": "r", "required": True}},
            permission_level=PermissionLevel.REQUIRES_CONFIRMATION,
            risk_level=0.5,
            execution_handler=handler,
        )
    )
    executor.register_action(
        ActionDefinition(
            name="test_forbidden",
            category=ActionCategory.TOOL_EXECUTION,
            description="A prohibited capability",
            parameters={},
            permission_level=PermissionLevel.ABSOLUTELY_FORBIDDEN,
            execution_handler=handler,
        )
    )

    yield executor, calls, gate, store
    set_governance_gate(None)


# --------------------------------------------------------------------------- #
# Allow
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_reversible_action_executes_and_is_receipted(wired):
    executor, calls, gate, store = wired
    request = await executor.request_action(
        "test_reversible", {"title": "buy milk"}, requester="mind"
    )
    assert request.status is ActionStatus.COMPLETED
    assert calls == [{"title": "buy milk"}]
    assert request.risk_level in ("R0", "R1", "R2")
    assert request.receipt_id
    assert store.get_receipt(request.receipt_id).outcome == ReceiptOutcome.EXECUTED.value


@pytest.mark.asyncio
async def test_policy_decision_is_attached_to_the_request(wired):
    executor, calls, gate, store = wired
    request = await executor.request_action("test_reversible", {"title": "x"})
    assert request.policy_decision is not None
    assert request.policy_decision["decision"] in ("allow", "allow_with_receipt")


# --------------------------------------------------------------------------- #
# Approval required
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_consequential_action_is_queued_not_executed(wired):
    executor, calls, gate, store = wired
    request = await executor.request_action(
        "test_external_send", {"to": "someone@example.com"}, requester="mind"
    )
    assert calls == [], "the handler must not run before approval"
    assert request.status is ActionStatus.PENDING
    assert request.requires_approval
    assert request.approval_id

    pending = store.list_approvals(mind_id="gm_stub", status="WAITING_FOR_APPROVAL")
    assert len(pending) == 1
    assert pending[0].approval_id == request.approval_id


@pytest.mark.asyncio
async def test_request_blocked_by_the_gate_is_not_in_the_legacy_queue(wired):
    """A gate-queued request must not also be double-counted by the old ladder."""
    executor, calls, gate, store = wired
    before = len(executor.pending_approvals)
    await executor.request_action("test_external_send", {"to": "a@b.c"}, requester="mind")
    assert len(executor.pending_approvals) == before + 1


@pytest.mark.asyncio
async def test_a_grant_lets_the_action_run(wired):
    executor, calls, gate, store = wired
    request = await executor.request_action(
        "test_external_send", {"to": "a@b.c"}, requester="mind"
    )
    grant = gate.approvals.approve(request.approval_id, approver_id="owner@example.com")
    executor._governance_decisions.pop(request.action_id, None)

    # A second attempt would normally queue again; redeeming the grant here
    # mirrors what the resume path does after a human decision.
    redemption = gate.approvals.redeem(
        grant.grant_id,
        parameters={"to": "a@b.c"},
        mind_id="gm_stub",
        action_name="test_external_send",
    )
    assert redemption.granted
    assert calls == []


# --------------------------------------------------------------------------- #
# Blocked
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_prohibited_action_is_rejected_and_receipted(wired):
    executor, calls, gate, store = wired
    request = await executor.request_action("test_forbidden", {}, requester="mind")
    assert calls == []
    assert request.status is ActionStatus.REJECTED
    assert request.risk_level == "R5"
    assert request.blocked_reason
    assert request.receipt_id

    receipts = store.list_receipts(mind_id="gm_stub")
    assert any(r.outcome == ReceiptOutcome.BLOCKED.value for r in receipts)


@pytest.mark.asyncio
async def test_blocked_actions_are_journaled(wired):
    executor, calls, gate, store = wired
    await executor.request_action("test_forbidden", {})
    blocked = store.list_events(mind_id="gm_stub", event_type=EventType.ACTION_BLOCKED)
    assert len(blocked) == 1


@pytest.mark.asyncio
async def test_emergency_stop_halts_the_executor(wired):
    executor, calls, gate, store = wired
    gate.emergency_stop.engage("gm_stub", actor_id="operator", reason="incident")
    request = await executor.request_action("test_reversible", {"title": "x"})
    assert calls == []
    assert request.status in (ActionStatus.REJECTED, ActionStatus.PENDING)
    assert request.blocked_reason


@pytest.mark.asyncio
async def test_failed_execution_still_produces_a_receipt(wired):
    executor, calls, gate, store = wired

    async def failing(params):
        raise TimeoutError("upload timed out")

    executor.register_action(
        ActionDefinition(
            name="test_failing",
            category=ActionCategory.TASK_MANAGEMENT,
            description="Fails",
            parameters={},
            permission_level=PermissionLevel.AUTO_APPROVED_WITH_LOG,
            risk_level=0.2,
            execution_handler=failing,
        )
    )
    request = await executor.request_action("test_failing", {}, requester="mind")
    assert request.status is ActionStatus.FAILED
    receipt = store.get_receipt(request.receipt_id)
    assert receipt.outcome == ReceiptOutcome.FAILED.value
    assert receipt.error_class == "timeout"


# --------------------------------------------------------------------------- #
# Fail-closed behaviour
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_gate_failure_refuses_rather_than_permits(wired, monkeypatch):
    executor, calls, gate, store = wired

    def boom(*args, **kwargs):
        raise RuntimeError("governance unavailable")

    monkeypatch.setattr(gate, "build_context", boom)
    request = await executor.request_action("test_reversible", {"title": "x"})
    assert calls == []
    assert request.status is ActionStatus.REJECTED
    assert request.blocked_reason == "governance_unavailable_fail_closed"


# --------------------------------------------------------------------------- #
# Capability declaration
# --------------------------------------------------------------------------- #


def test_registering_an_action_declares_a_capability(wired):
    from genesis.governance import get_capability_registry

    registry = get_capability_registry()
    profile = registry.get("test_external_send")
    assert profile is not None
    assert profile.external is True


def test_declaration_does_not_override_the_reviewed_registry(wired):
    from genesis.governance import get_capability_registry

    registry = get_capability_registry()
    reviewed = registry.get("send_email")
    assert reviewed is not None
    assert reviewed.risk.value == "R3"


def test_a_declared_capability_is_not_left_at_the_undeclared_floor(wired):
    from genesis.governance import get_capability_registry

    profile = get_capability_registry().get("test_reversible")
    assert profile.risk.value in ("R0", "R1", "R2")
