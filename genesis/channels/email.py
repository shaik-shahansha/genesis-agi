"""Email channel: the Mind's own address, via IMAP and SMTP.

Standard library only — `imaplib`, `smtplib`, `email` — because adding a
dependency for what the stdlib does well would be the wrong trade for the first
channel. Both protocols are blocking, so every call runs in a worker thread
rather than stalling the event loop that the rest of the Mind shares.

The administrator supplies the credentials; the Mind never holds them. This is
the single-tenant path described in `docs/v3/DIGITAL_PRESENCE.md` §7.

Deliberately absent: **sending is the only thing that changes the world, and it
can only happen through `BaseChannel.send`**, which requires an
`ApprovedCommunication`. There is no `send_raw`, no convenience method that takes
a string, and no path from a model's output to a mailbox that does not pass
through governance.
"""

from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import smtplib
import ssl
import uuid
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, parseaddr
from typing import Optional

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

#: How far back a first read looks. A Mind introduced to a mailbox with years of
#: history should not ingest all of it on day one — that would be a huge,
#: unreviewed dump into memory, and almost none of it is addressed to the Mind.
DEFAULT_LOOKBACK = timedelta(days=3)

#: Cap on messages returned by one read, for the same reason.
DEFAULT_FETCH_LIMIT = 50


def _decode(value: Optional[str]) -> str:
    """Decode a possibly-encoded mail header.

    `make_header` is the only correct way to do this: headers can mix charsets
    within one value, and a naive `.decode()` throws on exactly the international
    mail most likely to matter.
    """
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001 - a malformed header must not break a read
        return str(value)


def _plain_body(message: email.message.Message) -> str:
    """Extract a plain-text body.

    Prefers `text/plain` and falls back to stripping tags from `text/html`.
    Attachments are not decoded — the body is what the Mind reads, and decoding
    arbitrary attachments is a parsing attack surface that belongs behind the
    sandbox, not in a channel adapter.
    """
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(
                part.get("Content-Disposition") or ""
            ):
                try:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
                except Exception:  # noqa: BLE001
                    continue
        for part in message.walk():
            if part.get_content_type() == "text/html":
                try:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    return _strip_tags(payload.decode(charset, errors="replace"))
                except Exception:  # noqa: BLE001
                    continue
        return ""

    try:
        payload = message.get_payload(decode=True) or b""
        charset = message.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        return _strip_tags(text) if message.get_content_type() == "text/html" else text
    except Exception:  # noqa: BLE001
        return ""


def _strip_tags(html: str) -> str:
    """Crude HTML-to-text.

    Not a parser, and not trying to be: this is for reading, and the Mind does not
    execute or render what it reads. A real renderer belongs nowhere near
    untrusted mail.
    """
    import re

    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"&amp;?", "&", text)
    text = re.sub(r"&lt;?", "<", text)
    text = re.sub(r"&gt;?", ">", text)
    return re.sub(r"\s{2,}", " ", text).strip()


