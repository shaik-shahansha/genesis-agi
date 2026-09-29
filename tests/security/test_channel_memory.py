"""Inbound messages becoming memories.

Without this a Mind answers someone and forgets them, so the next message from the
same person arrives with no context and the Mind asks a question it already answered.
That is the difference between a Mind that can reply and a Mind that can hold a
conversation.

Three things are worth pinning, and each is a decision that could go the other way:

**The body is stored, unlike in the journal.** Memory is content by definition, and a
memory that stored a hash would remember only that something happened. The domain
journal deliberately carries identity and metadata and never content, because it is an
*audit* record — two purposes, two rules. A test asserts the content is really there,
because "we store the message" is the kind of claim that quietly becomes false.

**But it is bounded.** Anyone who can send this Mind a message can otherwise write an
arbitrary amount into its store. Truncation is lossy and is reported in the metadata
rather than silently applied.

**Importance is derived, not chosen.** A memory's importance decides whether it
survives consolidation, so setting it from the caller's mood would make the Mind's
recall depend on whoever called.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest

from genesis.channels import ConversationMemory, DeliveryReceipt, DeliveryStatus, InboundEvent
from genesis.channels.gateway import EngagementOutcome
from genesis.storage.memory import MemoryManager, MemoryType


@pytest.fixture()
def memory() -> MemoryManager:
    return MemoryManager(mind_id=f"MIND-MEM-{uuid.uuid4().hex[:8]}")


def event(**overrides) -> InboundEvent:
    kwargs = dict(
        channel="email",
        provider_message_id="m-1",
        sender_handle="dana@example.test",
        sender_name="Dana",
        subject="Question about Friday",
        body="Are we still on for Friday?",
        thread_id="thread-1",
        received_at=datetime.now(timezone.utc),
        is_known_contact=True,
    )
    kwargs.update(overrides)
    return InboundEvent(**kwargs)


def outcome(**overrides) -> EngagementOutcome:
    """An engaged outcome.

    `delivered` is a **property** derived from the receipt, not a constructor
    argument, so "the Mind sent it" has to be expressed by supplying a SENT receipt.
    Passing `delivered=True` looks like it should work and raises instead.
    """
    overrides.setdefault(
        "receipt",
        DeliveryReceipt(channel="email", status=DeliveryStatus.SENT),
    )
    kwargs = dict(
        inbound=event(),
        engaged=True,
        reason="sent",
        reply_body="Yes, still on.",
        decision="allow",
    )
    kwargs.update(overrides)
    return EngagementOutcome(**kwargs)


def refused(**overrides) -> EngagementOutcome:
    """An outcome where nothing was sent: no receipt, so `delivered` is False."""
    kwargs = dict(
        inbound=event(),
        engaged=False,
        reason="chose not to reply",
        reply_body=None,
    )
    kwargs.update(overrides)
    return EngagementOutcome(**kwargs)


def memories(memory: MemoryManager) -> list:
    return list(memory.memories.values())


# ---------------------------------------------------------------------------
# What gets remembered
# ---------------------------------------------------------------------------


def test_a_message_becomes_a_memory(memory):
    bridge = ConversationMemory(memory=memory)

    memory_id = bridge(event(), outcome())

    assert memory_id is not None
    assert len(memories(memory)) == 1


def test_the_body_is_actually_stored(memory):
    """"We store the message" is the kind of claim that quietly becomes false.

    A memory that kept a hash, or only the sender, would satisfy "a memory was
    created" and be useless for holding a conversation.
    """
    bridge = ConversationMemory(memory=memory)
    bridge(event(body="The invoice is wrong and I need it fixed."), outcome())

    content = memories(memory)[0].content

    assert "The invoice is wrong and I need it fixed." in content


def test_the_reply_is_stored_with_it(memory):
    """A conversation memory that recorded only one side would make the Mind's own
    position unrecoverable."""
    bridge = ConversationMemory(memory=memory)
    bridge(event(), outcome(reply_body="Yes, still on for Friday."))

    content = memories(memory)[0].content

    assert "Yes, still on for Friday." in content


def test_a_refusal_is_remembered_with_its_reason(memory):
    """Recording *why* nothing was sent is the part that makes this useful later: a
    Mind that reads "I did not reply, because they asked not to be contacted" will not
    try again."""
    bridge = ConversationMemory(memory=memory)
    bridge(
        event(),
        refused(reason="Dana has asked not to be contacted"),
    )

    content = memories(memory)[0].content

    assert "I did not reply" in content
    assert "asked not to be contacted" in content


def test_a_message_with_no_body_is_still_remembered(memory):
    """Something arrived from someone. That is worth knowing even if the body was
    empty, and dropping it would make the Mind unable to answer "did they write?"."""
    bridge = ConversationMemory(memory=memory)
    bridge(event(body=""), outcome())

    content = memories(memory)[0].content

    assert "empty" in content


def test_the_subject_is_kept(memory):
    bridge = ConversationMemory(memory=memory)
    bridge(event(subject="Invoice 4471"), outcome())

    assert "Invoice 4471" in memories(memory)[0].content


def test_the_sender_is_named(memory):
    bridge = ConversationMemory(memory=memory)
    bridge(event(), outcome())

    content = memories(memory)[0].content

    assert "Dana" in content


def test_a_nameless_sender_falls_back_to_the_handle(memory):
    bridge = ConversationMemory(memory=memory)
    bridge(event(sender_name=""), outcome())

    assert "dana@example.test" in memories(memory)[0].content


def test_no_outcome_still_remembers_the_message(memory):
    """The poller may not have an outcome to hand, and losing the memory because of
    that would be worse than losing the context of what the Mind did."""
    bridge = ConversationMemory(memory=memory)
    bridge(event(), None)

    assert len(memories(memory)) == 1


# ---------------------------------------------------------------------------
# The type, the tags and the context
# ---------------------------------------------------------------------------


def test_it_is_an_episodic_memory(memory):
    """An experience that happened, not a fact or a skill."""
    bridge = ConversationMemory(memory=memory)
    bridge(event(), outcome())

    assert memories(memory)[0].type is MemoryType.EPISODIC


def test_it_is_tagged_by_channel_and_direction(memory):
    """So "forget everything from this channel" is a query rather than a scan."""
    bridge = ConversationMemory(memory=memory)
    bridge(event(channel="telegram"), outcome())

    tags = memories(memory)[0].tags

    assert "channel" in tags
    assert "telegram" in tags
    assert "inbound" in tags


def test_a_known_contact_is_tagged_and_contextualised(memory):
    bridge = ConversationMemory(memory=memory)
    bridge(event(is_known_contact=True), outcome())

    record = memories(memory)[0]

    assert "known-contact" in record.tags
    assert record.relationship_context == "personal"


def test_a_stranger_is_tagged_differently(memory):
    """A memory of a stranger and a memory of a colleague should not be
    indistinguishable at recall time."""
    bridge = ConversationMemory(memory=memory)
    bridge(event(is_known_contact=False), outcome())

    record = memories(memory)[0]

    assert "unknown-contact" in record.tags
    assert record.relationship_context == "generic"


def test_the_sender_is_recorded_as_the_user_email(memory):
    """The field the rest of the memory system already uses for "who was involved"."""
    bridge = ConversationMemory(memory=memory)
    bridge(event(), outcome())

    assert memories(memory)[0].user_email == "dana@example.test"


def test_the_metadata_carries_the_provenance(memory):
    """So a memory can be traced back to the message that produced it, and a duplicate
    message can be recognised."""
    bridge = ConversationMemory(memory=memory)
    bridge(event(provider_message_id="msg-99"), outcome())

    meta = memories(memory)[0].metadata

    assert meta["channel"] == "email"
    assert meta["provider_message_id"] == "msg-99"
    assert meta["direction"] == "inbound"
    assert meta["thread_id"] == "thread-1"


def test_the_metadata_records_the_governance_outcome(memory):
    """What the Mind was allowed to do is part of what it should remember."""
    bridge = ConversationMemory(memory=memory)
    bridge(event(), outcome(decision="requires_approval", approval_id="apr-7"))

    meta = memories(memory)[0].metadata

    assert meta["decision"] == "requires_approval"
    assert meta["approval_id"] == "apr-7"


# ---------------------------------------------------------------------------
# The bound
# ---------------------------------------------------------------------------


def test_a_long_body_is_truncated(memory):
    """Anyone who can send this Mind a message can otherwise write an arbitrary amount
    into its store."""
    bridge = ConversationMemory(memory=memory, max_body_chars=50)
    bridge(event(body="x" * 5000), outcome())

    content = memories(memory)[0].content

    assert len(content) < 500
    assert "x" * 51 not in content


def test_truncation_is_reported_rather_than_silent(memory):
    """A lossy write that does not say it was lossy is indistinguishable from a
    complete one, and the difference matters when recalling what someone said."""
    bridge = ConversationMemory(memory=memory, max_body_chars=50)
    bridge(event(body="y" * 5000), outcome())

    assert memories(memory)[0].metadata["body_truncated"] is True


def test_a_short_body_is_not_reported_as_truncated(memory):
    bridge = ConversationMemory(memory=memory, max_body_chars=5000)
    bridge(event(body="short"), outcome())

    assert memories(memory)[0].metadata["body_truncated"] is False


# ---------------------------------------------------------------------------
# Importance
# ---------------------------------------------------------------------------


def test_importance_is_derived_from_facts(memory):
    """A memory's importance decides whether it survives consolidation, so setting it
    from the caller's mood would make recall depend on whoever called."""
    bridge = ConversationMemory(memory=memory)

    bridge(event(is_known_contact=True, sender_verified=True), outcome())
    high = memories(memory)[0].importance

    bridge(
        event(
            provider_message_id="m-2",
            is_known_contact=False,
            sender_verified=False,
            subject="",
        ),
        refused(),
    )
    low = memories(memory)[1].importance

    assert high > low


