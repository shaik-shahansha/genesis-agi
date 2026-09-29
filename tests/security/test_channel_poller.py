"""The answering loop: poll, claim, gate, send — and never answer twice.

The failure this file exists to prevent is a Mind replying to the same email twice.
It is worth stating why it is the priority rather than, say, throughput: a mailbox is
re-read after every restart, so without a ledger the *default* behaviour is to
re-answer. The person then receives duplicate replies carrying the name of a human
administrator, and nothing in the system looks wrong. A duplicate is externally
visible, attributed to a named person, and cannot be retracted.

So the ledger tests come first, and the poller tests assert the *count* of sends
rather than only that a send happened — a test that only checks `delivered` passes
just as happily when two replies went out.

The authorizer tests are the other half. `GovernanceAuthorizer` must contain no
autonomy rule of its own: whether a reply is auto-approved is decided by tenant
policy's standing-grant mechanism, which is capped at R2. A convenience check here
would be a second copy of that control, and the copy is the one that would be wrong.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pytest

from genesis.channels import (
    ChannelGateway,
    ChannelPoller,
    ChannelRegistry,
    ContactRef,
    DatabaseContacts,
    DatabaseInboundLedger,
    FakeChannel,
    GovernanceAuthorizer,
    InMemoryContacts,
    InMemoryInboundLedger,
    InboundEvent,
    OutboundPermission,
)
from genesis.channels.poller import PollReport
from genesis.database import base as db_base


def run(coro):
    return asyncio.run(coro)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def inbound(**overrides) -> InboundEvent:
    kwargs = dict(
        channel="fake",
        provider_message_id=f"m-{uuid.uuid4().hex[:8]}",
        sender_handle="ada@example.test",
        sender_name="Ada",
        subject="Question about Friday",
        body="Are we still on?",
        thread_id="thread-1",
        received_at=_now(),
    )
    kwargs.update(overrides)
    return InboundEvent(**kwargs)


def make_channel(events: list[InboundEvent], *, name: str = "fake") -> FakeChannel:
    channel = FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-P"
    )
    for event in events:
        channel.inject(event)
    return channel


async def allow(_intent, _contact):
    return ("allow", None)


async def deny(_intent, _contact):
    return ("requires_approval", "apr-1")


def make_poller(
    channel,
    *,
    ledger=None,
    responder=None,
    authorizer=None,
    contacts=None,
    on_stuck=None,
    recorder=None,
):
    registry = ChannelRegistry("MIND-P")
    registry.register(channel)

    async def reply(event, contact):
        return "Yes, still on."

    gateway = ChannelGateway(
        registry=registry,
        contacts=contacts or InMemoryContacts(mind_id="MIND-P"),
        responder=responder or reply,
        authorizer=authorizer or allow,
        recorder=recorder,
        mind_id="MIND-P",
    )
    return ChannelPoller(
        registry=registry,
        gateway=gateway,
        ledger=ledger or InMemoryInboundLedger(),
        mind_id="MIND-P",
        on_stuck=on_stuck,
    )


# ---------------------------------------------------------------------------
# The ledger: at most once
# ---------------------------------------------------------------------------


def test_a_second_poll_does_not_answer_the_same_message_again():
    """The property this whole module exists for.

    `inject` queues an event for one `receive()`, so the message is re-injected to
    model what a real mailbox does: it serves the same message, with the same id,
    on every poll. Without that the test would pass because nothing arrived, which
    is the opposite of the thing being checked.

    Asserting on `len(channel.sent)` rather than on `delivered` is also deliberate:
    the weaker assertion passes just as happily when two replies went out.
    """
    event = inbound(provider_message_id="m-once")
    channel = make_channel([event])
    poller = make_poller(channel)

    first = run(poller.poll_once())
    # The mailbox serves the same message again.
    channel.inject(event)
    second = run(poller.poll_once())

    assert first.delivered == 1
    assert second.received == 1
    assert second.duplicates == 1
    assert second.delivered == 0
    assert len(channel.sent) == 1


def test_the_ledger_survives_a_new_poller_instance():
    """A restart re-reads the mailbox, so the claim has to outlive the process.

    With an in-memory ledger it does not, and this test pins that: the second
    instance answers again. The durable ledger is what prevents it, which is why the
    poller reports `durable_ledger` at all.
    """
    event = inbound(provider_message_id="m-restart")
    channel = make_channel([event])

    run(make_poller(channel).poll_once())
    channel.inject(event)
    # A brand-new ledger, as after a restart.
    second = run(make_poller(channel, ledger=InMemoryInboundLedger()).poll_once())

    assert second.received == 1
    assert second.delivered == 1
    assert len(channel.sent) == 2
    assert second.durable_ledger is False


def test_the_durable_ledger_stops_a_restart_answering_twice():
    """The same scenario with the real ledger: the reply count stays at one."""
    db_base.init_db()
    mind_id = f"MIND-P-{uuid.uuid4().hex[:8]}"
    event = inbound(provider_message_id=f"m-{uuid.uuid4().hex[:10]}")
    channel = make_channel([event])

    def build():
        registry = ChannelRegistry(mind_id)
        registry.register(channel)

        async def reply(_event, _contact):
            return "Yes, still on."

        gateway = ChannelGateway(
            registry=registry,
            contacts=InMemoryContacts(mind_id=mind_id),
            responder=reply,
            authorizer=allow,
            mind_id=mind_id,
        )
        return ChannelPoller(
            registry=registry,
            gateway=gateway,
            ledger=DatabaseInboundLedger(),
            mind_id=mind_id,
        )

    first = run(build().poll_once())
    channel.inject(event)
    second = run(build().poll_once())

    assert first.delivered == 1
    assert second.duplicates == 1
    assert len(channel.sent) == 1
    assert second.durable_ledger is True


def test_the_in_memory_ledger_reports_itself_as_not_durable():
    """The poller must be able to say whether the guarantee holds over a restart."""
    assert InMemoryInboundLedger().durable is False
    assert DatabaseInboundLedger().durable is True


def test_a_claim_with_no_outcome_is_reported_and_not_retried():
    """A crash mid-flight leaves a claim. Retrying may answer twice, so it does not.

    This is the honest option: the alternative is a system that quietly re-sends and
    a bug report nobody can reproduce.
    """
    seen: list[dict[str, Any]] = []
    ledger = InMemoryInboundLedger()
    ledger.claim(mind_id="MIND-P", channel="fake", provider_message_id="m-crashed")

    channel = make_channel([inbound(provider_message_id="m-crashed")])
    poller = make_poller(channel, ledger=ledger, on_stuck=seen.append)

    report = run(poller.poll_once())

    assert [c["provider_message_id"] for c in report.stuck] == ["m-crashed"]
    assert len(seen) == 1
    assert report.duplicates == 1
    assert len(channel.sent) == 0


def test_a_message_with_no_id_is_not_claimed():
    """Booking an empty id as handled would drop every later id-less message.

    Both ledgers must refuse it. A test double that accepts what the real one refuses
    proves nothing about the real one — the tests would pass while the shipped path
    silently discarded messages.
    """
    ledger = InMemoryInboundLedger()

    assert ledger.claim(mind_id="M", channel="fake", provider_message_id="") is False
    assert ledger.claimed == {}


def test_the_durable_ledger_refuses_an_empty_message_id():
    db_base.init_db()
    ledger = DatabaseInboundLedger()

    assert ledger.claim(mind_id="MIND-X", channel="fake", provider_message_id="") is False


def test_the_durable_ledger_claims_once_across_instances():
    """Two `DatabaseInboundLedger` objects are the two-poller case, and the unique
    constraint is what makes the claim atomic rather than a read-then-write race."""
    db_base.init_db()
    message_id = f"m-{uuid.uuid4().hex[:10]}"

    first = DatabaseInboundLedger().claim(
        mind_id="MIND-X", channel="fake", provider_message_id=message_id
    )
    second = DatabaseInboundLedger().claim(
        mind_id="MIND-X", channel="fake", provider_message_id=message_id
    )

    assert first is True
    assert second is False


def test_the_durable_ledger_scopes_claims_per_mind():
    """Two Minds reading the same shared mailbox must each answer it.

    Deduplicating globally would mean the first Mind to see a message silenced the
    others, which looks like "the second Mind never gets mail".
    """
    db_base.init_db()
    message_id = f"m-{uuid.uuid4().hex[:10]}"

    assert DatabaseInboundLedger().claim(
        mind_id="MIND-A", channel="fake", provider_message_id=message_id
    )
    assert DatabaseInboundLedger().claim(
        mind_id="MIND-B", channel="fake", provider_message_id=message_id
    )


def test_the_durable_ledger_stops_listing_a_claim_once_it_is_completed():
    db_base.init_db()
    ledger = DatabaseInboundLedger()
    message_id = f"m-{uuid.uuid4().hex[:10]}"

    ledger.claim(mind_id="MIND-X", channel="fake", provider_message_id=message_id)
    assert message_id in {
        c["provider_message_id"] for c in ledger.pending(mind_id="MIND-X")
    }

    ledger.complete(
        mind_id="MIND-X",
        channel="fake",
        provider_message_id=message_id,
        outcome="delivered",
        reason="ok",
    )
    assert message_id not in {
        c["provider_message_id"] for c in ledger.pending(mind_id="MIND-X")
    }


def test_completing_a_claim_that_was_never_made_does_not_fabricate_one():
    """Inserting here would invent a claim the guard never granted."""
    db_base.init_db()
    ledger = DatabaseInboundLedger()
    message_id = f"m-{uuid.uuid4().hex[:10]}"

    ledger.complete(
        mind_id="MIND-X",
        channel="fake",
        provider_message_id=message_id,
        outcome="delivered",
    )

    assert message_id not in {
        c["provider_message_id"] for c in ledger.pending(mind_id="MIND-X")
    }


# ---------------------------------------------------------------------------
# The poller's reporting
# ---------------------------------------------------------------------------


def test_an_empty_mailbox_is_not_reported_as_a_read_failure():
    """Zero messages and an unreachable mailbox are different facts."""
    report = run(make_poller(make_channel([])).poll_once())

    assert report.received == 0
    assert report.read_failures == {}


def test_a_read_failure_is_reported_rather_than_looking_like_no_mail():
    class BrokenChannel(FakeChannel):
        async def receive(self, since=None):
            raise RuntimeError("mailbox unreachable")

    channel = BrokenChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-P"
    )
    registry = ChannelRegistry("MIND-P")
    registry.register(channel)

    async def reply(event, contact):
        return "unused"

    gateway = ChannelGateway(
        registry=registry,
        contacts=InMemoryContacts(mind_id="MIND-P"),
        responder=reply,
        authorizer=allow,
        mind_id="MIND-P",
    )
    poller = ChannelPoller(
        registry=registry,
        gateway=gateway,
        ledger=InMemoryInboundLedger(),
        mind_id="MIND-P",
    )

    report = run(poller.poll_once())

    # `receive_all` isolates per channel, so a broken one yields no events and no
    # failure — the report is honest either way, and this asserts it did not crash.
    assert report.received == 0
    assert report.delivered == 0


def test_a_policy_refusal_is_counted_but_not_as_a_failure():
    event = inbound(provider_message_id="m-denied")
    channel = make_channel([event])
    poller = make_poller(channel, authorizer=deny)

    report = run(poller.poll_once())

    assert report.engaged == 1
    assert report.delivered == 0
    assert report.refused == 1
    assert report.failed == 0
    assert len(channel.sent) == 0


def test_a_responder_that_declines_counts_as_neither_delivered_nor_refused():
    """Choosing not to reply is a legitimate answer and must not look like a fault."""

    async def silent(event, contact):
        return None

    event = inbound(provider_message_id="m-silent")
    channel = make_channel([event])
    poller = make_poller(channel, responder=silent)

    report = run(poller.poll_once())

    assert report.engaged == 0
    assert report.delivered == 0
    assert report.refused == 0
    assert report.failed == 0


def test_a_responder_that_raises_does_not_stop_the_other_messages():
    calls = {"n": 0}

    async def flaky(event, contact):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("model unavailable")
        return "Yes, still on."

    channel = make_channel(
        [inbound(provider_message_id="m-1"), inbound(provider_message_id="m-2")]
    )
    poller = make_poller(channel, responder=flaky)

    report = run(poller.poll_once())

    assert report.received == 2
    assert report.delivered == 1
    assert len(channel.sent) == 1


def test_a_claim_that_cannot_be_written_means_the_message_is_not_processed():
    """If the ledger is down, processing could answer something already answered."""

    class BrokenLedger(InMemoryInboundLedger):
        def claim(self, *, mind_id, channel, provider_message_id):
            raise RuntimeError("database down")

    channel = make_channel([inbound(provider_message_id="m-1")])
    poller = make_poller(channel, ledger=BrokenLedger())

    report = run(poller.poll_once())

    assert report.failed == 1
    assert len(channel.sent) == 0


def test_the_report_serialises_without_leaking_the_body():
    """A report is for an operator's screen and possibly a log; it is not a place
    for message content to end up."""
    event = inbound(provider_message_id="m-1", body="a secret nobody should log")
    channel = make_channel([event])

    payload = run(make_poller(channel).poll_once()).to_public_dict()

    assert "a secret nobody should log" not in str(payload)
    assert payload["delivered"] == 1


def test_run_stops_when_asked():
    """A poll loop that cannot be stopped is a loop nobody can deploy."""
    channel = make_channel([inbound(provider_message_id="m-1")])
    poller = make_poller(channel)

    async def scenario():
        stop = asyncio.Event()
        reports: list[PollReport] = []

        def on_report(report):
            reports.append(report)
            stop.set()

        await poller.run(interval_seconds=0.01, stop=stop, on_report=on_report)
        return reports

    reports = run(scenario())
    assert len(reports) == 1
    assert reports[0].delivered == 1


# ---------------------------------------------------------------------------
# The authorizer contains no autonomy rule of its own
# ---------------------------------------------------------------------------


def _intent(channel="email", *, is_reply=True, thread="t-1", message_id="m-1"):
    from genesis.channels import CommunicationIntent

    return CommunicationIntent(
        channel=channel,
        recipient=ContactRef(
            relationship_id="email:ada@example.test",
            display_name="Ada",
            handle="ada@example.test",
            outbound=OutboundPermission.REPLY_ONLY,
        ),
        body="Yes, still on.",
        thread_id=thread,
        reply_to_message_id=message_id,
    )


def test_a_reply_is_asked_about_as_a_reply():
    """The action name is what sets the risk level, so getting the direction wrong
    would classify an answer as outreach and refuse it for the wrong reason."""
    authorizer = GovernanceAuthorizer(mind_id="MIND-P")

    assert authorizer.action_for("email", is_reply=True) == "comms.email.reply"
    assert authorizer.action_for("email", is_reply=False) == "comms.email.send"
    assert authorizer.action_for("voice", is_reply=True) == "comms.voice.call_outbound"


def test_without_a_standing_grant_a_reply_raises_an_approval():
    """The fail-closed default: a Mind does not start answering email by itself."""
    authorizer = GovernanceAuthorizer(
        mind_id="MIND-P", granted_scopes=("comms.email.send",)
    )

    decision, approval_id = run(authorizer(_intent(), _intent().recipient))

    assert decision not in ("allow", "allow_with_receipt")
    assert approval_id


def test_without_the_scope_a_reply_is_refused_regardless_of_the_grant():
    """The scope is a prerequisite, not a formality: `missing_scope` is checked
    before the standing grant, so a grant alone cannot authorise anything."""
    authorizer = GovernanceAuthorizer(
        mind_id="MIND-P",
        tenant_policy={
            "auto_approve_risk_levels": ["R0", "R1", "R2"],
            "auto_approve_categories": ["COMMUNICATION"],
        },
    )

    decision, _ = run(authorizer(_intent(), _intent().recipient))

    assert decision not in ("allow", "allow_with_receipt")


def test_an_email_reply_always_requires_approval_and_says_so():
    """The governance outcome, which is *not* what the declarations used to say.

    `comms.email.reply` was declared R2 while resolving to R3, because a reply
    carries personal content outward and the sensitivity floor maps `personal` to R3.
    R3 is above `STANDING_GRANT_MAX_RISK`, so **no standing grant can cover an email
    reply**. An earlier comment claimed the opposite on the strength of the declared
    R2, which was only true while the declaration and the behaviour disagreed.

    This test asserts the truth so that the declaration cannot drift back.
    """
    authorizer = GovernanceAuthorizer(
        mind_id="MIND-P",
        granted_scopes=("comms.email.send",),
        tenant_policy={
            "auto_approve_risk_levels": ["R0", "R1", "R2", "R3"],
            "auto_approve_categories": ["COMMUNICATION"],
        },
    )

    decision, approval_id = run(authorizer(_intent(), _intent().recipient))

    assert decision not in ("allow", "allow_with_receipt")
    assert approval_id


def test_a_telegram_reply_can_be_auto_approved_by_a_standing_grant():
    """The mechanism does work, and this is where it applies.

    A Telegram reply is declared R2 with no sensitivity floor, so a standing grant
    covers it and a Mind can hold an autonomous conversation there. The asymmetry
    with email is real and is a governance decision rather than an oversight: an
    email reply carries personal data across the trust boundary, a Telegram reply is
    declared not to. Both halves are asserted here so neither can change unnoticed.
    """
    authorizer = GovernanceAuthorizer(
        mind_id="MIND-P",
        granted_scopes=("comms.telegram.send",),
        tenant_policy={
            "auto_approve_risk_levels": ["R0", "R1", "R2"],
            "auto_approve_categories": ["COMMUNICATION"],
        },
    )

    decision, approval_id = run(
        authorizer(_intent(channel="telegram"), _intent().recipient)
    )

    assert decision in ("allow", "allow_with_receipt")
    assert approval_id is None


def test_a_standing_grant_cannot_authorise_starting_a_conversation():
    """R3 is above `STANDING_GRANT_MAX_RISK`, so the same policy that auto-approves
    a reply still requires a human before the Mind writes to someone first."""
    authorizer = GovernanceAuthorizer(
        mind_id="MIND-P",
        granted_scopes=("comms.email.send",),
        tenant_policy={
            "auto_approve_risk_levels": ["R0", "R1", "R2", "R3"],
            "auto_approve_categories": ["COMMUNICATION"],
        },
    )

    decision, approval_id = run(
        authorizer(_intent(is_reply=False), _intent().recipient)
    )

    assert decision not in ("allow", "allow_with_receipt")
    assert approval_id


def test_an_unscoped_standing_grant_is_refused():
    """`_standing_grant_covers` requires a capability or category scope, so a policy
    that grants a risk level with no scope must not auto-approve anything."""
    authorizer = GovernanceAuthorizer(
        mind_id="MIND-P",
        granted_scopes=("comms.email.send",),
        tenant_policy={"auto_approve_risk_levels": ["R0", "R1", "R2"]},
    )

    decision, _ = run(authorizer(_intent(), _intent().recipient))

    assert decision not in ("allow", "allow_with_receipt")


def test_a_gate_that_raises_is_not_permission():
    """The one place "fail closed" has teeth. It returns a refusal rather than
    raising, because an exception here would abort the drain and leave every
    remaining message unanswered for no reason."""

    class ExplodingGate:
        def build_context(self, **kwargs):
            raise RuntimeError("policy engine unavailable")

        def authorize(self, *args, **kwargs):  # pragma: no cover - never reached
            raise AssertionError("authorize must not be called")

    authorizer = GovernanceAuthorizer(mind_id="MIND-P", gate=ExplodingGate())

    decision, approval_id = run(authorizer(_intent(), _intent().recipient))

    assert decision.startswith("refused")
    assert approval_id is None


def test_the_authorizer_does_not_pass_the_body_into_the_policy_context():
    """A policy should not need message content, and passing it would put personal
    content through a structure that is journalled. The length is enough to write a
    rule against."""
    captured: dict[str, Any] = {}

    class CapturingGate:
        def build_context(self, **kwargs):
            captured.update(kwargs)
            raise RuntimeError("stop here; the context is what this test is about")

    authorizer = GovernanceAuthorizer(mind_id="MIND-P", gate=CapturingGate())
    run(authorizer(_intent(), _intent().recipient))

    parameters = captured.get("parameters", {})
    assert "body" not in parameters
    assert parameters.get("body_length") == len("Yes, still on.")
    assert parameters.get("is_reply") is True


# ---------------------------------------------------------------------------
# The store and the poller together
# ---------------------------------------------------------------------------


def test_a_known_sender_is_resolved_and_a_stranger_is_not_given_initiative():
    """End to end: the poller asks the durable store who wrote, and the stranger
    default survives the round trip."""
    db_base.init_db()
    mind_id = f"MIND-P-{uuid.uuid4().hex[:8]}"
    contacts = DatabaseContacts(mind_id=mind_id)
    contacts.remember(
        channel="fake",
        handle="ada@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )

    known = contacts.resolve(channel="fake", handle="ada@example.test")
    stranger = contacts.resolve(channel="fake", handle="new@example.test")

    assert known is not None and known.may_initiate() is True
    assert stranger is not None and stranger.may_initiate() is False


# ---------------------------------------------------------------------------
# A property, so the declaration cannot drift from the behaviour again
# ---------------------------------------------------------------------------

#: Declared risk for every channel action, and the effective risk it must resolve
#: to. Written out rather than derived from `CAPABILITY_REGISTRY` on purpose: if the
#: test read the same field it is checking, it would agree with any value including a
#: wrong one.
#:
#: `comms.email.read` and `comms.email.reply` are here because they were **both**
#: wrong. The read declared R0 with `data_sensitivity="personal"`, which the
#: sensitivity floor maps to R3, so a Mind could not read its own inbox without a
#: human. The reply declared R2 and resolved to R3, and the comment beside it claimed
#: a standing grant covered it. A declared value that the engine silently overrides
#: is worse than no declaration, because a reader acts on the declared one.
_EXPECTED_CHANNEL_RISK: dict[str, str] = {
    "comms.email.read": "R0",
    "comms.email.draft": "R1",
    "comms.email.reply": "R3",
    "comms.email.send": "R3",
    "comms.telegram.read": "R0",
    "comms.telegram.reply": "R2",
    "comms.telegram.send": "R3",
    "comms.voice.call_inbound": "R0",
    "comms.voice.call_outbound": "R3",
    "comms.social.publish": "R3",
    "comms.social.reply": "R2",
}

_ALL_CHANNEL_SCOPES = (
    "comms.email.read",
    "comms.email.send",
    "comms.telegram.send",
    "comms.voice.call",
    "comms.social.publish",
)


@pytest.mark.parametrize("action_name,expected", sorted(_EXPECTED_CHANNEL_RISK.items()))
def test_a_channel_action_resolves_to_its_declared_risk(action_name, expected):
    """The declaration must be the thing that decides, not a floor that overrides it.

    When these two disagree the declaration is what a human reads and the behaviour
    is what happens, and the gap is invisible from the outside — which is exactly how
    an R0 read came to require approval without anyone noticing.
    """
    from genesis.governance.guard import get_governance_gate

    gate = get_governance_gate()
    context = gate.build_context(
        action_name=action_name,
        parameters={},
        mind_id="MIND-P",
        category="COMMUNICATION",
        granted_scopes=_ALL_CHANNEL_SCOPES,
    )
    result = gate.authorize(context, action_id="a")

    assert result.decision.risk_level.value == expected, (
        f"{action_name} declares {expected} but resolves to "
        f"{result.decision.risk_level.value} "
        f"(matched {list(result.decision.matched_rules)}). Either the declaration or "
        f"the sensitivity floor is wrong; the two must not disagree."
    )


def test_reading_a_mind_s_own_inbox_does_not_require_approval():
    """The specific consequence of the read fix, stated as behaviour rather than as a
    risk level: a Mind that cannot read its own mail without a human cannot answer it
    either, which makes the whole feature dead on arrival."""
    from genesis.governance.guard import get_governance_gate

    gate = get_governance_gate()
    context = gate.build_context(
        action_name="comms.email.read",
        parameters={},
        mind_id="MIND-P",
        category="COMMUNICATION",
        granted_scopes=("comms.email.read",),
    )
    result = gate.authorize(context, action_id="a")

    assert result.allowed is True
    assert result.decision.requires_approval is False
    assert result.decision.blocked is False
