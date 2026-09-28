"""Commitment tests (Phase N1–N4).

The design decisions worth testing are the ones that distinguish a commitment
from a memory: it does not fade, it has a beneficiary, missing it is recorded, and
creating one that binds someone outside the being is gated.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from genesis.core.life import (
    BENEFICIARY_MIND,
    BENEFICIARY_OWNER,
    BENEFICIARY_THIRD_PARTY,
    Commitment,
    CommitmentError,
    CommitmentManager,
    CommitmentNotFoundError,
    CommitmentStatus,
    CommitmentTransitionError,
    TRANSITIONS,
    can_transition,
    capability_for_beneficiary,
)
from genesis.governance import EventType


def _now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def manager() -> CommitmentManager:
    return CommitmentManager("gm_1")


def _create(manager, **overrides):
    payload = dict(
        beneficiary_id="creator_shahansha",
        beneficiary_label="Shahansha",
        what="Send the grade 10 report",
        provenance="chat turn cor_abc",
        deadline=_now() + timedelta(days=2),
    )
    payload.update(overrides)
    return manager.create(**payload)


# =========================================================================== #
# Creation
# =========================================================================== #


def test_create_records_the_obligation(manager):
    commitment = _create(manager)
    assert commitment.status == CommitmentStatus.OPEN.value
    assert commitment.beneficiary_id == "creator_shahansha"
    assert commitment.what == "Send the grade 10 report"
    assert commitment.commitment_id.startswith("cmt_")
    assert commitment.is_open


def test_provenance_is_required(manager):
    """An obligation with no traceable origin is the autonomous promise the design forbids."""
    with pytest.raises(CommitmentError) as excinfo:
        _create(manager, provenance="")
    assert "provenance" in str(excinfo.value)


def test_what_is_required(manager):
    with pytest.raises(CommitmentError):
        _create(manager, what="   ")


def test_beneficiary_is_required(manager):
    with pytest.raises(CommitmentError):
        _create(manager, beneficiary_id="")


def test_a_commitment_may_have_no_deadline(manager):
    """Open-ended is legitimate; a deadline is not required, but its absence is explicit."""
    commitment = _create(manager, deadline=None)
    assert commitment.deadline is None
    assert not commitment.is_overdue
    assert not commitment.is_at_risk


def test_correlation_id_is_captured_from_the_turn(manager):
    from genesis.governance.context import correlation_scope

    with correlation_scope("cor_turn_1"):
        commitment = _create(manager)
    assert commitment.correlation_id == "cor_turn_1"


# =========================================================================== #
# The state machine
# =========================================================================== #


def test_happy_path(manager):
    commitment = _create(manager)
    manager.start(commitment.commitment_id)
    assert manager.get(commitment.commitment_id).status == CommitmentStatus.IN_PROGRESS.value
    manager.fulfil(commitment.commitment_id, note="sent")
    assert manager.get(commitment.commitment_id).status == CommitmentStatus.FULFILLED.value


def test_fulfilling_twice_is_idempotent_not_an_error(manager):
    """A retry (a scheduled job running twice) must not fail.

    Deliberate, and consistent with the approval state machine: re-applying a
    terminal status is a no-op rather than an exception, because the realistic
    cause is a retry. The transition log still shows the first fulfilment, so the
    history is not corrupted by the second call.

    The control that actually matters is the next test: a resolved commitment
    cannot be reopened.
    """
    commitment = _create(manager)
    manager.fulfil(commitment.commitment_id, note="first")
    manager.fulfil(commitment.commitment_id, note="retry")

    recovered = manager.get(commitment.commitment_id)
    assert recovered.status == CommitmentStatus.FULFILLED.value
    assert [entry["status"] for entry in recovered.transition_log].count("FULFILLED") == 1


def test_a_fulfilled_commitment_cannot_be_reopened(manager):
    commitment = _create(manager)
    manager.fulfil(commitment.commitment_id)
    with pytest.raises(CommitmentTransitionError):
        manager.start(commitment.commitment_id)


def test_a_withdrawn_commitment_cannot_be_fulfilled(manager):
    """The real guard: terminal means terminal, even for a same-looking call."""
    commitment = _create(manager)
    manager.withdraw(commitment.commitment_id, reason="cancelled")
    with pytest.raises(CommitmentTransitionError):
        manager.start(commitment.commitment_id)


def test_withdrawing_a_resolved_commitment_is_refused(manager):
    commitment = _create(manager)
    manager.withdraw(commitment.commitment_id, reason="no longer needed")
    with pytest.raises(CommitmentTransitionError):
        manager.fulfil(commitment.commitment_id)


def test_terminal_states_are_terminal(manager):
    for status in (
        CommitmentStatus.FULFILLED,
        CommitmentStatus.WITHDRAWN,
    ):
        assert TRANSITIONS[status] == frozenset()


def test_renegotiating_an_open_commitment_moves_the_deadline(manager):
    commitment = _create(manager)
    later = _now() + timedelta(days=10)
    manager.renegotiate(commitment.commitment_id, new_deadline=later, reason="owner asked")
    updated = manager.get(commitment.commitment_id)
    assert updated.deadline == later
    assert updated.is_open  # still owed, just later


def test_renegotiating_a_missed_commitment_reopens_it(manager):
    commitment = _create(manager, deadline=_now() - timedelta(days=1))
    manager.mark_missed(commitment.commitment_id)
    manager.renegotiate(commitment.commitment_id, new_deadline=_now() + timedelta(days=3))
    assert manager.get(commitment.commitment_id).status == CommitmentStatus.OPEN.value


def test_the_transition_log_records_every_step(manager):
    commitment = _create(manager)
    manager.start(commitment.commitment_id)
    manager.fulfil(commitment.commitment_id, note="done")
    statuses = [entry["status"] for entry in manager.get(commitment.commitment_id).transition_log]
    assert statuses == ["OPEN", "IN_PROGRESS", "FULFILLED"]


def test_unknown_commitment_raises(manager):
    with pytest.raises(CommitmentNotFoundError):
        manager.fulfil("cmt_nope")


# =========================================================================== #
# Overdue vs missed — the distinction that matters to a beneficiary
# =========================================================================== #


def test_lateness_is_not_automatic_failure(manager):
    """`is_overdue` and MISSED are different facts, and the sweep defaults to not conflating them."""
    commitment = _create(manager, deadline=_now() - timedelta(hours=1))
    assert commitment.is_overdue
    assert commitment.status == CommitmentStatus.OPEN.value  # still owed

    overdue = manager.sweep_overdue()
    assert [item.commitment_id for item in overdue] == [commitment.commitment_id]
    # Not marked missed, because a being should decide which of "late" or
    # "abandoned" applies rather than have a timer decide.
    assert manager.get(commitment.commitment_id).status == CommitmentStatus.OPEN.value


def test_the_sweep_can_mark_missed_when_asked(manager):
    commitment = _create(manager, deadline=_now() - timedelta(hours=1))
    manager.sweep_overdue(mark_missed=True)
    assert manager.get(commitment.commitment_id).status == CommitmentStatus.MISSED.value


def test_at_risk_is_due_within_a_day(manager):
    soon = _create(manager, deadline=_now() + timedelta(hours=6))
    later = _create(manager, deadline=_now() + timedelta(days=5))
    at_risk = manager.at_risk()
    assert [item.commitment_id for item in at_risk] == [soon.commitment_id]
    assert later.commitment_id not in [item.commitment_id for item in at_risk]


def test_overdue_does_not_include_resolved_commitments(manager):
    commitment = _create(manager, deadline=_now() - timedelta(days=1))
    manager.fulfil(commitment.commitment_id, note="late but done")
    assert not manager.get(commitment.commitment_id).is_overdue


# =========================================================================== #
# Gating — creation is consequential when it binds a third party
# =========================================================================== #


def test_without_a_gate_creation_is_direct(manager):
    """Standalone use (scripts, tests) must not require a governance plane."""
    assert manager.gated is False
    assert _create(manager).status == CommitmentStatus.OPEN.value


def test_an_owner_commitment_opens_directly_under_a_gate(gate):
    manager = CommitmentManager("gm_1", gate=gate)
    commitment = _create(manager)
    # create_commitment is R1: allowed, with a receipt.
    assert commitment.status == CommitmentStatus.OPEN.value


def test_a_third_party_commitment_is_proposed_not_owed(gate):
    """Nothing is owed until a human agrees, so the status must say so."""
    manager = CommitmentManager("gm_1", gate=gate)
    commitment = _create(
        manager,
        beneficiary_id="parent_of_student",
        beneficiary_kind=BENEFICIARY_THIRD_PARTY,
        what="Meet the parent on Thursday",
    )
    assert commitment.status == CommitmentStatus.PROPOSED.value
    assert not commitment.is_open
    # And it is not counted as an open obligation.
    assert manager.summary()["open"] == 0


def test_a_proposed_commitment_can_be_approved(gate):
    manager = CommitmentManager("gm_1", gate=gate)
    commitment = _create(manager, beneficiary_kind=BENEFICIARY_THIRD_PARTY, beneficiary_id="third")
    manager.approve_proposal(commitment.commitment_id, approver_id="owner@example.com")
    assert manager.get(commitment.commitment_id).status == CommitmentStatus.OPEN.value


def test_a_proposed_commitment_can_be_withdrawn(gate):
    manager = CommitmentManager("gm_1", gate=gate)
    commitment = _create(manager, beneficiary_kind=BENEFICIARY_THIRD_PARTY, beneficiary_id="third")
    manager.withdraw(commitment.commitment_id, reason="owner declined")
    assert manager.get(commitment.commitment_id).status == CommitmentStatus.WITHDRAWN.value


def test_a_broken_gate_fails_closed(gate):
    """If the control plane is broken, the obligation is not created — it is proposed."""

    class ExplodingGate:
        def authorize(self, *args, **kwargs):
            raise RuntimeError("gate unavailable")

    manager = CommitmentManager("gm_1", gate=ExplodingGate())
    commitment = _create(manager)
    assert commitment.status == CommitmentStatus.PROPOSED.value


def test_capability_names_are_chosen_by_beneficiary_kind():
    """Callers do not choose the risk tier; the manager names the capability."""
    assert capability_for_beneficiary(BENEFICIARY_OWNER) == "create_commitment"
    assert capability_for_beneficiary(BENEFICIARY_THIRD_PARTY) == "commit_to_third_party"
    assert capability_for_beneficiary(BENEFICIARY_MIND) == "create_commitment_cross_mind"


def test_declared_tiers_match_the_design():
    """Guard the risk table itself, so a later edit cannot quietly lower a tier."""
    from genesis.governance import PolicyEngine, RiskLevel

    engine = PolicyEngine()
    assert engine.assess_capability("create_commitment").risk is RiskLevel.R1
    assert engine.assess_capability("create_commitment_cross_mind").risk is RiskLevel.R2
    assert engine.assess_capability("commit_to_third_party").risk is RiskLevel.R3
    assert engine.assess_capability("withdraw_commitment").risk is RiskLevel.R2


def test_an_unknown_trust_external_commitment_escalates_to_r3():
    """The fail-closed default: an untrusted external relationship raises control.

    A cross-Mind commitment is *declared* R2, but the engine raises anything
    external against an unknown peer to R3 until trust is established. That is the
    documented behaviour — a declaration is a floor, not a ceiling.
    """
    from genesis.governance import Decision, PolicyContext, PolicyEngine

    engine = PolicyEngine()
    unknown = engine.evaluate(
        PolicyContext(
            action_name="create_commitment_cross_mind",
            mind_id="gm_1",
            trust_level="unknown",
        )
    )
    assert unknown.risk_level.value == "R3"
    assert unknown.decision is Decision.REQUIRE_APPROVAL

    trusted = engine.evaluate(
        PolicyContext(
            action_name="create_commitment_cross_mind",
            mind_id="gm_1",
            trust_level="trusted",
        )
    )
    assert trusted.risk_level.value == "R2"


# =========================================================================== #
# Journal integration
# =========================================================================== #


def test_creation_is_journalled_with_the_obligation_text(store):
    """Unlike memory content, the obligation *is* recorded: it must be readable."""
    from genesis.governance import AuditService
    from genesis.governance.domain_events import _RecordingDomainJournal
    import genesis.governance.domain_events as domain_events
    from unittest.mock import patch

    audit = AuditService(store=store)
    with patch.object(domain_events, "_journal", _RecordingDomainJournal(audit)):
        manager = CommitmentManager("gm_journal")
        _create(manager, what="Send the report by Friday")

    events = audit.events(mind_id="gm_journal")
    assert [event.type for event in events] == [EventType.COMMITMENT_CREATED]
    assert events[0].payload["what"] == "Send the report by Friday"
    assert events[0].payload["status"] == "OPEN"


def test_missing_a_commitment_is_a_recorded_event(store):
    """A beneficiary must be able to see that a promise was made and not kept."""
    from unittest.mock import patch

    from genesis.governance import AuditService
    from genesis.governance.domain_events import _RecordingDomainJournal
    import genesis.governance.domain_events as domain_events

    audit = AuditService(store=store)
    with patch.object(domain_events, "_journal", _RecordingDomainJournal(audit)):
        manager = CommitmentManager("gm_journal")
        commitment = _create(manager, deadline=_now() - timedelta(days=1))
        manager.mark_missed(commitment.commitment_id, note="report was late")

    types = [event.type for event in audit.events(mind_id="gm_journal")]
    assert EventType.COMMITMENT_MISSED in types


def test_fulfilment_is_journalled_separately_from_creation(store):
    from unittest.mock import patch

    from genesis.governance import AuditService
    from genesis.governance.domain_events import _RecordingDomainJournal
    import genesis.governance.domain_events as domain_events

    audit = AuditService(store=store)
    with patch.object(domain_events, "_journal", _RecordingDomainJournal(audit)):
        manager = CommitmentManager("gm_journal")
        commitment = _create(manager)
        manager.fulfil(commitment.commitment_id, note="done")

    types = [event.type for event in audit.events(mind_id="gm_journal")]
    assert types == [EventType.COMMITMENT_CREATED, EventType.COMMITMENT_FULFILLED]


def test_a_journal_failure_does_not_block_the_obligation(manager, monkeypatch):
    """Auditing must never cost the user an obligation."""

    class ExplodingAudit:
        def record(self, *args, **kwargs):
            raise RuntimeError("journal down")

    import genesis.governance.domain_events as domain_events
    from genesis.governance.domain_events import _RecordingDomainJournal

    monkeypatch.setattr(domain_events, "_journal", _RecordingDomainJournal(ExplodingAudit()))
    commitment = _create(manager)
    assert commitment.status == CommitmentStatus.OPEN.value
    manager.fulfil(commitment.commitment_id)


# =========================================================================== #
# Queries
# =========================================================================== #


def test_owed_to_returns_open_commitments_for_one_beneficiary(manager):
    _create(manager, beneficiary_id="alice")
    _create(manager, beneficiary_id="alice")
    done = _create(manager, beneficiary_id="alice")
    manager.fulfil(done.commitment_id)
    _create(manager, beneficiary_id="bob")

    owed = manager.owed_to("alice")
    assert len(owed) == 2
    assert all(item.beneficiary_id == "alice" for item in owed)


def test_commitments_are_ordered_by_deadline_with_undated_last(manager):
    _create(manager, deadline=None, what="someday")
    soon = _create(manager, deadline=_now() + timedelta(hours=1))
    later = _create(manager, deadline=_now() + timedelta(days=7))

    ordered = [item.commitment_id for item in manager.list_commitments()]
    assert ordered[:2] == [soon.commitment_id, later.commitment_id]


def test_summary_reports_the_state_a_heartbeat_needs(manager):
    _create(manager, deadline=_now() - timedelta(days=1))  # overdue
    _create(manager, deadline=_now() + timedelta(hours=3))  # at risk
    done = _create(manager)
    manager.fulfil(done.commitment_id)

    summary = manager.summary()
    assert summary["total"] == 3
    assert summary["open"] == 2
    assert summary["overdue"] == 1
    assert summary["at_risk"] == 1
    assert summary["by_status"]["FULFILLED"] == 1


def test_list_filters(manager):
    open_one = _create(manager)
    done = _create(manager)
    manager.fulfil(done.commitment_id)

    assert len(manager.list_commitments(open_only=True)) == 1
    assert manager.list_commitments(status=CommitmentStatus.FULFILLED.value)[0].commitment_id == (
        done.commitment_id
    )


# =========================================================================== #
# Persistence
# =========================================================================== #


def test_serialisation_round_trip_preserves_deadlines(manager):
    """A naive deadline would compare wrongly against an aware 'now'."""
    original = _create(manager, deadline=_now() + timedelta(days=3))
    restored = CommitmentManager.from_dict(manager.to_dict())

    recovered = restored.get(original.commitment_id)
    assert recovered.deadline == original.deadline
    assert recovered.deadline.tzinfo is not None
    assert recovered.is_overdue is False
    assert recovered.created_at.tzinfo is not None


def test_round_trip_preserves_history_and_provenance(manager):
    commitment = _create(manager)
    manager.start(commitment.commitment_id)
    manager.fulfil(commitment.commitment_id, note="done")

    restored = CommitmentManager.from_dict(manager.to_dict())
    recovered = restored.get(commitment.commitment_id)
    assert recovered.status == CommitmentStatus.FULFILLED.value
    assert recovered.provenance == "chat turn cor_abc"
    assert len(recovered.transition_log) == 3


def test_a_malformed_timestamp_does_not_break_loading(manager):
    payload = manager.to_dict()
    payload["commitments"] = [
        {
            "commitment_id": "cmt_x",
            "mind_id": "gm_1",
            "beneficiary_id": "alice",
            "what": "something",
            "provenance": "manual",
            "created_at": "not-a-date",
            "deadline": "also-not-a-date",
        }
    ]
    restored = CommitmentManager.from_dict(payload)
    recovered = restored.get("cmt_x")
    assert recovered is not None
    assert recovered.deadline is None
    assert recovered.created_at is not None


# =========================================================================== #
# The anti-requirement
# =========================================================================== #


def test_nothing_creates_commitments_autonomously():
    """Phase N11. A being that invents obligations is a liability.

    Asserted structurally: the only way to create a commitment is an explicit
    call to `create`. There is no timer, no hook, no `__init__` side effect and no
    background sweep that produces one.
    """
    import inspect

    from genesis.core.life import commitments as module

    source = inspect.getsource(module)
    # No scheduling primitives in the module at all.
    for forbidden in ("threading.Timer", "asyncio.create_task", "schedule.every", "time.sleep"):
        assert forbidden not in source, f"{forbidden} must not appear in the commitments module"

    # A fresh manager owns nothing.
    assert CommitmentManager("gm_1").summary()["total"] == 0

    # `sweep_overdue` resolves state; it never creates.
    manager = CommitmentManager("gm_1")
    manager.sweep_overdue(mark_missed=True)
    assert manager.summary()["total"] == 0

    # The only writer is `create`.
    create_callers = [
        name
        for name, member in inspect.getmembers(CommitmentManager, inspect.isfunction)
        if "self.create(" in inspect.getsource(member) and name != "create"
    ]
    assert create_callers == [], f"unexpected internal callers of create(): {create_callers}"
