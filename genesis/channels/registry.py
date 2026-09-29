"""Channel registry: which channels a Mind has, and whether they are usable.

Resolves adapters from administrator-configured credentials, validates them, and
reports status. Two rules are enforced here rather than trusted to adapters:

* **A channel that cannot disclose is not registered.** An adapter reporting
  `supports_disclosure=False` is refused, because an undisclosed outbound message
  is the one outcome the product cannot ship.
* **A channel with no identity is not registered.** No address, no channel.

Both refusals keep the adapter in the registry with `enabled=False` and a
`reason`, rather than dropping it silently. A channel that vanishes from the list
because it is misconfigured is indistinguishable from one that was never
configured, and the operator needs to see which.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .base import (
    ChannelCapabilities,
    ChannelIdentity,
    CommunicationChannel,
    InboundEvent,
)
from .ledger import DatabaseOptOutRegistry, DatabaseOutboundLedger
from .limits import ChannelLimits, parse_call_window

logger = logging.getLogger(__name__)


@dataclass
class ChannelRegistration:
    """A channel, whether it can be used, and why not when it cannot."""

    name: str
    adapter: Optional[CommunicationChannel] = None
    identity: Optional[ChannelIdentity] = None
    enabled: bool = False
    #: Why it is disabled. Always set when `enabled` is False, so the operator
    #: has something to act on rather than a missing row.
    reason: str = ""

    def capabilities(self) -> ChannelCapabilities:
        if self.adapter is None:
            return ChannelCapabilities()
        return self.adapter.capabilities()

    def to_public_dict(self) -> dict[str, Any]:
        caps = self.capabilities()
        return {
            "name": self.name,
            "enabled": self.enabled,
            "reason": self.reason,
            "address": self.identity.address if self.identity else None,
            "display_name": self.identity.display_name if self.identity else None,
            "disclosed": bool(self.identity.is_disclosed) if self.identity else False,
            "capabilities": caps.to_dict(),
        }


class ChannelRegistry:
    """The channels one Mind has available.

    Scoped to a Mind because each Mind owns its own addresses. Two Minds on one
    installation must not share an inbox: they would answer each other's mail and
    neither could tell whose memory a thread belonged to.
    """

    def __init__(self, mind_id: str):
        self.mind_id = mind_id
        self._channels: dict[str, ChannelRegistration] = {}

    def register(self, adapter: CommunicationChannel) -> ChannelRegistration:
        """Validate and register an adapter.

        Validation runs here, once, so every later call can assume a registered
        channel has an identity and can disclose. Checks scattered across call
        sites are checks that some call site is missing.
        """
        name = getattr(adapter, "name", "") or "?"

        identity = getattr(adapter, "identity", None)
        if identity is None:
            return self._disable(name, adapter, "adapter exposes no identity")

        caps = adapter.capabilities()
        if not caps.supports_disclosure:
            return self._disable(
                name,
                adapter,
                "channel cannot carry an AI disclosure; undisclosed outbound "
                "messages are not permitted, so this channel stays off",
            )

        if not identity.is_disclosed:
            return self._disable(
                name,
                adapter,
                "identity has no disclosure text; the channel would not be able to "
                "state that it is AI-operated",
            )

        if not identity.address:
            return self._disable(name, adapter, "identity has no address")

        registration = ChannelRegistration(
            name=name,
            adapter=adapter,
            identity=identity,
            enabled=True,
            reason="",
        )
        self._channels[name] = registration
        logger.info(
            "channel %s registered for %s as %s", name, self.mind_id, identity.address
        )
        return registration

    def _disable(
        self, name: str, adapter: Optional[CommunicationChannel], reason: str
    ) -> ChannelRegistration:
        registration = ChannelRegistration(
            name=name, adapter=adapter, enabled=False, reason=reason
        )
        self._channels[name] = registration
        logger.warning("channel %s disabled for %s: %s", name, self.mind_id, reason)
        return registration

    def get(self, name: str) -> Optional[ChannelRegistration]:
        return self._channels.get(name)

    def enabled(self) -> list[ChannelRegistration]:
        return [r for r in self._channels.values() if r.enabled]

    def all(self) -> list[ChannelRegistration]:
        return list(self._channels.values())

    def has(self, name: str) -> bool:
        registration = self._channels.get(name)
        return bool(registration and registration.enabled)

    def describe(self) -> dict[str, Any]:
        """What `GET /system/providers` reports, so a deployment can see reality."""
        return {
            "mind_id": self.mind_id,
            "channels": [r.to_public_dict() for r in self.all()],
            "enabled": [r.name for r in self.enabled()],
        }

    async def receive_all(self, since: Optional[datetime] = None) -> list[InboundEvent]:
        """Collect inbound events from every enabled channel.

        One channel failing does not stop the others: a Mind with a broken
        telegram token should still read its email. R0 — reading changes nothing
        outside the container.
        """
        events: list[InboundEvent] = []
        for registration in self.enabled():
            if not registration.capabilities().can_receive:
                continue
            try:
                events.extend(await registration.adapter.receive(since=since))
            except Exception as exc:  # noqa: BLE001 - one channel must not break the rest
                logger.warning(
                    "channel %s receive failed for %s: %s", registration.name, self.mind_id, exc
                )
        return events


# ---------------------------------------------------------------------------
# Building from configuration
# ---------------------------------------------------------------------------


@dataclass
class ChannelCredentials:
    """Per-channel credentials, resolved from settings or per-Mind config.

    The administrator supplies these. The Mind never holds them — it holds an
    intent, the registry holds the secret, and the policy holds the veto.
    """

    channels: dict[str, dict[str, Any]] = field(default_factory=dict)
    administrator: str = ""

    def for_channel(self, name: str) -> dict[str, Any]:
        return dict(self.channels.get(name) or {})

    def has_any(self) -> bool:
        return any(bool(v) for v in self.channels.values())


def credentials_from_settings(settings: Any) -> ChannelCredentials:
    """Read install-level channel credentials from settings.

    Install-level is the single-tenant case and the documented default. Per-Mind
    provisioning (each Mind with its own address) is a later phase; when it lands
    it overrides this rather than replacing it, so an installation with one Mind
    keeps working without configuration.
    """
    channels: dict[str, dict[str, Any]] = {}

    email = {
        "address": getattr(settings, "mind_email_address", None),
        "display_name": getattr(settings, "mind_email_display_name", None),
        "imap_host": getattr(settings, "mind_email_imap_host", None),
        "imap_port": getattr(settings, "mind_email_imap_port", 993),
        "smtp_host": getattr(settings, "mind_email_smtp_host", None),
        "smtp_port": getattr(settings, "mind_email_smtp_port", 587),
        "username": getattr(settings, "mind_email_username", None),
        "password": getattr(settings, "mind_email_password", None),
        "use_tls": getattr(settings, "mind_email_use_tls", True),
    }
    # Both halves are required. An address with no password is a half-configured
    # channel, and registering it would produce a channel that appears enabled and
    # then fails on first use.
    if email["address"] and email["password"]:
        channels["email"] = email

    telegram = {
        "address": getattr(settings, "mind_telegram_bot_username", None),
        "bot_token": getattr(settings, "mind_telegram_bot_token", None),
    }
    if telegram["bot_token"]:
        channels["telegram"] = telegram

    # Hostinger Mail API. Preferred over plain IMAP/SMTP when configured, because
    # the token is scoped to specific mailboxes and the provider threads replies
    # and can enforce an outgoing allow list.
    hostinger = {
        "api_token": getattr(settings, "mind_hostinger_mail_api_token", None),
        "mailbox_id": getattr(settings, "mind_hostinger_mailbox_id", None),
        "address": getattr(settings, "mind_hostinger_mail_address", None),
        "display_name": getattr(settings, "mind_hostinger_mail_display_name", None),
        "base_url": getattr(settings, "mind_hostinger_mail_base_url", None),
        "api_version": getattr(settings, "mind_hostinger_mail_api_version", None),
    }
    if hostinger["api_token"] and hostinger["mailbox_id"]:
        channels["email"] = hostinger

    ringg = {
        "api_key": getattr(settings, "mind_ringg_api_key", None),
        "agent_id": getattr(settings, "mind_ringg_agent_id", None),
        "from_number_id": getattr(settings, "mind_ringg_from_number_id", None),
        "phone_number": getattr(settings, "mind_ringg_phone_number", None),
        "disclosure_confirmed": getattr(settings, "mind_ringg_disclosure_confirmed", False),
    }
    # The provider enforces its own calling window; this aligns our floor with it
    # so a call inside the operator's window does not fail at the provider as an
    # unexplained delivery error. Unparseable means the default floor is kept and
    # the operator is told, rather than the control silently disappearing.
    window_text = getattr(settings, "mind_ringg_call_window", None)
    window = parse_call_window(window_text)
    if window is None and window_text:
        logger.warning(
            "MIND_RINGG_CALL_WINDOW=%r is not a window like '09:00-18:00'; "
            "the default quiet hours (%d:00-%d:00) stay in force",
            window_text,
            ChannelLimits().default_quiet_hours[0],
            ChannelLimits().default_quiet_hours[1],
        )
    if window is not None:
        ringg["quiet_hours"] = window
    # All three ids are required. Any subset would produce a channel that appears
    # configured and fails on the first call.
    if ringg["api_key"] and ringg["agent_id"] and ringg["from_number_id"]:
        channels["voice"] = ringg

    return ChannelCredentials(
        channels=channels,
        administrator=getattr(settings, "mind_administrator_name", "") or "",
    )


def build_registry(mind_id: str, credentials: ChannelCredentials) -> ChannelRegistry:
    """Construct the channels an administrator has provisioned.

    Only channels with credentials are attempted. A channel with no credentials is
    not registered as disabled either — it was never configured, which is a
    different fact from "configured and refused", and conflating them would fill
    the status list with noise and hide the refusals that matter.

    Order matters for email: **Hostinger Mail is preferred when configured**,
    because its token is scoped to specific mailboxes, the provider threads replies
    for us, and an outgoing allow list can reject a misaddressed send at the
    provider even if our own code is wrong. Plain IMAP/SMTP is the fallback for
    anyone with a mailbox elsewhere.

    **The ledger and the opt-out registry are created once here and shared by every
    channel.** That is load-bearing, not tidiness. `BaseChannel.__init__` builds its
    own when none is injected, so before this both controls were per-channel:

    * the weekly cap was enforced *per channel*, so a Mind could send three emails,
      three Telegram messages and three calls — nine contacts in a week against a
      documented limit of three, with each channel individually compliant;
    * an opt-out recorded on one channel did not apply on another, so someone who
      said "stop" by email could be telephoned. That is the precise behaviour the
      opt-out exists to prevent, and it was invisible because it worked in the
      common case of a Mind that only had one channel configured.

    Both were verified by observing the behaviour rather than by reading the code,
    which is the only way this class of bug is ever found: each channel was
    individually correct.
    """
    registry = ChannelRegistry(mind_id)
    administrator = credentials.administrator

    # One ledger and one opt-out registry for the whole Mind, so the cap follows the
    # person rather than the channel, and "stop" means stop everywhere.
    ledger = DatabaseOutboundLedger()
    optouts = DatabaseOptOutRegistry(mind_id=mind_id)

    email_cfg = credentials.for_channel("email")
    if email_cfg and email_cfg.get("api_token"):
        from .hostinger_mail import HostingerMailChannel

        registry.register(
            HostingerMailChannel(
                api_token=email_cfg["api_token"],
                mailbox_id=email_cfg["mailbox_id"],
                address=email_cfg.get("address") or email_cfg["mailbox_id"],
                display_name=email_cfg.get("display_name") or email_cfg.get("address") or "",
                base_url=email_cfg.get("base_url") or "",
                api_version=email_cfg.get("api_version") or "",
                administrator=administrator,
                mind_id=mind_id,
                ledger=ledger,
                optouts=optouts,
            )
        )
    elif email_cfg:
        from .email import EmailChannel

        registry.register(
            EmailChannel(
                address=email_cfg["address"],
                display_name=email_cfg.get("display_name") or email_cfg["address"],
                imap_host=email_cfg.get("imap_host") or "",
                imap_port=int(email_cfg.get("imap_port") or 993),
                smtp_host=email_cfg.get("smtp_host") or "",
                smtp_port=int(email_cfg.get("smtp_port") or 587),
                username=email_cfg.get("username") or email_cfg["address"],
                password=email_cfg.get("password") or "",
                use_tls=bool(email_cfg.get("use_tls", True)),
                administrator=administrator,
                mind_id=mind_id,
                ledger=ledger,
                optouts=optouts,
            )
        )

    telegram_cfg = credentials.for_channel("telegram")
    if telegram_cfg:
        from .telegram import TelegramChannel

        registry.register(
            TelegramChannel(
                bot_token=telegram_cfg["bot_token"],
                bot_username=telegram_cfg.get("address") or "",
                administrator=administrator,
                mind_id=mind_id,
                ledger=ledger,
                optouts=optouts,
            )
        )

    ringg_cfg = credentials.for_channel("voice")
    if ringg_cfg:
        from .ringg_voice import RinggVoiceChannel

        quiet_hours = ringg_cfg.get("quiet_hours")
        registry.register(
            RinggVoiceChannel(
                api_key=ringg_cfg["api_key"],
                agent_id=ringg_cfg["agent_id"],
                from_number_id=ringg_cfg["from_number_id"],
                phone_number=ringg_cfg.get("phone_number") or "",
                display_name="Genesis Mind",
                disclosure_confirmed=bool(ringg_cfg.get("disclosure_confirmed")),
                # Passing limits explicitly only when the operator configured a
                # window keeps the documented default reachable and makes it
                # obvious which of the two is in force.
                **(
                    {"limits": ChannelLimits(default_quiet_hours=tuple(quiet_hours))}
                    if quiet_hours
                    else {}
                ),
                administrator=administrator,
                mind_id=mind_id,
                ledger=ledger,
                optouts=optouts,
            )
        )

    return registry


def build_fake_registry(
    mind_id: str, *, administrator: str = "Test Operator"
) -> ChannelRegistry:
    """A registry of in-memory channels, for tests and dry runs."""
    from .fake import FakeChannel

    registry = ChannelRegistry(mind_id)
    registry.register(
        FakeChannel(
            address="sage@example.test",
            display_name="Sage",
            administrator=administrator,
        )
    )
    return registry
