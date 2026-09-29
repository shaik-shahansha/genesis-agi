"""The durable contact store: consent per channel, and what a stranger is.

The point of these tests is the *default*. Everything here is about what happens
when nobody has recorded anything, because that is the state a real installation
spends most of its time in and it is where a permissive default would be
invisible: a Mind that cold-emails people once they write to it looks exactly
like a Mind that is working.

Three properties are load-bearing and each has a test that fails if the property
is removed:

1. `permission` and `consent_source` are **separate**. A row can say `initiate`
   and still grant nothing, because `may_initiate()` also requires a recorded
   reason. That is what makes an initiation a fact rather than an assertion.
2. `record_inbound` grants **reply only**. One inbound message is proof the
   address works, not an opt-in to weekly outreach.
3. The store is bound to one **Mind**. Consent is per-Mind, so a shared resolver
   would let a Mind initiate using another Mind's permission — the gateway refuses
   that, and it is tested here as well as in the gateway suite.

The store enforces nothing else. No quiet hours, no rate limits, no gate — those
live in the adapter and the governance plane, and a store that also enforced would
be a second place for the rules to live and a second place for them to be wrong.
"""

from __future__ import annotations

import uuid

import pytest

from genesis.channels import (
    ChannelGateway,
    ChannelRegistry,
    ContactRef,
    DatabaseContacts,
    FakeChannel,
    InMemoryContacts,
    InboundEvent,
    OutboundPermission,
    normalise_handle,
)
from genesis.database import base as db_base


@pytest.fixture()
def mind_id() -> str:
    """A fresh Mind id per test, so rows never leak between tests.

    The suite shares one database file for the session, so tests must not assume
    an empty table — they must assume a table containing other tests' rows.
    """
    return f"MIND-CONTACT-{uuid.uuid4().hex[:8]}"


@pytest.fixture()
def contacts(mind_id: str) -> DatabaseContacts:
    db_base.init_db()
    return DatabaseContacts(mind_id=mind_id)


def run(coro):
    import asyncio

    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# A stranger
# ---------------------------------------------------------------------------


def test_an_unknown_sender_is_reply_only(contacts):
    """The default that matters most.

    If this returned `INITIATE`, a Mind's first inbound message from anyone would
    be the permission to contact them weekly.
    """
    contact = contacts.resolve(channel="email", handle="stranger@example.test")

    assert contact is not None
    assert contact.outbound is OutboundPermission.REPLY_ONLY
    assert contact.may_reply() is True
    assert contact.may_initiate() is False


def test_an_unknown_sender_has_no_consent_source(contacts):
    """Reply-only *and* no provenance, so raising the permission still is not enough
    on its own: whoever raises it has to say why."""
    contact = contacts.resolve(channel="email", handle="stranger@example.test")

    assert contact is not None
    assert contact.consent_source == ""


def test_an_unknown_sender_keeps_their_name_for_the_reply(contacts):
    contact = contacts.resolve(
        channel="email", handle="stranger@example.test", display_name="Dana"
    )

    assert contact is not None
    assert contact.display_name == "Dana"


def test_an_empty_handle_cannot_be_resolved(contacts):
    assert contacts.resolve(channel="email", handle="   ") is None


# ---------------------------------------------------------------------------
# Recording who someone is
# ---------------------------------------------------------------------------


def test_remember_makes_a_contact_resolvable(contacts):
    rid = contacts.remember(
        channel="email", handle="dana@example.test", display_name="Dana"
    )

    assert rid
    contact = contacts.resolve(channel="email", handle="dana@example.test")
    assert contact is not None
    assert contact.relationship_id == rid
    assert contact.display_name == "Dana"


def test_remember_is_idempotent(contacts):
    """Seeing an address twice must not create two people.

    Two rows for one address would mean two consent records, and an opt-out
    recorded against one would silently not apply to the other.
    """
    first = contacts.remember(channel="email", handle="dana@example.test")
    second = contacts.remember(channel="email", handle="dana@example.test")

    assert first == second


def test_remember_does_not_lower_an_existing_permission(contacts):
    """A routine "I saw this address again" must not revoke a human's decision."""
    contacts.remember(channel="email", handle="dana@example.test")
    contacts.set_permission(
        channel="email",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="signed the intake form on 2026-09-29",
    )

    contacts.remember(channel="email", handle="dana@example.test")

    contact = contacts.resolve(channel="email", handle="dana@example.test")
    assert contact is not None
    assert contact.outbound is OutboundPermission.INITIATE


