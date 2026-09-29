"""In-memory channel for tests and dry runs.

Exists so the floors — disclosure, quiet hours, weekly caps, opt-out, approval
integrity — can be tested against the same code path a real provider uses,
rather than against a mock that reimplements them. A test double that bypasses
the behaviour it is meant to verify proves nothing.

It also gives the UI something to render before a real provider is configured, so
the approval card can be exercised without anyone's credentials.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from .adapter import BaseChannel
from .base import (
    ApprovedCommunication,
    ChannelCapabilities,
    ConversationThread,
    DeliveryReceipt,
    DeliveryStatus,
    ExternalContact,
    InboundEvent,
)


class FakeChannel(BaseChannel):
    """A channel that records instead of delivering."""

    name = "fake"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #: Every message that reached `_deliver`, in order.
        self.sent: list[ApprovedCommunication] = []
        self._inbound: list[InboundEvent] = []
        self._contacts: list[ExternalContact] = []
        self._threads: dict[str, ConversationThread] = {}
        #: Set to raise from `_deliver`, to test provider failure paths.
        self.fail_next_with: Optional[Exception] = None
        #: Set to make `_deliver` report UNKNOWN, which some providers do.
        self.report_unknown_delivery: bool = False

    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            can_receive=True,
            can_send=True,
            can_reply_in_thread=True,
            can_attach=True,
            metered=False,
            unit_cost_usd=0.0,
            supports_disclosure=True,
            confirms_delivery=True,
        )

    # -- test helpers ------------------------------------------------------

    def inject(self, event: InboundEvent) -> None:
        """Queue an inbound event for the next `receive()`."""
        self._inbound.append(event)

    def add_contact(self, contact: ExternalContact) -> None:
        self._contacts.append(contact)

    def add_thread(self, thread: ConversationThread) -> None:
        self._threads[thread.thread_id] = thread

    # -- provider side -----------------------------------------------------

    async def _deliver(self, approved: ApprovedCommunication) -> DeliveryReceipt:
        if self.fail_next_with is not None:
            error = self.fail_next_with
            self.fail_next_with = None
            raise error

        self.sent.append(approved)

        if self.report_unknown_delivery:
            return DeliveryReceipt(
                channel=self.name,
                status=DeliveryStatus.UNKNOWN,
                provider_response="accepted, no confirmation available",
            )

        return DeliveryReceipt(
            channel=self.name,
            status=DeliveryStatus.SENT,
            provider_message_id=f"fake-{uuid.uuid4().hex[:12]}",
            provider_response="recorded in memory",
            cost_usd=0.0,
        )

    async def _fetch_inbound(self, since: Optional[datetime]) -> list[InboundEvent]:
        events = [e for e in self._inbound if since is None or e.received_at >= since]
        self._inbound = [e for e in self._inbound if e not in events]
        return events

    async def _fetch_thread(self, thread_id: str) -> Optional[ConversationThread]:
        return self._threads.get(thread_id)

    async def _discover_contacts(self) -> list[ExternalContact]:
        return list(self._contacts)
