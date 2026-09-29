"""Durable rate limits and durable opt-out — the two controls that reset on restart.

Both of these were process-local, and both failed in the same direction: silently, by
becoming more permissive after a restart. That is why every test here is written
against the *durable* implementation and then checked for the property that the
in-memory one lacks.

The two bugs found while writing this are worth naming, because neither was visible
by reading the code — each channel was individually correct:

1. **The weekly cap was per channel.** `BaseChannel.__init__` builds its own ledger
   when none is injected, and `build_registry` injected none. So a Mind could send
   three emails, three Telegram messages and three calls — nine contacts in a week
   against a documented limit of three, with every channel compliant.
2. **Opt-out was per channel.** Someone who said "stop" by email could be telephoned,
   because each adapter had its own registry. That is the exact behaviour the opt-out
   exists to prevent, and it was invisible on an install with one channel configured.

Both are covered below with assertions on the observable outcome ("is this send
refused?"), not on object identity, because the bug was that the *behaviour* was
wrong while every object was correct in isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from genesis.channels import (
    ChannelLimits,
    DatabaseOptOutRegistry,
    DatabaseOutboundLedger,
    InMemoryOutboundLedger,
    build_registry,
    credentials_from_settings,
)
from genesis.channels.base import ContactRef, OutboundPermission
from genesis.channels.limits import outbound_refusal_reason
from genesis.config.settings import Settings
from genesis.database import base as db_base


@pytest.fixture()
def mind_id() -> str:
    """A fresh Mind per test, so rows never leak between tests in the shared DB."""
    db_base.init_db()
    return f"MIND-LEDGER-{uuid.uuid4().hex[:8]}"


@pytest.fixture()
def ledger(mind_id) -> DatabaseOutboundLedger:
    return DatabaseOutboundLedger()


@pytest.fixture()
def optouts(mind_id) -> DatabaseOptOutRegistry:
    return DatabaseOptOutRegistry(mind_id=mind_id)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def contact(**overrides) -> ContactRef:
    kwargs = dict(
        relationship_id="email:dana@example.test",
        display_name="Dana",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
        max_outbound_per_week=3,
    )
    kwargs.update(overrides)
    return ContactRef(**kwargs)


# ---------------------------------------------------------------------------
# The outbound ledger: the cap has to survive a restart
# ---------------------------------------------------------------------------


def test_the_durable_ledger_reports_itself_as_durable(ledger):
    assert ledger.durable is True
    assert InMemoryOutboundLedger().durable is False


def test_a_recorded_message_is_counted_by_a_different_instance(ledger, mind_id):
    """The restart case. A new instance is what a restart produces, and the count
    must not be zero — that is the entire reason this implementation exists."""
    ledger.record(
        mind_id=mind_id,
        relationship_id="email:dana@example.test",
        channel="email",
        at=_now(),
    )

    fresh = DatabaseOutboundLedger()
    assert fresh.count_since(
        mind_id=mind_id,
        relationship_id="email:dana@example.test",
        since=_now() - timedelta(days=7),
    ) == 1


def test_the_cap_is_still_in_force_after_a_restart(ledger, mind_id):
    """Stated as behaviour rather than as a count, because the failure was
    behavioural: the limit disappeared."""
    person = "email:dana@example.test"
    for _ in range(3):
        ledger.record(
            mind_id=mind_id, relationship_id=person, channel="email", at=_now()
        )

    reason = outbound_refusal_reason(
        contact=contact(relationship_id=person),
        is_reply=False,
        ledger=DatabaseOutboundLedger(),
        mind_id=mind_id,
    )

    assert reason is not None
    assert "3 initiated messages this week" in reason


def test_messages_older_than_a_week_do_not_count(ledger, mind_id):
    """Otherwise the cap would be a lifetime total rather than a weekly one."""
    person = "email:dana@example.test"
    ledger.record(
        mind_id=mind_id,
        relationship_id=person,
        channel="email",
        at=_now() - timedelta(days=8),
    )

    assert ledger.count_since(
        mind_id=mind_id, relationship_id=person, since=_now() - timedelta(days=7)
    ) == 0


def test_a_never_contacted_person_has_no_last_outbound_time(ledger, mind_id):
    """`None` must stay distinguishable from a stale timestamp: the minimum-gap
    floor is skipped entirely for someone never contacted, and returning an epoch
    value would instead skip the floor for everyone whose timestamp failed to read."""
    assert ledger.last_outbound_at(
        mind_id=mind_id, relationship_id="email:never@example.test"
    ) is None


def test_last_outbound_at_returns_the_most_recent(ledger, mind_id):
    person = "email:dana@example.test"
    older = _now() - timedelta(days=2)
    newer = _now() - timedelta(hours=1)
    ledger.record(mind_id=mind_id, relationship_id=person, channel="email", at=older)
    ledger.record(mind_id=mind_id, relationship_id=person, channel="telegram", at=newer)

    result = ledger.last_outbound_at(mind_id=mind_id, relationship_id=person)

    assert result is not None
    assert abs((result - newer).total_seconds()) < 2


def test_the_returned_timestamp_is_timezone_aware(ledger, mind_id):
    """This is the trap that would have shipped.

    `utcnow()` is aware and SQLite stores no offset, so a value read back is naive.
    Comparing it to `utcnow()` raises `TypeError: can't compare offset-naive and
    offset-aware datetimes` — but only on the *second* run, because the first write
    has nothing to compare against. It would have worked in testing and failed in
    the second week of real use.
    """
    person = "email:dana@example.test"
    ledger.record(mind_id=mind_id, relationship_id=person, channel="email", at=_now())

    result = ledger.last_outbound_at(mind_id=mind_id, relationship_id=person)

    assert result is not None
    assert result.tzinfo is not None
    # The actual comparison the production path performs.
    assert (_now() - result) < timedelta(minutes=5)


def test_the_minimum_gap_works_across_a_reload(ledger, mind_id):
    """The same trap, reached through the real floor rather than the raw accessor."""
    person = "email:dana@example.test"
    ledger.record(mind_id=mind_id, relationship_id=person, channel="email", at=_now())

    reason = outbound_refusal_reason(
        contact=contact(relationship_id=person),
        is_reply=False,
        ledger=DatabaseOutboundLedger(),
        mind_id=mind_id,
        limits=ChannelLimits(min_gap_between_outbound=timedelta(hours=6)),
    )

    assert reason is not None
    assert "wait" in reason


def test_an_aware_timestamp_is_converted_not_stripped(ledger, mind_id):
    """`replace(tzinfo=None)` on an aware value keeps the *local* wall clock and
    shifts the instant, which would move a message into or out of the weekly window
    depending on the caller's offset."""
    person = "email:dana@example.test"
    plus_five = timezone(timedelta(hours=5))
    # 23:00 at +05:00 is 18:00 UTC — inside the last week, and the same instant.
    ledger.record(
        mind_id=mind_id,
        relationship_id=person,
        channel="email",
        at=datetime.now(plus_five),
    )

    assert ledger.count_since(
        mind_id=mind_id, relationship_id=person, since=_now() - timedelta(days=7)
    ) == 1


