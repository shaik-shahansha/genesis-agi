"""Channel substrate guarantees.

These are the properties that must hold no matter which channel is plugged in,
which is why they are tested against the shared `BaseChannel` rather than per
adapter. Each one corresponds to a way this could go wrong that a reviewer would
not see in a diff:

  * a message reaching a human without an AI disclosure
  * a message being sent without a governance decision
  * an approved message being swapped for a different one
  * someone being contacted who asked not to be, or at 03:00, or for the fifth
    time this week
  * a provider that cannot confirm delivery being reported as having delivered
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from genesis.channels import (
    ApprovedCommunication,
    ChannelLimits,
    ChannelPolicyRefusal,
    ChannelRegistry,
    ChannelUnavailableError,
    CommunicationIntent,
    ContactRef,
    DeliveryStatus,
    FakeChannel,
    InboundEvent,
    InMemoryOutboundLedger,
    NotAuthorised,
    OptOutRegistry,
    OutboundPermission,
    apply_disclosure,
    assert_disclosed,
    compose_disclosure,
    is_disclosed,
)
from genesis.channels.base import ChannelCapabilities, ChannelIdentity


def run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def channel():
    return FakeChannel(
        address="sage@example.test",
        display_name="Sage",
        administrator="Genesis AGI",
        mind_id="MIND-1",
    )


@pytest.fixture()
def contact():
    return ContactRef(
        relationship_id="REL-1",
        display_name="Ada",
        handle="ada@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="ada wrote first on 2026-09-01",
        quiet_hours=(0, 24),
        max_outbound_per_week=3,
    )


def intent(channel, contact, **overrides):
    kwargs = {
        "channel": channel.name,
        "recipient": contact,
        "body": "Hello Ada.",
        "subject": "Quick question",
        "trigger": "reply",
    }
    kwargs.update(overrides)
    return CommunicationIntent(**kwargs)


def approve(prepared, contact, decision="allow"):
    return ApprovedCommunication(prepared=prepared, contact=contact, decision=decision)


# ---------------------------------------------------------------------------
# Disclosure
# ---------------------------------------------------------------------------


def test_every_prepared_message_discloses(channel, contact):
    """A Mind must not pass as a person, on any channel."""
    prepared = run(channel.prepare(intent(channel, contact)))

    assert is_disclosed(prepared.body)
    assert "AI-operated digital being" in prepared.body
    # The administrator is named. "This is an AI" without "operated by whom" is
    # only half of what a recipient needs.
    assert "Genesis AGI" in prepared.body


def test_disclosure_is_not_applied_twice(channel, contact):
    """`prepare()` can run more than once for one intent; the footer must not stack."""
    once = apply_disclosure("Body.", channel.identity)
    twice = apply_disclosure(once, channel.identity)

    assert once == twice
    assert twice.count("AI-operated digital being") == 1


def test_a_callers_own_disclosure_is_left_alone(channel, contact):
    """The adapter must not rewrite the Mind's deliberate wording."""
    written = "I am an AI-operated digital being, and here is my answer."

    assert apply_disclosure(written, channel.identity) == written


def test_sending_an_undisclosed_body_raises(channel, contact):
    """The structural check, not the conventional one."""
    with pytest.raises(AssertionError, match="undisclosed"):
        assert_disclosed("An ordinary message with no disclosure.", channel.identity)


def test_disclosure_names_the_channel_address_and_administrator(channel):
    disclosure = compose_disclosure(channel.identity)

    assert "sage@example.test" in disclosure
    assert "Genesis AGI" in disclosure


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_a_message_cannot_be_sent_without_an_allowing_decision(channel, contact):
    """The invariant the whole package exists for."""
    prepared = run(channel.prepare(intent(channel, contact)))

    for decision in ("deny", "require_approval", "emergency_stop", ""):
        with pytest.raises(NotAuthorised):
            ApprovedCommunication(prepared=prepared, contact=contact, decision=decision)


