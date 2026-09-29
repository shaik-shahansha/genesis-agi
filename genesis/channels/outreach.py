"""Proactive outreach: the Mind reaches out because a *fact* says it should.

This is the half of the channel layer that did not exist. Everything else could
answer; nothing could start. `may_initiate()` was only ever checked, never reached,
because nothing produced an initiating intent.

## The rule this module is built around

Proactive behaviour must be **triggered**, and every trigger is a fact the system
already holds. `DIGITAL_PRESENCE.md` §8 states it as: random model initiative is out
of scope, because it produces unpredictable contact and "the being felt like it" is
not an accountable trigger.

So a trigger here is never a vibe. It is a commitment with a deadline, and the
`reason` attached to every message is the obligation itself — which is what makes the
message reviewable by the human who has to approve it.

## Two idempotence problems, not one

The obvious one is sending twice. The less obvious one is **proposing** twice, and it
is worse. A commitment at risk for 24 hours is noticed on every poll, so a planner
that only deduplicated sends would raise 96 approval requests in a day about the same
obligation. Every request individually compliant, the aggregate a person being
nagged — and an approver who sees the same card 96 times learns to click it without
reading, which destroys the control the card exists to provide.

`OutreachAttemptRecord` is written **before** the attempt, so one trigger instance
produces exactly one attempt whether it was proposed, sent, refused or failed.

## Proactive outreach always needs a human, and that is not a limitation

`comms.email.send` is R3, and `STANDING_GRANT_MAX_RISK` is R2, so **no standing grant
can ever cover it**. A Mind cannot start a conversation without a human deciding.
That is the correct governance position — starting a conversation is externally
visible and hard to retract — and it means this module's output is normally an
*approval request* rather than a sent message.

Making it autonomous is a governance change to `comms.email.send`, and it should be
made deliberately rather than discovered. It is not a configuration flag here.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Protocol

from .base import CommunicationIntent, ContactRef, OutboundPermission
from .gateway import ChannelGateway

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


#: Trigger kinds. Strings rather than an Enum so a new trigger source is additive and
#: a reader never fails on an unknown value — the same reasoning as `EventType`.
TRIGGER_COMMITMENT_AT_RISK = "commitment_at_risk"
TRIGGER_COMMITMENT_OVERDUE = "commitment_overdue"

#: Outcomes recorded for one attempt.
OUTCOME_PROPOSED = "proposed"
OUTCOME_SENT = "sent"
OUTCOME_REFUSED = "refused"
OUTCOME_FAILED = "failed"
OUTCOME_UNREACHABLE = "unreachable"


@dataclass(frozen=True)
class OutreachTrigger:
    """A fact that says this Mind should contact this person.

    `reason` is not decoration. It is what a human reads on the approval card, and it
    is recorded on the receipt — so "why did this being write to me?" is answerable
    from the record rather than reconstructed from the timing.

    `ref` is required, and `OutreachPlanner` refuses a trigger without one. An
    unidentifiable trigger cannot be deduplicated, and an undeduplicable trigger on a
    loop is the nagging failure described above.
    """

    kind: str
    ref: str
    reason: str
    beneficiary_id: str
    beneficiary_label: str
    beneficiary_kind: str = "third_party"
    #: Higher sorts first. Set from the commitment's own state rather than chosen by
    #: the caller, so an overdue obligation outranks one merely approaching.
    urgency: int = 0

    def __post_init__(self) -> None:
        if not (self.ref or "").strip():
            raise ValueError(
                "an outreach trigger needs a ref: without one it cannot be "
                "deduplicated, and a trigger that cannot be deduplicated will fire "
                "on every poll"
            )
        if not (self.reason or "").strip():
            raise ValueError(
                "an outreach trigger needs a reason: it is what the approver reads "
                "and what the receipt records"
            )


class BeneficiaryResolver(Protocol):
    """Finds a way to reach the person a commitment is owed to.

    Separate from `ContactResolver` because the question is different. That one asks
    "who sent this message"; this asks "can I reach the person I owe something to",
    starting from a commitment rather than an address.
    """

    def resolve(self, trigger: OutreachTrigger) -> Optional[ContactRef]: ...


@dataclass
class ContactStoreBeneficiaries:
    """Resolves a beneficiary through the durable contact store.

    `beneficiary_id` is looked up as a relationship id first, then as a handle. Both
    because the two are not distinguishable from the commitment alone: a Mind that
    recorded a commitment to "dana@example.test" meant an address, and one recorded to
    "email:dana@example.test" meant a contact record.

    Returns `None` when there is no way to reach them. That is a real outcome and is
    reported as `unreachable` rather than silently skipped — a Mind that owes someone
    something and cannot reach them is a fact an operator needs to know.
    """

    contacts: Any  # DatabaseContacts
    #: Channel to use. One channel for now: choosing between them well needs a
    #: preference model that does not exist, and guessing would produce contact on
    #: whichever channel happened to be first in a dict.
    channel: str = "email"

    def resolve(self, trigger: OutreachTrigger) -> Optional[ContactRef]:
        for attempt in (trigger.beneficiary_id, trigger.beneficiary_label):
            if not attempt:
                continue
            found = self._try(attempt)
            if found is not None:
                return found
        return None

    def _try(self, value: str) -> Optional[ContactRef]:
        # As a handle on the configured channel.
        try:
            by_handle = self.contacts.resolve(channel=self.channel, handle=value)
        except Exception as exc:  # noqa: BLE001
            logger.warning("outreach: contact lookup failed for %r: %s", value, exc)
            raise
        if by_handle is not None and not by_handle.relationship_id.startswith("unknown:"):
            return by_handle

        # As a relationship id. The store resolves by channel+handle, so this walks
        # the known handles and matches on the relationship instead.
        try:
            for handle in self.contacts.known_handles(channel=self.channel):
                candidate = self.contacts.resolve(channel=self.channel, handle=handle)
                if candidate is not None and candidate.relationship_id == value:
                    return candidate
        except Exception as exc:  # noqa: BLE001
            logger.warning("outreach: relationship lookup failed for %r: %s", value, exc)
            raise
        return None


@dataclass
class OutreachOutcome:
    """What the planner did about one trigger."""

    trigger: OutreachTrigger
    attempted: bool
    outcome: str
    reason: str
    channel: str = ""
    decision: Optional[str] = None
    approval_id: Optional[str] = None
    receipt: Any = None

    @property
    def sent(self) -> bool:
        return self.outcome == OUTCOME_SENT

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "trigger": self.trigger.kind,
            "trigger_ref": self.trigger.ref,
            "beneficiary": self.trigger.beneficiary_label or self.trigger.beneficiary_id,
            "attempted": self.attempted,
            "outcome": self.outcome,
            "reason": self.reason,
            "channel": self.channel,
            "decision": self.decision,
            "approval_id": self.approval_id,
        }


@dataclass
class OutreachReport:
    """One planning pass."""

    considered: int = 0
    proposed: int = 0
    sent: int = 0
    refused: int = 0
    failed: int = 0
    unreachable: int = 0
    already_attempted: int = 0
    outcomes: list[OutreachOutcome] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "considered": self.considered,
            "proposed": self.proposed,
            "sent": self.sent,
            "refused": self.refused,
            "failed": self.failed,
            "unreachable": self.unreachable,
            "already_attempted": self.already_attempted,
        }


#: Produces the triggers for a Mind. Injected so a new trigger source is a new
#: callable rather than a change to the planner.
TriggerSource = Callable[[], list[OutreachTrigger]]


class CommitmentTriggers:
    """Turns open commitments into outreach triggers.

    Only two facts qualify, and both are already recorded:

    * **overdue** — past its deadline and not yet decided about. The honour path is to
      fulfil, renegotiate, or mark it missed, and telling the beneficiary is part of
      renegotiating honestly.
    * **at risk** — due within 24 hours.

    A commitment with no deadline produces nothing. "At risk" is meaningless without a
    date, and treating undated obligations as urgent would mean a Mind that contacts
    people about things it never agreed a time for.

    Deliberately not a trigger: a commitment that is merely *open*. A Mind with forty
    open commitments would produce forty contacts, which is the "message them as
    needed" failure in a different costume.
    """

    def __init__(self, manager: Any, *, max_triggers: int = 10):
        self.manager = manager
        #: Bounded, because a backlog should not become a burst of contact even
        #: though the floors would cap what actually gets through. The cap is on
        #: *considering* them, so the report stays readable.
        self.max_triggers = max(1, max_triggers)

    def __call__(self) -> list[OutreachTrigger]:
        triggers: list[OutreachTrigger] = []
        try:
            items = self.manager.list_commitments(open_only=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("outreach: could not list commitments: %s", exc)
            return []

        for commitment in items:
            trigger = self._for(commitment)
            if trigger is not None:
                triggers.append(trigger)

        # Overdue before at-risk, then soonest deadline first. Sorted here rather
        # than left to the manager so the ordering is a property of the planner, and
        # the most pressing obligation is considered first if the cap bites.
        triggers.sort(key=lambda t: (-t.urgency, t.ref))
        return triggers[: self.max_triggers]

    @staticmethod
    def _for(commitment: Any) -> Optional[OutreachTrigger]:
        try:
            overdue = bool(commitment.is_overdue)
            at_risk = bool(commitment.is_at_risk)
        except Exception:  # noqa: BLE001
            return None
        if not (overdue or at_risk):
            return None

        what = str(getattr(commitment, "what", "") or "").strip()
        label = str(getattr(commitment, "beneficiary_label", "") or "")
        kind = str(getattr(commitment, "beneficiary_kind", "") or "third_party")

        if overdue:
            reason = (
                f"a commitment to {label or 'this person'} is past its deadline: {what}"
            )
            return OutreachTrigger(
                kind=TRIGGER_COMMITMENT_OVERDUE,
                ref=str(commitment.commitment_id),
                reason=reason,
                beneficiary_id=str(getattr(commitment, "beneficiary_id", "") or ""),
                beneficiary_label=label,
                beneficiary_kind=kind,
                urgency=2,
            )

        deadline = getattr(commitment, "deadline", None)
        when = deadline.isoformat() if deadline is not None else "soon"
        reason = (
            f"a commitment to {label or 'this person'} is due {when}: {what}"
        )
        return OutreachTrigger(
            kind=TRIGGER_COMMITMENT_AT_RISK,
            ref=str(commitment.commitment_id),
            reason=reason,
            beneficiary_id=str(getattr(commitment, "beneficiary_id", "") or ""),
            beneficiary_label=label,
            beneficiary_kind=kind,
            urgency=1,
        )


class OutreachPlanner:
    """Considers triggers and, for each new one, proposes or sends a message.

    Owns no policy. The gate decides, exactly as it does for a reply, and the adapter
    floors decide again. The only judgement this class makes on its own is to *stop* —
    which it does whenever it cannot record the attempt, because an unrecorded attempt
    will be repeated.
    """

    def __init__(
        self,
        *,
        mind_id: str,
        registry: Any,
        contacts: Any,
        authorizer: Any,
        triggers: list[TriggerSource],
        drafter: Any,
        ledger: Any = None,
        attempts: Any = None,
        beneficiaries: Optional[BeneficiaryResolver] = None,
        recorder: Optional[Any] = None,
        channel: str = "email",
    ):
        self.mind_id = mind_id
        self.registry = registry
        self.authorizer = authorizer
        self.triggers = list(triggers)
        self.drafter = drafter
        self.ledger = ledger
        self.attempts = attempts
        self.recorder = recorder
        self.channel = channel
        self.beneficiaries = beneficiaries or ContactStoreBeneficiaries(
            contacts=contacts, channel=channel
        )

    def _record(self, payload: dict[str, Any]) -> None:
        if self.recorder is None:
            return
        try:
            self.recorder(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("outreach: recording failed: %s", exc)

    async def consider(self) -> OutreachReport:
        """One planning pass over every trigger source."""
        report = OutreachReport()

        collected: list[OutreachTrigger] = []
        for source in self.triggers:
            try:
                collected.extend(source() or [])
            except Exception as exc:  # noqa: BLE001
                # One broken source must not stop the others, the same reasoning as
                # `ChannelRegistry.receive_all`.
                logger.error("outreach: a trigger source failed: %s", exc)

        # Highest urgency first across all sources, so the cap on work per pass falls
        # on the least pressing obligation rather than on whichever source ran last.
        collected.sort(key=lambda t: (-t.urgency, t.kind, t.ref))
        report.considered = len(collected)

        for trigger in collected:
            outcome = await self._handle(trigger)
            report.outcomes.append(outcome)
            if outcome.outcome == OUTCOME_PROPOSED:
                report.proposed += 1
            elif outcome.outcome == OUTCOME_SENT:
                report.sent += 1
            elif outcome.outcome == OUTCOME_REFUSED:
                report.refused += 1
            elif outcome.outcome == OUTCOME_UNREACHABLE:
                report.unreachable += 1
            elif outcome.outcome == OUTCOME_FAILED:
                report.failed += 1
            if not outcome.attempted:
                report.already_attempted += 1

        return report

    async def _handle(self, trigger: OutreachTrigger) -> OutreachOutcome:
        # Step 1: claim the attempt. Before anything else, because an unrecorded
        # attempt is repeated on the next pass and the repetition is the harm.
        claimed, refusal = self._claim(trigger)
        if not claimed:
            return OutreachOutcome(
                trigger=trigger,
                attempted=False,
                outcome=refusal[0],
                reason=refusal[1],
            )

        registration = self.registry.get(self.channel)
        if registration is None or not registration.enabled:
            reason = (
                registration.reason
                if registration is not None
                else f"no {self.channel} channel is configured"
            )
            self._complete(trigger, OUTCOME_UNREACHABLE, reason)
            return OutreachOutcome(
                trigger=trigger, attempted=True, outcome=OUTCOME_UNREACHABLE, reason=reason
            )

        contact = self.beneficiaries.resolve(trigger)
        if contact is None:
            reason = (
                f"no way to reach {trigger.beneficiary_label or trigger.beneficiary_id} "
                f"on {self.channel}; the commitment stands but cannot be raised with them"
            )
            self._complete(trigger, OUTCOME_UNREACHABLE, reason)
            return OutreachOutcome(
                trigger=trigger,
                attempted=True,
                outcome=OUTCOME_UNREACHABLE,
                reason=reason,
                channel=self.channel,
            )

        if contact.outbound is OutboundPermission.NONE:
            # Not a failure: the person has said they are not open to contact, and a
            # commitment does not override that. Recorded so it is not re-proposed.
            reason = (
                f"{contact.display_name} is not open to contact, so a commitment "
                f"owed to them cannot be raised with them"
            )
            self._complete(trigger, OUTCOME_REFUSED, reason)
            return OutreachOutcome(
                trigger=trigger,
                attempted=True,
                outcome=OUTCOME_REFUSED,
                reason=reason,
                channel=self.channel,
            )

        body = await self._draft(trigger, contact)
        if not body:
            reason = "the Mind chose not to send anything about this commitment"
            self._complete(trigger, OUTCOME_REFUSED, reason)
            return OutreachOutcome(
                trigger=trigger,
                attempted=True,
                outcome=OUTCOME_REFUSED,
                reason=reason,
                channel=self.channel,
            )

        intent = CommunicationIntent(
            channel=self.channel,
            recipient=contact,
            body=body,
            subject=self._subject(trigger),
            # `is_reply` stays False. This is outreach, so the floors treat it as
            # capped, the minimum gap applies, and it is R3 rather than R2 — which is
            # the whole reason it cannot be granted standing approval.
            trigger=trigger.kind,
            trigger_ref=trigger.ref,
        )

        prepared = await registration.adapter.prepare(intent)
        if prepared.requires_approval_because:
            reason = "; ".join(prepared.requires_approval_because)
            self._complete(trigger, OUTCOME_REFUSED, reason)
            self._record(
                {
                    "event": "channel.outreach_refused",
                    "mind_id": self.mind_id,
                    "trigger": trigger.kind,
                    "trigger_ref": trigger.ref,
                    "reason": reason,
                }
            )
            return OutreachOutcome(
                trigger=trigger,
                attempted=True,
                outcome=OUTCOME_REFUSED,
                reason=reason,
                channel=self.channel,
            )

        return await self._authorize_and_send(trigger, intent, registration)

    # -- the gate ----------------------------------------------------------

    async def _authorize_and_send(
        self, trigger: OutreachTrigger, intent: CommunicationIntent, registration: Any
    ) -> OutreachOutcome:
        try:
            decision, approval_id = await self.authorizer(intent, intent.recipient)
        except Exception as exc:  # noqa: BLE001
            reason = f"governance unavailable: {exc}"
            self._complete(trigger, OUTCOME_FAILED, reason)
            return OutreachOutcome(
                trigger=trigger,
                attempted=True,
                outcome=OUTCOME_FAILED,
                reason=reason,
                channel=self.channel,
            )

        if decision not in ("allow", "allow_with_receipt"):
            # The expected outcome for an R3 action, and not a fault. Recorded as
            # `proposed` when an approval was actually raised, so the operator can see
            # the difference between "waiting for you" and "policy refused".
            outcome = OUTCOME_PROPOSED if approval_id else OUTCOME_REFUSED
            reason = (
                f"waiting for a human to approve (approval {approval_id})"
                if approval_id
                else f"refused by policy: {decision}"
            )
            self._complete(trigger, outcome, reason)
            self._record(
                {
                    "event": "channel.outreach_proposed",
                    "mind_id": self.mind_id,
                    "trigger": trigger.kind,
                    "trigger_ref": trigger.ref,
                    "beneficiary": intent.recipient.display_name,
                    "approval_id": approval_id,
                    "decision": decision,
                }
            )
            return OutreachOutcome(
                trigger=trigger,
                attempted=True,
                outcome=outcome,
                reason=reason,
                channel=self.channel,
                decision=decision,
                approval_id=approval_id,
            )

        return await self._send(trigger, intent, registration, decision, approval_id)

    async def _send(
        self,
        trigger: OutreachTrigger,
        intent: CommunicationIntent,
        registration: Any,
        decision: str,
        approval_id: Optional[str],
    ) -> OutreachOutcome:
        from .base import ApprovedCommunication

        # Re-prepare rather than reusing the earlier value: `prepare` is pure, and
        # the approval digest is computed over the prepared message, so building it
        # once and passing it around would mean a stale digest if anything about the
        # message changed between the gate and the send.
        prepared = await registration.adapter.prepare(intent)
        try:
            approved = ApprovedCommunication(
                prepared=prepared,
                contact=intent.recipient,
                decision=decision,
                decided_by="policy",
                approval_id=approval_id,
            )
            receipt = await registration.adapter.send(approved)
        except Exception as exc:  # noqa: BLE001
            reason = f"send failed: {exc}"
            self._complete(trigger, OUTCOME_FAILED, reason)
            return OutreachOutcome(
                trigger=trigger,
                attempted=True,
                outcome=OUTCOME_FAILED,
                reason=reason,
                channel=self.channel,
                decision=decision,
                approval_id=approval_id,
            )

        sent = getattr(receipt, "status", None)
        sent_ok = getattr(sent, "value", sent) == "sent"
        if sent_ok:
            self._complete(trigger, OUTCOME_SENT, "sent")
        else:
            error = getattr(receipt, "error", "") or "provider did not confirm delivery"
            self._complete(trigger, OUTCOME_FAILED, str(error))

        return OutreachOutcome(
            trigger=trigger,
            attempted=True,
            outcome=OUTCOME_SENT if sent_ok else OUTCOME_FAILED,
            reason="sent" if sent_ok else str(getattr(receipt, "error", "") or "failed"),
            channel=self.channel,
            decision=decision,
            approval_id=approval_id,
            receipt=receipt,
        )

    # -- drafting ----------------------------------------------------------

    async def _draft(self, trigger: OutreachTrigger, contact: ContactRef) -> Optional[str]:
        """Ask cognition what to say, or None to say nothing.

        Awaited, because a drafter is a model call. `MindResponder` is async for the
        same reason, and a sync drafter here would mean the one component that talks
        to a provider had to be called from a thread to work.

        Returns `None` rather than raising, because "this does not need a message" is
        a legitimate answer — a commitment may already have been fulfilled in
        conversation, and a Mind that always produces text would always send.
        """
        try:
            result = self.drafter(trigger, contact)
            if inspect.isawaitable(result):
                result = await result
            return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("outreach: drafting failed for %s: %s", trigger.ref, exc)
            return None

    @staticmethod
    def _subject(trigger: OutreachTrigger) -> str:
        if trigger.kind == TRIGGER_COMMITMENT_OVERDUE:
            return "About something I said I would do"
        return "Coming up"

    # -- attempts ----------------------------------------------------------

    def _claim(self, trigger: OutreachTrigger) -> tuple[bool, tuple[str, str]]:
        """Claim the one attempt for this trigger. Returns (claimed, refusal)."""
        if self.attempts is None:
            return True, ("", "")

        try:
            claimed = self.attempts.claim(
                mind_id=self.mind_id,
                trigger=trigger.kind,
                trigger_ref=trigger.ref,
                relationship_id=trigger.beneficiary_id,
                channel=self.channel,
            )
        except Exception as exc:  # noqa: BLE001
            # If the attempt cannot be recorded, it must not be made: proceeding
            # would repeat on every pass. Refusing here is the whole point of the
            # table, and it is reported rather than silently skipped.
            logger.error(
                "outreach: could not claim the attempt for %s/%s: %s",
                trigger.kind,
                trigger.ref,
                exc,
            )
            return False, (OUTCOME_FAILED, f"could not record the attempt: {exc}")

        if not claimed:
            return False, (
                OUTCOME_REFUSED,
                "already attempted for this trigger; not repeating it",
            )
        return True, ("", "")

    def _complete(self, trigger: OutreachTrigger, outcome: str, reason: str) -> None:
        if self.attempts is None:
            return
        try:
            self.attempts.complete(
                mind_id=self.mind_id,
                trigger=trigger.kind,
                trigger_ref=trigger.ref,
                outcome=outcome,
                reason=reason[:400],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "outreach: could not record the outcome for %s/%s: %s",
                trigger.kind,
                trigger.ref,
                exc,
            )


class OutreachAttempts:
    """The durable record of one attempt per trigger instance.

    Claim-before-attempt, with a unique constraint as the mechanism, for the same
    reason the inbound ledger works that way: a read-then-write would be a race, and
    the race produces the duplicate.
    """

    def __init__(self, *, session_factory: Optional[Any] = None):
        self._session_factory = session_factory

    @property
    def durable(self) -> bool:
        return True

    def _session(self):
        if self._session_factory is not None:
            return self._session_factory()
        from genesis.database.base import get_session_factory

        return get_session_factory()()

    def claim(
        self,
        *,
        mind_id: str,
        trigger: str,
        trigger_ref: str,
        relationship_id: str = "",
        channel: str = "",
    ) -> bool:
        from sqlalchemy.exc import IntegrityError

        from genesis.database.models import OutreachAttemptRecord

        if not trigger_ref:
            logger.warning("outreach: %r has no trigger_ref; not claiming", trigger)
            return False

        session = self._session()
        try:
            session.add(
                OutreachAttemptRecord(
                    mind_id=mind_id,
                    trigger=trigger,
                    trigger_ref=trigger_ref,
                    relationship_id=relationship_id,
                    channel=channel,
                    outcome="",
                )
            )
            session.commit()
            return True
        except IntegrityError:
            session.rollback()
            return False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def complete(
        self,
        *,
        mind_id: str,
        trigger: str,
        trigger_ref: str,
        outcome: str,
        reason: str = "",
    ) -> None:
        from genesis.database.models import OutreachAttemptRecord

        session = self._session()
        try:
            row = (
                session.query(OutreachAttemptRecord)
                .filter_by(mind_id=mind_id, trigger=trigger, trigger_ref=trigger_ref)
                .one_or_none()
            )
            if row is None:
                logger.warning(
                    "outreach: no attempt to complete for %s/%s", trigger, trigger_ref
                )
                return
            row.outcome = outcome
            row.reason = reason
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def pending(self, *, mind_id: str) -> list[dict[str, Any]]:
        """Attempts with no outcome: the process died mid-flight.

        Reported rather than retried, exactly as the inbound ledger does. A retry may
        contact someone who was already contacted.
        """
        from genesis.database.models import OutreachAttemptRecord

        session = self._session()
        try:
            rows = (
                session.query(OutreachAttemptRecord)
                .filter(
                    OutreachAttemptRecord.mind_id == mind_id,
                    OutreachAttemptRecord.outcome == "",
                )
                .all()
            )
            return [
                {
                    "trigger": row.trigger,
                    "trigger_ref": row.trigger_ref,
                    "channel": row.channel,
                    "attempted_at": row.attempted_at,
                }
                for row in rows
            ]
        finally:
            session.close()

    def recent(self, *, mind_id: str, limit: int = 200) -> list[dict[str, Any]]:
        """Every attempt, newest first — the record of what a Mind did unprompted."""
        from genesis.database.models import OutreachAttemptRecord

        session = self._session()
        try:
            rows = (
                session.query(OutreachAttemptRecord)
                .filter(OutreachAttemptRecord.mind_id == mind_id)
                .order_by(OutreachAttemptRecord.attempted_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "trigger": row.trigger,
                    "trigger_ref": row.trigger_ref,
                    "channel": row.channel,
                    "outcome": row.outcome,
                    "reason": row.reason,
                    "attempted_at": row.attempted_at,
                }
                for row in rows
            ]
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Assembling one from a Mind
# ---------------------------------------------------------------------------


def build_planner(
    mind: Any,
    *,
    settings: Optional[Any] = None,
    drafter: Optional[Any] = None,
    attempts: Optional[Any] = None,
) -> Optional[OutreachPlanner]:
    """Build a planner for a Mind, or `None` when outreach is switched off.

    Returns `None` rather than a disabled planner, so "off" and "on and doing nothing"
    cannot look the same — the same reasoning as `build_poller`.

    The drafter is `MindResponder` with an outreach-shaped prompt, which means the
    model is told what it owes and to whom, and is told nothing about policy. It is
    the same class, so the guarantees that class documents — no policy in the prompt,
    actions disabled, declining is a first-class answer — apply here unchanged.
    """
    from genesis.config import get_settings

    settings = settings or get_settings()
    if not getattr(settings, "mind_outreach_enabled", False):
        logger.info(
            "outreach: not started — MIND_OUTREACH_ENABLED is off. A Mind does not "
            "contact anyone because it decided it owed them something until an "
            "operator enables it."
        )
        return None

    registry = mind.channels
    if not registry.enabled():
        logger.warning(
            "outreach: MIND_OUTREACH_ENABLED is on but no channel is enabled, so "
            "there is nowhere to raise a commitment. Configure a channel and restart."
        )
        return None

    commitments = getattr(mind, "commitments", None)
    if commitments is None:
        logger.warning(
            "outreach: MIND_OUTREACH_ENABLED is on but this Mind has no commitment "
            "manager, so there is nothing to be proactive about."
        )
        return None

    mind_id = mind.identity.gmid
    tenant_policy = _parse_tenant_policy(
        getattr(settings, "mind_channel_tenant_policy", "")
    )
    granted_scopes = _split_csv(getattr(settings, "mind_channel_granted_scopes", ""))

    # Imported here rather than at module level: `poller` imports from `gateway`,
    # and this module is imported by `__init__` alongside both, so a top-level import
    # would make the cycle real.
    from .contacts import DatabaseContacts
    from .poller import GovernanceAuthorizer, JournalRecorder

    authorizer = GovernanceAuthorizer(
        mind_id=mind_id,
        tenant_policy=tenant_policy,
        granted_scopes=granted_scopes,
    )

    if drafter is None:
        from .responder import OutreachResponder

        drafter = OutreachResponder(mind=mind)

    max_per_pass = max(1, int(getattr(settings, "mind_outreach_max_per_pass", 10) or 10))

    return OutreachPlanner(
        mind_id=mind_id,
        registry=registry,
        contacts=DatabaseContacts(mind_id=mind_id),
        authorizer=authorizer,
        triggers=[CommitmentTriggers(commitments, max_triggers=max_per_pass)],
        drafter=drafter,
        attempts=attempts or OutreachAttempts(),
        recorder=JournalRecorder(mind_id=mind_id),
        channel="email",
    )


def _split_csv(value: Optional[str]) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def _parse_tenant_policy(value: Optional[str]) -> dict[str, Any]:
    """Parse the tenant policy from settings. Imported from `poller` so the two
    cannot drift: a typo must mean "no standing grant" in both places or in neither."""
    from .poller import _parse_tenant_policy as parse

    return parse(value)