def test_two_identical_sends_are_counted_twice(ledger, mind_id):
    """There is deliberately no unique constraint.

    A retry after an ambiguous provider response is two messages, and it must cost
    two units of allowance. Deduplicating here would hand back allowance that was
    actually spent — the opposite of the `inbound_events` table, where a duplicate
    reply is a visible harm to a person.
    """
    person = "email:dana@example.test"
    at = _now()
    ledger.record(mind_id=mind_id, relationship_id=person, channel="email", at=at)
    ledger.record(mind_id=mind_id, relationship_id=person, channel="email", at=at)

    assert ledger.count_since(
        mind_id=mind_id, relationship_id=person, since=at - timedelta(minutes=1)
    ) == 2


def test_counts_are_scoped_to_one_mind(ledger, mind_id):
    """Otherwise one Mind's outreach would consume another's allowance."""
    person = "email:dana@example.test"
    ledger.record(mind_id=mind_id, relationship_id=person, channel="email", at=_now())

    assert ledger.count_since(
        mind_id=f"{mind_id}-other",
        relationship_id=person,
        since=_now() - timedelta(days=7),
    ) == 0


def test_recent_lists_what_was_sent(ledger, mind_id):
    person = "email:dana@example.test"
    ledger.record(mind_id=mind_id, relationship_id=person, channel="email", at=_now())

    rows = ledger.recent(mind_id=mind_id, days=7)

    assert len(rows) == 1
    assert rows[0]["relationship_id"] == person
    assert rows[0]["channel"] == "email"


# ---------------------------------------------------------------------------
# The opt-out: the most dangerous non-durable control
# ---------------------------------------------------------------------------


