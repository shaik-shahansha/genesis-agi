"""Contactability floors: quiet hours, weekly caps, and opt-out.

`docs/v3/DIGITAL_PRESENCE.md` §6. Three rules, and the reason each is here rather
than in the caller:

* **Quiet hours.** A caller that forgets wakes someone at 03:00. Cheap to check,
  expensive to get wrong, and no reviewer can see a missing check in a diff.
* **Weekly caps.** "Message them as needed" becomes a daily habit. Counting
  *initiated* messages only; answering someone who wrote first is not outreach.
* **Opt-out is permanent and cross-channel.** If someone asks a Mind to stop, it
  stops — on every channel, not the one they happened to say it on. Anything else
  is the behaviour the user is trying to escape from the rest of the internet.

The ledger is an injected protocol rather than a module-level dict because a rate
limit that resets on restart is a control that reports success when it never ran.
The default below is honest about not being durable; the composition layer wires a
journal-backed implementation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

from .base import ChannelPolicyRefusal, ContactRef, OutboundPermission, utcnow

logger = logging.getLogger(__name__)


@dataclass
class ChannelLimits:
    """Defaults applied when a contact has not specified its own."""

    #: Nothing initiated outside this local-hours window.
    default_quiet_hours: tuple[int, int] = (8, 20)
    #: Cap on initiated messages per contact per week.
    default_max_outbound_per_week: int = 3
    #: Minimum gap between two initiated messages to the same person.
    min_gap_between_outbound: timedelta = timedelta(hours=6)


def parse_call_window(value: Optional[str]) -> Optional[tuple[int, int]]:
    """Parse an `"HH:MM-HH:MM"` window into quiet hours, or None.

    Telephony providers let an operator set their own calling window, and a
    provider-side window is enforced by the provider, not by us. This exists so the
    adapter's *own* floor can be aligned with what the operator configured: if our
    window is wider than the provider's, the Mind believes a call is allowed and
    the provider refuses it at the last moment, which surfaces as an unexplained
    delivery failure rather than a policy refusal.

    Returns None for anything unparseable rather than raising. The caller keeps its
    default in that case, and the caller is expected to say so — silently treating
    a typo as "no hours configured" would remove a control and look like a
    configuration change.
    """
    if not value:
        return None
    text = value.strip()
    for separator in ("-", "–", "to"):
        if separator in text:
            start_text, _, end_text = text.partition(separator)
            start = _parse_clock(start_text)
            end = _parse_clock(end_text)
            if start is not None and end is not None:
                return (start, end)
            return None
    # A bare hour means "from this hour to midnight-ish"; treat as 24h unparseable
    # rather than inventing an end.
    return None


def _parse_clock(value: str) -> Optional[int]:
    """`"9"`, `"09:00"`, `"9:30 pm"` -> hour. Minutes are dropped rather than
    rounded, because rounding *up* would extend the window past what was asked
    for, and rounding down would shorten a window a human deliberately set."""
    text = value.strip().lower().replace(".", "")
    if not text:
        return None
    if text.endswith("pm") or text.endswith("am"):
        meridiem = text[-2:]
        text = text[:-2].strip()
    else:
        meridiem = ""
    text = text.split(":")[0].strip()
    if not text.isdigit():
        return None
    hour = int(text)
    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    if not 0 <= hour <= 24:
        return None
    return hour


class OutboundLedger(Protocol):
    """Records and counts messages a Mind *initiated*.

    Replies are deliberately excluded: answering someone who wrote to you is not
    outreach, and counting it would make a Mind unable to hold a conversation.
    """

    @property
    def durable(self) -> bool:
        """False when the counts are lost on restart.

        Exposed so the composition layer can report it. A non-durable limiter
        still helps within a process, but it must not be presented as a cap that
        holds over time.
        """

    def record(
        self,
        *,
        mind_id: str,
        relationship_id: str,
        channel: str,
        at: datetime,
        trigger: str = "manual",
        trigger_ref: Optional[str] = None,
    ) -> None: ...

    def count_since(self, *, mind_id: str, relationship_id: str, since: datetime) -> int: ...

    def last_outbound_at(self, *, mind_id: str, relationship_id: str) -> Optional[datetime]: ...


@dataclass
class InMemoryOutboundLedger:
    """Process-local counting. **Not durable.**

    Useful for tests and for a single long-lived process, and explicitly not a
    substitute for a durable one. `durable` is False so callers can tell.

    `trigger` and `trigger_ref` are accepted and **discarded**. That is deliberate
    and it is the honest behaviour for this implementation: the idempotence check
    (`already_reached_out` on the durable ledger) is what stops proactive outreach
    repeating, and a process-local version of it would reset on restart and let the
    same obligation be raised again. Silently pretending to deduplicate would be
    worse than not offering it, so this class simply does not implement
    `already_reached_out` — a caller that needs it gets an `AttributeError` rather
    than a wrong answer.
    """

    _entries: list[tuple[str, str, str, datetime]] = field(default_factory=list)

    @property
    def durable(self) -> bool:
        return False

    def record(
        self,
        *,
        mind_id: str,
        relationship_id: str,
        channel: str,
        at: datetime,
        trigger: str = "manual",
        trigger_ref: Optional[str] = None,
    ) -> None:
        self._entries.append((mind_id, relationship_id, channel, at))

    def count_since(self, *, mind_id: str, relationship_id: str, since: datetime) -> int:
        return sum(
            1
            for m, r, _c, when in self._entries
            if m == mind_id and r == relationship_id and when >= since
        )

    def last_outbound_at(self, *, mind_id: str, relationship_id: str) -> Optional[datetime]:
        matches = [when for m, r, _c, when in self._entries if m == mind_id and r == relationship_id]
        return max(matches) if matches else None


# ---------------------------------------------------------------------------
# Opt-out
# ---------------------------------------------------------------------------


@dataclass
class OptOutRegistry:
    """People who have asked not to be contacted.

    Keyed by a normalised handle *and* by relationship, because someone may say
    "stop" on one channel and the Mind must treat it as applying everywhere. The
    handle map is what makes it cross-channel: it catches the same person
    reaching the Mind through a different address.

    In-memory here for the same reason as the ledger; the interface is what
    matters and the composition layer supplies durability.
    """

    _relationships: set[str] = field(default_factory=set)
    _handles: set[str] = field(default_factory=set)

    @staticmethod
    def normalise(handle: str) -> str:
        return (handle or "").strip().lower()

    def opt_out(self, *, relationship_id: str = "", handle: str = "") -> None:
        if relationship_id:
            self._relationships.add(relationship_id)
        if handle:
            self._handles.add(self.normalise(handle))

    def is_opted_out(self, *, relationship_id: str = "", handle: str = "") -> bool:
        if relationship_id and relationship_id in self._relationships:
            return True
        return bool(handle) and self.normalise(handle) in self._handles

    def clear(self, *, relationship_id: str) -> None:
        """Re-enable contact, but only when a person has actually asked again.

        Exposed deliberately as a separate call so that nothing in a normal send
        path can clear an opt-out as a side effect.
        """
        self._relationships.discard(relationship_id)


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------


def outbound_refusal_reason(
    *,
    contact: ContactRef,
    is_reply: bool,
    ledger: OutboundLedger,
    mind_id: str,
    limits: Optional[ChannelLimits] = None,
    at: Optional[datetime] = None,
    opted_out: bool = False,
) -> Optional[str]:
    """Why this message may not be sent, or None if it may.

    Returns a reason rather than raising so the caller can attach it to a
    prepared message's warnings and let governance see *why* something needs
    attention. The adapter calls `assert_can_send` just before sending, which
    turns the same reason into a refusal.
    """
    cfg = limits or ChannelLimits()

    # Opt-out outranks everything. It is not a soft preference.
    if opted_out:
        return f"{contact.display_name} has asked not to be contacted"

    # A reply only needs the reply permission. Everything below is about outreach.
    if is_reply:
        if not contact.may_reply():
            return f"{contact.display_name} is not open to replies on this channel"
        return None

    if contact.outbound is OutboundPermission.NONE:
        return (
            f"{contact.display_name} has not consented to being contacted "
            "(outbound permission is 'none')"
        )

    if not contact.may_initiate():
        return (
            f"{contact.display_name} may be contacted but there is no recorded consent source; "
            "consent without provenance is an assertion, not permission"
        )

    now = at or utcnow()

    if not contact.within_quiet_hours(now):
        start, end = contact.quiet_hours
        return (
            f"outside {contact.display_name}'s contactable hours "
            f"({start:02d}:00–{end:02d}:00 local); initiating now would be {now.hour:02d}:00 their time"
        )

    week_ago = now - timedelta(days=7)
    initiated = ledger.count_since(mind_id=mind_id, relationship_id=contact.relationship_id, since=week_ago)
    if initiated >= contact.max_outbound_per_week:
        return (
            f"{contact.display_name} has already received {initiated} initiated messages this week "
            f"(limit {contact.max_outbound_per_week})"
        )

    last = ledger.last_outbound_at(mind_id=mind_id, relationship_id=contact.relationship_id)
    if last is not None:
        elapsed = now - last
        if elapsed < cfg.min_gap_between_outbound:
            remaining = cfg.min_gap_between_outbound - elapsed
            minutes = max(1, int(remaining.total_seconds() // 60))
            return (
                f"last contacted {contact.display_name} {int(elapsed.total_seconds() // 60)} minutes ago; "
                f"wait {minutes} more"
            )

    return None


def assert_can_send(**kwargs) -> None:
    """`outbound_refusal_reason` as a refusal.

    Called by adapters immediately before handing a message to a provider. The
    second check is not redundant: `prepare()` and `send()` are separated by a
    governance round-trip that may involve a human, and a person can ask to be
    left alone in that window.
    """
    reason = outbound_refusal_reason(**kwargs)
    if reason:
        raise ChannelPolicyRefusal(reason)
