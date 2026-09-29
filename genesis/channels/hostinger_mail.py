"""Hostinger Mail API channel.

The recommended email provider. Hostinger runs a Mail API **separate from their
hosting API** — different base URL, different tokens, different SDK. The hosting
API *manages mailboxes*; this one **reads and sends mail**, which is the part a
Mind needs.

Why this over the IMAP/SMTP `EmailChannel`:

* **Its own token, scoped down.** A token is limited to one order and optionally
  to specific mailboxes, with permissions split between SMTP/IMAP actions and
  webhook management. That is the same shape as our capability model, and it means
  the credential a Mind uses cannot reach anything it was not granted.
* **Threading is done by the provider.** `inReplyTo` makes the API copy the
  original's message id and references into the new message and flag the source as
  answered, so conversations thread correctly without us assembling headers — and
  header assembly is exactly where a reply silently stops being a reply.
* **A provider-side allow list.** When non-empty, mail can only go to listed
  addresses or domains. That turns "the agent emailed the wrong person" into a
  rejected send, and unlike our own floors it holds even if our code is wrong.
* **Webhooks**, so reacting to new mail does not need a poll loop.

## Which endpoint paths are verified

`POST /{version}/mailboxes/{mailboxResourceId}/send` is **confirmed** — quoted
verbatim in Hostinger's SDK documentation.

The read paths are **inferred** from a documented convention that is explicit:
*"The mailbox resource ID comes first. Every operation except `getCurrentAccount`
is scoped to one mailbox; message operations take the folder next."* The class
names are documented; their exact paths are not.

So every path is overridable — a wrong guess is a config change, not a release —
and `verify()` checks each one against a real token and reports which resolved.
That is the difference between "written" and "works", and it is one call rather
than a guess.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .adapter import BaseChannel
from .base import (
    ApprovedCommunication,
    ChannelCapabilities,
    ChannelUnavailableError,
    ConversationThread,
    DeliveryReceipt,
    DeliveryStatus,
    ExternalContact,
    InboundEvent,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.mail.hostinger.com"
DEFAULT_API_VERSION = "v1"
REQUEST_TIMEOUT_S = 30

#: Page size for message reads. The API caps this at 100 and defaults to 25.
#: Deliberately below the cap: reading 100 messages in one call pushes a large
#: unreviewed block into memory, and a second page is cheap.
PAGE_SIZE = 25

#: Hard stop on pagination. A mailbox with years of history must not be walked on
#: the first read — not for cost, but because ingesting an unbounded archive is a
#: memory decision nobody reviewed.
MAX_PAGES = 4

DEFAULT_LOOKBACK = timedelta(days=3)

#: Provider error codes translated into something an operator can act on. Anything
#: unlisted is surfaced with the provider's own text, which is more useful than a
#: paraphrase that drops the code.
_ACTIONABLE_CODES: dict[str, str] = {
    "ERR_MAILBOX_NOT_FOUND": (
        "the configured mailbox id does not exist, or this token cannot see it. "
        "Check the mailbox id and the token's mailbox scope."
    ),
    "ERR_UNAUTHORIZED": (
        "the token was rejected. Hostinger Mail tokens are separate from hosting "
        "tokens and are created under Agentic Mail -> API access."
    ),
    "ERR_FORBIDDEN": (
        "the token lacks the permission this call needs. Read and send are "
        "separate permissions chosen when the token is created."
    ),
    "ERR_QUOTA_EXCEEDED": "the mailbox is over its storage quota.",
    "ERR_RATE_LIMITED": "the API rate limit was hit. Back off rather than retrying.",
}


class HostingerMailError(ChannelUnavailableError):
    """A Mail API call failed, with the provider's own code preserved.

    Subclasses `ChannelUnavailableError` because every failure it raises means
    nothing was delivered — as opposed to a delivery failure, where the provider
    accepted the request and then failed it.
    """

    def __init__(self, message: str, *, code: str = "", status: int = 0):
        super().__init__(message)
        self.code = code
        self.status = status


class HostingerMailChannel(BaseChannel):
    """A mailbox on Hostinger Email, reached over the Mail API."""

    name = "email"

    def __init__(
        self,
        *,
        api_token: str,
        mailbox_id: str,
        address: str,
        display_name: str = "",
        base_url: str = DEFAULT_BASE_URL,
        api_version: str = DEFAULT_API_VERSION,
        lookback: timedelta = DEFAULT_LOOKBACK,
        folder: str = "INBOX",
        paths: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(address=address, display_name=display_name, **kwargs)
        self.api_token = api_token
        self.mailbox_id = mailbox_id
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_version = api_version or DEFAULT_API_VERSION
        self.lookback = lookback
        self.folder = folder
        self.paths = {**self.default_paths(), **(paths or {})}

    @staticmethod
    def default_paths() -> dict[str, str]:
        return {
            "account": "/api/{version}/account",
            "folders": "/api/{version}/mailboxes/{mailbox}/folders",
            "messages": "/api/{version}/mailboxes/{mailbox}/folders/{folder}/messages",
            "message": "/api/{version}/mailboxes/{mailbox}/folders/{folder}/messages/{uid}",
            "send": "/api/{version}/mailboxes/{mailbox}/send",
        }

    def _path(self, key: str, **values: str) -> str:
        return self.paths[key].format(
            version=self.api_version,
            mailbox=self.mailbox_id,
            folder=self.folder,
            **values,
        )

    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            can_receive=bool(self.api_token and self.mailbox_id),
            can_send=bool(self.api_token and self.mailbox_id),
            can_reply_in_thread=True,
            can_attach=True,
            # Email through the account's own plan. No per-message charge, and
            # unlike a bulk-sending service this is not a metered relay.
            metered=False,
            unit_cost_usd=0.0,
            max_body_bytes=5_000_000,
            max_attachments=20,
            supports_disclosure=True,
            # The API reports an accepted send; whether it lands is the
            # recipient's mail server's business. Claiming more would overstate.
            confirms_delivery=False,
        )

    # -- transport ---------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Call the Mail API and unwrap its envelope.

        Three things a naive `response.json()` would not do:

        * **Unwraps `data`.** The API wraps every payload, so returning the raw
          body would leak that detail into every caller.
        * **Reads `code`, not just the HTTP status.** Errors carry a
          machine-readable code alongside a human message. Branching on status
          alone collapses "token is scoped to another mailbox" into "403", which
          is the difference between a five-second fix and an hour.
        * **Translates the actionable codes.** An operator reading a log needs to
          know that a Mail token is not a hosting token.
        """
        import httpx

        if not self.api_token:
            raise HostingerMailError(
                "Hostinger Mail is not configured: an API token is required. "
                "Create one under Agentic Mail -> API access."
            )

        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
                response = await client.request(
                    method, url, params=params, json=json_body, headers=headers
                )
        except Exception as exc:  # noqa: BLE001 - a network failure is unavailability
            raise HostingerMailError(f"Hostinger Mail unreachable: {exc}") from exc

        try:
            body: dict[str, Any] = response.json() if response.content else {}
        except Exception:  # noqa: BLE001
            raise HostingerMailError(
                f"Hostinger Mail returned a non-JSON response ({response.status_code})",
                status=response.status_code,
            ) from None

        if response.status_code >= 400:
            code = str(body.get("code") or "")
            message = _ACTIONABLE_CODES.get(code) or str(
                body.get("error") or body.get("message") or f"HTTP {response.status_code}"
            )
            suffix = f" (code {code})" if code and code not in _ACTIONABLE_CODES else ""
            raise HostingerMailError(
                f"Hostinger Mail rejected the request: {message}{suffix}",
                code=code,
                status=response.status_code,
            )

        data = body.get("data")
        result: dict[str, Any] = data if isinstance(data, dict) else {}
        # Pagination travels *alongside* `data`, not inside it.
        pagination = body.get("pagination")
        if isinstance(pagination, dict):
            result["_pagination"] = pagination
        return result

    # -- send --------------------------------------------------------------

    async def _deliver(self, approved: ApprovedCommunication) -> DeliveryReceipt:
        prepared = approved.prepared

        payload: dict[str, Any] = {
            "to": [prepared.recipient_handle],
            "subject": prepared.subject or "(no subject)",
            "text": prepared.body,
        }

        # A reply is the same call with a reference attached. The API copies the
        # original's id and references across and flags the source as answered, so
        # threading is the provider's job rather than ours.
        if prepared.is_reply:
            in_reply_to = getattr(approved, "reply_to_message_id", None)
            if in_reply_to:
                payload["inReplyTo"] = in_reply_to

        result = await self._request("POST", self._path("send"), json_body=payload)

        message_id = result.get("messageId") or result.get("message_id") or result.get("id")
        return DeliveryReceipt(
            channel=self.name,
            status=DeliveryStatus.SENT if message_id else DeliveryStatus.UNKNOWN,
            provider_message_id=str(message_id) if message_id else None,
            provider_response="accepted by the Mail API",
            cost_usd=0.0,
        )

    # -- receive -----------------------------------------------------------

    async def _fetch_inbound(self, since: Optional[datetime]) -> list[InboundEvent]:
        cutoff = since or (datetime.now(timezone.utc) - self.lookback)

        events: list[InboundEvent] = []
        seen: set[str] = set()

        for page in range(1, MAX_PAGES + 1):
            result = await self._request(
                "GET",
                self._path("messages"),
                params={"page": page, "per_page": PAGE_SIZE},
            )

            messages = result.get("messages") or result.get("items") or []
            if not isinstance(messages, list) or not messages:
                break

            for message in messages:
                event = self._to_event(message)
                if event is None or event.provider_message_id in seen:
                    continue
                seen.add(event.provider_message_id)
                if event.received_at >= cutoff:
                    events.append(event)

            pagination = result.get("_pagination") or {}
            total_pages = pagination.get("totalPages") or pagination.get("total_pages")
            if not isinstance(total_pages, int) or page >= total_pages:
                break
            if page == MAX_PAGES:
                logger.info(
                    "hostinger mail: stopped after %d pages; older messages in %s were not read",
                    MAX_PAGES,
                    self.folder,
                )

        return events

    def _to_event(self, message: dict[str, Any]) -> Optional[InboundEvent]:
        """Normalise one provider message.

        Field names are read defensively. The envelope and the pagination keys are
        documented; a message's individual fields are not, and committing to one
        spelling per field would make a rename look like an empty mailbox. Reading
        several plausible spellings and defaulting to "absent" is the honest
        version of not knowing.
        """
        if not isinstance(message, dict):
            return None

        sender = message.get("from") or message.get("sender") or {}
        if isinstance(sender, str):
            sender_handle, sender_name = sender, ""
        else:
            sender_handle = str(
                sender.get("address") or sender.get("email") or sender.get("handle") or ""
            )
            sender_name = str(sender.get("name") or sender.get("display_name") or "")

        if not sender_handle:
            return None

        message_id = str(
            message.get("messageId")
            or message.get("message_id")
            or message.get("id")
            or message.get("uid")
            or ""
        )
        if not message_id:
            return None

        received_at = datetime.now(timezone.utc)
        for key in ("receivedAt", "received_at", "date", "timestamp"):
            raw = message.get(key)
            if isinstance(raw, str) and raw:
                try:
                    received_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    break
                except ValueError:
                    continue

        body = (
            message.get("text")
            or message.get("textBody")
            or message.get("plain")
            or message.get("snippet")
            or ""
        )

        in_reply_to = message.get("inReplyTo") or message.get("in_reply_to")
        references = message.get("references")

        return InboundEvent(
            channel=self.name,
            provider_message_id=message_id,
            sender_handle=sender_handle,
            sender_name=sender_name or sender_handle,
            subject=message.get("subject") or None,
            body=str(body)[:50_000],
            thread_id=str(references or in_reply_to or message.get("threadId") or "") or None,
            received_at=received_at,
            # The API authenticates *our* token, not the sender's identity.
            # Whether the From header is genuine is SPF/DKIM's question — the
            # provider's and the receiver's business, not something this adapter
            # can assert.
            sender_verified=False,
            metadata={"folder": self.folder, "to": message.get("to")},
        )

    # -- threads and contacts ---------------------------------------------

    async def _fetch_thread(self, thread_id: str) -> Optional[ConversationThread]:
        """Not supported.

        The API threads replies for us on send, but exposes no thread endpoint
        this adapter can rely on. Returning None keeps the caller honest rather
        than fabricating a participant list.
        """
        return None

    async def _discover_contacts(self) -> list[ExternalContact]:
        """Senders in the recent window.

        Not an address-book import. These arrive unverified and grant nothing:
        `ContactRef` still requires a recorded `consent_source` before the floors
        allow an initiated message, because having someone's address is not
        permission to write to them.
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

    # -- diagnostics -------------------------------------------------------

    async def verify(self) -> dict[str, Any]:
        """Check the token and each read path against the live API.

        Exists because the read paths are inferred rather than documented. Rather
        than hoping, an operator (or CI with a token in the environment) runs this
        and gets a per-path verdict. It returns a report instead of raising, so one
        wrong path does not hide the state of the others.
        """
        report: dict[str, Any] = {
            "base_url": self.base_url,
            "mailbox_id": self.mailbox_id,
            "paths": {},
        }

        for key, params in (
            ("account", None),
            ("folders", None),
            ("messages", {"page": 1, "per_page": 1}),
        ):
            path = self._path(key)
            try:
                await self._request("GET", path, params=params)
                report["paths"][key] = {"ok": True, "path": path}
            except HostingerMailError as exc:
                report["paths"][key] = {
                    "ok": False,
                    "path": path,
                    "status": exc.status,
                    "code": exc.code,
                    "error": str(exc),
                }
            except Exception as exc:  # noqa: BLE001
                report["paths"][key] = {"ok": False, "path": path, "error": str(exc)}

        # `send` is deliberately not exercised: verifying it would send a real
        # email to a real person.
        report["paths"]["send"] = {
            "ok": None,
            "path": self._path("send"),
            "note": "not exercised - verifying it would send a real message",
        }

        report["ok"] = all(
            entry.get("ok") is not False for entry in report["paths"].values()
        )
        return report