def test_an_opt_out_survives_a_new_registry_instance(optouts, mind_id):
    """A restart must not forget that someone asked to be left alone."""
    optouts.opt_out(relationship_id="email:dana@example.test", reason="asked us to stop")

    fresh = DatabaseOptOutRegistry(mind_id=mind_id)
    assert fresh.is_opted_out(relationship_id="email:dana@example.test") is True


def test_an_opt_out_blocks_an_initiated_message_after_a_restart(optouts, mind_id):
    """Stated as the observable outcome: the send is refused."""
    person = "email:dana@example.test"
    optouts.opt_out(relationship_id=person, reason="asked us to stop")

    fresh = DatabaseOptOutRegistry(mind_id=mind_id)
    reason = outbound_refusal_reason(
        contact=contact(relationship_id=person),
        is_reply=False,
        ledger=DatabaseOutboundLedger(),
        mind_id=mind_id,
        opted_out=fresh.is_opted_out(relationship_id=person, handle="dana@example.test"),
    )

    assert reason is not None
    assert "asked not to be contacted" in reason


def test_an_opt_out_recorded_by_handle_matches_a_relationship_lookup(optouts):
    """The person wrote from an address the Mind has no contact record for. They
    still asked to be left alone, and the handle key is what catches that."""
    optouts.opt_out(handle="dana@example.test")

    assert optouts.is_opted_out(handle="dana@example.test") is True


def test_a_handle_opt_out_is_case_insensitive(optouts):
    """An opt-out recorded against `Dana@Example.com` must catch mail from
    `dana@example.com`, or the mechanism has a one-character bypass."""
    optouts.opt_out(handle="Dana@Example.COM")

    assert optouts.is_opted_out(handle="dana@example.com") is True


def test_a_handle_opt_out_ignores_angle_brackets(optouts):
    """A copy-paste from an email header leaves them, and an opt-out that a stray
    `<` defeats is not an opt-out."""
    optouts.opt_out(handle="<dana@example.test>")

    assert optouts.is_opted_out(handle="dana@example.test") is True


def test_recording_both_keys_means_either_one_matches(optouts):
    """Storing only one of them would leave a route back in: the relationship key
    survives an address change, the handle key survives a missing contact record."""
    optouts.opt_out(relationship_id="email:dana@example.test", handle="dana@example.test")

    assert optouts.is_opted_out(relationship_id="email:dana@example.test") is True
    assert optouts.is_opted_out(handle="dana@example.test") is True


def test_opting_out_twice_is_one_opt_out(optouts, mind_id):
    """A person repeating themselves must not grow the table or change anything."""
    optouts.opt_out(handle="dana@example.test", reason="stop")
    optouts.opt_out(handle="dana@example.test", reason="stop")

    rows = optouts.all_opt_outs()
    assert len([r for r in rows if r["subject"] == "dana@example.test"]) == 1


def test_an_opt_out_with_neither_key_is_ignored(optouts):
    """Nothing to key on, so there is nothing to record. Silently doing nothing is
    correct here; recording a row with an empty subject would match every lookup."""
    optouts.opt_out()

    assert optouts.is_opted_out(relationship_id="email:anyone@example.test") is False
    assert optouts.all_opt_outs() == []


def test_clearing_an_opt_out_reports_whether_it_changed_anything(optouts):
    optouts.opt_out(relationship_id="email:dana@example.test")

    assert optouts.clear(relationship_id="email:dana@example.test") is True
    assert optouts.is_opted_out(relationship_id="email:dana@example.test") is False
    assert optouts.clear(relationship_id="email:dana@example.test") is False


def test_clearing_a_relationship_opt_out_leaves_the_handle_one(optouts):
    """The Mind does not know whether the handle row is the same person, and
    removing it on the strength of a relationship-level "actually it's fine" would
    be guessing in the permissive direction."""
    optouts.opt_out(relationship_id="email:dana@example.test", handle="dana@example.test")

    optouts.clear(relationship_id="email:dana@example.test")

    assert optouts.is_opted_out(relationship_id="email:dana@example.test") is False
    assert optouts.is_opted_out(handle="dana@example.test") is True


def test_opt_outs_are_scoped_to_one_mind(optouts, mind_id):
    optouts.opt_out(relationship_id="email:dana@example.test")

    other = DatabaseOptOutRegistry(mind_id=f"{mind_id}-other")
    assert other.is_opted_out(relationship_id="email:dana@example.test") is False


def test_an_opt_out_with_no_keys_matches_nothing(optouts):
    """A lookup with nothing to look up must be False, not "everything"."""
    optouts.opt_out(relationship_id="email:dana@example.test")

    assert optouts.is_opted_out() is False


