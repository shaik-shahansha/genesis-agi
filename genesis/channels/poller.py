"""Driving the channel loop: poll inbound, answer through the gate, never twice.

`ChannelGateway` implements the loop for one event. Nothing ran it, so a Mind could
address someone and could not answer — which is half of what "the Mind reads and
responds to its own email" means.

This module adds the three things that turns it into something that can run
unattended:

1. **An inbound ledger.** The single worst failure mode of a poller is answering
   the same message twice: the person receives a duplicate reply, and nothing in
   the system looks wrong. A mailbox is re-read after every restart, so this is not
   a rare race — it is the default behaviour without a ledger.
2. **A governance authorizer.** Replies go through the *existing* policy engine at
   `comms.email.reply` (R2), not through a decision made here. Whether a reply is
   auto-approved is answered by tenant policy's standing-grant mechanism, which is
   already capped at R2 (`STANDING_GRANT_MAX_RISK`) and cannot be used to grant R3.
   So this file contains no autonomy toggle of its own — adding one would be a
   second, weaker copy of a control that already exists.
3. **A journal recorder.** What happened is written to the governance event journal
   rather than to a log, so it lands in the same timeline as everything else and
   appears in `/journal`.

## At-most-once, and what it costs

The ledger **claims** an inbound message before the gateway sees it. A claimed
message is never processed again, whatever happens next.

That choice has a real cost, and it is the right one: if the process dies between
claiming and sending, the reply is never sent. The alternatives are worse. Claiming
after the send means a crash re-answers, and a person receives the same reply twice
— which is externally visible, attributed to a named human administrator, and
cannot be retracted. A missing auto-reply is recoverable by a person reading
`pending()`; a duplicate is not recoverable at all.

A claim with no outcome means the process died mid-flight. `pending()` returns
those, and the poller reports them rather than retrying, because retrying is exactly
the duplicate this design exists to prevent. Someone has to look. That is the honest
option: the alternative is a system that quietly re-sends and a bug report nobody
can reproduce.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional, Protocol

from .base import CommunicationIntent, ContactRef, InboundEvent, OutboundPermission
from .contacts import DatabaseContacts
from .gateway import ChannelGateway, EngagementOutcome

#: Imported at module level for the event vocabulary only — the journal *service* is
#: resolved lazily in `JournalRecorder.audit`, so importing this module does not
#: require a configured governance store.
from genesis.governance.models import EventType

logger = logging.getLogger(__name__)

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------


class InboundLedger(Protocol):
    """Records which inbound messages have already been handled.

    `durable` is exposed for the same reason `OutboundLedger.durable` is: a
    non-durable ledger still prevents duplicates within one process, but it must
    not be presented as a guarantee that holds over a restart. The poller reports
    which it has.
    """

    @property
    def durable(self) -> bool: ...

    def claim(
        self, *, mind_id: str, channel: str, provider_message_id: str
    ) -> bool:
        """Claim a message. True if this call claimed it, False if already claimed.

        Must be atomic. Two pollers racing on one mailbox is exactly the
        configuration where a check-then-act ledger answers a message twice.
        """

    def complete(
        self,
        *,
        mind_id: str,
        channel: str,
        provider_message_id: str,
        outcome: str,
        reason: str = "",
    ) -> None:
        """Record what happened, so a claim is not left dangling."""

    def pending(self, *, mind_id: str) -> list[dict[str, Any]]:
        """Claims with no outcome: the process died mid-flight.

        Returned rather than retried. Retrying is the duplicate the ledger exists
        to prevent, so this is a list for a human, not a work queue.
        """


@dataclass
class InMemoryInboundLedger:
    """Process-local. **Not durable.**

    Adequate for a single long-running process and for tests. It does not survive a
    restart, so a Mind would re-answer everything it had already handled — which is
    why `durable` reports `False` rather than nothing.

    It refuses an empty message id for the same reason the durable ledger does. That
    check is easy to forget in a test double, and a double that accepts what the real
    thing refuses proves nothing about the real thing — the tests would pass while
    the shipped path dropped every id-less message.
    """

    claimed: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)

    @property
    def durable(self) -> bool:
        return False

    def claim(self, *, mind_id: str, channel: str, provider_message_id: str) -> bool:
        if not provider_message_id:
            # Storing `''` would book every id-less message as handled, and every
            # future one would be silently dropped as a duplicate.
            logger.warning(
                "inbound ledger: %s event has no provider message id; not claiming", channel
            )
            return False
        key = (mind_id, channel, provider_message_id)
        if key in self.claimed:
            return False
        self.claimed[key] = {"claimed_at": _utcnow(), "outcome": "", "reason": ""}
        return True

    def complete(
        self,
        *,
        mind_id: str,
        channel: str,
        provider_message_id: str,
        outcome: str,
        reason: str = "",
    ) -> None:
        key = (mind_id, channel, provider_message_id)
        record = self.claimed.setdefault(
            key, {"claimed_at": _utcnow(), "outcome": "", "reason": ""}
        )
        record["outcome"] = outcome
        record["reason"] = reason

    def pending(self, *, mind_id: str) -> list[dict[str, Any]]:
        return [
            {"channel": channel, "provider_message_id": message_id, **record}
            for (owner, channel, message_id), record in self.claimed.items()
            if owner == mind_id and not record.get("outcome")
        ]


class DatabaseInboundLedger:
    """Durable, and atomic through a unique constraint rather than a read-then-write.

    Two steps that matter:

    * `claim` **inserts** and treats an `IntegrityError` as "someone else got it".
      A `SELECT` followed by an `INSERT` would be a race, and the race is exactly
      the duplicate reply this table exists to prevent.
    * `complete` **updates** rather than inserting, so a claim can only be resolved
      by the poller that made it.
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

    def claim(self, *, mind_id: str, channel: str, provider_message_id: str) -> bool:
        from sqlalchemy.exc import IntegrityError

        from genesis.database.models import InboundEventRecord

        if not provider_message_id:
            # A message with no id cannot be deduplicated, so it must not be
            # claimed. Claiming it would book the empty string as handled and
            # silently drop every future message that also had no id.
            logger.warning(
                "inbound ledger: %s event has no provider message id; not claiming", channel
            )
            return False

        session = self._session()
        try:
            session.add(
                InboundEventRecord(
                    mind_id=mind_id,
                    channel=channel,
                    provider_message_id=provider_message_id,
                    claimed_at=_utcnow(),
                )
            )
            session.commit()
            return True
        except IntegrityError:
            # Already claimed. This is the normal path on a re-read, not an error.
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
        channel: str,
        provider_message_id: str,
        outcome: str,
        reason: str = "",
    ) -> None:
        from genesis.database.models import InboundEventRecord

        session = self._session()
        try:
            row = (
                session.query(InboundEventRecord)
                .filter_by(
                    mind_id=mind_id,
                    channel=channel,
                    provider_message_id=provider_message_id,
                )
                .one_or_none()
            )
            if row is None:
                # The claim was never made, so there is nothing to complete. Log
                # rather than insert: inserting here would fabricate a claim that
                # the guard never granted.
                logger.warning(
                    "inbound ledger: no claim to complete for %s/%s",
                    channel,
                    provider_message_id,
                )
                return
            row.outcome = outcome
            row.reason = reason
            row.completed_at = _utcnow()
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def pending(self, *, mind_id: str) -> list[dict[str, Any]]:
        from genesis.database.models import InboundEventRecord

        session = self._session()
        try:
            rows = (
                session.query(InboundEventRecord)
                .filter(
                    InboundEventRecord.mind_id == mind_id,
                    InboundEventRecord.outcome == "",
                )
                .all()
            )
            return [
                {
                    "channel": row.channel,
                    "provider_message_id": row.provider_message_id,
                    "claimed_at": row.claimed_at,
                }
                for row in rows
            ]
        finally:
            session.close()