def test_an_initiate_row_without_a_reason_still_grants_nothing(contacts):
    """The two fields are independent, and that is the design.

    A row that says `initiate` with no `consent_source` is *stored* — refusing the
    write would lose the operator's intent and look identical to "nobody ever
    asked" — but `may_initiate()` refuses it, so nothing is sent.
    """
    contacts.remember(
        channel="email", handle="dana@example.test", outbound=OutboundPermission.INITIATE
    )

    contact = contacts.resolve(channel="email", handle="dana@example.test")
    assert contact is not None
    assert contact.outbound is OutboundPermission.INITIATE
    assert contact.consent_source == ""
    assert contact.may_initiate() is False


def test_setting_initiate_without_a_reason_is_refused_outright(contacts):
    """`remember` stores it silently; `set_permission` refuses it loudly.

    The difference is intent: `remember` is called by automated paths that should
    not crash, `set_permission` is called by an operator making a decision, and an
    operator who writes `initiate` with no reason should be told the permission
    will not take effect rather than discovering it later.
    """
    contacts.remember(channel="email", handle="dana@example.test")

    with pytest.raises(ValueError, match="consent_source"):
        contacts.set_permission(
            channel="email",
            handle="dana@example.test",
            outbound=OutboundPermission.INITIATE,
        )


def test_a_reason_makes_initiation_permitted(contacts):
    contacts.remember(channel="email", handle="dana@example.test")
    assert contacts.set_permission(
        channel="email",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="they asked us to follow up",
    )

    contact = contacts.resolve(channel="email", handle="dana@example.test")
    assert contact is not None
    assert contact.may_initiate() is True


def test_a_permission_can_be_lowered_deliberately(contacts):
    contacts.remember(
        channel="email",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )
    contacts.set_permission(
        channel="email", handle="dana@example.test", outbound=OutboundPermission.NONE
    )

    contact = contacts.resolve(channel="email", handle="dana@example.test")
    assert contact is not None
    assert contact.outbound is OutboundPermission.NONE
    assert contact.may_reply() is False


def test_set_permission_on_an_unknown_handle_changes_nothing(contacts):
    assert (
        contacts.set_permission(
            channel="email",
            handle="nobody@example.test",
            outbound=OutboundPermission.INITIATE,
            consent_source="x",
        )
        is False
    )


# ---------------------------------------------------------------------------
# Revoking
# ---------------------------------------------------------------------------


def test_revoking_keeps_the_row_and_remembers_the_decision(contacts):
    """Deleting would make the next inbound message look like a first contact.

    That is the bug: a deleted row means the next message from this person is
    reply-only *and* re-invitable the moment anything raises the permission again.
    Keeping the row with `none` records that a decision was made.
    """
    contacts.remember(
        channel="email",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )

    assert contacts.revoke(channel="email", handle="dana@example.test", reason="asked us to stop")

    contact = contacts.resolve(channel="email", handle="dana@example.test")
    assert contact is not None
    assert contact.outbound is OutboundPermission.NONE
    assert contact.consent_source == "asked us to stop"
    assert contact.relationship_id != "unknown:email:dana@example.test"


def test_revoking_an_unknown_handle_reports_that_it_did_nothing(contacts):
    assert contacts.revoke(channel="email", handle="nobody@example.test") is False


# ---------------------------------------------------------------------------
# Learning someone from an inbound message
# ---------------------------------------------------------------------------


def test_an_inbound_message_grants_a_reply_and_not_an_initiation(contacts):
    """The single most important default in this file.

    A message that reaches a Mind proves the address works and that someone there
    expects to be reached by it. It says nothing about being contacted later.
    Writing `INITIATE` here would make one inbound message an opt-in to outreach.
    """
    contacts.record_inbound(
        channel="email", handle="dana@example.test", display_name="Dana"
    )

    contact = contacts.resolve(channel="email", handle="dana@example.test")
    assert contact is not None
    assert contact.may_reply() is True
    assert contact.may_initiate() is False
    assert contact.consent_source == ""


def test_an_inbound_message_marks_the_handle_verified(contacts, mind_id):
    """The mailbox answered, which is the only proof an address is theirs."""
    contacts.record_inbound(channel="email", handle="dana@example.test")

    from genesis.database.models import ContactChannelRecord, ContactRecord

    with db_base.get_session() as session:
        row = (
            session.query(ContactChannelRecord)
            .join(ContactRecord, ContactChannelRecord.contact_id == ContactRecord.id)
            .filter(
                # Scoped by mind_id as well: the suite shares one database, so a
                # different test's contact with the same default relationship id
                # is genuinely present in this table.
                ContactRecord.mind_id == mind_id,
                ContactRecord.relationship_id == "email:dana@example.test",
                ContactChannelRecord.channel == "email",
            )
            .one()
        )
        assert row.verified is True