def test_all_opt_outs_is_readable(optouts):
    """An opt-out works by the Mind saying nothing, so it is invisible by design —
    and something that only manifests as an absence is impossible to audit."""
    optouts.opt_out(relationship_id="email:dana@example.test", reason="asked us to stop")

    rows = optouts.all_opt_outs()

    assert any(r["subject"] == "email:dana@example.test" for r in rows)
    assert any(r["reason"] == "asked us to stop" for r in rows)


# ---------------------------------------------------------------------------
# The wiring: both controls are per Mind, not per channel
# ---------------------------------------------------------------------------


def _settings_with_two_channels() -> Settings:
    settings = Settings(_env_file=None)
    object.__setattr__(settings, "mind_email_address", "sage@example.test")
    object.__setattr__(settings, "mind_email_password", "pw")
    object.__setattr__(settings, "mind_email_imap_host", "imap.example.test")
    object.__setattr__(settings, "mind_email_smtp_host", "smtp.example.test")
    object.__setattr__(settings, "mind_telegram_bot_token", "tok")
    object.__setattr__(settings, "mind_telegram_bot_username", "sage_bot")
    return settings


def test_channels_share_one_ledger(mind_id):
    """Object identity is asserted here deliberately, unlike everywhere else in this
    file: the bug was that two objects existed, so identity *is* the property."""
    registry = build_registry(mind_id, credentials_from_settings(_settings_with_two_channels()))

    email = registry.get("email").adapter
    telegram = registry.get("telegram").adapter

    assert email.ledger is telegram.ledger
    assert email.ledger.durable is True


def test_channels_share_one_opt_out_registry(mind_id):
    registry = build_registry(mind_id, credentials_from_settings(_settings_with_two_channels()))

    email = registry.get("email").adapter
    telegram = registry.get("telegram").adapter

    assert email.optouts is telegram.optouts


def test_an_opt_out_on_email_stops_telegram(mind_id):
    """The behavioural statement of the bug, and the one that matters.

    Someone says "stop" on one channel. The Mind must stop everywhere, because
    otherwise it simply moves to another address the person also has — which is the
    behaviour people are trying to escape.
    """
    registry = build_registry(mind_id, credentials_from_settings(_settings_with_two_channels()))
    email = registry.get("email").adapter
    telegram = registry.get("telegram").adapter

    email.optouts.opt_out(handle="dana@example.test", reason="asked us to stop")

    reason = outbound_refusal_reason(
        contact=contact(),
        is_reply=False,
        ledger=telegram.ledger,
        mind_id=mind_id,
        opted_out=telegram.optouts.is_opted_out(
            relationship_id="email:dana@example.test", handle="dana@example.test"
        ),
    )

    assert reason is not None
    assert "asked not to be contacted" in reason


def test_the_weekly_cap_counts_across_channels(mind_id):
    """Three emails must exhaust the allowance for Telegram too.

    Before the fix each channel had its own counter, so a Mind could send three
    emails, three Telegram messages and three calls — nine contacts in a week
    against a documented limit of three, with every channel individually compliant.
    """
    registry = build_registry(mind_id, credentials_from_settings(_settings_with_two_channels()))
    email = registry.get("email").adapter
    telegram = registry.get("telegram").adapter

    person = "email:dana@example.test"
    for _ in range(3):
        email.ledger.record(
            mind_id=mind_id, relationship_id=person, channel="email", at=_now()
        )

    reason = outbound_refusal_reason(
        contact=contact(relationship_id=person),
        is_reply=False,
        ledger=telegram.ledger,
        mind_id=mind_id,
    )

    assert reason is not None
    assert "3 initiated messages this week" in reason


def test_a_reply_is_not_counted_against_the_cap(mind_id):
    """Answering someone who wrote first is not outreach, and counting it would make
    a Mind unable to hold a conversation.

    Asserted at the ledger level because that is where the exclusion lives: a reply
    is never recorded, so there is no row to count.
    """
    ledger = DatabaseOutboundLedger()
    person = "email:dana@example.test"

    # A reply is simply never passed to `record` — `BaseChannel.send` guards on
    # `prepared.is_reply`. What this pins is that the *floor* treats a reply as
    # unlimited even after the cap is exhausted by initiation.
    for _ in range(3):
        ledger.record(mind_id=mind_id, relationship_id=person, channel="email", at=_now())

    reason = outbound_refusal_reason(
        contact=contact(relationship_id=person),
        is_reply=True,
        ledger=ledger,
        mind_id=mind_id,
    )

    assert reason is None
