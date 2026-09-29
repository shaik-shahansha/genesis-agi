"""Proactive outreach: a Mind reaches out because a fact says it should.

Two properties carry this module, and the second is the one that is easy to miss.

**A trigger must be a fact.** Every trigger is a commitment with a deadline, and the
`reason` it carries is what the approver reads. There is no path by which a model's
own inclination produces contact, because `OutreachTrigger` refuses to exist without a
`ref` and a `reason`.

**Proposing twice is worse than sending twice.** A commitment at risk for 24 hours is
noticed on every planning pass. A planner that only deduplicated *sends* would raise
96 approval requests in a day about the same obligation — every request individually
compliant, the aggregate a person being nagged, and an approver who learns to click
the card without reading. `OutreachAttempts` claims before the attempt, so one trigger
instance produces exactly one attempt whatever the outcome.

Every test below that involves a second pass asserts on the **number of attempts**, not
on whether an attempt happened. The weaker assertion passes just as happily when two
approval requests went out.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pytest

from genesis.channels import (
    ChannelRegistry,
    ContactRef,
    DatabaseContacts,
    FakeChannel,
    OutreachAttempts,
    OutreachPlanner,
    OutreachTrigger,
    OutboundPermission,
)
from genesis.channels.outreach import (
    OUTCOME_FAILED,
    OUTCOME_PROPOSED,
    OUTCOME_REFUSED,
    OUTCOME_SENT,
    OUTCOME_UNREACHABLE,
    TRIGGER_COMMITMENT_AT_RISK,
    TRIGGER_COMMITMENT_OVERDUE,
    CommitmentTriggers,
    ContactStoreBeneficiaries,
)
from genesis.database import base as db_base


def run(coro):
    return asyncio.run(coro)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Doubles
# ---------------------------------------------------------------------------


class StubCommitment:
    """A commitment as far as the trigger source is concerned."""

    def __init__(
        self,
        *,
        commitment_id: str,
        what: str = "send the weekly update",
        #: Matches the channel the harness registers, which is `FakeChannel`, whose
        #: name is "fake". A mismatch here resolves to nobody and every test reports
        #: `unreachable` — which is the planner working correctly on bad data.
        beneficiary_id: str = "fake:dana@example.test",
        beneficiary_label: str = "Dana",
        beneficiary_kind: str = "third_party",
        deadline: Optional[datetime] = None,
    ):
        self.commitment_id = commitment_id
        self.what = what
        self.beneficiary_id = beneficiary_id
        self.beneficiary_label = beneficiary_label
        self.beneficiary_kind = beneficiary_kind
        self.deadline = deadline

    @property
    def is_overdue(self) -> bool:
        return self.deadline is not None and _now() > self.deadline

    @property
    def is_at_risk(self) -> bool:
        if self.deadline is None:
            return False
        return timedelta(0) <= (self.deadline - _now()) <= timedelta(hours=24)


class StubManager:
    def __init__(self, items: list[StubCommitment]):
        self.items = items

    def list_commitments(self, *, open_only: bool = False):
        return list(self.items)


async def allow(_intent, _contact):
    return ("allow", None)


async def require_approval(_intent, _contact):
    return ("requires_approval", "apr-42")


async def refuse(_intent, _contact):
    return ("refused by policy: not permitted", None)


def make_channel(mind_id: str = "MIND-O", **kwargs) -> FakeChannel:
    """The channel under test.

    `mind_id` is a parameter rather than a constant because the outbound ledger is
    keyed on it: a channel recording under one id while the test queries another
    silently records nothing the test can see, which reads as "the trigger was not
    recorded" when it was.
    """
    return FakeChannel(
        address="sage@example.test",
        administrator="Genesis AGI",
        mind_id=mind_id,
        **kwargs,
    )


def make_planner(
    *,
    channel=None,
    commitments=None,
    authorizer=None,
    drafter=None,
    attempts=None,
    contacts=None,
    mind_id="MIND-O",
    with_consent=True,
):
    """Build a planner wired to a `FakeChannel`.

    `with_consent` records a contact with `INITIATE` and a `consent_source`, because
    without both the planner correctly refuses to initiate — which is a *pass* for the
    consent model and a *failure* for a test trying to exercise the send path. Being
    explicit about it keeps the two apart.
    """
    channel = channel or make_channel(mind_id=mind_id)
    registry = ChannelRegistry(mind_id)
    registry.register(channel)

    contacts = contacts or DatabaseContacts(mind_id=mind_id)
    if with_consent:
        contacts.remember(
            channel="fake",
            handle="dana@example.test",
            display_name="Dana",
            outbound=OutboundPermission.INITIATE,
            consent_source="asked us to follow up",
        )

    async def default_drafter(trigger, contact):
        return f"About {trigger.ref}: I said I would do this."

    planner = OutreachPlanner(
        mind_id=mind_id,
        registry=registry,
        contacts=contacts,
        authorizer=authorizer or allow,
        triggers=[CommitmentTriggers(StubManager(commitments or []))],
        drafter=drafter or default_drafter,
        attempts=attempts or OutreachAttempts(),
        # `FakeChannel.name` is "fake". The planner defaults to "email", which would
        # find no registered channel and report `unreachable` for every trigger.
        channel="fake",
    )
    return planner, channel


@pytest.fixture()
def mind_id() -> str:
    db_base.init_db()
    return f"MIND-OUT-{uuid.uuid4().hex[:8]}"


def at_risk_commitment(commitment_id: str = "cm-1") -> StubCommitment:
    return StubCommitment(commitment_id=commitment_id, deadline=_now() + timedelta(hours=6))


def overdue_commitment(commitment_id: str = "cm-over") -> StubCommitment:
    return StubCommitment(commitment_id=commitment_id, deadline=_now() - timedelta(hours=3))


# ---------------------------------------------------------------------------
# A trigger must be a fact
# ---------------------------------------------------------------------------


def test_a_trigger_without_a_ref_is_refused():
    """Without a ref it cannot be deduplicated, and an undeduplicable trigger on a
    loop fires on every pass."""
    with pytest.raises(ValueError, match="ref"):
        OutreachTrigger(
            kind=TRIGGER_COMMITMENT_AT_RISK,
            ref="",
            reason="something",
            beneficiary_id="x",
            beneficiary_label="X",
        )


def test_a_trigger_without_a_reason_is_refused():
    """The reason is what the approver reads and what the receipt records. A
    trigger without one produces contact nobody can account for."""
    with pytest.raises(ValueError, match="reason"):
        OutreachTrigger(
            kind=TRIGGER_COMMITMENT_AT_RISK,
            ref="cm-1",
            reason="   ",
            beneficiary_id="x",
            beneficiary_label="X",
        )


def test_an_open_commitment_with_no_deadline_produces_nothing():
    """"At risk" is meaningless without a date, and treating undated obligations as
    urgent would mean contacting people about things no time was agreed for."""
    source = CommitmentTriggers(StubManager([StubCommitment(commitment_id="cm-1")]))

    assert source() == []


def test_a_commitment_far_from_its_deadline_produces_nothing():
    """Merely *open* is deliberately not a trigger: a Mind with forty open
    commitments would produce forty contacts."""
    far = StubCommitment(
        commitment_id="cm-1", deadline=_now() + timedelta(days=10)
    )
    source = CommitmentTriggers(StubManager([far]))

    assert source() == []


def test_an_at_risk_commitment_produces_a_trigger():
    source = CommitmentTriggers(StubManager([at_risk_commitment()]))

    triggers = source()

    assert len(triggers) == 1
    assert triggers[0].kind == TRIGGER_COMMITMENT_AT_RISK
    assert triggers[0].ref == "cm-1"
    assert "due" in triggers[0].reason


def test_an_overdue_commitment_produces_a_trigger_with_the_higher_urgency():
    source = CommitmentTriggers(StubManager([overdue_commitment()]))

    triggers = source()

    assert triggers[0].kind == TRIGGER_COMMITMENT_OVERDUE
    assert "past its deadline" in triggers[0].reason

    at_risk = CommitmentTriggers(StubManager([at_risk_commitment()]))()
    assert triggers[0].urgency > at_risk[0].urgency


def test_overdue_outranks_at_risk():
    """The most pressing obligation is considered first, so if a cap bites it falls
    on the least urgent one."""
    source = CommitmentTriggers(
        StubManager([at_risk_commitment("cm-a"), overdue_commitment("cm-b")])
    )

    triggers = source()

    assert [t.ref for t in triggers] == ["cm-b", "cm-a"]


def test_the_reason_names_what_is_owed():
    """The reason is read by a human deciding whether to approve, so it has to say
    what the obligation actually is."""
    source = CommitmentTriggers(
        StubManager([at_risk_commitment()])
    )

    triggers = source()

    assert "send the weekly update" in triggers[0].reason
    assert "Dana" in triggers[0].reason


def test_the_trigger_list_is_bounded():
    """A backlog should not become a burst of proposals even though the floors would
    cap what gets through; the report has to stay readable."""
    many = [at_risk_commitment(f"cm-{i}") for i in range(50)]
    source = CommitmentTriggers(StubManager(many), max_triggers=5)

    assert len(source()) == 5


def test_a_broken_manager_produces_no_triggers_rather_than_raising():
    class Broken:
        def list_commitments(self, *, open_only=False):
            raise RuntimeError("life state unavailable")

    assert CommitmentTriggers(Broken())() == []


# ---------------------------------------------------------------------------
# The idempotence property
# ---------------------------------------------------------------------------


def test_a_second_pass_does_not_propose_again(mind_id):
    """The property this module exists for.

    Asserting on the attempt count, not on whether an attempt happened: the weaker
    assertion passes just as happily when two approval requests went out.
    """
    planner, _ = make_planner(
        commitments=[at_risk_commitment()],
        authorizer=require_approval,
        mind_id=mind_id,
    )

    first = run(planner.consider())
    second = run(planner.consider())

    assert first.proposed == 1
    assert second.considered == 1
    assert second.proposed == 0
    assert second.already_attempted == 1


def test_a_second_pass_does_not_send_again(mind_id):
    planner, channel = make_planner(
        commitments=[at_risk_commitment()], mind_id=mind_id
    )

    run(planner.consider())
    run(planner.consider())

    assert len(channel.sent) == 1


def test_a_new_commitment_is_not_sent_inside_the_minimum_gap(mind_id):
    """A second obligation does not authorise a second message an hour later.

    Keyed on the trigger *and* its ref, so a different obligation is not suppressed
    by an earlier one — but it is still subject to the minimum gap, which is what
    stops two commitments becoming two messages in the same afternoon. The distinct
    ref is what makes it a *new attempt*; the floor is what decides whether anything
    is sent.
    """
    manager = StubManager([at_risk_commitment("cm-1")])
    attempts = OutreachAttempts()
    registry = ChannelRegistry(mind_id)
    channel = make_channel(mind_id=mind_id)
    registry.register(channel)

    contacts = DatabaseContacts(mind_id=mind_id)
    contacts.remember(
        channel="fake",
        handle="dana@example.test",
        display_name="Dana",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )

    async def drafter(trigger, contact):
        return f"About {trigger.ref}."

    def build():
        return OutreachPlanner(
            mind_id=mind_id,
            registry=registry,
            contacts=contacts,
            authorizer=allow,
            triggers=[CommitmentTriggers(manager)],
            drafter=drafter,
            attempts=attempts,
            channel="fake",
        )

    first = run(build().consider())
    manager.items = [at_risk_commitment("cm-2")]
    second = run(build().consider())

    assert first.sent == 1
    # A new attempt was made — that is the idempotence key working.
    assert second.already_attempted == 0
    assert second.considered == 1
    # And the minimum gap stopped it, which is the floor working.
    assert second.refused == 1
    assert "wait" in second.outcomes[0].reason
    assert len(channel.sent) == 1


def test_an_attempt_is_recorded_before_the_send(mind_id):
    """Claim-before-attempt, so a process that dies mid-flight leaves a record and
    the next pass does not repeat it."""
    seen: list[bool] = []

    class SpyAttempts(OutreachAttempts):
        def claim(self, **kwargs):
            claimed = super().claim(**kwargs)
            seen.append(claimed)
            return claimed

    planner, _ = make_planner(
        commitments=[at_risk_commitment()], attempts=SpyAttempts(), mind_id=mind_id
    )
    run(planner.consider())

    assert seen == [True]


def test_a_refused_attempt_is_not_retried(mind_id):
    """Policy will not change between passes, so retrying is noise."""
    planner, _ = make_planner(
        commitments=[at_risk_commitment()],
        authorizer=refuse,
        mind_id=mind_id,
    )

    first = run(planner.consider())
    second = run(planner.consider())

    assert first.refused == 1
    assert second.already_attempted == 1


def test_an_unreachable_beneficiary_is_recorded_and_not_retried(mind_id):
    """A Mind that owes someone something and cannot reach them is a fact an
    operator needs, not something to silently skip."""
    planner, _ = make_planner(
        commitments=[
            StubCommitment(
                commitment_id="cm-1",
                beneficiary_id="nobody@example.test",
                beneficiary_label="Nobody",
                deadline=_now() + timedelta(hours=6),
            )
        ],
        with_consent=False,
        mind_id=mind_id,
    )

    first = run(planner.consider())
    second = run(planner.consider())

    assert first.unreachable == 1
    assert "no way to reach" in first.outcomes[0].reason
    assert second.already_attempted == 1


def test_a_claim_that_cannot_be_written_means_nothing_is_attempted(mind_id):
    """If the attempt cannot be recorded it must not be made, because proceeding
    would repeat on every pass."""

    class BrokenAttempts(OutreachAttempts):
        def claim(self, **kwargs):
            raise RuntimeError("database down")

    planner, channel = make_planner(
        commitments=[at_risk_commitment()], attempts=BrokenAttempts(), mind_id=mind_id
    )

    report = run(planner.consider())

    assert report.failed == 1
    assert len(channel.sent) == 0


def test_pending_lists_an_unresolved_attempt(mind_id):
    """Reported rather than retried: a retry may contact someone already contacted."""
    attempts = OutreachAttempts()
    attempts.claim(
        mind_id=mind_id, trigger=TRIGGER_COMMITMENT_AT_RISK, trigger_ref="cm-orphan"
    )

    pending = attempts.pending(mind_id=mind_id)

    assert [p["trigger_ref"] for p in pending] == ["cm-orphan"]


def test_completing_an_attempt_resolves_it(mind_id):
    attempts = OutreachAttempts()
    attempts.claim(
        mind_id=mind_id, trigger=TRIGGER_COMMITMENT_AT_RISK, trigger_ref="cm-1"
    )

    attempts.complete(
        mind_id=mind_id,
        trigger=TRIGGER_COMMITMENT_AT_RISK,
        trigger_ref="cm-1",
        outcome=OUTCOME_SENT,
        reason="sent",
    )

    assert attempts.pending(mind_id=mind_id) == []


def test_attempts_are_scoped_to_one_mind(mind_id):
    """Two Minds noticing the same commitment id must each get their own attempt."""
    first = OutreachAttempts()
    second = OutreachAttempts()

    assert first.claim(
        mind_id=mind_id, trigger=TRIGGER_COMMITMENT_AT_RISK, trigger_ref="cm-1"
    )
    assert second.claim(
        mind_id=f"{mind_id}-other",
        trigger=TRIGGER_COMMITMENT_AT_RISK,
        trigger_ref="cm-1",
    )


def test_an_attempt_without_a_ref_is_refused(mind_id):
    """An unidentifiable trigger cannot be deduplicated, so claiming it would book
    an empty key and suppress every future attempt."""
    attempts = OutreachAttempts()

    assert attempts.claim(
        mind_id=mind_id, trigger=TRIGGER_COMMITMENT_AT_RISK, trigger_ref=""
    ) is False


def test_recent_lists_attempts(mind_id):
    planner, _ = make_planner(
        commitments=[at_risk_commitment()], mind_id=mind_id
    )
    run(planner.consider())

    rows = OutreachAttempts().recent(mind_id=mind_id)

    assert len(rows) == 1
    assert rows[0]["outcome"] == OUTCOME_SENT


# ---------------------------------------------------------------------------
# The floors and the gate still apply
# ---------------------------------------------------------------------------


def test_proactive_outreach_is_treated_as_outreach_not_a_reply(mind_id):
    """`is_reply` stays False, which is what makes the weekly cap, the minimum gap
    and R3 all apply. Sending it as a reply would bypass every one of them."""
    captured: dict[str, Any] = {}

    async def spy(intent, contact):
        captured["intent"] = intent
        return ("allow", None)

    planner, _ = make_planner(
        commitments=[at_risk_commitment()], authorizer=spy, mind_id=mind_id
    )
    run(planner.consider())

    assert captured["intent"].is_reply is False
    assert captured["intent"].trigger == TRIGGER_COMMITMENT_AT_RISK
    assert captured["intent"].trigger_ref == "cm-1"


def test_a_contact_who_is_not_open_to_contact_is_not_approached(mind_id):
    """A commitment does not override someone's stated preference. Refused, and
    recorded so it is not re-proposed."""
    contacts = DatabaseContacts(mind_id=mind_id)
    contacts.remember(
        channel="fake",
        handle="dana@example.test",
        display_name="Dana",
        outbound=OutboundPermission.NONE,
    )

    planner, channel = make_planner(
        commitments=[at_risk_commitment()],
        contacts=contacts,
        with_consent=False,
        mind_id=mind_id,
    )
    report = run(planner.consider())

    assert report.refused == 1
    assert "not open to contact" in report.outcomes[0].reason
    assert len(channel.sent) == 0


def test_a_floor_refusal_is_recorded_and_not_retried(mind_id):
    """The contact has a weekly cap of zero, so the adapter refuses. Recorded as
    refused rather than left to be retried on every pass."""
    contacts = DatabaseContacts(mind_id=mind_id)
    contacts.remember(
        channel="fake",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )
    # Exhaust the allowance by hand.
    with db_base.get_session() as session:
        from genesis.database.models import ContactChannelRecord, ContactRecord

        row = (
            session.query(ContactChannelRecord)
            .join(ContactRecord, ContactChannelRecord.contact_id == ContactRecord.id)
            .filter(
                ContactRecord.mind_id == mind_id,
                ContactChannelRecord.channel == "fake",
                ContactChannelRecord.address == "dana@example.test",
            )
            .one()
        )
        row.contact.max_outbound_per_week = 0

    planner, channel = make_planner(
        commitments=[at_risk_commitment()],
        contacts=contacts,
        with_consent=False,
        mind_id=mind_id,
    )
    report = run(planner.consider())

    assert report.refused == 1
    assert len(channel.sent) == 0


def test_a_policy_refusal_is_recorded_as_refused_not_proposed(mind_id):
    """The distinction the operator needs: "waiting for you" versus "policy said no"."""
    planner, _ = make_planner(
        commitments=[at_risk_commitment()], authorizer=refuse, mind_id=mind_id
    )

    report = run(planner.consider())

    assert report.refused == 1
    assert report.proposed == 0
    assert report.outcomes[0].approval_id is None


def test_an_approval_is_recorded_as_proposed_with_the_id(mind_id):
    planner, _ = make_planner(
        commitments=[at_risk_commitment()],
        authorizer=require_approval,
        mind_id=mind_id,
    )

    report = run(planner.consider())

    assert report.proposed == 1
    assert report.outcomes[0].approval_id == "apr-42"


def test_a_governance_failure_means_no_message(mind_id):
    async def exploding(_intent, _contact):
        raise RuntimeError("policy engine unavailable")

    planner, channel = make_planner(
        commitments=[at_risk_commitment()], authorizer=exploding, mind_id=mind_id
    )

    report = run(planner.consider())

    assert report.failed == 1
    assert len(channel.sent) == 0


def test_a_drafter_that_declines_means_no_message(mind_id):
    """A commitment may already have been fulfilled in conversation, and a Mind that
    always produces text would always send."""

    async def silent(trigger, contact):
        return None

    planner, channel = make_planner(
        commitments=[at_risk_commitment()], drafter=silent, mind_id=mind_id
    )

    report = run(planner.consider())

    assert report.refused == 1
    assert len(channel.sent) == 0


def test_a_drafter_that_raises_does_not_send(mind_id):
    async def exploding(trigger, contact):
        raise RuntimeError("model unavailable")

    planner, channel = make_planner(
        commitments=[at_risk_commitment()], drafter=exploding, mind_id=mind_id
    )

    report = run(planner.consider())

    assert report.refused == 1
    assert len(channel.sent) == 0


def test_a_send_failure_is_recorded_and_not_retried(mind_id):
    channel = make_channel()
    channel.fail_next_with = RuntimeError("provider down")

    planner, _ = make_planner(
        commitments=[at_risk_commitment()], channel=channel, mind_id=mind_id
    )

    first = run(planner.consider())
    second = run(planner.consider())

    assert first.failed == 1
    assert second.already_attempted == 1


def test_no_channel_means_unreachable_not_a_crash(mind_id):
    registry = ChannelRegistry(mind_id)  # nothing registered

    async def drafter(trigger, contact):
        return "hello"
    planner = OutreachPlanner(
        mind_id=mind_id,
        registry=registry,
        contacts=DatabaseContacts(mind_id=mind_id),
        authorizer=allow,
        triggers=[CommitmentTriggers(StubManager([at_risk_commitment()]))],
        drafter=drafter,
        attempts=OutreachAttempts(),
        channel="fake",
    )

    report = run(planner.consider())

    assert report.unreachable == 1
    assert "no fake channel is configured" in report.outcomes[0].reason


def test_one_broken_trigger_source_does_not_stop_the_others(mind_id):
    def exploding():
        raise RuntimeError("life state unavailable")

    registry = ChannelRegistry(mind_id)
    registry.register(make_channel(mind_id=mind_id))

    contacts = DatabaseContacts(mind_id=mind_id)
    contacts.remember(
        channel="fake",
        handle="dana@example.test",
        display_name="Dana",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )

    async def drafter(trigger, contact):
        return "hello"

    planner = OutreachPlanner(
        mind_id=mind_id,
        registry=registry,
        contacts=contacts,
        authorizer=allow,
        triggers=[
            exploding,
            CommitmentTriggers(StubManager([at_risk_commitment()])),
        ],
        drafter=drafter,
        attempts=OutreachAttempts(),
        channel="fake",
    )

    report = run(planner.consider())

    assert report.considered == 1
    assert report.sent == 1


# ---------------------------------------------------------------------------
# The trigger travels with the message
# ---------------------------------------------------------------------------


def test_the_sent_message_records_its_trigger_in_the_ledger(mind_id):
    """"Why did this being contact me?" must be answerable from the record."""
    from genesis.channels import DatabaseOutboundLedger

    ledger = DatabaseOutboundLedger()
    channel = make_channel(mind_id=mind_id, ledger=ledger)

    planner, _ = make_planner(
        commitments=[at_risk_commitment()], channel=channel, mind_id=mind_id
    )
    run(planner.consider())

    assert ledger.already_reached_out(
        mind_id=mind_id, trigger=TRIGGER_COMMITMENT_AT_RISK, trigger_ref="cm-1"
    )


def test_the_ledger_counts_a_sent_outreach_against_the_cap(mind_id):
    from genesis.channels import DatabaseOutboundLedger

    ledger = DatabaseOutboundLedger()
    channel = make_channel(mind_id=mind_id, ledger=ledger)

    planner, _ = make_planner(
        commitments=[at_risk_commitment()], channel=channel, mind_id=mind_id
    )
    run(planner.consider())

    count = ledger.count_since(
        mind_id=mind_id,
        relationship_id="fake:dana@example.test",
        since=_now() - timedelta(days=7),
    )
    assert count == 1


def test_a_reply_is_not_recorded_as_an_outreach_attempt(mind_id):
    """The two ledgers answer different questions and must not be conflated: the
    outbound ledger counts what was sent, the attempts table deduplicates triggers."""
    from genesis.channels import DatabaseOutboundLedger

    ledger = DatabaseOutboundLedger()
    attempts = OutreachAttempts()

    assert ledger.already_reached_out(
        mind_id=mind_id, trigger=TRIGGER_COMMITMENT_AT_RISK, trigger_ref="cm-1"
    ) is False
    assert attempts.pending(mind_id=mind_id) == []


# ---------------------------------------------------------------------------
# Resolving the beneficiary
# ---------------------------------------------------------------------------


def test_a_beneficiary_is_resolved_by_relationship_id(mind_id):
    contacts = DatabaseContacts(mind_id=mind_id)
    rid = contacts.remember(
        channel="fake",
        handle="dana@example.test",
        display_name="Dana",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )

    resolver = ContactStoreBeneficiaries(contacts=contacts, channel="fake")
    trigger = OutreachTrigger(
        kind=TRIGGER_COMMITMENT_AT_RISK,
        ref="cm-1",
        reason="test",
        beneficiary_id=rid,
        beneficiary_label="Dana",
    )

    found = resolver.resolve(trigger)

    assert found is not None
    assert found.relationship_id == rid


def test_a_beneficiary_is_resolved_by_handle(mind_id):
    contacts = DatabaseContacts(mind_id=mind_id)
    contacts.remember(
        channel="fake",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )

    resolver = ContactStoreBeneficiaries(contacts=contacts, channel="fake")
    trigger = OutreachTrigger(
        kind=TRIGGER_COMMITMENT_AT_RISK,
        ref="cm-1",
        reason="test",
        beneficiary_id="dana@example.test",
        beneficiary_label="Dana",
    )

    assert resolver.resolve(trigger) is not None


def test_an_unknown_beneficiary_does_not_resolve_to_a_stranger(mind_id):
    """The store returns a reply-only stranger for an unknown handle, which must not
    be mistaken for "we know this person" — otherwise a commitment would authorise
    contact with someone the Mind has no relationship with."""
    contacts = DatabaseContacts(mind_id=mind_id)
    resolver = ContactStoreBeneficiaries(contacts=contacts, channel="fake")
    trigger = OutreachTrigger(
        kind=TRIGGER_COMMITMENT_AT_RISK,
        ref="cm-1",
        reason="test",
        beneficiary_id="stranger@example.test",
        beneficiary_label="Stranger",
    )

    assert resolver.resolve(trigger) is None
