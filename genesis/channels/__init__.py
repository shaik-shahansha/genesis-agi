"""Channels: how a Mind exists in the digital world outside its container.

A channel is a medium the Mind owns an identity on — an email address, a telegram
bot, a phone number. The Mind never holds a credential; it holds an intent to
communicate, the adapter holds the secret, and governance holds the veto.

See `docs/v3/DIGITAL_PRESENCE.md`.

The invariant this package exists to make structural:

    `send()` accepts only `ApprovedCommunication`, which refuses to construct
    without a permitting governance decision. There is no path from a model's
    output to a human's inbox that does not pass through the gate.
"""

from .adapter import BaseChannel
from .base import (
    ApprovedCommunication,
    ChannelCapabilities,
    ChannelDeliveryError,
    ChannelError,
    ChannelIdentity,
    ChannelPolicyRefusal,
    ChannelUnavailableError,
    CommunicationIntent,
    ContactRef,
    ConversationThread,
    DeliveryReceipt,
    DeliveryStatus,
    ExternalContact,
    InboundEvent,
    NotAuthorised,
    OutboundPermission,
    PreparedMessage,
    digest_of,
    utcnow,
)
from .disclosure import (
    DISCLOSURE_MARKER,
    apply_disclosure,
    assert_disclosed,
    compose_disclosure,
    is_disclosed,
)
from .fake import FakeChannel
from .gateway import ChannelGateway, EngagementOutcome, InMemoryContacts
from .limits import (
    ChannelLimits,
    InMemoryOutboundLedger,
    OptOutRegistry,
    OutboundLedger,
    assert_can_send,
    outbound_refusal_reason,
    parse_call_window,
)
from .registry import (
    ChannelCredentials,
    ChannelRegistration,
    ChannelRegistry,
    build_fake_registry,
    build_registry,
    credentials_from_settings,
)

__all__ = [
    # protocol and types
    "BaseChannel",
    "ApprovedCommunication",
    "ChannelCapabilities",
    "ChannelIdentity",
    "CommunicationIntent",
    "ContactRef",
    "ConversationThread",
    "DeliveryReceipt",
    "DeliveryStatus",
    "ExternalContact",
    "InboundEvent",
    "OutboundPermission",
    "PreparedMessage",
    "digest_of",
    "utcnow",
    # errors
    "ChannelError",
    "ChannelUnavailableError",
    "ChannelPolicyRefusal",
    "ChannelDeliveryError",
    "NotAuthorised",
    # disclosure
    "DISCLOSURE_MARKER",
    "apply_disclosure",
    "assert_disclosed",
    "compose_disclosure",
    "is_disclosed",
    # floors
    "ChannelLimits",
    "InMemoryOutboundLedger",
    "OptOutRegistry",
    "OutboundLedger",
    "assert_can_send",
    "outbound_refusal_reason",
    "parse_call_window",
    # registry
    "ChannelCredentials",
    "ChannelRegistration",
    "ChannelRegistry",
    "build_fake_registry",
    "build_registry",
    "credentials_from_settings",
    # gateway
    "ChannelGateway",
    "EngagementOutcome",
    "InMemoryContacts",
    # test double
    "FakeChannel",
]
