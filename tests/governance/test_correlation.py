"""Correlation context tests (plan item D1/D3).

The capability under test is narrow and easy to get wrong: everything caused by
one cognitive turn must share an id, and nothing else may accidentally share it.
Concurrency is the interesting case, because a shared global would pass a
single-threaded test and corrupt a busy server.
"""

from __future__ import annotations

import asyncio

import pytest

from genesis.governance.context import (
    correlation_scope,
    current_correlation_id,
    current_correlation_label,
    explain_chain,
    new_correlation_id,
    set_correlation_id,
)


def test_no_scope_means_no_correlation_id():
    """An event outside a turn must not be attributed to a turn that exists."""
    assert current_correlation_id() is None
    assert current_correlation_label() is None


def test_scope_provides_an_id():
    with correlation_scope() as correlation_id:
        assert correlation_id.startswith("cor_")
        assert current_correlation_id() == correlation_id


def test_scope_clears_after_exit():
    with correlation_scope():
        assert current_correlation_id() is not None
    assert current_correlation_id() is None


def test_scope_clears_after_an_exception():
    """A turn that raises must not leak its id into the next one."""
    with pytest.raises(RuntimeError):
        with correlation_scope():
            raise RuntimeError("turn failed")
    assert current_correlation_id() is None


def test_explicit_id_is_reused():
    """Resuming a suspended objective should continue its chain, not start one."""
    with correlation_scope("cor_existing") as correlation_id:
        assert correlation_id == "cor_existing"


def test_nested_scopes_restore_the_outer_value():
    with correlation_scope("cor_outer") as outer:
        with correlation_scope() as inner:
            assert inner != outer
            assert current_correlation_id() == inner
        # The outer turn is still in force.
        assert current_correlation_id() == outer


def test_label_is_recorded_and_restored():
    with correlation_scope(label="autonomous tick"):
        assert current_correlation_label() == "autonomous tick"
        with correlation_scope(label="reflection"):
            assert current_correlation_label() == "reflection"
        assert current_correlation_label() == "autonomous tick"
    assert current_correlation_label() is None


def test_ids_are_unique():
    ids = {new_correlation_id() for _ in range(200)}
    assert len(ids) == 200


def test_set_correlation_id_without_a_scope():
    set_correlation_id("cor_pinned")
    try:
        assert current_correlation_id() == "cor_pinned"
    finally:
        set_correlation_id(None)


# --------------------------------------------------------------------------- #
# Concurrency: contextvars, not a global
# --------------------------------------------------------------------------- #


def test_concurrent_tasks_do_not_share_an_id():
    """The property that makes this safe on a busy API server."""

    async def turn(label: str) -> tuple[str, str]:
        with correlation_scope(label=label) as correlation_id:
            # Yield, so any shared state would be observed by the other task.
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            return label, correlation_id

    async def run_all():
        return await asyncio.gather(*(turn(f"turn-{index}") for index in range(20)))

    results = asyncio.run(run_all())
    ids = [correlation_id for _, correlation_id in results]
    labels = {label: correlation_id for label, correlation_id in results}

    assert len(set(ids)) == 20, "concurrent turns shared a correlation id"
    assert len(set(labels.values())) == 20


def test_a_nested_task_inherits_the_parents_scope():
    """asyncio copies context into a new task, which is what we want."""

    async def child() -> str | None:
        return current_correlation_id()

    async def parent():
        with correlation_scope("cor_parent"):
            return await asyncio.create_task(child())

    assert asyncio.run(parent()) == "cor_parent"


# --------------------------------------------------------------------------- #
# explain_chain — the shape the workspace timeline needs
# --------------------------------------------------------------------------- #


class _Event:
    """Stand-in for AuditEvent, to keep these tests independent of the store."""

    def __init__(self, event_id, type, sequence, payload=None, **extra):
        self.event_id = event_id
        self.type = type
        self.sequence = sequence
        self.payload = payload or {}
        self.timestamp = f"2026-09-28T10:00:{sequence:02d}+00:00"
        self.correlation_id = "cor_1"
        self.causation_id = None
        self.actor_type = "mind"
        self.actor_id = "gm_1"
        for key, value in extra.items():
            setattr(self, key, value)


def test_explain_chain_orders_by_sequence():
    events = [
        _Event("e3", "action.executed", 3, {"outcome": "executed"}),
        _Event("e1", "action.proposed", 1, {"action_name": "send_email"}),
        _Event("e2", "action.policy_evaluated", 2, {"decision": "require_approval"}),
    ]
    chain = explain_chain(events)
    assert [step["type"] for step in chain["steps"]] == [
        "action.proposed",
        "action.policy_evaluated",
        "action.executed",
    ]
    assert chain["count"] == 3
    assert chain["correlation_id"] == "cor_1"


def test_explain_chain_summarises_without_dumping_the_payload():
    events = [
        _Event(
            "e1",
            "action.policy_evaluated",
            1,
            {"action_name": "send_email", "decision": "require_approval", "noise": "x" * 500},
        )
    ]
    chain = explain_chain(events)
    summary = chain["steps"][0]["summary"]
    assert "send_email" in summary
    assert "require_approval" in summary
    # The summary is short; the full payload is still available separately.
    assert len(summary) < 200
    assert chain["steps"][0]["payload"]["noise"]


def test_explain_chain_accepts_plain_dicts():
    """The API may hand back serialised events rather than objects."""
    events = [
        {"event_id": "e1", "type": "action.blocked", "sequence": 1, "payload": {"reason_code": "constitution_prohibited"}, "correlation_id": "cor_9"},
    ]
    chain = explain_chain(events)
    assert chain["steps"][0]["type"] == "action.blocked"
    assert "constitution_prohibited" in chain["steps"][0]["summary"]


def test_explain_chain_handles_an_empty_journal():
    """A partial or empty chain must not make the UI raise."""
    chain = explain_chain([])
    assert chain == {"correlation_id": None, "steps": [], "count": 0, "types": []}


def test_explain_chain_handles_an_unfamiliar_event_type():
    """A new event family should still render something."""
    chain = explain_chain([_Event("e1", "skill.learned", 1, {"skill": "summarise"})])
    assert "summarise" in chain["steps"][0]["summary"]


def test_explain_chain_never_includes_content_keys():
    """The journal excludes memory content; the summary must not reintroduce it."""
    chain = explain_chain(
        [_Event("e1", "memory.accepted", 1, {"memory_type": "episodic", "content_length": 42})]
    )
    summary = chain["steps"][0]["summary"]
    assert "episodic" in summary
    assert "content=" not in summary