def test_an_inbound_message_does_not_undo_a_revocation(contacts):
    """Someone may write to us after opting out; that is not new consent.

    Silently restoring a permission on inbound would mean the only way to make a
    Mind stop is to make it stop *and* never write again, which is not a choice
    anyone agreed to.
    """
    contacts.remember(
        channel="email",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )
    contacts.revoke(channel="email", handle="dana@example.test", reason="opted out")

    contacts.record_inbound(channel="email", handle="dana@example.test")

    contact = contacts.resolve(channel="email", handle="dana@example.test")
    assert contact is not None
    assert contact.outbound is OutboundPermission.NONE


def test_mark_verified_on_an_unknown_handle_reports_that_it_did_nothing(contacts):
    assert contacts.mark_verified(channel="email", handle="nobody@example.test") is False


# ---------------------------------------------------------------------------
# Consent is per channel, and per Mind
# ---------------------------------------------------------------------------


def test_consent_on_one_channel_does_not_grant_another(contacts):
    """Someone who gave an email address has not agreed to be telephoned.

    This is the reason permission lives on the channel row rather than on the
    contact: one verdict about a person would let a Mind upgrade an address into a
    call.
    """
    contacts.remember(
        channel="email",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )

    assert contacts.resolve(channel="voice", handle="+15550000000") is None or (
        contacts.resolve(channel="voice", handle="+15550000000").may_initiate() is False
    )
    assert contacts.resolve(channel="email", handle="dana@example.test").may_initiate() is True


def test_two_minds_do_not_share_a_contact(mind_id):
    """Consent is per-Mind, so one Mind's permission is not another's."""
    db_base.init_db()
    first = DatabaseContacts(mind_id=mind_id)
    second = DatabaseContacts(mind_id=f"{mind_id}-other")

    first.remember(
        channel="email",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked the first Mind to follow up",
    )

    other = second.resolve(channel="email", handle="dana@example.test")
    assert other is not None
    assert other.may_initiate() is False


def test_known_handles_lists_only_this_mind(contacts, mind_id):
    contacts.remember(channel="email", handle="dana@example.test")
    other = DatabaseContacts(mind_id=f"{mind_id}-other")
    other.remember(channel="email", handle="sam@example.test")

    assert contacts.known_handles(channel="email") == {"dana@example.test"}


# ---------------------------------------------------------------------------
# Handles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  Sage@Example.COM  ", "sage@example.com"),
        ("<sage@example.com>", "sage@example.com"),
        (" <Sage@Example.com> ", "sage@example.com"),
    ],
)
def test_email_handles_normalise(raw, expected):
    assert normalise_handle("email", raw) == expected


def test_phone_handles_are_not_lowercased_into_a_false_match():
    """Digits are unaffected by case, so lowercasing would only hide a malformed
    number — and `+1 (555)` normalising to the same thing as `+1555` is not a
    decision this layer should make."""
    assert normalise_handle("voice", "+15550000000") == "+15550000000"


def test_two_spellings_of_one_address_are_one_contact(contacts):
    """Otherwise an opt-out against one spelling does not apply to the other."""
    first = contacts.remember(channel="email", handle="Sage@Example.com")
    second = contacts.remember(channel="email", handle=" sage@example.com ")

    assert first == second


# ---------------------------------------------------------------------------
# Corrupt rows fail closed
# ---------------------------------------------------------------------------


def _force_row(mind_id: str, **values):
    """Write a value the code would never write, to test how it reads it."""
    from genesis.database.models import ContactChannelRecord, ContactRecord

    with db_base.get_session() as session:
        contact = ContactRecord(
            mind_id=mind_id,
            relationship_id=f"email:corrupt-{uuid.uuid4().hex[:6]}@example.test",
            display_name="Corrupt",
            **{k: v for k, v in values.items() if k in {"trust", "quiet_hours",
                                                       "max_outbound_per_week",
                                                       "timezone_offset_hours"}},
        )
        session.add(contact)
        session.flush()
        session.add(
            ContactChannelRecord(
                contact_id=contact.id,
                channel="email",
                address=contact.relationship_id.split(":", 1)[1],
                outbound=values.get("outbound", "none"),
                consent_source=values.get("consent_source", ""),
            )
        )
        return contact.relationship_id.split(":", 1)[1]


