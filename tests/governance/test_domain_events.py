"""Domain journal tests (plan item D2).

The two rules from `genesis/governance/domain_events.py` are the whole point of
this module, and both are security-relevant:

1. **Content never enters the journal** — only identity and metadata. If this
   breaks, deleting a memory stops being true, and the most widely-readable
   artifact in the system starts holding the most personal data.
2. **Journaling never breaks the domain operation** — a journal outage must not
   fail a memory write or lose user data.

Neither is visible from the happy path, so both are tested directly.
"""

from __future__ import annotations

import pytest

from genesis.governance import EventType
from genesis.governance.domain_events import (
    NullDomainJournal,
    get_domain_journal,
    reset_domain_journal,
    set_domain_journal,
)


@pytest.fixture
def audit(store):
    from genesis.governance import AuditService

    return AuditService(store=store)


@pytest.fixture
def journal(audit):
    from genesis.governance.domain_events import _RecordingDomainJournal

    return _RecordingDomainJournal(audit)


class _Memory:
    """Minimal stand-in for `Memory`."""

    def __init__(self, content="a private thought", **kwargs):
        self.id = kwargs.get("id", "mem_1")
        self.content = content
        self.importance = kwargs.get("importance", 0.7)
        self.tags = kwargs.get("tags", ["personal"])
        self.relationship_context = kwargs.get("relationship_context", "personal")
        self.environment_id = kwargs.get("environment_id", None)
        self.user_email = kwargs.get("user_email", "owner@example.com")
        self.metadata = kwargs.get("metadata", {})

        class _Type:
            value = "episodic"

        self.type = _Type()


class _Relationship:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "creator_shahansha")
        self.entity_name = kwargs.get("entity_name", "Shahansha")
        self.relationship_type = kwargs.get("relationship_type", "creator")
        self.trust_level = kwargs.get("trust_level", 0.9)
        self.bond_strength = kwargs.get("bond_strength", 0.5)

    def is_mind_relationship(self):
        return False


class _Goal:
    def __init__(self, **kwargs):
        self.goal_id = kwargs.get("goal_id", "goal_1")
        self.title = kwargs.get("title", "Master Advanced Skills")
        self.description = kwargs.get("description", "long description that is content")
        self.status = kwargs.get("status", "active")


# =========================================================================== #
# Rule 1 — content never enters the journal
# =========================================================================== #


def test_memory_content_is_not_journalled(journal, audit):
    """Decisive test: the memory text must appear nowhere in the event."""
    secret = "my social security number is 123-45-6789"
    journal.memory_accepted(mind_id="gm_1", memory=_Memory(content=secret))

    events = audit.events(mind_id="gm_1")
    assert len(events) == 1
    serialised = str(events[0].payload)
    assert secret not in serialised
    assert "123-45-6789" not in serialised


def test_memory_event_carries_identity_and_metadata(journal, audit):
    journal.memory_accepted(
        mind_id="gm_1", memory=_Memory(id="mem_42", importance=0.85, tags=["work", "urgent"])
    )
    payload = audit.events(mind_id="gm_1")[0].payload

    assert payload["memory_id"] == "mem_42"
    assert payload["memory_type"] == "episodic"
    assert payload["importance"] == 0.85
    assert payload["tags"] == ["work", "urgent"]
    # Scope labels are useful for access review, and describe where a memory
    # belongs rather than what it says.
    assert payload["relationship_context"] == "personal"


def test_memory_event_records_length_not_text(journal, audit):
    """A length is a useful review signal; the text is not ours to copy."""
    journal.memory_accepted(mind_id="gm_1", memory=_Memory(content="x" * 1234))
    payload = audit.events(mind_id="gm_1")[0].payload
    assert payload["content_length"] == 1234
    assert "x" * 100 not in str(payload)


def test_memory_forgotten_does_not_retain_the_content(journal, audit):
    """A deletion record that kept the text would make deletion meaningless."""
    journal.memory_forgotten(mind_id="gm_1", memory_id="mem_9", reason="user asked")
    payload = audit.events(mind_id="gm_1")[0].payload
    assert payload == {"memory_id": "mem_9", "reason": "user asked"}


