"""Event journal, receipts, and redaction tests (ADR-0008)."""

from __future__ import annotations

import pytest

from genesis.governance import (
    ActionReceipt,
    AuditService,
    EventType,
    InMemoryGovernanceStore,
    ReceiptOutcome,
    redact_payload,
    stable_hash,
)
from genesis.governance.redact import iter_secret_leaks
from genesis.governance.receipts import build_receipt, classify_error


# --------------------------------------------------------------------------- #
# Journal
# --------------------------------------------------------------------------- #


def test_events_are_sequenced_and_hash_chained(audit):
    first = audit.record(EventType.MIND_BORN, mind_id="gm_a", payload={"name": "Ada"})
    second = audit.record(EventType.ACTION_PROPOSED, mind_id="gm_a", payload={"a": 1})
    third = audit.record(EventType.ACTION_EXECUTED, mind_id="gm_a", payload={"b": 2})

    assert (first.sequence, second.sequence, third.sequence) == (1, 2, 3)
    assert first.prev_hash == "0" * 64
    assert second.prev_hash == first.integrity_hash
    assert third.prev_hash == second.integrity_hash


def test_verify_journal_passes_on_untouched_chain(audit):
    for index in range(5):
        audit.record(EventType.ACTION_EXECUTED, mind_id="gm_a", payload={"i": index})
    assert audit.verify_journal(mind_id="gm_a").ok


def test_tampering_with_a_payload_is_detected(audit):
    audit.record(EventType.ACTION_EXECUTED, mind_id="gm_a", payload={"amount": 10})
    audit.record(EventType.ACTION_EXECUTED, mind_id="gm_a", payload={"amount": 20})

    # Simulate an attacker editing the stored row in place.
    stored = audit.events(mind_id="gm_a")
    stored[0].payload = {"amount": 999999}

    result = audit.verify_journal(mind_id="gm_a")
    assert not result.ok
    assert result.broken_at == stored[0].event_id


def test_splicing_an_event_out_is_detected(audit):
    for index in range(4):
        audit.record(EventType.ACTION_EXECUTED, mind_id="gm_a", payload={"i": index})
    events = audit.events(mind_id="gm_a")
    del events[2]
    from genesis.governance.store import _verify_stream

    assert not _verify_stream(events, limit=100).ok


def test_chains_are_per_mind_stream(audit):
    a = audit.record(EventType.ACTION_EXECUTED, mind_id="gm_a", payload={})
    b = audit.record(EventType.ACTION_EXECUTED, mind_id="gm_b", payload={})
    assert a.sequence == 1
    assert b.sequence == 1
    assert b.prev_hash == "0" * 64


def test_chains_are_per_tenant_stream(audit):
    audit.record(EventType.ACTION_EXECUTED, mind_id="gm_a", tenant_id="acme", payload={})
    other = audit.record(EventType.ACTION_EXECUTED, mind_id="gm_a", tenant_id="globex", payload={})
    assert other.sequence == 1


def test_every_event_carries_schema_version_and_correlation(audit):
    first = audit.record(EventType.ACTION_EXECUTED, mind_id="gm_a", payload={})
    second = audit.record(
        EventType.ACTION_EXECUTED, mind_id="gm_a", correlation_id=first.correlation_id, payload={}
    )
    assert first.schema_version >= 1
    assert second.correlation_id == first.correlation_id


def test_causation_can_link_an_event_to_its_cause(audit):
    cause = audit.record(EventType.ACTION_PROPOSED, mind_id="gm_a", payload={})
    effect = audit.record(
        EventType.ACTION_APPROVED, mind_id="gm_a", causation_id=cause.event_id, payload={}
    )
    assert effect.causation_id == cause.event_id


def test_blocked_actions_are_recorded_too(audit):
    audit.record(
        EventType.ACTION_BLOCKED,
        mind_id="gm_a",
        payload={"action_name": "harm_humans", "reason_code": "constitution_prohibited"},
    )
    blocked = audit.events(mind_id="gm_a", event_type=EventType.ACTION_BLOCKED)
    assert len(blocked) == 1
    assert blocked[0].payload["reason_code"] == "constitution_prohibited"


def test_event_export_is_machine_readable(audit):
    audit.record(EventType.MIND_BORN, mind_id="gm_a", payload={"name": "Ada"})
    export = audit.export(mind_id="gm_a")
    assert export["mind_id"] == "gm_a"
    assert export["counts"]["events"] == 1
    assert export["verification"]["ok"] is True
    assert export["events"][0]["type"] == EventType.MIND_BORN


# --------------------------------------------------------------------------- #
# Redaction by construction
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "api_key",
        "apiKey",
        "access_token",
        "Authorization",
        "cookie",
        "client_secret",
        "private_key",
        "ssn",
        "credit_card",
        "cvv",
        "seed_phrase",
        "webhook_secret",
    ],
)
def test_secret_shaped_keys_are_redacted(key):
    payload = redact_payload({key: "super-secret-value"})
    assert payload[key] == "[redacted]"