def test_an_unrecognised_permission_reads_as_none(contacts, mind_id):
    """The most restrictive reading of a value we cannot parse."""
    handle = _force_row(mind_id, outbound="yolo")

    contact = contacts.resolve(channel="email", handle=handle)
    assert contact is not None
    assert contact.outbound is OutboundPermission.NONE
    assert contact.may_reply() is False


def test_an_unreadable_trust_score_reads_as_untrusted(contacts, mind_id):
    """`trust_in` returns 0.0 for an absent domain, so a score we cannot read must
    not become a score we can."""
    handle = _force_row(mind_id, trust={"email": "very much"})

    contact = contacts.resolve(channel="email", handle=handle)
    assert contact is not None
    assert contact.trust_in("email") == 0.0


def test_a_missing_domain_is_untrusted_not_neutral(contacts, mind_id):
    """The scalar `trust_level` on `RelationshipRecord` defaults to 0.5, which
    makes an unconsidered domain half trusted. That is the wrong direction."""
    handle = _force_row(mind_id, trust={"email": 0.9})

    contact = contacts.resolve(channel="email", handle=handle)
    assert contact is not None
    assert contact.trust_in("email") == pytest.approx(0.9)
    assert contact.trust_in("phone") == 0.0


def test_a_malformed_window_falls_back_to_the_default(contacts, mind_id):
    handle = _force_row(mind_id, quiet_hours=["morning", "evening"])

    contact = contacts.resolve(channel="email", handle=handle)
    assert contact is not None
    assert contact.quiet_hours == (8, 20)


def test_an_absent_window_uses_the_default_rather_than_no_window(contacts, mind_id):
    """Null means "use the channel default". A window of `(0, 0)` would mean
    "never", which is not what an absent value says."""
    handle = _force_row(mind_id, quiet_hours=None)

    contact = contacts.resolve(channel="email", handle=handle)
    assert contact is not None
    assert contact.quiet_hours == (8, 20)


def test_an_absent_cap_uses_the_default_rather_than_zero(contacts, mind_id):
    """Zero would mean "may never be contacted", which is what `outbound="none"`
    is for. Conflating the two would silently disable every contact."""
    handle = _force_row(mind_id, max_outbound_per_week=None)

    contact = contacts.resolve(channel="email", handle=handle)
    assert contact is not None
    assert contact.max_outbound_per_week == 3


# ---------------------------------------------------------------------------
# The gateway refuses another Mind's resolver
# ---------------------------------------------------------------------------


def test_the_gateway_refuses_a_resolver_belonging_to_another_mind():
    """A wiring mistake that would otherwise be silent.

    The resolver would answer "may I contact this person?" with the *other* Mind's
    consent, so this Mind would initiate a message using a permission that was
    never granted to it. There is no safe way to guess which side is correct, so
    nothing is sent.
    """

    async def scenario():
        channel = FakeChannel(
            address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-A"
        )
        channel.inject(
            InboundEvent(
                channel="email",
                provider_message_id="m-1",
                sender_handle="dana@example.test",
                sender_name="Dana",
                subject="Hello",
                body="Are you there?",
            )
        )

        async def responder(event, contact):
            return "Yes."

        async def authorizer(intent, contact):
            return ("allow", None)

        registry = ChannelRegistry("MIND-A")
        registry.register(channel)

        gateway = ChannelGateway(
            registry=registry,
            # Belongs to MIND-B.
            contacts=InMemoryContacts(mind_id="MIND-B"),
            responder=responder,
            authorizer=authorizer,
            mind_id="MIND-A",
        )
        return await gateway.drain()

    outcomes = run(scenario())

    assert len(outcomes) == 1
    assert outcomes[0].engaged is False
    assert "MIND-B" in outcomes[0].reason
    assert outcomes[0].receipt is None


def test_a_resolver_with_no_mind_id_is_not_refused():
    """An empty id means "belongs to no particular Mind", which is what a test or
    a dry run wants. Refusing it would make the in-memory double unusable."""

    async def scenario():
        channel = FakeChannel(
            address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-A"
        )
        channel.inject(
            InboundEvent(
                channel="fake",
                provider_message_id="m-1",
                sender_handle="dana@example.test",
                subject="Hello",
                body="Are you there?",
            )
        )

        async def responder(event, contact):
            return "Yes."

        async def authorizer(intent, contact):
            return ("allow", None)

        registry = ChannelRegistry("MIND-A")
        registry.register(channel)

        gateway = ChannelGateway(
            registry=registry,
            contacts=InMemoryContacts(),
            responder=responder,
            authorizer=authorizer,
            mind_id="MIND-A",
        )
        return await gateway.drain()

    outcomes = run(scenario())
    assert outcomes[0].delivered is True
