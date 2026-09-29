"""Telegram channel via the Bot API.

Telegram is the easiest real channel to stand up — a bot token from @BotFather is
all an administrator needs, no business verification, no phone number — which is
why it is the second channel after email.

It also has the property that makes it the *most* honest channel to start with:
**a bot cannot message a user who has not started the chat.** The platform
enforces the consent model that `DIGITAL_PRESENCE.md` §6 asks for, so
`comms.telegram.send` is R2 rather than R3 — every reachable chat is one where
the person made contact first.

The check is duplicated in `ContactRef` anyway. A platform guarantee is a reason
to be confident, not a reason to skip the check: the platform's rule can change,
and our fail-closed default must not depend on someone else's.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .adapter import BaseChannel
from .base import (
    ApprovedCommunication,
    ChannelCapabilities,
    ChannelDeliveryError,
    ChannelUnavailableError,
    ConversationThread,
    DeliveryReceipt,
    DeliveryStatus,
    ExternalContact,
    InboundEvent,
)

logger = logging.getLogger(__name__)

API_ROOT = "https://api.telegram.org"
REQUEST_TIMEOUT_S = 30
#: Bot API hard limit on a text message.
MAX_MESSAGE_CHARS = 4096
#: Server-side cap on one `getUpdates` page.
MAX_UPDATES_PER_POLL = 100


class TelegramChannel(BaseChannel):
    """A Mind's own Telegram bot identity."""

    name = "telegram"

    def __init__(
        self,
        *,
        bot_token: str,
        bot_username: str = "",
        **kwargs,
    ):
        super().__init__(
            address=bot_username or "telegram-bot",
            display_name=bot_username or "Genesis Mind",
            **kwargs,
        )
        self.bot_token = bot_token
        self.bot_username = bot_username
        #: Highest update_id we have acknowledged. In memory, so a restart
        #: re-reads recent updates; deduplication by `provider_message_id` is what
        #: makes that harmless, and a durable offset belongs with the inbound
        #: event store rather than here.
        self._offset: Optional[int] = None

    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            can_receive=True,
            can_send=bool(self.bot_token),
            can_reply_in_thread=True,
            can_attach=True,
            # The Bot API is free to use.
            metered=False,
            unit_cost_usd=0.0,
            # Telegram counts UTF-16 code units, and a message over the limit is
            # rejected outright rather than truncated.
            max_body_bytes=MAX_MESSAGE_CHARS * 4,
            max_attachments=10,
            supports_disclosure=True,
            confirms_delivery=True,
        )

    # -- http --------------------------------------------------------------

    async def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Call a Bot API method, translating failures into channel errors.

        Telegram signals application errors with HTTP 200 plus `ok: false`, so
        checking the status code alone would treat a rejection as a success — the
        same shape as the sandbox reading `rc=0` off a container that never
        started.
        """
        import httpx

        if not self.bot_token:
            raise ChannelUnavailableError("telegram is not configured: bot token is required")

        url = f"{API_ROOT}/bot{self.bot_token}/{method}"
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
                response = await client.post(url, json=payload)
        except Exception as exc:  # noqa: BLE001 - network failure is unavailability
            raise ChannelUnavailableError(f"telegram unreachable: {exc}") from exc

        try:
            body = response.json()
        except Exception as exc:  # noqa: BLE001
            raise ChannelDeliveryError(
                f"telegram returned a non-JSON response ({response.status_code})"
            ) from exc

        if not body.get("ok"):
            description = str(body.get("description") or "unknown error")
            # 403 "bot can't initiate conversation with a user" is the platform's
            # consent rule, and it should read as a policy refusal rather than a
            # transport fault, because that is what it is.
            if "can't initiate conversation" in description or "chat not found" in description:
                raise ChannelUnavailableError(
                    f"telegram refused: {description}. A bot may only message a user who "
                    "has started the chat, which is the platform enforcing consent."
                )
            raise ChannelDeliveryError(f"telegram API error: {description}")

        return body.get("result") or {}

    # -- send --------------------------------------------------------------

    async def _deliver(self, approved: ApprovedCommunication) -> DeliveryReceipt:
        prepared = approved.prepared

        payload: dict[str, Any] = {
            "chat_id": prepared.recipient_handle,
            "text": prepared.body,
        }
        if prepared.is_reply:
            reply_to = getattr(approved, "reply_to_message_id", None)
            if reply_to:
                payload["reply_to_message_id"] = reply_to

        result = await self._call("sendMessage", payload)

        # A `message_id` is Telegram confirming the message exists. Without one we
        # cannot claim delivery, so we say so.
        message_id = result.get("message_id")
        return DeliveryReceipt(
            channel=self.name,
            status=DeliveryStatus.SENT if message_id else DeliveryStatus.UNKNOWN,
            provider_message_id=str(message_id) if message_id else None,
            provider_response="accepted" if message_id else "accepted without a message id",
            cost_usd=0.0,
        )

    # -- receive -----------------------------------------------------------

    async def _fetch_inbound(self, since: Optional[datetime]) -> list[InboundEvent]:
        payload: dict[str, Any] = {"limit": MAX_UPDATES_PER_POLL, "timeout": 0}
        if self._offset is not None:
            payload["offset"] = self._offset

        updates = await self._call("getUpdates", payload)
        if not isinstance(updates, list):
            return []

        events: list[InboundEvent] = []
        for update in updates:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                # Acknowledge so the next poll does not repeat it.
                self._offset = max(self._offset or 0, update_id + 1)

            event = self._to_event(update)
            if event is not None and (since is None or event.received_at >= since):
                events.append(event)

        return events

    def _to_event(self, update: dict[str, Any]) -> Optional[InboundEvent]:
        """Normalise an update.

        Only `message` is handled. `edited_message`, `callback_query` and the
        rest are deliberately ignored rather than half-handled: an unhandled
        update type that silently becomes an empty event is worse than one that
        is clearly not supported yet.
        """
        message = update.get("message")
        if not isinstance(message, dict):
            return None

        chat = message.get("chat") or {}
        sender = message.get("from") or {}
        text = message.get("text") or message.get("caption") or ""

        received_at = datetime.now(timezone.utc)
        if isinstance(message.get("date"), int):
            received_at = datetime.fromtimestamp(message["date"], tz=timezone.utc)

        chat_id = chat.get("id")
        if chat_id is None:
            return None

        return InboundEvent(
            channel=self.name,
            provider_message_id=str(message.get("message_id") or update.get("update_id") or ""),
            sender_handle=str(chat_id),
            sender_name=" ".join(
                part for part in (sender.get("first_name"), sender.get("last_name")) if part
            )
            or sender.get("username")
            or str(chat_id),
            subject=None,
            body=text[:50_000],
            thread_id=str(chat_id),
            received_at=received_at,
            # The platform vouches that the sender controls the account; it does
            # not vouch that they are who they claim to be in text.
            sender_verified=True,
            metadata={
                "username": sender.get("username"),
                "chat_type": chat.get("type"),
                "update_id": update.get("update_id"),
            },
        )

    # -- threads and contacts ---------------------------------------------

    async def _fetch_thread(self, thread_id: str) -> Optional[ConversationThread]:
        """A Telegram chat is the thread.

        `getChat` costs a call and returns metadata rather than message history —
        the Bot API does not expose history. So this reports the participant only,
        and `message_count` stays 0 rather than being invented from something
        else.
        """
        try:
            chat = await self._call("getChat", {"chat_id": thread_id})
        except Exception as exc:  # noqa: BLE001
            logger.debug("telegram getChat failed for %s: %s", thread_id, exc)
            return None

        title = chat.get("title") or chat.get("username") or str(thread_id)
        return ConversationThread(
            thread_id=thread_id,
            channel=self.name,
            subject=title,
            participants=[title],
            message_count=0,
            last_activity=None,
        )

    async def _discover_contacts(self) -> list[ExternalContact]:
        """Chats the bot has seen, from recent updates.

        Everyone here started the chat, which is why the platform guarantees
        contactability — but the `consent_source` still has to be recorded against
        the contact before the floors will allow an initiated message, because
        `ContactRef` does not trust the platform on our behalf.
        """
        try:
            updates = await self._call("getUpdates", {"limit": MAX_UPDATES_PER_POLL, "timeout": 0})
        except Exception as exc:  # noqa: BLE001
            logger.debug("telegram contact sync failed: %s", exc)
            return []

        seen: dict[str, ExternalContact] = {}
        for update in updates if isinstance(updates, list) else []:
            message = update.get("message") or {}
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            if chat_id is None:
                continue
            handle = str(chat_id)
            if handle in seen:
                continue
            sender = message.get("from") or {}
            seen[handle] = ExternalContact(
                handle=handle,
                display_name=" ".join(
                    part for part in (sender.get("first_name"), sender.get("last_name")) if part
                )
                or chat.get("title")
                or handle,
                channel=self.name,
                # They messaged the bot, so the handle is real. That is not the
                # same as permission to be contacted, and it does not set it.
                verified=True,
            )
        return list(seen.values())