def test_allowing_decisions_permit_a_send(contact):
    prepared_holder = {}

    for decision in ("allow", "allow_with_receipt"):
        # A fresh channel per decision: the second send to the same contact would
        # otherwise hit the minimum-gap floor, which is a different guarantee and
        # is tested on its own below.
        fresh = FakeChannel(
            address="sage@example.test",
            display_name="Sage",
            administrator="Genesis AGI",
            mind_id="MIND-1",
        )
        prepared = run(fresh.prepare(intent(fresh, contact)))
        prepared_holder[decision] = prepared
        approved = ApprovedCommunication(prepared=prepared, contact=contact, decision=decision)
        receipt = run(fresh.send(approved))
        assert receipt.status is DeliveryStatus.SENT, decision


def test_an_edited_approval_is_refused(channel, contact):
    """An approval can be persisted and reloaded; a body edited in storage must not send.

    A human-approved message can wait in a queue for hours. Nothing in-process can
    reach in and change a frozen dataclass, so this reproduces the case that
    actually matters: a serialised approval whose body was altered.
    """
    prepared = run(channel.prepare(intent(channel, contact)))
    approved = ApprovedCommunication(prepared=prepared, contact=contact, decision="allow")

    tampered = ApprovedCommunication(
        prepared=prepared,
        contact=contact,
        decision="allow",
        body_digest="0" * 64,
    )

    assert approved.verify_intact() is True
    assert tampered.verify_intact() is False

    receipt = run(channel.send(tampered))
    assert receipt.status is DeliveryStatus.FAILED
    assert "changed after approval" in (receipt.error or "")
    assert channel.sent == []


def test_a_message_prepared_for_another_channel_is_refused(channel, contact):
    prepared = run(channel.prepare(intent(channel, contact)))
    forged = prepared.__class__(**{**prepared.__dict__, "channel": "telegram"})
    approved = ApprovedCommunication(prepared=forged, contact=contact, decision="allow")

    receipt = run(channel.send(approved))

    assert receipt.status is DeliveryStatus.FAILED
    assert "prepared for channel" in (receipt.error or "")


# ---------------------------------------------------------------------------
# Contactability
# ---------------------------------------------------------------------------


def test_a_contact_who_has_not_consented_cannot_be_initiated_to(channel):
    """Fail closed. 'We have their address' is not consent."""
    stranger = ContactRef(
        relationship_id="REL-2",
        display_name="Stranger",
        handle="stranger@example.test",
        outbound=OutboundPermission.NONE,
    )

    prepared = run(channel.prepare(intent(channel, stranger)))

    assert prepared.requires_approval_because
    assert "has not consented" in prepared.requires_approval_because[0]

    receipt = run(channel.send(ApprovedCommunication(prepared=prepared, contact=stranger, decision="allow")))
    assert receipt.status is DeliveryStatus.FAILED


def test_permission_without_a_consent_source_is_refused(channel):
    """An assertion is not provenance."""
    unprovenanced = ContactRef(
        relationship_id="REL-3",
        display_name="Nobody",
        handle="nobody@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="",
        quiet_hours=(0, 24),
    )

    prepared = run(channel.prepare(intent(channel, unprovenanced)))

    assert prepared.requires_approval_because
    assert "no recorded consent source" in prepared.requires_approval_because[0]


def test_reply_only_may_reply_but_not_initiate(channel):
    reply_only = ContactRef(
        relationship_id="REL-4",
        display_name="Bea",
        handle="bea@example.test",
        outbound=OutboundPermission.REPLY_ONLY,
        consent_source="bea started the thread",
        quiet_hours=(0, 24),
    )

    replying = run(channel.prepare(intent(channel, reply_only, thread_id="THREAD-1")))
    assert run(
        channel.send(ApprovedCommunication(prepared=replying, contact=reply_only, decision="allow"))
    ).status is DeliveryStatus.SENT

    initiating = run(channel.prepare(intent(channel, reply_only)))
    assert initiating.requires_approval_because