# ---------------------------------------------------------------------------
# The gate, reused rather than reimplemented
# ---------------------------------------------------------------------------

#: Which capability an outbound message is, per channel and direction. The names
#: match `genesis.governance.risk`, so the risk level, the required scopes and the
#: reversibility all come from the one registry that already declares them.
_ACTION_BY_CHANNEL: dict[str, tuple[str, str]] = {
    # channel: (reply action, initiate action)
    "email": ("comms.email.reply", "comms.email.send"),
    "telegram": ("comms.telegram.reply", "comms.telegram.send"),
    "voice": ("comms.voice.call_outbound", "comms.voice.call_outbound"),
}

#: The scope each action requires, so a grant can actually be satisfied. Taken from
#: the profiles in `risk.py`; a mismatch here would show up as every reply being
#: refused for a missing scope, which is at least loud.
_SCOPES_BY_ACTION: dict[str, tuple[str, ...]] = {
    "comms.email.reply": ("comms.email.send",),
    "comms.email.send": ("comms.email.send",),
    "comms.telegram.reply": ("comms.telegram.send",),
    "comms.telegram.send": ("comms.telegram.send",),
    "comms.voice.call_outbound": ("comms.voice.call",),
}


class GovernanceAuthorizer:
    """An `Authorizer` that asks the policy engine, and nothing else.

    Deliberately contains no notion of "trusted contact therefore allow". That rule
    already exists, is already tested, and is already capped at R2: tenant policy's
    `auto_approve_risk_levels` plus a capability or category scope decides it, and
    `STANDING_GRANT_MAX_RISK` prevents it being extended to R3. A convenience check
    here would be a second copy of that control, and a second copy would be the one
    that turns out to be wrong.

    Returns the decision string the gateway expects, which is not a policy decision
    id: the gateway only needs to know whether a permitted decision exists and, if
    not, whether an approval was raised. `allow` and `allow_with_receipt` are the
    two it treats as permission.
    """

    def __init__(
        self,
        *,
        mind_id: str,
        gate: Optional[Any] = None,
        tenant_policy: Optional[dict[str, Any]] = None,
        granted_scopes: Optional[tuple[str, ...]] = None,
    ):
        self.mind_id = mind_id
        self._gate = gate
        self.tenant_policy = dict(tenant_policy or {})
        #: Explicitly granted scopes. Without the scope a reply is refused for
        #: `missing_scope` regardless of risk level, so this is required for a
        #: standing grant to be able to apply at all.
        self.granted_scopes = tuple(granted_scopes or ())

    @property
    def gate(self):
        if self._gate is None:
            from genesis.governance.guard import get_governance_gate

            self._gate = get_governance_gate()
        return self._gate

    def action_for(self, channel: str, *, is_reply: bool) -> str:
        reply_action, initiate_action = _ACTION_BY_CHANNEL.get(
            channel, (f"comms.{channel}.reply", f"comms.{channel}.send")
        )
        return reply_action if is_reply else initiate_action

    async def __call__(
        self, intent: CommunicationIntent, contact: ContactRef
    ) -> tuple[str, Optional[str]]:
        """Authorize one outbound message. Never raises for a policy outcome."""
        action_name = self.action_for(intent.channel, is_reply=intent.is_reply)
        requested = _SCOPES_BY_ACTION.get(action_name, ())
        granted = tuple(
            sorted(set(self.granted_scopes) | {s for s in requested if s in self.granted_scopes})
        )

        try:
            context = self.gate.build_context(
                action_name=action_name,
                parameters={
                    "channel": intent.channel,
                    "to": contact.handle,
                    # The body is passed so a policy can inspect it, but it is also
                    # redacted on the way into the journal — `redact` runs in the
                    # writer, so this cannot be the path that leaks a message into
                    # the audit store.
                    "body_length": len(intent.body or ""),
                    "is_reply": intent.is_reply,
                    "relationship_id": contact.relationship_id,
                    "contact_trusted": bool(contact.consent_source.strip()),
                },
                mind_id=self.mind_id,
                category="COMMUNICATION",
                granted_scopes=granted,
                tenant_policy=self.tenant_policy,
            )
            result = self.gate.authorize(context, action_id=_action_id(intent))
        except Exception as exc:  # noqa: BLE001
            # A gate that cannot be consulted is not permission. This is the one
            # place where "fail closed" has teeth, so it returns a refusal rather
            # than raising: an exception here would abort the whole drain and the
            # remaining messages would go unanswered for no reason.
            logger.error(
                "channel authorizer: governance gate failed for %s: %s", action_name, exc
            )
            return (f"refused: governance unavailable ({exc})", None)

        if result.allowed:
            decision = getattr(result.decision, "decision", None)
            name = getattr(decision, "value", "") or ""
            return (name if name in ("allow", "allow_with_receipt") else "allow", None)

        approval = getattr(result, "approval", None)
        approval_id = getattr(approval, "approval_id", None) if approval else None
        if approval_id:
            return ("requires_approval", approval_id)
        return (f"refused by policy: {result.reason}", None)


