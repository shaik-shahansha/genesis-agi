"""Ringg AI voice channel.

Ringg runs the voice assistant. The Mind decides *who* to call and *what context*
to give it; Ringg's assistant speaks, using a prompt and voice configured in
Ringg's dashboard. The Mind does not synthesise speech and does not see the words
in real time — it starts a call and reads the result.

That is a genuinely different shape from every other channel here, and pretending
otherwise would produce a lie in the receipts:

* **The prepared body is not sent.** `prepare()` exists and runs (so the floors
  apply, the disclosure is composed, and a human can read what the call is *for*),
  but the text that reaches Ringg is `custom_args_values` — structured context for
  the assistant's prompt, not a script. A receipt from this channel therefore
  cannot claim the body was delivered, and does not.
* **`send()` starts a call, it does not deliver a message.** The receipt carries a
  `call_id`. Delivery means "the call was placed", not "the recipient heard this".
  The transcript arrives later by webhook or from call history.
* **Disclosure cannot be verified.** This is the important one — see below.

## The disclosure problem, stated plainly

Every other channel can prove it discloses, because the adapter composes the
disclosure into the body it sends. Ringg cannot: the words spoken come from a
prompt living in Ringg's dashboard, and no API returns that prompt's text.

An undisclosed voice channel is the one outcome this product must not ship. A
phone call is the most human-seeming thing a Mind can do, and a person who
believes they are talking to a person has been deceived regardless of intent.

So the rule is the same as everywhere else — a channel that cannot demonstrate
disclosure is not enabled — with one honest difference: here the evidence is a
human's explicit assertion rather than a capability flag. The channel registers
**disabled** until the operator sets `disclosure_confirmed`, the assertion is
recorded in the channel's status, and the docs say it is an assertion.

`DISCLOSURE_ARG` exists to make the assertion cheap to honour: the disclosure text
is always passed as a `custom_args_values` entry, so an assistant prompt written
to speak `@{{ai_disclosure}}` discloses by construction. What we cannot do is
prove the prompt does.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
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
    utcnow,
)
from .disclosure import compose_disclosure

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://prod-api.ringg.ai/ca/api/v0"
REQUEST_TIMEOUT_S = 30

#: The `custom_args_values` key the disclosure is always passed under, so an
#: assistant prompt can reference `@{{ai_disclosure}}` and disclose without the
#: operator composing it by hand each time.
DISCLOSURE_ARG = "ai_disclosure"

#: Ringg's own pagination cap.
MAX_PAGE_SIZE = 100


class RinggVoiceError(ChannelUnavailableError):
    """A Ringg API call failed.

    Subclasses `ChannelUnavailableError` because a failure here means no call was
    placed.
    """

    def __init__(self, message: str, *, code: str = "", status: int = 0):
        super().__init__(message)
        self.code = code
        self.status = status


class RinggVoiceChannel(BaseChannel):
    """Outbound voice calls via a Ringg assistant."""

    name = "voice"

    def __init__(
        self,
        *,
        api_key: str,
        agent_id: str,
        from_number_id: str,
        phone_number: str = "",
        display_name: str = "",
        base_url: str = DEFAULT_BASE_URL,
        disclosure_confirmed: bool = False,
        callback_url: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            address=phone_number or from_number_id,
            display_name=display_name or "Genesis Mind",
            **kwargs,
        )
        self.api_key = api_key
        self.agent_id = agent_id
        self.from_number_id = from_number_id
        self.phone_number = phone_number
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.disclosure_confirmed = disclosure_confirmed
        self.callback_url = callback_url

    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            # Inbound calls arrive as webhooks, which is a delivery mechanism this
            # adapter does not implement yet. Saying `False` is the honest answer:
            # a Mind that cannot answer the phone should not appear to.
            can_receive=False,
            can_send=bool(self.api_key and self.agent_id and self.from_number_id),
            can_reply_in_thread=False,
            can_attach=False,
            can_voice=True,
            # Telephony is metered per minute at the provider. We do not know the
            # rate without a plan, so the cost is stated as zero and the *fact*
            # that it is metered is carried here, which is what governance needs
            # to require a budget check rather than an exact figure.
            metered=True,
            unit_cost_usd=0.0,
            max_body_bytes=20_000,
            max_attachments=0,
            # Not a capability of the wire — a capability of the *assistant*, and
            # one we cannot inspect. `registry` calls this method to decide whether
            # to enable the channel, so reporting the assertion here is what makes
            # an unasserted voice channel refuse to register.
            supports_disclosure=bool(self.disclosure_confirmed),
            confirms_delivery=True,
        )

    # -- transport ---------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        import httpx

        if not self.api_key:
            raise RinggVoiceError(
                "Ringg is not configured: an API key is required (Settings -> API Key "
                "in the Ringg dashboard; it is shown once)."
            )

        url = f"{self.base_url}{path}"
        headers = {"X-API-KEY": self.api_key, "Accept": "application/json"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
                response = await client.request(method, url, json=json_body, headers=headers)
        except Exception as exc:  # noqa: BLE001
            raise RinggVoiceError(f"Ringg unreachable: {exc}") from exc

        try:
            body: dict[str, Any] = response.json() if response.content else {}
        except Exception:  # noqa: BLE001
            raise RinggVoiceError(
                f"Ringg returned a non-JSON response ({response.status_code})",
                status=response.status_code,
            ) from None

        if response.status_code >= 400:
            error = body.get("error") if isinstance(body.get("error"), dict) else {}
            code = str(error.get("code") or "")
            message = str(error.get("message") or body.get("message") or f"HTTP {response.status_code}")
            # 401 here almost always means the key was regenerated, because
            # regenerating immediately revokes the previous key.
            if response.status_code == 401:
                message = (
                    "Ringg rejected the API key. Regenerating a key revokes the old "
                    "one immediately, so check whether it was rotated."
                )
            raise RinggVoiceError(f"Ringg rejected the request: {message}", code=code, status=response.status_code)

        data = body.get("data")
        return data if isinstance(data, dict) else body

    # -- send --------------------------------------------------------------

    async def _deliver(self, approved: ApprovedCommunication) -> DeliveryReceipt:
        """Place the call.

        Note what is *not* sent: `prepared.body`. It exists, the floors ran
        against it, and a human read it when approving — but the words spoken come
        from the Ringg assistant's prompt. Sending the body as a script would imply
        the Mind delivers its own sentences over the phone, which it does not.
        """

        prepared = approved.prepared

        # The disclosure is passed to the assistant as a variable, so a prompt
        # written to speak it discloses without the operator composing anything.
        # This is the *whole* mitigation available to us: we cannot verify the prompt.
        custom_args: dict[str, Any] = {
            DISCLOSURE_ARG: compose_disclosure(self.identity),
            "call_reason": prepared.subject or approved.contact.display_name,
            "recipient_name": approved.contact.display_name,
        }
        if approved.correlation_id:
            custom_args["correlation_id"] = approved.correlation_id

        payload: dict[str, Any] = {
            "name": approved.contact.display_name,
            "mobile_number": prepared.recipient_handle,
            "agent_id": self.agent_id,
            "from_number_id": self.from_number_id,
            "custom_args_values": custom_args,
        }
        if self.callback_url:
            payload["callback_url"] = self.callback_url

        result = await self._request("POST", "/calling/outbound/individual", json_body=payload)

        call_id = result.get("call_id") or result.get("callId") or result.get("id")

        return DeliveryReceipt(
            channel=self.name,
            status=DeliveryStatus.SENT if call_id else DeliveryStatus.UNKNOWN,
            provider_message_id=str(call_id) if call_id else None,
            provider_response=(
                "call placed; the spoken words come from the Ringg assistant, and the "
                "transcript arrives by webhook or from call history"
            ),
            cost_usd=0.0,
        )

    # -- receive -----------------------------------------------------------

    async def _fetch_inbound(self, since: Optional[datetime]) -> list[InboundEvent]:
        """Not implemented.

        Ringg delivers inbound calls as webhooks (`call_started`,
        `call_completed`, `all_processing_completed`). Turning those into
        `InboundEvent`s is the webhook gateway's job, not a poll here — and
        `capabilities().can_receive` is False so nothing calls this expecting
        results.
        """
        return []

    # -- history -----------------------------------------------------------

    async def call_history(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Recent calls, for reconciliation against receipts.

        Webhooks are the right path for production; this is for a dashboard or for
        working out what happened to a call whose webhook was missed.
        """
        result = await self._request("GET", f"/calling/history?limit={min(limit, MAX_PAGE_SIZE)}")
        calls = result.get("calls") or result.get("data") or result.get("items") or []
        return calls if isinstance(calls, list) else []

    async def transcript(self, call_id: str) -> Optional[str]:
        """The transcript of a finished call, if Ringg has one.

        A transcript is how the Mind learns what was actually said — which is the
        only way a call becomes a memory rather than an action. Returns None rather
        than raising when it is not ready, because a transcript genuinely is not
        available until the call completes.
        """
        for entry in await self.call_history(limit=MAX_PAGE_SIZE):
            if str(entry.get("call_id") or entry.get("callId") or entry.get("id")) != str(call_id):
                continue
            return entry.get("transcript") or entry.get("transcript_text") or None
        return None

    # -- diagnostics -------------------------------------------------------

    async def verify(self) -> dict[str, Any]:
        """Check the key, workspace, assistant and number before placing a call.

        Worth doing up front: a call that fails validation still costs a request to
        a metered provider, and the Ringg troubleshooting guide lists these four as
        the reasons a call does not start.
        """
        report: dict[str, Any] = {
            "base_url": self.base_url,
            "agent_id": self.agent_id,
            "from_number_id": self.from_number_id,
            "disclosure_confirmed": self.disclosure_confirmed,
            "checks": {},
        }

        try:
            workspace = await self._request("GET", "/workspace")
            report["checks"]["workspace"] = {"ok": True, "credits": workspace.get("credits")}
        except RinggVoiceError as exc:
            report["checks"]["workspace"] = {"ok": False, "error": str(exc)}

        try:
            agents = await self._request("GET", "/agent/all")
            found = self._contains_id(agents, self.agent_id)
            report["checks"]["assistant"] = {
                "ok": found,
                "error": None if found else f"agent_id {self.agent_id!r} is not in this workspace",
            }
        except RinggVoiceError as exc:
            report["checks"]["assistant"] = {"ok": False, "error": str(exc)}

        try:
            numbers = await self._request("GET", "/workspace/numbers")
            found = self._contains_id(numbers, self.from_number_id)
            report["checks"]["number"] = {
                "ok": found,
                "error": None if found else f"from_number_id {self.from_number_id!r} is not available",
            }
        except RinggVoiceError as exc:
            report["checks"]["number"] = {"ok": False, "error": str(exc)}

        if not self.disclosure_confirmed:
            report["checks"]["disclosure"] = {
                "ok": False,
                "error": (
                    "the Ringg assistant's prompt must open with an AI disclosure and this "
                    "cannot be verified from the API. Set MIND_RINGG_DISCLOSURE_CONFIRMED=true "
                    "once the prompt does. The channel stays disabled until then."
                ),
            }

        report["ok"] = all(
            entry.get("ok") is not False for entry in report["checks"].values()
        )
        return report

    @staticmethod
    def _contains_id(payload: Any, wanted: str) -> bool:
        """Whether an id appears anywhere in a list-shaped response.

        Written loosely on purpose: Ringg's list endpoints are documented by class
        (`/agent/all`, `/workspace/numbers`) but not by item shape, so committing to
        one key would make a rename look like a missing assistant. A substring scan
        over the serialised payload answers "is this id here" without asserting a
        schema we have not seen.
        """
        if not wanted:
            return False
        import json

        try:
            return wanted in json.dumps(payload)
        except Exception:  # noqa: BLE001
            return False