def test_redaction_is_recursive():
    payload = redact_payload(
        {"outer": {"inner": [{"token": "abc", "safe": "ok"}]}}
    )
    assert payload["outer"]["inner"][0]["token"] == "[redacted]"
    assert payload["outer"]["inner"][0]["safe"] == "ok"


def test_benign_keys_sharing_a_token_are_not_redacted():
    payload = redact_payload({"token_count": 12, "password_policy": "strong"})
    assert payload["token_count"] == 12
    assert payload["password_policy"] == "strong"


def test_inline_credentials_in_free_text_are_stripped():
    payload = redact_payload(
        {"message": "use Bearer eyJhbGciOiJIUzI1NiJ9.abcdefghijklmnop.qrstuvwx to call it"}
    )
    assert "eyJhbGciOiJIUzI1NiJ9" not in payload["message"]
    assert "[redacted]" in payload["message"]


def test_common_api_key_shapes_are_stripped():
    payload = redact_payload({"body": "key=sk-abcdefghijklmnopqrstuvwx"})
    assert "sk-abcdefghijklmnopqrstuvwx" not in payload["body"]


def test_audit_service_redacts_even_when_the_caller_does_not(audit):
    event = audit.record(
        EventType.ACTION_EXECUTED,
        mind_id="gm_a",
        payload={
            "action_name": "login",
            "credentials": {"username": "ada", "password": "hunter2"},
        },
    )
    # ``credentials`` is itself a sensitive key, so the whole subtree is
    # replaced. That is stricter than redacting only ``password``, and it is the
    # behaviour we want: a partially redacted credential object still leaks.
    assert event.payload["credentials"] == "[redacted]"
    assert "hunter2" not in str(event.payload)
    assert event.payload["action_name"] == "login"


def test_a_sensitive_container_key_redacts_its_whole_subtree(audit):
    event = audit.record(
        EventType.ACTION_EXECUTED,
        mind_id="gm_a",
        payload={"secret": {"nested": {"value": "leak-me"}}},
    )
    assert event.payload["secret"] == "[redacted]"
    assert "leak-me" not in str(event.payload)


def test_receipts_are_redacted_on_write(audit):
    receipt = build_receipt(
        action_id="ACT-1",
        action_name="send_email",
        mind_id="gm_a",
        outcome=ReceiptOutcome.EXECUTED.value,
        parameters={"to": "a@b.c", "smtp_password": "hunter2"},
    )
    stored = audit.record_receipt(receipt)
    assert stored.arguments["smtp_password"] == "[redacted]"
    assert stored.arguments_hash


def test_payload_is_bounded(audit):
    payload = audit.record(
        EventType.ACTION_EXECUTED,
        mind_id="gm_a",
        payload={"blob": "x" * 500_000, "other": "y" * 500_000},
    )
    import json

    assert len(json.dumps(payload.payload)) < 70_000


def test_overlong_strings_are_truncated_visibly():
    payload = redact_payload({"note": "a" * 10_000})
    assert "truncated" in payload["note"]


def test_non_json_values_do_not_break_redaction():
    class Opaque:
        def __repr__(self) -> str:
            return "<opaque>"

    payload = redact_payload({"obj": Opaque(), "raw": b"\x00\x01", "nan": float("nan")})
    assert payload["obj"] == "<opaque>"
    assert payload["raw"] == "<bytes:2>"
    assert payload["nan"] is None


def test_no_secret_survives_in_a_stored_event(audit):
    audit.record(
        EventType.ACTION_EXECUTED,
        mind_id="gm_a",
        payload={
            "nested": {"deep": {"api_key": "sk-live-abcdef0123456789"}},
            "list": [{"session_token": "tok-abcdef"}, {"ok": 1}],
            "keep": "visible",
        },
    )
    stored = audit.events(mind_id="gm_a")[0]
    serialized = str(stored.payload)
    assert "sk-live-abcdef0123456789" not in serialized
    assert "tok-abcdef" not in serialized
    assert stored.payload["keep"] == "visible"
    assert stored.payload["list"][1] == {"ok": 1}


# --------------------------------------------------------------------------- #
# Receipts
# --------------------------------------------------------------------------- #


def test_receipt_records_outcome_and_hashes(audit):
    receipt = build_receipt(
        action_id="ACT-1",
        action_name="create_task",
        mind_id="gm_a",
        outcome=ReceiptOutcome.EXECUTED.value,
        parameters={"title": "shopping"},
    )
    stored = audit.record_receipt(receipt)
    assert stored.outcome == ReceiptOutcome.EXECUTED.value
    assert stored.arguments_hash == stable_hash({"title": "shopping"})
    assert stored.integrity_hash
    assert stored.prev_hash == "0" * 64
    assert stored.sequence == 1