def _action_id(intent: CommunicationIntent) -> str:
    """A stable id for one outbound attempt, used for the journal correlation."""
    if intent.correlation_id:
        return intent.correlation_id
    thread = intent.thread_id or "no-thread"
    return f"{intent.channel}:{thread}:{intent.reply_to_message_id or 'new'}"


class JournalRecorder:
    """Writes channel outcomes to the governance event journal.

    Not to a log file. A log is a debugging aid; the journal is the record of what a
    Mind did and is verifiable, queryable and the thing an operator reads. Sending a
    message is a governed action, so it belongs there.

    Best-effort by construction — `ChannelGateway._record` swallows a failure here,
    on the same reasoning as the domain journal: an audit store outage must not
    become a Mind that stops answering. The cost is that a journal outage loses
    records, which is why this does not pretend to be transactional with the send.
    """

    #: Gateway event name → journal event type. Explicit rather than derived, so an
    #: event family is not invented by string concatenation at runtime.
    _EVENT_TYPES: dict[str, str] = {
        "channel.inbound_received": EventType.CHANNEL_INBOUND_RECEIVED,
        "channel.reply_sent": EventType.CHANNEL_REPLY_SENT,
        "channel.reply_refused": EventType.CHANNEL_REPLY_REFUSED,
        "channel.reply_not_sent": EventType.CHANNEL_REPLY_NOT_SENT,
    }

    def __init__(self, *, mind_id: str, audit: Optional[Any] = None):
        self.mind_id = mind_id
        self._audit = audit

    @property
    def audit(self):
        if self._audit is None:
            from genesis.governance.audit import get_audit_service

            self._audit = get_audit_service()
        return self._audit

    def __call__(self, payload: dict[str, Any]) -> None:
        raw_event = str(payload.get("event", ""))
        event_type = self._EVENT_TYPES.get(raw_event)
        if event_type is None:
            # An unrecognised event is not silently re-filed under a guess: it is
            # recorded under a `channel.` name that says it was unrecognised, so the
            # gap is visible in the journal rather than papered over.
            logger.warning("channel recorder: unrecognised event %r", raw_event)
            event_type = EventType.CHANNEL_REPLY_NOT_SENT

        owner = payload.get("mind_id") or self.mind_id
        # `record`, not `record_event` — and it redacts the payload itself, so
        # message content does not reach the journal by this path.
        self.audit.record(
            event_type,
            mind_id=owner,
            actor_type="mind",
            actor_id=owner,
            payload={k: v for k, v in payload.items() if k not in ("event", "mind_id")},
        )