class EmailChannel(BaseChannel):
    """A Mind's own email address."""

    name = "email"

    def __init__(
        self,
        *,
        address: str,
        display_name: str = "",
        imap_host: str = "",
        imap_port: int = 993,
        smtp_host: str = "",
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
        lookback: timedelta = DEFAULT_LOOKBACK,
        fetch_limit: int = DEFAULT_FETCH_LIMIT,
        **kwargs,
    ):
        super().__init__(address=address, display_name=display_name, **kwargs)
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username or address
        self.password = password
        self.use_tls = use_tls
        self.lookback = lookback
        self.fetch_limit = fetch_limit

    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            can_receive=bool(self.imap_host and self.password),
            can_send=bool(self.smtp_host and self.password),
            can_reply_in_thread=True,
            can_attach=True,
            # SMTP is the administrator's own account. No per-message charge, even
            # though a bulk-sending service would be metered — and this adapter is
            # not usable for bulk sending, because `comms.broadcast` is prohibited.
            metered=False,
            unit_cost_usd=0.0,
            max_body_bytes=1_000_000,
            max_attachments=10,
            supports_disclosure=True,
            # SMTP reports acceptance by a relay, not arrival. Claiming more would
            # be a receipt that overstates delivery.
            confirms_delivery=False,
        )

    # -- send --------------------------------------------------------------

    async def _deliver(self, approved: ApprovedCommunication) -> DeliveryReceipt:
        prepared = approved.prepared

        if not self.capabilities().can_send:
            raise ChannelUnavailableError(
                "email sending is not configured: SMTP host and password are required"
            )

        message = EmailMessage()
        message["From"] = formataddr((self.display_name, self.address))
        message["To"] = prepared.recipient_handle
        message["Subject"] = prepared.subject or "(no subject)"
        message["Message-ID"] = make_msgid(domain=self.address.split("@")[-1] or None)
        if prepared.is_reply and prepared.warnings:
            logger.debug("replying; %s", "; ".join(prepared.warnings))
        message.set_content(prepared.body)

        try:
            await asyncio.to_thread(self._smtp_send, message)
        except ChannelUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ChannelDeliveryError(f"SMTP send failed: {exc}") from exc

        return DeliveryReceipt(
            channel=self.name,
            status=DeliveryStatus.SENT,
            provider_message_id=message["Message-ID"],
            provider_response="accepted by the relay",
            cost_usd=0.0,
        )

    def _smtp_send(self, message: EmailMessage) -> None:
        """Blocking SMTP. Runs in a worker thread."""
        context = ssl.create_default_context()
        try:
            if self.smtp_port == 465:
                # Implicit TLS.
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context, timeout=30) as server:
                    server.login(self.username, self.password)
                    server.send_message(message)
                return

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(message)
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPConnectError) as exc:
            # These are configuration and reachability problems, not delivery
            # failures: nothing was attempted.
            raise ChannelUnavailableError(f"SMTP unavailable: {exc}") from exc

    # -- receive -----------------------------------------------------------

    async def _fetch_inbound(self, since: Optional[datetime]) -> list[InboundEvent]:
        if not self.capabilities().can_receive:
            raise ChannelUnavailableError(
                "email reading is not configured: IMAP host and password are required"
            )

        cutoff = since or (datetime.now() - self.lookback)

        try:
            raw_messages = await asyncio.to_thread(self._imap_fetch, cutoff)
        except ChannelUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ChannelUnavailableError(f"IMAP read failed: {exc}") from exc

        return [event for event in (self._to_event(m) for m in raw_messages) if event is not None]

    def _imap_fetch(self, cutoff: datetime) -> list[email.message.Message]:
        """Blocking IMAP fetch. Runs in a worker thread.

        Search is by date, then filtered in-process, because IMAP `SINCE` has
        day granularity and would return more than asked for.
        """
        messages: list[email.message.Message] = []
        try:
            with imaplib.IMAP4_SSL(self.imap_host, self.imap_port, timeout=30) as client:
                client.login(self.username, self.password)
                client.select("INBOX", readonly=True)

                since_str = cutoff.strftime("%d-%b-%Y")
                status, data = client.search(None, f'(SINCE "{since_str}")')
                if status != "OK":
                    raise ChannelUnavailableError(f"IMAP search failed with status {status}")

                uids = (data[0] or b"").split()
                # Newest last; take the tail so a busy mailbox yields recent mail.
                for uid in uids[-self.fetch_limit :]:
                    status, payload = client.fetch(uid, "(RFC822)")
                    if status != "OK" or not payload or not isinstance(payload[0], tuple):
                        continue
                    messages.append(email.message_from_bytes(payload[0][1]))
        except imaplib.IMAP4.error as exc:
            raise ChannelUnavailableError(f"IMAP unavailable: {exc}") from exc

        return messages

    def _to_event(self, message: email.message.Message) -> Optional[InboundEvent]:
        try:
            sender_name, sender_handle = parseaddr(_decode(message.get("From")))
            if not sender_handle:
                return None

            date_header = message.get("Date")
            received_at = datetime.now()
            if date_header:
                try:
                    from email.utils import parsedate_to_datetime

                    parsed = parsedate_to_datetime(date_header)
                    if parsed is not None:
                        received_at = parsed
                except Exception:  # noqa: BLE001 - a bad Date header is not fatal
                    pass

            return InboundEvent(
                channel=self.name,
                provider_message_id=_decode(message.get("Message-ID")) or str(uuid.uuid4()),
                sender_handle=sender_handle,
                sender_name=sender_name or sender_handle,
                subject=_decode(message.get("Subject")),
                body=_plain_body(message)[:50_000],
                thread_id=_decode(message.get("References") or message.get("In-Reply-To")) or None,
                received_at=received_at,
                # SMTP gives no sender authentication. `From` is trivially forged,
                # so nothing here may be treated as verified — SPF/DKIM would be
                # needed, and this adapter does not check them.
                sender_verified=False,
                metadata={"to": _decode(message.get("To"))},
            )
        except Exception as exc:  # noqa: BLE001 - one bad message must not stop a read
            logger.warning("skipping an unparseable email: %s", exc)
            return None

    # -- threads and contacts ---------------------------------------------

    async def _fetch_thread(self, thread_id: str) -> Optional[ConversationThread]:
        """IMAP threads are server-dependent and inconsistent.

        Returning None is honest: the receipt carries the message id, and the
        thread can be reconstructed from stored inbound events, which is a
        better source than asking each provider to implement threading
        differently.
        """
        return None

    async def _discover_contacts(self) -> list[ExternalContact]:
        """Discover senders from the recent window.

        Not an address-book import. Importing a contact list into a system that
        can subsequently act on it is how a Mind acquires hundreds of people it
        has no permission to contact — so these arrive with `verified=False` and
        grant nothing until a `consent_source` is recorded against them.
        """
        events = await self._fetch_inbound(since=None)
        seen: dict[str, ExternalContact] = {}
        for event in events:
            if event.sender_handle and event.sender_handle not in seen:
                seen[event.sender_handle] = ExternalContact(
                    handle=event.sender_handle,
                    display_name=event.sender_name,
                    channel=self.name,
                    verified=False,
                )
        return list(seen.values())