def test_importance_is_never_zero(memory):
    """A zero-importance memory is consolidated away immediately, which is the same
    as not remembering it."""
    bridge = ConversationMemory(memory=memory)
    bridge(
        event(is_known_contact=False, sender_verified=False, subject=""),
        refused(),
    )

    assert memories(memory)[0].importance > 0.0


def test_importance_stays_within_range(memory):
    bridge = ConversationMemory(memory=memory)
    bridge(event(is_known_contact=True, sender_verified=True), outcome())

    assert 0.0 <= memories(memory)[0].importance <= 1.0


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_a_storage_failure_does_not_raise(memory):
    """The message has already been handled by this point. A memory failure must not
    turn into a channel failure, or a storage problem would look like a mail problem.
    """

    class Broken:
        def add_memory(self, **kwargs):
            raise RuntimeError("storage unavailable")

    bridge = ConversationMemory(memory=Broken())

    assert bridge(event(), outcome()) is None


def test_a_storage_failure_is_not_reported_as_a_memory(memory):
    class Broken:
        def add_memory(self, **kwargs):
            raise RuntimeError("storage unavailable")

    bridge = ConversationMemory(memory=Broken())

    assert bridge(event(), outcome()) is None


def test_the_bridge_can_be_disabled(memory):
    bridge = ConversationMemory(memory=memory, enabled=False)

    assert bridge(event(), outcome()) is None
    assert memories(memory) == []