# ---------------------------------------------------------------------------
# The poller
# ---------------------------------------------------------------------------


@dataclass
class PollReport:
    """What one pass did. Counts, plus the things a human has to act on."""

    received: int = 0
    duplicates: int = 0
    engaged: int = 0
    delivered: int = 0
    refused: int = 0
    failed: int = 0
    #: Claims with no outcome from a previous run. Reported, never retried.
    stuck: list[dict[str, Any]] = field(default_factory=list)
    #: Channel-level read failures, by channel. A broken mailbox must not read as
    #: "no new mail", which is why this is separate from `received == 0`.
    read_failures: dict[str, str] = field(default_factory=dict)
    durable_ledger: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "received": self.received,
            "duplicates": self.duplicates,
            "engaged": self.engaged,
            "delivered": self.delivered,
            "refused": self.refused,
            "failed": self.failed,
            "stuck": self.stuck,
            "read_failures": self.read_failures,
            "durable_ledger": self.durable_ledger,
        }


#: Called when a claim is left dangling, so an operator learns about it.
StuckClaimHandler = Callable[[dict[str, Any]], None]


class ChannelPoller:
    """Reads inbound events and hands each one to the gateway, once.

    Owns no policy. Its jobs are claiming, delegating, recording the outcome and
    reporting — and the only decision it makes on its own is to *stop*, which it
    does whenever it cannot tell whether a message has already been handled.
    """

    def __init__(
        self,
        *,
        registry: Any,
        gateway: ChannelGateway,
        ledger: InboundLedger,
        mind_id: str,
        lookback: timedelta = timedelta(days=3),
        on_stuck: Optional[StuckClaimHandler] = None,
    ):
        self.registry = registry
        self.gateway = gateway
        self.ledger = ledger
        self.mind_id = mind_id
        self.lookback = lookback
        self.on_stuck = on_stuck

    async def poll_once(self, *, since: Optional[datetime] = None) -> PollReport:
        """One pass over every enabled channel."""
        report = PollReport(durable_ledger=self.ledger.durable)

        # Surface stuck claims first. Doing it before the work means an operator
        # reading the report sees the previous crash alongside this run rather than
        # a run that looks clean because nothing new arrived.
        try:
            report.stuck = self.ledger.pending(mind_id=self.mind_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("channel poller: could not read pending claims: %s", exc)
            report.read_failures["<ledger>"] = f"could not read pending claims: {exc}"
        for claim in report.stuck:
            logger.error(
                "channel poller: unhandled inbound message %s/%s claimed at %s; "
                "NOT retrying, because a retry may answer it twice",
                claim.get("channel"),
                claim.get("provider_message_id"),
                claim.get("claimed_at"),
            )
            if self.on_stuck is not None:
                try:
                    self.on_stuck(claim)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("channel poller: on_stuck handler failed: %s", exc)

        try:
            events = await self.registry.receive_all(
                since=since or (_utcnow() - self.lookback)
            )
        except Exception as exc:  # noqa: BLE001
            # `receive_all` is supposed to isolate per channel. If it does not, the
            # whole pass failed and saying so beats reporting zero messages.
            logger.error("channel poller: inbound read failed entirely: %s", exc)
            report.read_failures["<all>"] = str(exc)
            return report

        report.received = len(events)

        for event in events:
            await self._process(event, report)

        return report

    async def _process(self, event: InboundEvent, report: PollReport) -> None:
        try:
            claimed = self.ledger.claim(
                mind_id=self.mind_id,
                channel=event.channel,
                provider_message_id=event.provider_message_id or "",
            )
        except Exception as exc:  # noqa: BLE001
            # If the ledger cannot be written, the message must NOT be processed:
            # proceeding would answer something that may already have been answered
            # on a previous pass. Not proceeding is the whole point of the ledger.
            logger.error(
                "channel poller: could not claim %s/%s, skipping: %s",
                event.channel,
                event.provider_message_id,
                exc,
            )
            report.failed += 1
            return

        if not claimed:
            report.duplicates += 1
            return

        outcome: Optional[EngagementOutcome] = None
        try:
            outcome = await self.gateway.handle(event)
        except Exception as exc:  # noqa: BLE001
            # The gateway catches its own failures; reaching here means something
            # outside that contract broke. The claim stands, so this becomes a
            # `pending` row for a human rather than a retry.
            logger.error(
                "channel poller: gateway raised for %s/%s: %s",
                event.channel,
                event.provider_message_id,
                exc,
            )
            self._complete(event, "failed", f"gateway raised: {exc}")
            report.failed += 1
            return

        self._complete(
            event,
            "delivered" if outcome.delivered else "not_sent",
            f"{outcome.reason}" + (f" / {outcome.decision}" if outcome.decision else ""),
        )

        if outcome.engaged:
            report.engaged += 1
        if outcome.delivered:
            report.delivered += 1
        elif outcome.engaged:
            report.refused += 1

    def _complete(self, event: InboundEvent, outcome: str, reason: str) -> None:
        try:
            self.ledger.complete(
                mind_id=self.mind_id,
                channel=event.channel,
                provider_message_id=event.provider_message_id or "",
                outcome=outcome,
                reason=reason[:400],
            )
        except Exception as exc:  # noqa: BLE001
            # The claim now looks stuck, which is the correct alarm. The message was
            # still handled, so this does not become a retry.
            logger.error(
                "channel poller: could not record the outcome for %s/%s: %s",
                event.channel,
                event.provider_message_id,
                exc,
            )

    async def run(
        self,
        *,
        interval_seconds: float = 60.0,
        stop: Optional[asyncio.Event] = None,
        on_report: Optional[Callable[[PollReport], None]] = None,
    ) -> None:
        """Poll until stopped.

        A failing pass does not end the loop: a mailbox that is temporarily
        unreachable should not stop a Mind from answering the other channels, and a
        loop that exits on the first error is a loop nobody notices has stopped.
        The report carries the failures, so silence is not the only signal.
        """
        while stop is None or not stop.is_set():
            try:
                report = await self.poll_once()
                if on_report is not None:
                    try:
                        on_report(report)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("channel poller: on_report failed: %s", exc)
            except Exception as exc:  # noqa: BLE001
                logger.error("channel poller: pass failed: %s", exc)

            try:
                if stop is None:
                    await asyncio.sleep(interval_seconds)
                else:
                    await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
            except asyncio.TimeoutError:
                continue


# ---------------------------------------------------------------------------
# Assembling one from a Mind
# ---------------------------------------------------------------------------


def _split_csv(value: Optional[str]) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def _parse_tenant_policy(value: Optional[str]) -> dict[str, Any]:
    """Parse the tenant policy from settings.

    A malformed value yields `{}`, which means "no standing grant", so every reply
    needs approval. That is the fail-closed reading, and it is logged: silently
    treating a typo as "no policy configured" would look identical to a policy that
    was never set, and the operator would conclude the setting does not work.
    """
    import json

    if not value or not str(value).strip():
        return {}
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError) as exc:
        logger.error(
            "MIND_CHANNEL_TENANT_POLICY is not valid JSON (%s); no standing grant is "
            "in force, so every reply will need approval",
            exc,
        )
        return {}
    if not isinstance(parsed, dict):
        logger.error(
            "MIND_CHANNEL_TENANT_POLICY must be a JSON object, not %s; ignoring it",
            type(parsed).__name__,
        )
        return {}
    return parsed