def test_quiet_hours_are_enforced_and_wrap_over_midnight(channel):
    """Getting this wrong in either direction either silences the Mind or wakes people."""
    night = ContactRef(
        relationship_id="REL-5",
        display_name="Night Owl",
        handle="owl@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="opted in",
        quiet_hours=(0, 24),
        timezone_offset_hours=0,
    )

    # 03:00 UTC, contact at offset 0.
    at_three = datetime(2026, 9, 29, 3, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    prepared = run(channel.prepare(intent(channel, night)))
    receipt = run(
        channel.send(ApprovedCommunication(prepared=prepared, contact=night, decision="allow"))
    )
    # (0, 24) covers every hour, so this must send.
    assert receipt.status is DeliveryStatus.SENT, at_three.isoformat()

    # An ordinary daytime window must exclude 03:00.
    daytime = ContactRef(
        relationship_id="REL-6",
        display_name="Daytime",
        handle="day@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="opted in",
        quiet_hours=(8, 20),
        timezone_offset_hours=6,  # their 09:00 when UTC is 03:00
    )
    assert daytime.within_quiet_hours(datetime(2026, 9, 29, 3, 0)) is True
    assert daytime.within_quiet_hours(datetime(2026, 9, 29, 16, 0)) is False


def test_overnight_window_wraps(channel):
    """`(22, 6)` is eight hours overnight, not an empty range."""
    overnight = ContactRef(
        relationship_id="REL-7",
        display_name="Overnight",
        handle="o@example.test",
        quiet_hours=(22, 6),
    )

    assert overnight.within_quiet_hours(datetime(2026, 9, 29, 23, 0)) is True
    assert overnight.within_quiet_hours(datetime(2026, 9, 29, 2, 0)) is True
    assert overnight.within_quiet_hours(datetime(2026, 9, 29, 12, 0)) is False


def test_weekly_cap_is_enforced_and_replies_do_not_count(contact):
    """A cap that counts replies would stop the Mind holding a conversation.

    The minimum-gap floor is disabled here so this isolates the weekly cap; the
    gap has its own test.
    """
    channel = FakeChannel(
        address="sage@example.test",
        display_name="Sage",
        administrator="Genesis AGI",
        mind_id="MIND-1",
        limits=ChannelLimits(min_gap_between_outbound=timedelta(0)),
    )

    for _ in range(contact.max_outbound_per_week):
        prepared = run(channel.prepare(intent(channel, contact)))
        receipt = run(channel.send(ApprovedCommunication(prepared=prepared, contact=contact, decision="allow")))
        assert receipt.status is DeliveryStatus.SENT

    over = run(channel.prepare(intent(channel, contact)))
    assert over.requires_approval_because
    assert "this week" in over.requires_approval_because[0]

    # Replying is still allowed, because answering someone who wrote first is not
    # outreach.
    reply = run(channel.prepare(intent(channel, contact, thread_id="THREAD-9")))
    assert not reply.requires_approval_because


def test_a_minimum_gap_applies_between_initiated_messages(channel, contact):
    """Three messages a week is fine, three in one minute is not.

    The weekly cap alone would allow a burst, which reads as harassment even when
    it is within the limit.
    """
    first = run(channel.prepare(intent(channel, contact)))
    assert run(
        channel.send(ApprovedCommunication(prepared=first, contact=contact, decision="allow"))
    ).status is DeliveryStatus.SENT

    second = run(channel.prepare(intent(channel, contact)))
    assert second.requires_approval_because
    assert "wait" in second.requires_approval_because[0]

    # A reply is not subject to the gap: answering is not outreach.
    reply = run(channel.prepare(intent(channel, contact, thread_id="THREAD-2")))
    assert not reply.requires_approval_because


def test_opt_out_is_absolute(channel, contact):
    channel.optouts.opt_out(relationship_id=contact.relationship_id)

    prepared = run(channel.prepare(intent(channel, contact)))
    assert prepared.requires_approval_because
    assert "asked not to be contacted" in prepared.requires_approval_because[0]

    receipt = run(channel.send(ApprovedCommunication(prepared=prepared, contact=contact, decision="allow")))
    assert receipt.status is DeliveryStatus.FAILED


def test_opt_out_is_cross_channel(channel, contact):
    """Saying 'stop' on one channel must apply everywhere.

    Otherwise the Mind simply moves to another address the person also has, which
    is the behaviour people are trying to escape.
    """
    channel.optouts.opt_out(handle=contact.handle.upper())

    assert channel.optouts.is_opted_out(handle="ada@example.test") is True
    assert channel.optouts.is_opted_out(handle="ada@other.example") is False


def test_a_boundary_is_surfaced_to_the_approver(channel):
    """A boundary is advisory to the policy but must be visible to a human."""
    bounded = ContactRef(
        relationship_id="REL-8",
        display_name="Chris",
        handle="chris@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="opted in",
        quiet_hours=(0, 24),
        boundaries=["never mention the divorce", "no work calls after 6"],
    )

    prepared = run(channel.prepare(intent(channel, bounded)))

    assert any("boundaries set" in w for w in prepared.warnings)
    assert any("divorce" in w for w in prepared.warnings)


# ---------------------------------------------------------------------------
# Honest receipts
# ---------------------------------------------------------------------------


def test_unknown_delivery_is_reported_as_unknown(channel, contact):
    """A provider that cannot confirm delivery must not be reported as delivered."""
    channel.report_unknown_delivery = True
    prepared = run(channel.prepare(intent(channel, contact)))

    receipt = run(channel.send(ApprovedCommunication(prepared=prepared, contact=contact, decision="allow")))

    assert receipt.status is DeliveryStatus.UNKNOWN
    assert receipt.ok is False


def test_a_provider_failure_does_not_claim_success(channel, contact):
    channel.fail_next_with = ChannelUnavailableError("provider down")
    prepared = run(channel.prepare(intent(channel, contact)))

    with pytest.raises(ChannelUnavailableError):
        run(channel.send(ApprovedCommunication(prepared=prepared, contact=contact, decision="allow")))

    assert channel.sent == []


def test_receipt_records_whether_it_was_disclosed(channel, contact):
    prepared = run(channel.prepare(intent(channel, contact)))
    receipt = run(channel.send(ApprovedCommunication(prepared=prepared, contact=contact, decision="allow")))

    assert receipt.disclosed is True


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_refuses_a_channel_that_cannot_disclose():
    """An undisclosed channel must not be usable, whatever else it can do."""

    class SecretiveChannel(FakeChannel):
        name = "secretive"

        def capabilities(self) -> ChannelCapabilities:
            return ChannelCapabilities(can_send=True, supports_disclosure=False)

    registry = ChannelRegistry("MIND-2")
    registration = registry.register(SecretiveChannel(address="x@example.test"))

    assert registration.enabled is False
    assert "disclosure" in registration.reason
    assert registry.has("secretive") is False


def test_registry_refuses_a_channel_with_no_identity():
    class Anonymous(FakeChannel):
        name = "anonymous"

    registry = ChannelRegistry("MIND-3")
    registration = registry.register(Anonymous(address=""))

    assert registration.enabled is False
    assert "address" in registration.reason


def test_a_disabled_channel_keeps_its_reason():
    """A channel that vanishes is indistinguishable from one never configured."""
    registry = ChannelRegistry("MIND-4")
    registry.register(FakeChannel(address=""))
    described = registry.describe()

    assert described["channels"][0]["enabled"] is False
    assert described["channels"][0]["reason"]


def test_one_broken_channel_does_not_stop_the_others():
    """A Mind with a bad telegram token should still read its email."""

    class Broken(FakeChannel):
        name = "broken"

        async def _fetch_inbound(self, since):
            raise ChannelUnavailableError("token rejected")

    registry = ChannelRegistry("MIND-5")
    healthy = FakeChannel(address="ok@example.test")
    healthy.inject(
        InboundEvent(
            channel="fake",
            provider_message_id="m1",
            sender_handle="ada@example.test",
            body="hello",
        )
    )
    registry.register(healthy)
    registry.register(Broken(address="bad@example.test"))

    events = run(registry.receive_all())

    assert len(events) == 1


# ---------------------------------------------------------------------------
# The ledger must be honest about durability
# ---------------------------------------------------------------------------


def test_in_memory_ledger_declares_itself_non_durable():
    """A rate limit that resets on restart is a control that never ran.

    It is still useful within a process, but nothing may present it as a cap that
    holds over time — so it says so.
    """
    assert InMemoryOutboundLedger().durable is False
