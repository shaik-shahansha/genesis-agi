"""End-to-end governance gate tests.

These exercise the composed control plane the action executor actually calls.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from genesis.governance import Decision, PolicyContext, ReceiptOutcome
from genesis.governance.models import EventType


def context(gate, **kwargs):
    params = kwargs.pop("parameters", {})
    action_name = kwargs.pop("action_name")
    return gate.build_context(
        action_name=action_name,
        parameters=params,
        mind_id=kwargs.pop("mind_id", "gm_a"),
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# Allow paths
# --------------------------------------------------------------------------- #


def test_read_only_action_is_allowed_without_a_receipt(gate):
    result = gate.authorize(
        context(gate, action_name="search_memory", parameters={"query": "x"}),
        action_id="ACT-1",
        requested_by="mind",
    )
    assert result.allowed
    assert result.decision.decision is Decision.ALLOW
    assert result.receipt is None


def test_reversible_internal_action_is_allowed_with_a_receipt(gate):
    result = gate.authorize(
        context(gate, action_name="create_task", parameters={"title": "x"}),
        action_id="ACT-1",
        requested_by="mind",
    )
    assert result.allowed
    assert result.decision.decision is Decision.ALLOW_WITH_RECEIPT
    assert result.receipt is not None
    assert result.receipt.outcome == ReceiptOutcome.ALLOWED.value
    assert result.receipt.risk_level == "R1"


def test_policy_evaluation_is_always_journaled(gate, audit):
    gate.authorize(
        context(gate, action_name="search_memory", parameters={"query": "x"}),
        action_id="ACT-1",
    )
    events = audit.events(mind_id="gm_a", event_type=EventType.ACTION_POLICY_EVALUATED)
    assert len(events) == 1
    assert events[0].payload["action_name"] == "search_memory"


# --------------------------------------------------------------------------- #
# Approval path
# --------------------------------------------------------------------------- #


def test_consequential_action_is_queued_not_executed(gate):
    result = gate.authorize(
        context(
            gate,
            action_name="send_email",
            parameters={"to": "a@b.c", "subject": "s", "body": "b"},
            granted_scopes=("comms.email.send",),
        ),
        action_id="ACT-2",
        requested_by="mind",
        intent="email the class",
    )
    assert not result.allowed
    assert result.requires_approval
    assert result.approval is not None
    assert result.approval.status == "WAITING_FOR_APPROVAL"
    assert result.receipt is not None
    assert result.receipt.outcome == ReceiptOutcome.REQUIRES_APPROVAL.value


def test_approval_then_grant_allows_execution(gate, approvals):
    ctx = context(
        gate,
        action_name="send_email",
        parameters={"to": "a@b.c", "subject": "s", "body": "b"},
        granted_scopes=("comms.email.send",),
    )
    first = gate.authorize(ctx, action_id="ACT-2", requested_by="mind")
    assert not first.allowed

    grant = approvals.approve(first.approval.approval_id, approver_id="owner@example.com")
    second = gate.authorize(
        ctx, action_id="ACT-3", requested_by="mind", grant_id=grant.grant_id
    )
    assert second.allowed
    assert second.reason == "grant_redeemed"
    assert second.receipt.outcome == ReceiptOutcome.ALLOWED.value
    assert second.receipt.approval_id == first.approval.approval_id


def test_grant_for_different_parameters_does_not_allow_execution(gate, approvals):
    ctx = context(
        gate,
        action_name="send_email",
        parameters={"to": "a@b.c", "subject": "s", "body": "b"},
        granted_scopes=("comms.email.send",),
    )
    first = gate.authorize(ctx, action_id="ACT-2", requested_by="mind")
    grant = approvals.approve(first.approval.approval_id, approver_id="owner")

    tampered = context(
        gate,
        action_name="send_email",
        parameters={"to": "attacker@evil.example", "subject": "s", "body": "b"},
        granted_scopes=("comms.email.send",),
    )
    result = gate.authorize(
        tampered, action_id="ACT-4", requested_by="mind", grant_id=grant.grant_id
    )
    assert not result.allowed
    assert "parameters changed" in result.reason
    # And it is queued for a fresh human decision rather than silently dropped.
    assert result.approval is not None


def test_second_use_of_the_same_grant_is_refused(gate, approvals):
    ctx = context(
        gate,
        action_name="send_email",
        parameters={"to": "a@b.c", "subject": "s", "body": "b"},
        granted_scopes=("comms.email.send",),
    )
    first = gate.authorize(ctx, action_id="ACT-2", requested_by="mind")
    grant = approvals.approve(first.approval.approval_id, approver_id="owner")

    assert gate.authorize(ctx, action_id="ACT-3", grant_id=grant.grant_id).allowed
    replay = gate.authorize(ctx, action_id="ACT-4", grant_id=grant.grant_id)
    assert not replay.allowed


# --------------------------------------------------------------------------- #
# Blocked paths
# --------------------------------------------------------------------------- #


def test_prohibited_capability_is_denied_and_receipted(gate, audit):
    result = gate.authorize(
        context(gate, action_name="execute_exploit", parameters={"target": "x"}),
        action_id="ACT-9",
        requested_by="mind",
    )
    assert not result.allowed
    assert result.decision.decision is Decision.DENY
    assert result.receipt is not None
    assert result.receipt.outcome == ReceiptOutcome.BLOCKED.value
    blocked = audit.events(mind_id="gm_a", event_type=EventType.ACTION_BLOCKED)
    assert len(blocked) == 1


def test_catastrophic_capability_latches_the_emergency_stop(gate, estop, audit):
    result = gate.authorize(
        context(gate, action_name="harm_humans", parameters={}),
        action_id="ACT-9",
        requested_by="mind",
    )
    assert result.decision.decision is Decision.EMERGENCY_STOP
    assert estop.is_engaged("gm_a")
    assert audit.events(mind_id="gm_a", event_type=EventType.ACTION_EMERGENCY_STOP)
    assert result.receipt.outcome == ReceiptOutcome.EMERGENCY_STOP.value


def test_a_latched_stop_blocks_subsequent_actions(gate, estop):
    estop.engage("gm_a", actor_id="operator", reason="suspicious behaviour")
    result = gate.authorize(
        context(gate, action_name="create_task", parameters={"title": "x"}),
        action_id="ACT-10",
    )
    assert result.decision.decision is Decision.EMERGENCY_STOP


def test_a_latched_stop_still_permits_read_only_observation(gate, estop):
    estop.engage("gm_a", actor_id="operator", reason="investigating")
    result = gate.authorize(
        context(gate, action_name="search_memory", parameters={"query": "x"}),
        action_id="ACT-11",
    )
    assert result.allowed


def test_released_stop_restores_normal_operation(gate, estop):
    estop.engage("gm_a", actor_id="operator", reason="test")
    estop.release("gm_a", actor_id="operator", note="resolved")
    result = gate.authorize(
        context(gate, action_name="create_task", parameters={"title": "x"}),
        action_id="ACT-12",
    )
    assert result.allowed


def test_stop_state_is_rehydrated_from_the_journal(gate, estop, audit):
    from genesis.governance import EmergencyStopService

    estop.engage("gm_a", actor_id="operator", reason="incident 42")
    fresh = EmergencyStopService(audit=audit)
    assert fresh.is_engaged("gm_a") is False
    state = fresh.rehydrate("gm_a")
    assert state.engaged is True
    assert state.reason == "incident 42"


def test_stop_release_is_rehydrated_too(audit):
    from genesis.governance import EmergencyStopService

    service = EmergencyStopService(audit=audit)
    service.engage("gm_a", actor_id="operator", reason="incident")
    service.engage("gm_b", actor_id="operator", reason="other")
    service.release("gm_a", actor_id="operator", note="fine")

    fresh = EmergencyStopService(audit=audit)
    assert fresh.rehydrate("gm_a").engaged is False


# --------------------------------------------------------------------------- #
# Outcome recording
# --------------------------------------------------------------------------- #


def test_record_outcome_writes_a_terminal_receipt(gate):
    ctx = context(gate, action_name="create_task", parameters={"title": "x"})
    result = gate.authorize(ctx, action_id="ACT-1", requested_by="mind")
    from datetime import datetime, timezone

    start = datetime.now(timezone.utc)
    receipt = gate.record_outcome(
        ctx,
        result.decision,
        action_id="ACT-1",
        outcome=ReceiptOutcome.EXECUTED.value,
        requested_by="mind",
        started_at=start,
        completed_at=start,
        result_summary="task created",
    )
    assert receipt.outcome == ReceiptOutcome.EXECUTED.value
    assert receipt.evidence["result_summary"] == "task created"


def test_record_outcome_journals_the_lifecycle_event(gate, audit):
    ctx = context(gate, action_name="create_task", parameters={"title": "x"})
    result = gate.authorize(ctx, action_id="ACT-1")
    gate.record_outcome(
        ctx, result.decision, action_id="ACT-1", outcome=ReceiptOutcome.FAILED.value,
        error=TimeoutError("timed out"),
    )
    events = audit.events(mind_id="gm_a", event_type=EventType.ACTION_FAILED)
    assert len(events) == 1
    assert "timed out" in events[0].payload["error"]


def test_receipts_never_contain_a_raw_secret(gate, audit):
    ctx = context(
        gate,
        action_name="create_task",
        parameters={"title": "x", "api_key": "sk-live-abcdef0123456789"},
    )
    result = gate.authorize(ctx, action_id="ACT-1", requested_by="mind")
    gate.record_outcome(
        ctx, result.decision, action_id="ACT-1", outcome=ReceiptOutcome.EXECUTED.value
    )
    stored = audit.receipts(mind_id="gm_a")
    assert stored
    assert "sk-live-abcdef0123456789" not in str([r.to_dict() for r in stored])


# --------------------------------------------------------------------------- #
# Context building
# --------------------------------------------------------------------------- #


def test_build_context_reads_the_emergency_stop(gate, estop):
    estop.engage("gm_a", actor_id="operator", reason="x")
    ctx = context(gate, action_name="create_task", parameters={})
    assert ctx.emergency_stop is True


def test_build_context_derives_category_from_the_registry(gate):
    ctx = context(gate, action_name="send_email", parameters={})
    assert ctx.category == "COMMUNICATION"


def test_build_context_marks_physical_capabilities(gate):
    ctx = context(gate, action_name="actuate_robot", parameters={})
    assert ctx.physical is True


def test_autonomy_permissions_grant_a_scope(gate):
    class FakeAutonomy:
        autonomous_permissions = ["comms.email.send"]
        initiative_level = "medium"

    ctx = gate.build_context(
        action_name="send_email",
        parameters={"to": "a@b.c"},
        mind_id="gm_a",
        autonomy=FakeAutonomy(),
    )
    assert "comms.email.send" in ctx.granted_scopes


def test_autonomy_cannot_disable_the_approval_requirement(gate):
    class Permissive:
        autonomous_permissions = ["*"]
        initiative_level = "maximum"

    ctx = gate.build_context(
        action_name="send_email",
        parameters={"to": "a@b.c"},
        mind_id="gm_a",
        autonomy=Permissive(),
    )
    result = gate.authorize(ctx, action_id="ACT-1", requested_by="mind")
    assert not result.allowed
    assert result.requires_approval


def test_authorization_result_is_serializable(gate):
    result = gate.authorize(
        context(gate, action_name="search_memory", parameters={"query": "x"}),
        action_id="ACT-1",
    )
    payload = result.to_dict()
    assert payload["allowed"] is True
    assert payload["decision"]["risk"]["level"] == "R0"


def test_gate_survives_an_audit_failure(gate, monkeypatch):
    """A journal outage must not crash the action path."""
    def boom(*args, **kwargs):
        raise RuntimeError("journal unavailable")

    monkeypatch.setattr(gate.audit, "record", boom)
    result = gate.authorize(
        context(gate, action_name="search_memory", parameters={"query": "x"}),
        action_id="ACT-1",
    )
    assert result.allowed