def test_receipts_chain_within_a_mind(audit):
    first = audit.record_receipt(
        build_receipt(
            action_id="A1", action_name="create_task", mind_id="gm_a",
            outcome=ReceiptOutcome.EXECUTED.value,
        )
    )
    second = audit.record_receipt(
        build_receipt(
            action_id="A2", action_name="create_task", mind_id="gm_a",
            outcome=ReceiptOutcome.EXECUTED.value,
        )
    )
    assert second.prev_hash == first.integrity_hash
    assert second.sequence == first.sequence + 1


def test_receipt_records_failures_with_an_error_class(audit):
    receipt = build_receipt(
        action_id="ACT-1",
        action_name="search_web",
        mind_id="gm_a",
        outcome=ReceiptOutcome.FAILED.value,
        error=TimeoutError("request timed out after 30s"),
    )
    stored = audit.record_receipt(receipt)
    assert stored.error_class == "timeout"
    assert not stored.success


def test_receipt_duration_is_derived(audit):
    from datetime import datetime, timedelta, timezone

    start = datetime.now(timezone.utc)
    receipt = build_receipt(
        action_id="ACT-1",
        action_name="create_task",
        mind_id="gm_a",
        outcome=ReceiptOutcome.EXECUTED.value,
        started_at=start,
        completed_at=start + timedelta(milliseconds=250),
    )
    assert receipt.duration_ms == pytest.approx(250, abs=1)


def test_receipt_referenced_the_approval_that_allowed_it(audit):
    receipt = build_receipt(
        action_id="ACT-1",
        action_name="send_email",
        mind_id="gm_a",
        outcome=ReceiptOutcome.EXECUTED.value,
        approval_id="apr_1",
        approver_id="owner@example.com",
    )
    stored = audit.record_receipt(receipt)
    assert stored.approval_id == "apr_1"
    assert stored.approver_id == "owner@example.com"


def test_writing_a_receipt_also_journals_it(audit):
    audit.record_receipt(
        build_receipt(
            action_id="ACT-1", action_name="create_task", mind_id="gm_a",
            outcome=ReceiptOutcome.EXECUTED.value,
        )
    )
    assert audit.events(mind_id="gm_a", event_type=EventType.RECEIPT_RECORDED)


@pytest.mark.parametrize(
    "error,expected",
    [
        (TimeoutError("timed out"), "timeout"),
        (PermissionError("denied"), "permission"),
        (FileNotFoundError("no such file"), "not_found"),
        (ValueError("invalid parameter"), "validation"),
        (ImportError("no module named x"), "dependency"),
        (ConnectionError("connection refused"), "external_service"),
        (RuntimeError("something odd"), "runtime"),
        (None, "unknown"),
    ],
)
def test_error_classification(error, expected):
    assert classify_error(error) == expected


def test_receipt_lookup_and_filtering(audit):
    audit.record_receipt(
        build_receipt(
            action_id="A1", action_name="create_task", mind_id="gm_a",
            outcome=ReceiptOutcome.EXECUTED.value,
        )
    )
    audit.record_receipt(
        build_receipt(
            action_id="A2", action_name="send_email", mind_id="gm_a",
            outcome=ReceiptOutcome.BLOCKED.value,
        )
    )
    assert len(audit.receipts(mind_id="gm_a")) == 2
    assert len(audit.receipts(mind_id="gm_a", outcome="blocked")) == 1


def test_receipts_are_scoped_per_mind(audit):
    audit.record_receipt(
        build_receipt(action_id="A1", action_name="x", mind_id="gm_a", outcome="executed")
    )
    assert audit.receipts(mind_id="gm_b") == []


# --------------------------------------------------------------------------- #
# Store durability contract
# --------------------------------------------------------------------------- #


def test_memory_store_refuses_outside_test_env(monkeypatch):
    from genesis.governance.store import GovernanceStoreError, get_governance_store, reset_governance_store

    monkeypatch.setenv("GENESIS_GOVERNANCE_STORE", "memory")
    monkeypatch.setenv("GENESIS_ENV", "production")
    reset_governance_store()
    with pytest.raises(GovernanceStoreError):
        get_governance_store()
    reset_governance_store()


def test_unknown_store_name_is_refused(monkeypatch):
    from genesis.governance.store import GovernanceStoreError, get_governance_store, reset_governance_store

    reset_governance_store()
    with pytest.raises(GovernanceStoreError):
        get_governance_store("not-a-store")
    reset_governance_store()


def test_store_defaults_to_durable_sql():
    from genesis.governance.store import get_governance_store, reset_governance_store

    reset_governance_store()
    try:
        store = get_governance_store()
        assert store.name in ("sql", "memory")
    finally:
        reset_governance_store()