def test_relationship_event_does_not_carry_the_persons_name(journal, audit):
    """Otherwise the journal becomes a contact list."""
    journal.relationship_created(
        mind_id="gm_1", relationship=_Relationship(entity_name="Harmen van der Meer")
    )
    payload = audit.events(mind_id="gm_1")[0].payload
    assert "Harmen" not in str(payload)
    assert payload["relationship_type"] == "creator"
    assert payload["relationship_id"] == "creator_shahansha"


def test_goal_event_truncates_the_title(journal, audit):
    journal.goal_created(mind_id="gm_1", goal=_Goal(title="t" * 5000))
    payload = audit.events(mind_id="gm_1")[0].payload
    assert len(payload["title"]) <= 121  # 120 + the ellipsis
    # The description is content and must be absent entirely.
    assert "description" not in payload


def test_no_memory_content_survives_a_full_lifecycle(journal, audit):
    secret = "the door code is 9911"
    journal.memory_accepted(mind_id="gm_1", memory=_Memory(content=secret))
    journal.memory_forgotten(mind_id="gm_1", memory_id="mem_1", reason="forget this")
    journal.memory_consolidated(mind_id="gm_1", merged=4, removed=2)

    everything = str([event.to_dict() for event in audit.events(mind_id="gm_1")])
    assert secret not in everything
    assert "9911" not in everything


# =========================================================================== #
# Rule 2 — journaling never breaks the domain operation
# =========================================================================== #


def test_a_broken_audit_service_does_not_raise():
    """A journal outage must not fail the write that triggered it."""

    class ExplodingAudit:
        def record(self, *args, **kwargs):
            raise RuntimeError("journal unavailable")

    from genesis.governance.domain_events import _RecordingDomainJournal

    journal = _RecordingDomainJournal(ExplodingAudit())
    # None of these may raise.
    journal.memory_accepted(mind_id="gm_1", memory=_Memory())
    journal.memory_forgotten(mind_id="gm_1", memory_id="mem_1")
    journal.relationship_created(mind_id="gm_1", relationship=_Relationship())
    journal.goal_created(mind_id="gm_1", goal=_Goal())
    journal.goal_completed(mind_id="gm_1", goal_id="goal_1")


def test_a_malformed_object_does_not_raise(journal):
    """Domain objects come from several call sites; none may crash the journal."""

    class Nonsense:
        @property
        def importance(self):
            raise ValueError("no importance")

    # `importance` raising is caught by the outer guard, so this must not raise.
    journal.memory_accepted(mind_id="gm_1", memory=Nonsense())


def test_null_journal_accepts_every_method():
    """The protocol surface must stay complete, or domain code breaks on a no-op."""
    journal = NullDomainJournal()
    journal.memory_accepted(mind_id="gm_1", memory=_Memory())
    journal.memory_forgotten(mind_id="gm_1", memory_id="m")
    journal.memory_consolidated(mind_id="gm_1", merged=1, removed=0)
    journal.relationship_created(mind_id="gm_1", relationship=_Relationship())
    journal.relationship_interaction(mind_id="gm_1", relationship_id="r", positive=True)
    journal.goal_created(mind_id="gm_1", goal=_Goal())
    journal.goal_progress(mind_id="gm_1", goal_id="g", progress=0.5, status="active")
    journal.goal_completed(mind_id="gm_1", goal_id="g")
    journal.goal_abandoned(mind_id="gm_1", goal_id="g", reason="changed priorities")


def test_recording_journal_covers_the_whole_protocol(journal):
    """`_RecordingDomainJournal` inherits no-ops; assert none were inherited unused.

    A silently inherited no-op means a method exists but records nothing, which
    would look like working code in review.
    """
    from genesis.governance.domain_events import _RecordingDomainJournal

    overridden = set(_RecordingDomainJournal.__dict__)
    for name in (
        "memory_accepted",
        "memory_forgotten",
        "memory_consolidated",
        "relationship_created",
        "relationship_interaction",
        "goal_created",
        "goal_progress",
        "goal_completed",
        "goal_abandoned",
    ):
        assert name in overridden, f"{name} is inherited rather than implemented"


# =========================================================================== #
# Correlation inheritance (D3)
# =========================================================================== #


