"""Shared channel implementation.

The protocol in `base.py` says what a channel is. This says how the parts that
must behave identically everywhere actually work — because they are the parts
where a per-adapter implementation would drift.

Specifically: disclosure, quiet hours, weekly caps, opt-out and cost accounting
are implemented **here, once**. An adapter implements `_deliver()` and
`_fetch_inbound()` and gets the floors for free. The alternative — each adapter
calling `apply_disclosure` and `assert_can_send` itself — is a design where the
third adapter forgets, and the omission is invisible in review because it is a
*missing* line.

`send()` in this class is the only place in the whole subsystem that reaches a
provider, and it cannot be reached without an `ApprovedCommunication`.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .base import (
    ApprovedCommunication,
    ChannelCapabilities,
    ChannelIdentity,
    CommunicationIntent,
    ConversationThread,
    DeliveryReceipt,
    DeliveryStatus,
    ExternalContact,
    InboundEvent,
    PreparedMessage,
)
from .disclosure import apply_disclosure, assert_disclosed, compose_disclosure, is_disclosed
from .limits import (
    ChannelLimits,
    InMemoryOutboundLedger,
    OptOutRegistry,
    OutboundLedger,
    assert_can_send,
    outbound_refusal_reason,
)

logger = logging.getLogger(__name__)


class BaseChannel:
    """Common behaviour for every channel adapter.

    Subclasses set `name` and implement `capabilities()`, `_deliver()` and
    `_fetch_inbound()`.
    """

    #: Channel name, e.g. "email". Used in capability names and receipts.
    name: str = "channel"

    def __init__(
        self,
        *,
        address: str,
        display_name: str = "",
        administrator: str = "",
        limits: Optional[ChannelLimits] = None,
        ledger: Optional[OutboundLedger] = None,
        optouts: Optional[OptOutRegistry] = None,
        mind_id: str = "",
        verified: bool = False,
    ):
        self.address = address
        self.display_name = display_name or address
        self.administrator = administrator
        self.verified = verified
        self.limits = limits or ChannelLimits()
        self.ledger: OutboundLedger = ledger or InMemoryOutboundLedger()
        self.optouts = optouts or OptOutRegistry()
        self.mind_id = mind_id

    # -- identity ----------------------------------------------------------

    @property
    def identity(self) -> ChannelIdentity:
        """Identity, with the disclosure line filled in.

        Composed on each access rather than stored, so that changing the
        administrator's name updates every future message's disclosure without a
        migration. `registry.ChannelRegistry.register` refuses a channel whose
        identity has no disclosure, so a subclass that somehow produces an empty
        one is caught at registration rather than at send time.
        """
        base = ChannelIdentity(
            channel=self.name,
            address=self.address,
            display_name=self.display_name,
            disclosure="",
            administrator=self.administrator,
            verified=self.verified,
        )
        return ChannelIdentity(
            channel=base.channel,
            address=base.address,
            display_name=base.display_name,
            disclosure=compose_disclosure(base),
            administrator=base.administrator,
            verified=base.verified,
        )


    # -- to implement ------------------------------------------------------

    def capabilities(self) -> ChannelCapabilities:
        raise NotImplementedError

    async def _deliver(self, approved: ApprovedCommunication) -> DeliveryReceipt:
        """Provider-specific send. The only method that changes the world."""
        raise NotImplementedError

    async def _fetch_inbound(self, since: Optional[datetime]) -> list[InboundEvent]:
        """Provider-specific read. Must not act on what it reads."""
        return []

    def _capability_for(self, intent: CommunicationIntent) -> str:
        action = "reply" if intent.is_reply else "send"
        return f"comms.{self.name}.{action}"

    # -- shared flow -------------------------------------------------------

    async def prepare(self, intent: CommunicationIntent) -> PreparedMessage:
        """Build the message and compute what governance needs to judge it.

        Pure: no network, no writes, no clock mutation. Governance inspects the
        result, so it must be a value that cannot shift underneath the decision.
        """
        caps = self.capabilities()

        body = apply_disclosure(intent.body, self.identity)

        warnings: list[str] = []
        if intent.attachments and not caps.can_attach:
            warnings.append(
                f"{self.name} cannot carry attachments; {len(intent.attachments)} dropped"
            )
            body = body  # attachments are not appended to the body
        elif intent.attachments:
            warnings.append(
                f"{len(intent.attachments)} attachment(s) would be sent; "
                "attachment contents are visible to anyone who can read this thread"
            )

        if len(body.encode("utf-8")) > caps.max_body_bytes:
            warnings.append(
                f"body is {len(body.encode('utf-8'))} bytes, over the {caps.max_body_bytes} "
                "byte limit for this channel"
            )

        # Compute the refusal *now* so a human approving the message sees why it
        # would be refused, rather than approving something that then fails.
        reason = outbound_refusal_reason(
            contact=intent.recipient,
            is_reply=intent.is_reply,
            ledger=self.ledger,
            mind_id=self._ledger_key,
            limits=self.limits,
            opted_out=self.optouts.is_opted_out(
                relationship_id=intent.recipient.relationship_id,
                handle=intent.recipient.handle,
            ),
        )
        requires: list[str] = []
        if reason:
            requires.append(reason)

        if intent.recipient.boundaries:
            warnings.append(
                "boundaries set for this contact: " + "; ".join(intent.recipient.boundaries)
            )

        return PreparedMessage(
            channel=self.name,
            capability=self._capability_for(intent),
            recipient_name=intent.recipient.display_name,
            recipient_handle=intent.recipient.handle,
            subject=intent.subject,
            body=body,
            is_reply=intent.is_reply,
            requires_approval_because=requires,
            estimated_cost_usd=caps.unit_cost_usd if caps.metered else 0.0,
            warnings=warnings,
            trigger=intent.trigger or ("reply" if intent.is_reply else "manual"),
            trigger_ref=intent.trigger_ref,
            reply_to_message_id=intent.reply_to_message_id,
        )

    async def send(self, approved: ApprovedCommunication) -> DeliveryReceipt:
        """Deliver an approved message.

        Re-checks the floors immediately before handing anything to a provider.
        Not redundant: `prepare()` and `send()` are separated by a governance
        round-trip that can involve a human, and a person may have asked to be
        left alone in that window.
        """
        prepared = approved.prepared

        if prepared.channel != self.name:
            return DeliveryReceipt(
                channel=self.name,
                status=DeliveryStatus.FAILED,
                error=f"prepared for channel {prepared.channel!r}, sent to {self.name!r}",
            )

        # The message must still be the one that was approved. A frozen dataclass
        # cannot change in-process, but an approval that was persisted and reloaded
        # — a human-approved message can wait in a queue for hours — could have
        # been edited in storage.
        if not approved.verify_intact():
            logger.error(
                "channel %s refused a send: approved message no longer matches its digest",
                self.name,
            )
            return DeliveryReceipt(
                channel=self.name,
                status=DeliveryStatus.FAILED,
                error="message changed after approval; refusing to send an unapproved body",
                disclosed=is_disclosed(prepared.body),
            )

        # Disclosure: structural, not conventional. A bug upstream becomes a loud
        # failure rather than an undisclosed message reaching a human.
        assert_disclosed(prepared.body, self.identity)

        try:
            assert_can_send(
                contact=approved.contact,
                is_reply=prepared.is_reply,
                ledger=self.ledger,
                mind_id=self._ledger_key,
                limits=self.limits,
                opted_out=self.optouts.is_opted_out(
                    relationship_id=approved.contact.relationship_id,
                    handle=prepared.recipient_handle,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - a floor refusal is a refusal
            logger.warning("channel %s refused a send: %s", self.name, exc)
            return DeliveryReceipt(
                channel=self.name,
                status=DeliveryStatus.FAILED,
                error=str(exc),
                disclosed=True,
            )

        receipt = await self._deliver(approved)

        if receipt.status is DeliveryStatus.SENT and not prepared.is_reply:
            # Only initiated messages count against the weekly cap: answering
            # someone who wrote first is not outreach. Keyed on the relationship,
            # not the handle, so the cap follows the person across addresses.
            #
            # The trigger travels with it so the receipt can answer "why did this
            # being contact me?", and `trigger_ref` is the idempotence key that stops
            # proactive outreach repeating itself on every planning pass.
            self.ledger.record(
                mind_id=self._ledger_key,
                relationship_id=approved.contact.relationship_id,
                channel=self.name,
                at=receipt.sent_at,
                trigger=prepared.trigger,
                trigger_ref=prepared.trigger_ref,
            )

        receipt.disclosed = is_disclosed(prepared.body)
        return receipt

    @property
    def _ledger_key(self) -> str:
        """Identifies the Mind in the outbound ledger.

        Falls back to the channel address when no Mind id was supplied, which is
        the case for a standalone channel in a test. Two Minds must never share a
        ledger key, or one Mind's outreach would consume the other's allowance.
        """
        return self.mind_id or f"channel:{self.address}"


    # -- read --------------------------------------------------------------

    async def receive(self, since: Optional[datetime] = None) -> list[InboundEvent]:
        """Inbound events. R0: reading changes nothing outside the container."""
        if not self.capabilities().can_receive:
            return []
        return await self._fetch_inbound(since)

    async def get_thread(self, thread_id: str) -> Optional[ConversationThread]:
        if not self.capabilities().can_reply_in_thread:
            return None
        return await self._fetch_thread(thread_id)

    async def _fetch_thread(self, thread_id: str) -> Optional[ConversationThread]:
        return None

    async def sync_contacts(self) -> list[ExternalContact]:
        """Discovered contacts. Never grants contactability by itself."""
        return await self._discover_contacts()

    async def _discover_contacts(self) -> list[ExternalContact]:
        return []