# ---------------------------------------------------------------------------
# The poller writes the memory
# ---------------------------------------------------------------------------


def test_the_poller_remembers_a_handled_message():
    """End to end: the loop that answers also remembers."""
    from genesis.channels import (
        ChannelPoller,
        ChannelGateway,
        ChannelRegistry,
        DatabaseContacts,
        FakeChannel,
        InMemoryContacts,
        InMemoryInboundLedger,
    )
    from genesis.database import base as db_base

    db_base.init_db()
    mind_id = f"MIND-MEM-{uuid.uuid4().hex[:8]}"
    memory = MemoryManager(mind_id=mind_id)

    channel = FakeChannel(
        address="sage@example.test", administrator="G", mind_id=mind_id
    )
    channel.inject(event(channel="fake"))

    registry = ChannelRegistry(mind_id)
    registry.register(channel)

    async def responder(_event, _contact):
        return "Yes, still on."

    async def allow(_intent, _contact):
        return ("allow", None)

    gateway = ChannelGateway(
        registry=registry,
        contacts=InMemoryContacts(mind_id=mind_id),
        responder=responder,
        authorizer=allow,
        mind_id=mind_id,
    )
    poller = ChannelPoller(
        registry=registry,
        gateway=gateway,
        ledger=InMemoryInboundLedger(),
        mind_id=mind_id,
        conversations=ConversationMemory(memory=memory, mind_id=mind_id),
    )

    report = asyncio.run(poller.poll_once())

    assert report.delivered == 1
    assert len(memories(memory)) == 1
    assert "Are we still on for Friday?" in memories(memory)[0].content