def test_events_inherit_the_turn_correlation_id(journal, audit):
    from genesis.governance.context import correlation_scope

    with correlation_scope("cor_turn_42", label="chat turn"):
        journal.memory_accepted(mind_id="gm_1", memory=_Memory())
        journal.goal_created(mind_id="gm_1", goal=_Goal())

    events = audit.events(mind_id="gm_1")
    assert len(events) == 2
    assert {event.correlation_id for event in events} == {"cor_turn_42"}


def test_events_outside_a_turn_get_their_own_id(journal, audit):
    journal.memory_accepted(mind_id="gm_1", memory=_Memory())
    journal.goal_created(mind_id="gm_1", goal=_Goal())

    events = audit.events(mind_id="gm_1")
    # Two unrelated events, so they must not be presented as one causal chain.
    assert len({event.correlation_id for event in events}) == 2


# =========================================================================== #
# Resolution
# =========================================================================== #


def test_get_domain_journal_returns_a_usable_journal():
    reset_domain_journal()
    try:
        journal = get_domain_journal()
        assert hasattr(journal, "memory_accepted")
    finally:
        reset_domain_journal()


def test_explicit_journal_replaces_the_default():
    sentinel = NullDomainJournal()
    set_domain_journal(sentinel)
    try:
        assert get_domain_journal() is sentinel
    finally:
        set_domain_journal(None)
        reset_domain_journal()


def test_memory_manager_journals_acceptance(monkeypatch, tmp_path, audit):
    """End-to-end through the storage layer, with a real memory manager."""
    from genesis.storage.memory import MemoryManager, MemoryType

    set_domain_journal(None)
    reset_domain_journal()

    import genesis.governance.domain_events as domain_events
    from genesis.governance.domain_events import _RecordingDomainJournal

    monkeypatch.setattr(domain_events, "_journal", _RecordingDomainJournal(audit))

    manager = MemoryManager(mind_id="gm_storage")
    manager.add_memory(
        content="the passphrase is swordfish",
        memory_type=MemoryType.SEMANTIC,
        importance=0.9,
    )

    events = audit.events(mind_id="gm_storage")
    assert len(events) == 1
    assert events[0].type == EventType.MEMORY_ACCEPTED
    assert "swordfish" not in str(events[0].payload)
    assert events[0].payload["memory_id"]

    reset_domain_journal()


def test_forget_memory_removes_it_and_journals(monkeypatch, audit):
    """A forget must actually forget, in both stores."""
    from genesis.storage.memory import MemoryManager, MemoryType

    import genesis.governance.domain_events as domain_events
    from genesis.governance.domain_events import _RecordingDomainJournal

    monkeypatch.setattr(domain_events, "_journal", _RecordingDomainJournal(audit))

    manager = MemoryManager(mind_id="gm_storage")
    memory = manager.add_memory(
        content="temporary note", memory_type=MemoryType.EPISODIC, importance=0.3
    )

    assert manager.get_memory(memory.id) is not None
    assert manager.forget_memory(memory.id, reason="user asked") is True
    assert manager.get_memory(memory.id) is None

    types = [event.type for event in audit.events(mind_id="gm_storage")]
    assert EventType.MEMORY_FORGOTTEN in types

    # And forgetting something unknown is a no-op, not an error.
    assert manager.forget_memory("mem_does_not_exist") is False

    reset_domain_journal()


def test_a_journal_failure_during_forget_still_forgets(monkeypatch):
    """Deletion must win over auditing."""

    class ExplodingAudit:
        def record(self, *args, **kwargs):
            raise RuntimeError("journal down")

    from genesis.governance.domain_events import _RecordingDomainJournal
    import genesis.governance.domain_events as domain_events
    from genesis.storage.memory import MemoryManager, MemoryType

    monkeypatch.setattr(domain_events, "_journal", _RecordingDomainJournal(ExplodingAudit()))

    manager = MemoryManager(mind_id="gm_storage")
    memory = manager.add_memory(content="x", memory_type=MemoryType.EPISODIC, importance=0.2)

    assert manager.forget_memory(memory.id) is True
    assert manager.get_memory(memory.id) is None

    reset_domain_journal()
