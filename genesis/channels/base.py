"""Channel substrate: how a Mind reaches the world outside its container.

A **channel** is a medium the Mind owns an identity on — an email address, a
telegram bot, a phone number. A **channel adapter** speaks the provider's
protocol and holds its credentials.

Three rules shape this module, and they are the reason it exists rather than the
existing `integrations/` ABC being reused as-is:

1. **An adapter never decides.** It reports what it can do and executes what it
   is told. Judgement lives in governance, intent in cognition, consent in
   relationships.

2. **You cannot send without having been approved.** `send()` accepts
   `ApprovedCommunication` and nothing else, and that type refuses to construct
   without a real allow decision. This is not documentation; it is the type
   system, and it exists because `action_scheduler.py` used to send model
   scratchpad text to strangers on the strength of `"yes" in decision.lower()`.

3. **Disclosure and contactability are enforced here, not by callers.** A caller
   that forgets either one produces an invisible omission. Same reasoning as
   redaction: enforce it in the writer.

See `docs/v3/DIGITAL_PRESENCE.md`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ChannelError(RuntimeError):
    """Base for channel failures."""


class ChannelUnavailableError(ChannelError):
    """The provider is unreachable, unconfigured, or refused the connection.

    Distinct from a delivery failure: nothing was attempted.
    """


class ChannelPolicyRefusal(ChannelError):
    """The adapter refused on a rule it enforces itself.

    Raised for a missing disclosure, a closed contactability window, or a
    breached rate limit. This is not a governance decision — it is a floor the
    adapter will not go below even when governance says yes, which is why it
    lives in the adapter.
    """


class ChannelDeliveryError(ChannelError):
    """The provider accepted the request and then failed to deliver it."""


# ---------------------------------------------------------------------------
# Identity and capability
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChannelIdentity:
    """The address a Mind owns on a channel, and how it identifies itself.

    `disclosure` is part of the identity rather than a message template. A
    channel whose every message must carry "I am an AI operated by X" has that
    requirement in the same object as the address, so they cannot drift apart.
    """

    channel: str
    address: str
    display_name: str
    disclosure: str
    administrator: str = ""
    verified: bool = False

    @property
    def is_disclosed(self) -> bool:
        """Whether this identity can state what it is.

        An identity with no disclosure text is not usable — see
        `ChannelCapabilities.supports_disclosure`.
        """
        return bool(self.disclosure.strip())


@dataclass(frozen=True)
class ChannelCapabilities:
    """What an adapter can actually do.

    Read by the UI and by `GET /system/providers` so a deployment can see what is
    really available rather than inferring it from a config file.
    """

    can_receive: bool = False
    can_send: bool = False
    can_reply_in_thread: bool = False
    can_attach: bool = False
    can_voice: bool = False

    #: True when each message costs money. Telephony and SMS always do.
    metered: bool = False
    #: Best-effort unit cost, used by governance to check the budget *before*
    #: executing. Zero for free channels.
    unit_cost_usd: float = 0.0

    max_body_bytes: int = 100_000
    max_attachments: int = 0

    #: Whether outbound messages can carry an AI disclosure.
    #:
    #: A channel that cannot is not enabled. Disclosure is the line between a
    #: digital being and a deception, so it is a hard requirement rather than a
    #: feature flag — and expressing it as a capability means an adapter that
    #: cannot disclose fails to register instead of quietly sending undisclosed
    #: messages.
    supports_disclosure: bool = True

    #: Whether the adapter can confirm delivery. When False, receipts report
    #: "unknown" rather than claiming success.
    confirms_delivery: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_receive": self.can_receive,
            "can_send": self.can_send,
            "can_reply_in_thread": self.can_reply_in_thread,
            "can_attach": self.can_attach,
            "can_voice": self.can_voice,
            "metered": self.metered,
            "unit_cost_usd": self.unit_cost_usd,
            "max_body_bytes": self.max_body_bytes,
            "supports_disclosure": self.supports_disclosure,
            "confirms_delivery": self.confirms_delivery,
        }


# ---------------------------------------------------------------------------
# Contactability
# ---------------------------------------------------------------------------


class OutboundPermission(str, Enum):
    """Whether a Mind may start contact with someone, or only answer."""

    NONE = "none"
    REPLY_ONLY = "reply_only"
    INITIATE = "initiate"


@dataclass
class ContactRef:
    """A resolved recipient: who they are, and how to reach them.

    Deliberately carries the *relationship*, not just an address. Sending to a
    bare address with no relationship is the case the whole consent model exists
    to make impossible, so the type makes it awkward rather than convenient.
    """

    relationship_id: str
    display_name: str
    handle: str
    outbound: OutboundPermission = OutboundPermission.NONE
    #: How we know contact is permitted. Required when `outbound` is not NONE.
    consent_source: str = ""
    #: Local-time window, `(start_hour, end_hour)` in the contact's timezone.
    quiet_hours: tuple[int, int] = (8, 20)
    #: Hard cap on messages the Mind may *initiate* per week. Reply-only
    #: exchanges are not counted, because answering someone who wrote first is
    #: not outreach.
    max_outbound_per_week: int = 3
    boundaries: list[str] = field(default_factory=list)
    trust: dict[str, float] = field(default_factory=dict)
    timezone_offset_hours: int = 0

    def trust_in(self, domain: str) -> float:
        """Scoped trust, defaulting to zero.

        A missing domain is untrusted, not neutral. The scalar `trust_level` this
        replaces defaulted to 0.5, which meant an unknown domain was half trusted
        — the wrong direction for a fail-closed system.
        """
        return float(self.trust.get(domain, 0.0))

    def may_initiate(self) -> bool:
        """Whether the Mind may start a conversation.

        Requires both the permission *and* a recorded reason. Permission without
        provenance is an assertion; `consent_source` is what makes it a fact.
        """
        return self.outbound is OutboundPermission.INITIATE and bool(self.consent_source.strip())

    def may_reply(self) -> bool:
        return self.outbound in (OutboundPermission.REPLY_ONLY, OutboundPermission.INITIATE)

    def within_quiet_hours(self, at: Optional[datetime] = None) -> bool:
        """Whether it is a reasonable hour where this person is.

        Wraps correctly across midnight: a window of `(22, 6)` is eight hours
        overnight, not an empty range. Getting this wrong in either direction is
        a real cost — either the Mind never contacts anyone, or it wakes them.
        """
        start, end = self.quiet_hours
        now = (at or utcnow()).hour
        local = (now + self.timezone_offset_hours) % 24
        if start == end:
            return False
        if start < end:
            return start <= local < end
        return local >= start or local < end


# ---------------------------------------------------------------------------
# Intent, preparation, approval
# ---------------------------------------------------------------------------


@dataclass
class CommunicationIntent:
    """What cognition wants to say, before anyone has checked whether it may.

    `trigger` and `trigger_ref` are required. Every outbound message has a
    reason, and the reason is recorded — "the being felt like it" is not an
    accountable trigger, and `DIGITAL_PRESENCE.md` §8 rules out random
    initiative for exactly that reason.
    """

    channel: str
    recipient: ContactRef
    body: str
    subject: Optional[str] = None
    #: Set when replying within an existing thread. Its presence is what makes
    #: a message R2 rather than R3.
    thread_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    reply_to_message_id: Optional[str] = None
    attachments: list[str] = field(default_factory=list)

    trigger: str = "reply"
    trigger_ref: Optional[str] = None
    correlation_id: Optional[str] = None

    @property
    def is_reply(self) -> bool:
        return bool(self.thread_id or self.in_reply_to)


@dataclass(frozen=True)
class PreparedMessage:
    """A message ready to send, with everything governance needs to judge it.

    Produced by `prepare()`, which must be pure — no side effects, no network, no
    clock skew. Governance inspects this, so it has to be a plain value that
    cannot change underneath the decision.
    """

    channel: str
    capability: str
    recipient_name: str
    recipient_handle: str
    subject: Optional[str]
    body: str
    is_reply: bool
    requires_approval_because: list[str] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    warnings: list[str] = field(default_factory=list)
    #: Why this message exists: "reply" | "manual" | a `TRIGGER_*` kind. Carried
    #: through to the outbound ledger so "why did this being contact me?" is
    #: answerable from the record rather than reconstructed from the timing.
    trigger: str = "manual"
    #: The specific fact that triggered it, which doubles as the idempotence key for
    #: proactive outreach. Not part of the approval digest — see `digest_of`: a
    #: trigger is provenance, not message content, and a human approving a body has
    #: not approved a trigger string.
    trigger_ref: Optional[str] = None

    @property
    def body_bytes(self) -> int:
        return len(self.body.encode("utf-8"))

    def to_public_dict(self) -> dict[str, Any]:
        """What a human approves. Includes the body: approving a message you
        cannot read is not consent."""
        return {
            "channel": self.channel,
            "capability": self.capability,
            "to": self.recipient_name,
            "handle": self.recipient_handle,
            "subject": self.subject,
            "body": self.body,
            "is_reply": self.is_reply,
            "estimated_cost_usd": self.estimated_cost_usd,
            "warnings": list(self.warnings),
        }


class NotAuthorised(ChannelError):
    """Raised when something tries to send without a governance decision."""


#: Governance decisions that permit a send. Kept as a plain set so this module
#: does not import `genesis.governance`, which would make the substrate depend on
#: the plane that judges it — a cycle, and the wrong direction of dependency.
_PERMITTING_DECISIONS = frozenset({"allow", "allow_with_receipt"})


@dataclass(frozen=True)
class ApprovedCommunication:
    """A prepared message that passed governance.

    Constructing this without a permitting decision raises. That is deliberate:
    `send()` accepts only this type, so the only way to reach a provider is to
    have gone through the gate. The alternative — passing a string and trusting
    callers to have checked — is what produced the auto-reply loop that shipped
    model scratchpad text to strangers.

    `contact` travels with the approval because the decision was about sending to
    *this person*, not about a body of text. Re-checking the contactability floors
    at send time needs the same contact that was judged.

    `body_digest` is computed here and verified in `BaseChannel.send`. The message
    is frozen, so nothing can mutate it in-process; the digest exists for the case
    where an approval is **persisted and reloaded** — a human-approved message can
    sit in a queue for hours, and anything that edits the stored body between
    approval and send would otherwise be invisible.
    """

    prepared: PreparedMessage
    contact: ContactRef
    decision: str
    decided_by: str = "policy"
    approval_id: Optional[str] = None
    correlation_id: Optional[str] = None
    granted_at: datetime = field(default_factory=utcnow)
    #: Set automatically from `prepared`. Do not pass by hand.
    body_digest: str = ""

    def __post_init__(self) -> None:
        if self.decision not in _PERMITTING_DECISIONS:
            raise NotAuthorised(
                f"decision {self.decision!r} does not permit sending; "
                f"expected one of {sorted(_PERMITTING_DECISIONS)}. "
                "A message cannot be sent without an allowing governance decision."
            )
        if not self.body_digest:
            object.__setattr__(self, "body_digest", digest_of(self.prepared))

    def verify_intact(self) -> bool:
        """Whether the prepared message still matches what was approved."""
        return self.body_digest == digest_of(self.prepared)


def digest_of(prepared: PreparedMessage) -> str:
    """A stable digest over the parts of a message a human approved.

    Falls back to a plain repr when the governance redaction helpers are
    unavailable, so this never becomes the reason a legitimate message cannot be
    sent — but note the fallback still hashes the body, so the tamper check
    holds either way.
    """
    payload = {
        "channel": prepared.channel,
        "to": prepared.recipient_handle,
        "subject": prepared.subject,
        "body": prepared.body,
    }
    try:
        from genesis.governance.redact import stable_hash

        return stable_hash(payload)
    except Exception:  # noqa: BLE001 - hashing must never block delivery
        import hashlib
        import json

        blob = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()



# ---------------------------------------------------------------------------
# Inbound
# ---------------------------------------------------------------------------


@dataclass
class InboundEvent:
    """Something arrived from outside.

    Journalled at R0: receiving changes nothing outside the container, and
    recording it is what lets a Mind answer "who wrote to me and when".
    """

    channel: str
    provider_message_id: str
    sender_handle: str
    sender_name: str = ""
    subject: Optional[str] = None
    body: str = ""
    thread_id: Optional[str] = None
    received_at: datetime = field(default_factory=utcnow)
    #: Whether the provider verified the sender. Unverified senders are usable
    #: for reading but must not raise trust or grant contactability.
    sender_verified: bool = False
    is_known_contact: bool = False
    attachments: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "from": self.sender_name or self.sender_handle,
            "handle": self.sender_handle,
            "subject": self.subject,
            "received_at": self.received_at.isoformat(),
            "verified": self.sender_verified,
            "known_contact": self.is_known_contact,
        }


@dataclass
class ConversationThread:
    """A thread as the channel sees it."""

    thread_id: str
    channel: str
    subject: Optional[str] = None
    participants: list[str] = field(default_factory=list)
    message_count: int = 0
    last_activity: Optional[datetime] = None


@dataclass
class ExternalContact:
    """A contact discovered on a channel, before it becomes a relationship.

    Receiving one of these does **not** grant contactability. Importing an
    address book into a system that can then act on it is how a Mind acquires
    hundreds of people it may not contact; adding a contact is a deliberate
    act with a `consent_source`.
    """

    handle: str
    display_name: str = ""
    channel: str = ""
    verified: bool = False


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------


class DeliveryStatus(str, Enum):
    """What happened to a message.

    `UNKNOWN` exists because some providers accept a request and say nothing
    more. Reporting that as SENT would be a claim the adapter cannot support,
    and a receipt that overstates delivery is worse than one that admits doubt —
    it is the same failure as the sandbox reporting `rc=0` for a container that
    never started.
    """

    SENT = "sent"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class DeliveryReceipt:
    """The outcome. Recorded in the journal for every outbound message."""

    channel: str
    status: DeliveryStatus
    provider_message_id: Optional[str] = None
    provider_response: str = ""
    cost_usd: float = 0.0
    error: Optional[str] = None
    disclosed: bool = False
    sent_at: datetime = field(default_factory=utcnow)

    @property
    def ok(self) -> bool:
        return self.status is DeliveryStatus.SENT

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "status": self.status.value,
            "provider_message_id": self.provider_message_id,
            "cost_usd": self.cost_usd,
            "disclosed": self.disclosed,
            "error": self.error,
            "sent_at": self.sent_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# The protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class CommunicationChannel(Protocol):
    """A medium a Mind owns an identity on.

    Implementations hold credentials and speak a provider protocol. They do not
    decide anything.
    """

    name: str

    @property
    def identity(self) -> ChannelIdentity:
        """The address this Mind owns on this channel."""

    def capabilities(self) -> ChannelCapabilities:
        """What this adapter can do. Read before anything is attempted."""

    async def receive(self, since: Optional[datetime] = None) -> list[InboundEvent]:
        """Read inbound events. Must not act on them."""

    async def prepare(self, intent: CommunicationIntent) -> PreparedMessage:
        """Build a message and compute its cost. Must be pure and side-effect free."""

    async def send(self, approved: ApprovedCommunication) -> DeliveryReceipt:
        """Deliver an approved message. The only method that changes the world."""

    async def get_thread(self, thread_id: str) -> Optional[ConversationThread]:
        """Fetch a thread, or None when the channel cannot enumerate threads."""

    async def sync_contacts(self) -> list[ExternalContact]:
        """Discover contacts. Never grants contactability by itself."""
