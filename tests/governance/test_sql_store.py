"""Tests for the durable (SQLAlchemy) governance store.

Every other governance test uses the in-memory store, which is fast and
hermetic — but it is *not* the store production runs on, and the two differ in a
way that hid a real bug:

    `get_session()` commits and closes on exit, and SQLAlchemy expires ORM
    instances on commit. Reading an attribute of a row after the `with` block
    therefore raises DetachedInstanceError.

`SqlAlchemyGovernanceStore.verify_journal` did exactly that, so it worked while
the journal was empty and raised HTTP 500 as soon as it contained a single
event. The in-memory store cannot reproduce it; only a real database can. This
module runs the same lifecycle against SQLite so the suite covers the store that
actually ships.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import genesis.database.base as db_base
import genesis.database.governance_models  # noqa: F401 - registers tables on Base.metadata


@pytest.fixture
def sql_store(tmp_path: Path, monkeypatch):
    """Point the canonical store at a throwaway SQLite file and create the schema."""
    # Reset the module-level engine/session factory so they bind to this file.
    monkeypatch.setattr(db_base, "_engine", None, raising=False)
    monkeypatch.setattr(db_base, "_SessionLocal", None, raising=False)
    monkeypatch.setattr(
        db_base,
        "get_settings",
        lambda: SimpleNamespace(
            genesis_home=tmp_path,
            database_url=f"sqlite:///{tmp_path / 'governance-test.db'}",
            debug=False,
        ),
    )

    db_base.init_db()

    # Import after the engine is redirected so the store resolves the same DB.
    import genesis.governance.store as store_module

    importlib.reload(store_module)
    store = store_module.SqlAlchemyGovernanceStore()

    yield store

    # Leave no global engine bound to a deleted temp directory.
    db_base._engine = None
    db_base._SessionLocal = None
    importlib.reload(store_module)


# --------------------------------------------------------------------------- #
# Events
# --------------------------------------------------------------------------- #


def test_events_round_trip_with_readable_fields(sql_store):
    from genesis.governance.models import AuditEvent, EventType, utcnow

    for index in range(3):
        sql_store.append_event(
            AuditEvent(
                event_id=f"evt_{index}",
                type=EventType.ACTION_EXECUTED,
                timestamp=utcnow(),
                mind_id="gm_sql",
                actor_type="mind",
                actor_id="gm_sql",
                correlation_id="cor_1",
                payload={"index": index},
            )
        )

    events = sql_store.list_events(mind_id="gm_sql")
    assert [event.sequence for event in events] == [1, 2, 3]
    # Field access after the session closed is the regression under test: these
    # asserts read attributes off rows returned from a closed session.
    assert {event.payload["index"] for event in events} == {0, 1, 2}
    assert all(event.mind_id == "gm_sql" for event in events)
    assert events[0].prev_hash == "0" * 64
    assert events[1].prev_hash == events[0].integrity_hash


def test_verify_journal_works_once_the_journal_has_rows(sql_store):
    """The exact case that returned HTTP 500 in the container.

    The first verification sees an empty journal and succeeds trivially. The
    second one has to read rows, which is where the detached-instance error
    occurred.
    """
    from genesis.governance.audit import AuditService

    audit = AuditService(store=sql_store)

    first = audit.verify_journal(mind_id="gm_sql")
    assert first.ok

    # verify_journal itself journals a result event, so the journal is non-empty
    # from here on.
    assert sql_store.list_events(mind_id="gm_sql")

    second = audit.verify_journal(mind_id="gm_sql")
    assert second.ok
    assert second.checked >= 1

    third = audit.verify_journal(mind_id="gm_sql")
    assert third.ok


def test_chain_is_detected_as_broken_when_a_row_is_edited(sql_store):
    from genesis.database.base import get_session
    from genesis.database.governance_models import GovernanceEventRecord
    from genesis.governance.models import AuditEvent, EventType, utcnow

    for index in range(3):
        sql_store.append_event(
            AuditEvent(
                event_id=f"evt_{index}",
                type=EventType.ACTION_EXECUTED,
                timestamp=utcnow(),
                mind_id="gm_sql",
                payload={"index": index},
            )
        )

    with get_session() as session:
        row = session.get(GovernanceEventRecord, "evt_1")
        row.payload = {"index": 999}

    result = sql_store.verify_journal(mind_id="gm_sql")
    assert not result.ok
    assert result.broken_at == "evt_1"


def test_chains_are_independent_per_stream(sql_store):
    from genesis.governance.models import AuditEvent, EventType, utcnow

    for mind in ("gm_a", "gm_b"):
        for _ in range(2):
            sql_store.append_event(
                AuditEvent(
                    event_id=f"evt_{mind}_{utcnow().timestamp()}",
                    type=EventType.ACTION_EXECUTED,
                    timestamp=utcnow(),
                    mind_id=mind,
                    payload={},
                )
            )

    for mind in ("gm_a", "gm_b"):
        assert [event.sequence for event in sql_store.list_events(mind_id=mind)] == [1, 2]


# --------------------------------------------------------------------------- #
# Receipts
# --------------------------------------------------------------------------- #


def test_receipts_round_trip_and_chain(sql_store):
    from genesis.governance.models import ActionReceipt, ReceiptOutcome, utcnow
    from genesis.governance.receipts import build_receipt

    for index in range(2):
        receipt = build_receipt(
            action_id=f"ACT-{index}",
            action_name="send_email",
            mind_id="gm_sql",
            outcome=ReceiptOutcome.EXECUTED.value,
            parameters={"to": f"user{index}@example.com"},
            started_at=utcnow(),
            completed_at=utcnow(),
        )
        sql_store.save_receipt(receipt)

    stored = sql_store.list_receipts(mind_id="gm_sql")
    assert len(stored) == 2
    assert all(isinstance(receipt, ActionReceipt) for receipt in stored)
    assert all(receipt.arguments["to"] for receipt in stored)
    # Sequence and prev_hash are assigned by the store, and the chain must hold.
    by_sequence = sorted(stored, key=lambda item: item.sequence)
    assert by_sequence[0].sequence == 1
    assert by_sequence[1].prev_hash == by_sequence[0].integrity_hash


def test_receipt_can_be_fetched_by_id(sql_store):
    from genesis.governance.receipts import build_receipt

    receipt = build_receipt(
        action_id="ACT-1",
        action_name="create_task",
        mind_id="gm_sql",
        outcome="executed",
        parameters={"title": "x"},
    )
    sql_store.save_receipt(receipt)
    fetched = sql_store.get_receipt(receipt.receipt_id)
    assert fetched is not None
    assert fetched.action_name == "create_task"
    assert fetched.arguments == {"title": "x"}


# --------------------------------------------------------------------------- #
# Approvals and grants
# --------------------------------------------------------------------------- #


def test_approvals_round_trip_and_update_in_place(sql_store):
    from genesis.governance.models import ApprovalRequest, ApprovalStatus, utcnow

    approval = ApprovalRequest(
        approval_id="apr_1",
        action_id="ACT-1",
        action_name="send_email",
        mind_id="gm_sql",
        status=ApprovalStatus.WAITING_FOR_APPROVAL.value,
        requested_at=utcnow(),
        risk_level="R3",
        parameters={"to": "a@b.c"},
        parameters_hash="deadbeef",
        summary="send email",
        reason="because",
        expires_at=utcnow(),
    )
    sql_store.save_approval(approval)

    pending = sql_store.list_approvals(mind_id="gm_sql", status="WAITING_FOR_APPROVAL")
    assert len(pending) == 1
    assert pending[0].approval_id == "apr_1"
    assert pending[0].parameters == {"to": "a@b.c"}

    # Updating must not insert a second row.
    approval.status = ApprovalStatus.APPROVED.value
    sql_store.save_approval(approval)
    assert sql_store.list_approvals(mind_id="gm_sql") == [
        sql_store.get_approval("apr_1")
    ]
    assert sql_store.get_approval("apr_1").status == ApprovalStatus.APPROVED.value


def test_grants_round_trip_and_update_in_place(sql_store):
    from genesis.governance.models import PermissionGrant, utcnow

    grant = PermissionGrant(
        grant_id="grt_1",
        approval_id="apr_1",
        mind_id="gm_sql",
        action_name="send_email",
        parameters_hash="deadbeef",
        issued_at=utcnow(),
        expires_at=utcnow(),
        issued_by="owner@example.com",
    )
    sql_store.save_grant(grant)

    active = sql_store.list_grants(mind_id="gm_sql", active_only=True)
    assert [item.grant_id for item in active] == ["grt_1"]

    grant.consumed_at = utcnow()
    sql_store.save_grant(grant)
    assert sql_store.list_grants(mind_id="gm_sql", active_only=True) == []
    assert sql_store.get_grant("grt_1").is_consumed


def test_approval_and_grant_lifecycle_through_the_services(sql_store):
    """The full path: submit, approve, redeem, then redeem again and fail."""
    from genesis.governance.approval import ApprovalService
    from genesis.governance.audit import AuditService
    from genesis.governance.policy import PolicyContext, PolicyEngine

    audit = AuditService(store=sql_store)
    approvals = ApprovalService(store=sql_store, audit=audit)
    engine = PolicyEngine()

    parameters = {"to": "student@example.com", "subject": "Homework", "body": "Review please"}
    context = PolicyContext(
        action_name="send_email",
        parameters=parameters,
        mind_id="gm_sql",
        granted_scopes=frozenset({"comms.email.send"}),
    )
    decision = engine.evaluate(context)
    assert decision.requires_approval

    approval = approvals.submit(
        context=context, decision=decision, action_id="ACT-1", requested_by="mind"
    )
    assert approvals.inbox(mind_id="gm_sql")[0]["approval_id"] == approval.approval_id

    grant = approvals.approve(approval.approval_id, approver_id="owner@example.com")

    first = approvals.redeem(
        grant.grant_id, parameters=parameters, mind_id="gm_sql", action_name="send_email"
    )
    assert first.granted

    replay = approvals.redeem(
        grant.grant_id, parameters=parameters, mind_id="gm_sql", action_name="send_email"
    )
    assert not replay.granted
    assert "already used" in replay.reason

    tampered = approvals.redeem(
        grant.grant_id,
        parameters={"to": "attacker@evil.example", "subject": "Homework", "body": "Review please"},
        mind_id="gm_sql",
        action_name="send_email",
    )
    assert not tampered.granted

    # The whole exchange must still verify.
    assert audit.verify_journal(mind_id="gm_sql").ok


def test_store_still_verifies_after_many_writes(sql_store):
    """Guards the sequence-assignment path under repeated writes."""
    from genesis.governance.audit import AuditService
    from genesis.governance.models import EventType

    audit = AuditService(store=sql_store)
    for index in range(25):
        audit.record(EventType.ACTION_EXECUTED, mind_id="gm_sql", payload={"index": index})

    events = sql_store.list_events(mind_id="gm_sql", limit=100)
    assert len(events) == 25
    assert [event.sequence for event in events] == list(range(1, 26))
    assert audit.verify_journal(mind_id="gm_sql").ok