def test_the_poller_remembers_even_when_nothing_was_sent():
    """A message the Mind chose not to answer is still something it should know
    about — arguably more so, since the reason is the useful part."""
    from genesis.channels import (
        ChannelPoller,
        ChannelGateway,
        ChannelRegistry,
        FakeChannel,
        InMemoryContacts,
        InMemoryInboundLedger,
    )
    from genesis.database import base as db_base

    db_base.init_db()
    mind_id = f"MIND-MEM-{uuid.uuid4().hex[:8]}"
    memory = MemoryManager(mind_id=mind_id)

    channel = FakeChannel(
        address="sage@example.test", administrator="G", mind_id=mind_id
    )
    channel.inject(event(channel="fake"))

    registry = ChannelRegistry(mind_id)
    registry.register(channel)

    async def silent(_event, _contact):
        return None

    async def allow(_intent, _contact):
        return ("allow", None)

    gateway = ChannelGateway(
        registry=registry,
        contacts=InMemoryContacts(mind_id=mind_id),
        responder=silent,
        authorizer=allow,
        mind_id=mind_id,
    )
    poller = ChannelPoller(
        registry=registry,
        gateway=gateway,
        ledger=InMemoryInboundLedger(),
        mind_id=mind_id,
        conversations=ConversationMemory(memory=memory, mind_id=mind_id),
    )

    report = asyncio.run(poller.poll_once())

    assert report.delivered == 0
    assert len(memories(memory)) == 1
    assert "chose not to reply" in memories(memory)[0].content


# ---------------------------------------------------------------------------
# The gateway marks who the sender turned out to be
# ---------------------------------------------------------------------------


def _gateway_outcome_for(handle: str, contacts):
    """Run one message through the gateway and return the event it saw."""
    from genesis.channels import (
        ChannelGateway,
        ChannelRegistry,
        FakeChannel,
        InMemoryInboundLedger,
        InboundEvent,
    )

    channel = FakeChannel(
        address="sage@example.test", administrator="G", mind_id="MIND-G"
    )
    registry = ChannelRegistry("MIND-G")
    registry.register(channel)

    seen: dict = {}

    async def responder(event, contact):
        seen["event"] = event
        return "ok"

    async def allow(_intent, _contact):
        return ("allow", None)

    gateway = ChannelGateway(
        registry=registry,
        contacts=contacts,
        responder=responder,
        authorizer=allow,
        mind_id="MIND-G",
    )

    event = InboundEvent(
        channel="fake",
        provider_message_id="m-1",
        sender_handle=handle,
        body="hello",
    )
    asyncio.run(gateway.handle(event))
    return seen.get("event")


def test_the_gateway_marks_a_known_contact_on_the_event():
    """`InboundEvent.is_known_contact` was a field nothing ever wrote.

    It was therefore permanently False, which meant a memory of a colleague and a
    memory of a stranger were indistinguishable at recall time, and the journal said
    `known_contact: false` for everyone. The gateway is the one place that knows,
    because it has just resolved the contact.
    """
    from genesis.channels import InMemoryContacts, ContactRef, OutboundPermission

    known = InMemoryContacts(
        mind_id="MIND-G",
        known={
            "dana@example.test": ContactRef(
                relationship_id="email:dana@example.test",
                display_name="Dana",
                handle="dana@example.test",
                outbound=OutboundPermission.REPLY_ONLY,
            )
        },
    )

    event = _gateway_outcome_for("dana@example.test", known)

    assert event is not None
    assert event.is_known_contact is True


def test_the_gateway_does_not_mark_a_stranger_as_known():
    """The other half, and the one that matters more: a stranger tagged as known
    would be recalled as someone the Mind has a relationship with."""
    from genesis.channels import InMemoryContacts

    event = _gateway_outcome_for("stranger@example.test", InMemoryContacts(mind_id="MIND-G"))

    assert event is not None
    assert event.is_known_contact is False


def test_a_stranger_is_remembered_as_generic_context():
    """End to end: the gateway marks the event, and the memory reads the mark."""
    from genesis.channels import InMemoryContacts

    memory = MemoryManager(mind_id=f"MIND-MEM-{uuid.uuid4().hex[:8]}")
    event = _gateway_outcome_for("stranger@example.test", InMemoryContacts(mind_id="MIND-G"))
    ConversationMemory(memory=memory)(event, None)

    record = memories(memory)[0]

    assert "unknown-contact" in record.tags
    assert record.relationship_context == "generic"
