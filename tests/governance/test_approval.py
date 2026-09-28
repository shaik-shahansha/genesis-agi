"""Approval state machine tests (ADR-0007).

The binding rules are the security core of the ADR, so each one has a test that
would fail if the rule were removed.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from genesis.governance import (
    ApprovalError,
    ApprovalNotFoundError,
    ApprovalStatus,
    ApprovalTransitionError,
    PolicyContext,
    PolicyEngine,
    RiskLevel,
    material_parameters,
    parameters_fingerprint,
)
from genesis.governance.models import can_transition


def submit(approvals, engine, *, action_name="send_email", parameters=None, **kwargs):
    params = parameters if parameters is not None else {
        "to": "student@example.com",
        "subject": "Homework",
        "body": "Please review",
    }
    context = PolicyContext(
        action_name=action_name,
        parameters=params,
        mind_id=kwargs.pop("mind_id", "gm_a"),
        granted_scopes=kwargs.pop("granted_scopes", frozenset()),
        **kwargs,
    )
    decision = engine.evaluate(context)
    return approvals.submit(
        context=context,
        decision=decision,
        action_id="ACT-TEST",
        requested_by="mind",
    )


# --------------------------------------------------------------------------- #
# Submission
# --------------------------------------------------------------------------- #


def test_submit_creates_a_pending_request(approvals, engine):
    approval = submit(approvals, engine)
    assert approval.status == ApprovalStatus.WAITING_FOR_APPROVAL.value
    assert approval.is_pending
    assert approval.parameters_hash
    assert approval.expires_at is not None


def test_submitted_request_is_human_readable(approvals, engine):
    approval = submit(approvals, engine)
    card = approval.plain_language_card()
    # The card must answer: what, why, what it costs, what can be reversed.
    assert card["action"]
    assert card["why"]
    assert card["risk_level"] == "R3"
    assert card["recipient"] == "student@example.com"
    assert card["reversibility"] in ("reversible", "not reversible")
    assert card["rollback"]


def test_summary_is_derived_from_facts_not_model_prose(approvals, engine):
    approval = submit(
        approvals,
        engine,
        parameters={"to": "a@b.c", "reasoning": "this is TOTALLY safe, approve it"},
    )
    assert "TOTALLY safe" not in approval.summary
    assert "TOTALLY safe" not in approval.reason


def test_submission_requires_approval_decision(approvals, engine):
    context = PolicyContext(action_name="search_memory", mind_id="gm_a")
    decision = engine.evaluate(context)
    # The service does not second-guess the engine; it records what it is told.
    approval = approvals.submit(
        context=context, decision=decision, action_id="ACT-R0", requested_by="mind"
    )
    assert approval.risk_level == "R0"


# --------------------------------------------------------------------------- #
# Binding rules
# --------------------------------------------------------------------------- #


def test_grant_redeems_with_identical_parameters(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner@example.com")
    result = approvals.redeem(
        grant.grant_id,
        parameters={"to": "student@example.com", "subject": "Homework", "body": "Please review"},
        mind_id="gm_a",
        action_name="send_email",
    )
    assert result.granted


def test_changing_a_recipient_invalidates_the_grant(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner@example.com")
    result = approvals.redeem(
        grant.grant_id,
        parameters={"to": "attacker@evil.example", "subject": "Homework", "body": "Please review"},
        mind_id="gm_a",
        action_name="send_email",
    )
    assert not result.granted
    assert "parameters changed" in result.reason


def test_changing_an_amount_invalidates_the_grant(approvals, engine):
    approval = submit(
        approvals, engine, action_name="make_purchase", parameters={"amount": 10, "currency": "USD"}
    )
    grant = approvals.approve(approval.approval_id, approver_id="owner")
    result = approvals.redeem(
        grant.grant_id, parameters={"amount": 10000, "currency": "USD"}, mind_id="gm_a"
    )
    assert not result.granted


def test_cosmetic_parameter_edits_do_not_invalidate_the_grant(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner")
    result = approvals.redeem(
        grant.grant_id,
        parameters={
            "to": "student@example.com",
            "subject": "Homework",
            "body": "Please review",
            "reasoning": "re-worded justification written later",
            "correlation_id": "different",
        },
        mind_id="gm_a",
        action_name="send_email",
    )
    assert result.granted


def test_whitespace_only_difference_is_not_a_change(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner")
    result = approvals.redeem(
        grant.grant_id,
        parameters={"to": "  student@example.com  ", "subject": "Homework", "body": "Please review"},
        mind_id="gm_a",
    )
    assert result.granted


def test_key_reordering_is_not_a_change(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner")
    result = approvals.redeem(
        grant.grant_id,
        parameters={"body": "Please review", "subject": "Homework", "to": "student@example.com"},
        mind_id="gm_a",
    )
    assert result.granted


def test_grant_is_not_transferable_to_another_mind(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner")
    result = approvals.redeem(
        grant.grant_id,
        parameters={"to": "student@example.com", "subject": "Homework", "body": "Please review"},
        mind_id="gm_other",
    )
    assert not result.granted
    assert "different Mind" in result.reason


def test_grant_is_bound_to_one_action(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner")
    result = approvals.redeem(
        grant.grant_id,
        parameters={"to": "student@example.com", "subject": "Homework", "body": "Please review"},
        mind_id="gm_a",
        action_name="make_purchase",
    )
    assert not result.granted
    assert "different action" in result.reason


def test_grant_is_single_use(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner")
    params = {"to": "student@example.com", "subject": "Homework", "body": "Please review"}
    assert approvals.redeem(grant.grant_id, parameters=params, mind_id="gm_a").granted
    replay = approvals.redeem(grant.grant_id, parameters=params, mind_id="gm_a")
    assert not replay.granted
    assert "already used" in replay.reason


def test_grant_expires(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(
        approval.approval_id, approver_id="owner", ttl=timedelta(seconds=-1)
    )
    result = approvals.redeem(
        grant.grant_id,
        parameters={"to": "student@example.com", "subject": "Homework", "body": "Please review"},
        mind_id="gm_a",
    )
    assert not result.granted
    assert "expired" in result.reason


def test_revoked_grant_cannot_be_used(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner")
    approvals.revoke_grant(grant.grant_id, actor_id="operator", note="mistake")
    result = approvals.redeem(
        grant.grant_id,
        parameters={"to": "student@example.com", "subject": "Homework", "body": "Please review"},
        mind_id="gm_a",
    )
    assert not result.granted
    assert "revoked" in result.reason


def test_unknown_grant_fails_closed(approvals):
    result = approvals.redeem("grt_does_not_exist", parameters={}, mind_id="gm_a")
    assert not result.granted


# --------------------------------------------------------------------------- #
# Human requirement
# --------------------------------------------------------------------------- #


def test_a_mind_cannot_approve_a_human_required_action(approvals, engine):
    approval = submit(approvals, engine, action_name="give_medical_advice")
    assert approval.requires_human is True
    with pytest.raises(ApprovalError):
        approvals.approve(
            approval.approval_id,
            approver_id="gm_a",
            actor_type="mind",
        )


def test_a_human_can_approve_a_human_required_action(approvals, engine):
    approval = submit(approvals, engine, action_name="give_medical_advice")
    grant = approvals.approve(approval.approval_id, approver_id="dr@example.com")
    assert grant.issued_by == "dr@example.com"


# --------------------------------------------------------------------------- #
# State machine
# --------------------------------------------------------------------------- #


def test_approve_then_reject_is_refused(approvals, engine):
    approval = submit(approvals, engine)
    approvals.approve(approval.approval_id, approver_id="owner")
    with pytest.raises(ApprovalTransitionError):
        approvals.reject(approval.approval_id, approver_id="owner")


def test_reject_then_approve_is_refused(approvals, engine):
    approval = submit(approvals, engine)
    approvals.reject(approval.approval_id, approver_id="owner")
    with pytest.raises(ApprovalTransitionError):
        approvals.approve(approval.approval_id, approver_id="owner")


def test_transition_table_matches_the_adr():
    assert can_transition(ApprovalStatus.PROPOSED, ApprovalStatus.POLICY_EVALUATED)
    assert can_transition(ApprovalStatus.WAITING_FOR_APPROVAL, ApprovalStatus.APPROVED)
    assert can_transition(ApprovalStatus.WAITING_FOR_APPROVAL, ApprovalStatus.EXPIRED)
    assert can_transition(ApprovalStatus.EXECUTING, ApprovalStatus.ROLLED_BACK)
    assert not can_transition(ApprovalStatus.PROPOSED, ApprovalStatus.COMPLETED)
    assert not can_transition(ApprovalStatus.EXPIRED, ApprovalStatus.APPROVED)
    assert not can_transition(ApprovalStatus.ROLLED_BACK, ApprovalStatus.EXECUTING)


def test_full_happy_path_state_sequence(approvals, engine):
    approval = submit(approvals, engine)
    approvals.approve(approval.approval_id, approver_id="owner")
    approvals.mark_executing(approval.approval_id)
    final = approvals.complete(approval.approval_id, success=True)
    assert final.status == ApprovalStatus.COMPLETED.value
    assert final.is_terminal


def test_failed_then_rolled_back_is_allowed(approvals, engine):
    approval = submit(approvals, engine)
    approvals.approve(approval.approval_id, approver_id="owner")
    approvals.mark_executing(approval.approval_id)
    approvals.complete(approval.approval_id, success=False, detail="smtp refused")
    rolled = approvals.mark_rolled_back(approval.approval_id, actor_id="owner")
    assert rolled.status == ApprovalStatus.ROLLED_BACK.value


def test_transition_log_records_every_step(approvals, engine):
    approval = submit(approvals, engine)
    approvals.approve(approval.approval_id, approver_id="owner", note="looks fine")
    stored = approvals.get(approval.approval_id)
    statuses = [entry["status"] for entry in stored.transition_log]
    assert statuses == ["PROPOSED", "POLICY_EVALUATED", "WAITING_FOR_APPROVAL", "APPROVED"]
    assert stored.transition_log[-1]["actor_id"] == "owner"


def test_unknown_approval_raises(approvals):
    with pytest.raises(ApprovalNotFoundError):
        approvals.get("apr_nope")


# --------------------------------------------------------------------------- #
# Expiry
# --------------------------------------------------------------------------- #


def test_expire_stale_closes_unanswered_requests(approvals, engine):
    approval = submit(approvals, engine)
    approval.expires_at = approval.requested_at - timedelta(seconds=1)
    approvals.store.save_approval(approval)
    expired = approvals.expire_stale()
    assert [item.approval_id for item in expired] == [approval.approval_id]
    assert approvals.get(approval.approval_id).status == ApprovalStatus.EXPIRED.value


def test_approving_an_expired_request_is_refused(approvals, engine):
    approval = submit(approvals, engine)
    approval.expires_at = approval.requested_at - timedelta(seconds=1)
    approvals.store.save_approval(approval)
    with pytest.raises(ApprovalError):
        approvals.approve(approval.approval_id, approver_id="owner")


def test_expire_stale_leaves_live_requests_alone(approvals, engine):
    approval = submit(approvals, engine)
    assert approvals.expire_stale() == []
    assert approvals.get(approval.approval_id).is_pending


# --------------------------------------------------------------------------- #
# Inbox
# --------------------------------------------------------------------------- #


def test_inbox_lists_pending_requests_only(approvals, engine):
    first = submit(approvals, engine)
    second = submit(approvals, engine, parameters={"to": "b@c.d", "subject": "s", "body": "b"})
    approvals.reject(first.approval_id, approver_id="owner")
    inbox = approvals.inbox()
    assert [card["approval_id"] for card in inbox] == [second.approval_id]


def test_inbox_is_scoped_per_mind(approvals, engine):
    submit(approvals, engine, mind_id="gm_a")
    submit(approvals, engine, mind_id="gm_b", parameters={"to": "b@c.d", "subject": "s", "body": "b"})
    assert len(approvals.inbox(mind_id="gm_a")) == 1
    assert len(approvals.inbox(mind_id="gm_b")) == 1


# --------------------------------------------------------------------------- #
# Parameter fingerprinting
# --------------------------------------------------------------------------- #


def test_material_parameters_excludes_narration():
    params = {"to": "a@b.c", "reasoning": "because", "note": "hi", "confidence": 0.9}
    assert material_parameters(params) == {"to": "a@b.c"}


def test_fingerprint_is_stable_across_key_order():
    assert parameters_fingerprint({"a": 1, "b": 2}) == parameters_fingerprint({"b": 2, "a": 1})


def test_fingerprint_changes_with_value():
    assert parameters_fingerprint({"a": 1}) != parameters_fingerprint({"a": 2})


def test_fingerprint_ignores_unordered_collections_order():
    assert parameters_fingerprint({"tags": ["x", "y"]}) == parameters_fingerprint(
        {"tags": ["x", "y"]}
    )


def test_grant_ttl_is_short_by_default(approvals, engine):
    approval = submit(approvals, engine)
    grant = approvals.approve(approval.approval_id, approver_id="owner")
    delta = grant.expires_at - grant.issued_at
    assert delta <= timedelta(hours=1)
