"""The channel gateway: inbound event → cognition → governance → send.

Without this, the pieces do not form a loop. An adapter can read; an adapter can
send; but "the Mind read a message and replied" needs something that joins them
*through the gate*, and that is this.

It is deliberately small, because its whole job is to place the governance
decision in the one position where it cannot be skipped:

    receive → resolve who sent it → decide whether to engage → build an intent
            → prepare → GOVERNANCE → send → record

Two rules the shape enforces:

1. **The Mind decides whether to engage; the gateway decides whether it may.**
   Cognition produces an intent or nothing. It never sees an approval decision and
   cannot influence one.
2. **A reply is a reply.** An inbound message yields a reply intent with the
   thread attached, which is what makes it R2 rather than R3 — answering someone
   who wrote first is not outreach, and the floors treat it that way.

The gateway does **not** contain a model call. `responder` is injected: it receives
one inbound event plus the contact, and returns text or None. That keeps this file
free of the cognition coupling, makes the loop testable without a provider, and
means the old substring-matching auto-responder cannot reappear here by accident.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Protocol

from .base import (
    ApprovedCommunication,
    CommunicationIntent,
    ContactRef,
    DeliveryReceipt,
    DeliveryStatus,
    InboundEvent,
    OutboundPermission,
)
from .registry import ChannelRegistry

logger = logging.getLogger(__name__)


class ContactResolver(Protocol):
    """Finds the contact a message came from.

    Implemented by the relationship store. The gateway needs only this, so it does
    not depend on `core/relationships.py` — and a resolver that cannot find
    someone returning `None` is what keeps an unknown sender reply-only.

    `mind_id` is part of the protocol because consent is per-Mind. A resolver
    belonging to another Mind answers "may I contact this person?" with *that*
    Mind's consent, which would let a Mind it does not apply to initiate a message
    using someone else's permission. The gateway checks it, because a wiring
    mistake here is silent and the consequence is exactly what the consent model
    exists to prevent.
    """

    mind_id: str

    def resolve(self, *, channel: str, handle: str, display_name: str = "") -> Optional[ContactRef]: ...


@dataclass
class InMemoryContacts:
    """Resolves contacts from a dict. For tests and for a dry run.

    A sender the resolver does not know is returned as a reply-only contact with
    **no** consent source, so the floors refuse an initiated message and permit a
    reply. That is the fail-closed default for a stranger, and getting it backwards
    is how a Mind starts cold-emailing people who once wrote to it.
    """

    known: dict[str, ContactRef] = field(default_factory=dict)
    #: Matches `ContactResolver`. Empty means "belongs to no particular Mind",
    #: which is what a test wants; a real store always sets it.
    mind_id: str = ""

    def resolve(self, *, channel: str, handle: str, display_name: str = "") -> Optional[ContactRef]:
        existing = self.known.get(handle)
        if existing is not None:
            return existing
        return ContactRef(
            relationship_id=f"unknown:{handle}",
            display_name=display_name or handle,
            handle=handle,
            outbound=OutboundPermission.REPLY_ONLY,
            consent_source="",
        )


#: Cognition's entry point: one inbound event plus the contact, some text or None.
#: Returning None means "do not engage", which is a legitimate and common answer.
Responder = Callable[[InboundEvent, ContactRef], Awaitable[Optional[str]]]

#: The gate. Returns a decision string and, when one was needed, an approval id.
#: The gateway passes this straight through and never interprets it.
Authorizer = Callable[[CommunicationIntent, ContactRef], Awaitable[tuple[str, Optional[str]]]]

#: Records what happened. The gateway reports; it does not decide what is audited.
Recorder = Callable[[dict[str, Any]], None]


@dataclass
class EngagementOutcome:
    """What the gateway did with one inbound event."""

    inbound: InboundEvent
    engaged: bool
    reason: str
    reply_body: Optional[str] = None
    decision: Optional[str] = None
    approval_id: Optional[str] = None
    receipt: Optional[DeliveryReceipt] = None

    @property
    def delivered(self) -> bool:
        return self.receipt is not None and self.receipt.status is DeliveryStatus.SENT

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "channel": self.inbound.channel,
            "from": self.inbound.sender_name or self.inbound.sender_handle,
            "subject": self.inbound.subject,
            "engaged": self.engaged,
            "reason": self.reason,
            "decision": self.decision,
            "approval_id": self.approval_id,
            "delivered": self.delivered,
            "receipt": self.receipt.to_public_dict() if self.receipt else None,
        }


class ChannelGateway:
    """Joins inbound events to outbound sends through governance."""

    def __init__(
        self,
        *,
        registry: ChannelRegistry,
        contacts: ContactResolver,
        responder: Responder,
        authorizer: Authorizer,
        recorder: Optional[Recorder] = None,
        mind_id: str = "",
    ):
        self.registry = registry
        self.contacts = contacts
        self.responder = responder
        self.authorizer = authorizer
        self.recorder = recorder
        self.mind_id = mind_id

    def _record(self, payload: dict[str, Any]) -> None:
        """Best-effort recording. Never breaks the loop.

        Same principle as the domain journal: a failure to *record* what happened
        must not prevent it from happening, or an audit store outage becomes a
        Mind that stops answering.
        """
        if self.recorder is None:
            return
        try:
            self.recorder(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("channel gateway: recording failed: %s", exc)

    async def handle(self, event: InboundEvent) -> EngagementOutcome:
        """Process one inbound event end to end."""
        resolver_mind = getattr(self.contacts, "mind_id", "")
        if self.mind_id and resolver_mind and resolver_mind != self.mind_id:
            # A wiring mistake, and a silent one: the resolver would answer with
            # another Mind's consent, so this Mind could initiate a message on
            # permission that was never granted to it. Refuse rather than
            # proceed, because there is no safe way to guess which is correct.
            logger.error(
                "channel gateway: contact resolver for %r used by %r; refusing",
                resolver_mind,
                self.mind_id,
            )
            return EngagementOutcome(
                inbound=event,
                engaged=False,
                reason=(
                    f"contact resolver belongs to {resolver_mind!r}, not "
                    f"{self.mind_id!r}; consent from another Mind's store is not "
                    "usable here"
                ),
            )

        contact = self.contacts.resolve(
            channel=event.channel,
            handle=event.sender_handle,
            display_name=event.sender_name,
        )
        if contact is None:
            return EngagementOutcome(
                inbound=event, engaged=False, reason="sender could not be resolved"
            )

        registration = self.registry.get(event.channel)
        if registration is None or not registration.enabled:
            return EngagementOutcome(
                inbound=event,
                engaged=False,
                reason=f"no enabled {event.channel} channel; cannot reply",
            )

        # Cognition decides whether to engage. It is given the contact so it knows
        # who it is talking to, and it is given nothing about policy.
        try:
            body = await self.responder(event, contact)
        except Exception as exc:  # noqa: BLE001 - a responder failure is not a send
            logger.warning("channel gateway: responder failed for %s: %s", event.channel, exc)
            return EngagementOutcome(
                inbound=event, engaged=False, reason=f"responder failed: {exc}"
            )

        if not body or not str(body).strip():
            return EngagementOutcome(
                inbound=event, engaged=False, reason="chose not to reply"
            )

        intent = CommunicationIntent(
            channel=event.channel,
            recipient=contact,
            body=str(body),
            subject=_reply_subject(event.subject),
            thread_id=event.thread_id,
            in_reply_to=event.provider_message_id,
            reply_to_message_id=event.provider_message_id,
            trigger="reply",
            trigger_ref=event.provider_message_id,
            correlation_id=event.metadata.get("correlation_id"),
        )

        prepared = await registration.adapter.prepare(intent)
        if prepared.requires_approval_because:
            # The floors already said no. There is no point asking governance,
            # and asking anyway would produce an approval card for a message the
            # adapter will refuse to send — noise that trains approvers to click.
            reason = "; ".join(prepared.requires_approval_because)
            self._record(
                {"event": "channel.reply_refused", "mind_id": self.mind_id, **event.to_public_dict(), "reason": reason}
            )
            return EngagementOutcome(
                inbound=event, engaged=False, reason=reason, reply_body=prepared.body
            )

        decision, approval_id = await self.authorizer(intent, contact)
        outcome = EngagementOutcome(
            inbound=event,
            engaged=True,
            reason="sent",
            reply_body=prepared.body,
            decision=decision,
            approval_id=approval_id,
        )

        if decision not in ("allow", "allow_with_receipt"):
            outcome.reason = f"governance decision was {decision}"
            self._record(
                {
                    "event": "channel.reply_not_sent",
                    "mind_id": self.mind_id,
                    **event.to_public_dict(),
                    "decision": decision,
                    "approval_id": approval_id,
                }
            )
            return outcome

        approved = ApprovedCommunication(
            prepared=prepared,
            contact=contact,
            decision=decision,
            approval_id=approval_id,
            correlation_id=event.metadata.get("correlation_id"),
        )

        receipt = await registration.adapter.send(approved)
        outcome.receipt = receipt
        if not receipt.ok:
            outcome.reason = receipt.error or f"delivery status {receipt.status.value}"

        self._record(
            {
                "event": "channel.reply",
                "mind_id": self.mind_id,
                **event.to_public_dict(),
                "decision": decision,
                "approval_id": approval_id,
                "receipt": receipt.to_public_dict(),
            }
        )
        return outcome

    async def drain(self, *, since: Optional[datetime] = None) -> list[EngagementOutcome]:
        """Read every enabled channel and handle what arrived.

        Sequential, not concurrent, and that is a deliberate choice for now: sends
        to one provider share a rate limit, and the floors count initiated messages
        in a shared ledger, so treating a burst in parallel would race the counter.
        Concurrency here is an optimisation to make once the ledger is durable.
        """
        events = await self.registry.receive_all(since=since)
        return [await self.handle(event) for event in events]


def _reply_subject(subject: Optional[str]) -> str:
    """`Re:` a subject, without stacking prefixes.

    A thread that goes three round trips should not read `Re: Re: Re:`. The check
    is case-insensitive because `RE:` and `Re:` are the same prefix to a reader,
    and a reply subject is only ever cosmetic anyway — threading is carried by the
    message references.
    """
    if not subject:
        return "Re: (no subject)"
    if subject.lower().startswith("re:"):
        return subject
    return f"Re: {subject}"