def build_poller(
    mind: Any,
    *,
    settings: Optional[Any] = None,
    responder: Optional[Any] = None,
    ledger: Optional[InboundLedger] = None,
) -> Optional["ChannelPoller"]:
    """Build a poller for a Mind, or `None` when answering is switched off.

    Returns `None` rather than a disabled poller so the caller cannot accidentally
    start one: "answering is off" and "answering is on and doing nothing" must not
    look the same, and a poller that silently does nothing is exactly the failure
    mode this project keeps finding.

    The registry comes from `mind.channels`, so the channels are the ones an
    administrator provisioned, with the refused ones carrying their reasons.
    """
    from genesis.config import get_settings

    settings = settings or get_settings()
    if not getattr(settings, "mind_channel_autoreply_enabled", False):
        logger.info(
            "channel poller: not started — MIND_CHANNEL_AUTOREPLY_ENABLED is off. "
            "A Mind does not answer inbound messages until an operator enables it "
            "and configures an approval policy."
        )
        return None

    registry = mind.channels
    if not registry.enabled():
        logger.warning(
            "channel poller: MIND_CHANNEL_AUTOREPLY_ENABLED is on but no channel is "
            "enabled, so there is nothing to read. Configure an email or Telegram "
            "channel and restart."
        )
        return None

    mind_id = mind.identity.gmid
    tenant_policy = _parse_tenant_policy(
        getattr(settings, "mind_channel_tenant_policy", "")
    )
    granted_scopes = _split_csv(getattr(settings, "mind_channel_granted_scopes", ""))

    authorizer = GovernanceAuthorizer(
        mind_id=mind_id,
        tenant_policy=tenant_policy,
        granted_scopes=granted_scopes,
    )

    if responder is None:
        from .responder import MindResponder

        responder = MindResponder(mind=mind)

    gateway = ChannelGateway(
        registry=registry,
        contacts=DatabaseContacts(mind_id=mind_id),
        responder=responder,
        authorizer=authorizer,
        recorder=JournalRecorder(mind_id=mind_id),
        mind_id=mind_id,
    )

    lookback = timedelta(
        days=max(1, int(getattr(settings, "mind_channel_lookback_days", 3) or 3))
    )

    def on_stuck(claim: dict[str, Any]) -> None:
        # Journalled, not just logged: an unresolved claim is a message a person
        # wrote that will never be answered, and that belongs in the timeline an
        # operator reads rather than in a log file.
        try:
            JournalRecorder(mind_id=mind_id)(
                {
                    "event": "channel.reply_not_sent",
                    "mind_id": mind_id,
                    "reason": "inbound message was claimed but never handled",
                    **claim,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("channel poller: could not journal a stuck claim: %s", exc)

    return ChannelPoller(
        registry=registry,
        gateway=gateway,
        ledger=ledger or DatabaseInboundLedger(),
        mind_id=mind_id,
        lookback=lookback,
        on_stuck=on_stuck,
    )
