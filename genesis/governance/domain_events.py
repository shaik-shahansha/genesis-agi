"""Journaling for domain code: memory, relationships, goals.

**Why this module exists (plan item D2).**

ADR-0006's risk register says: *"Every write path must emit events — discipline
plus a helper/service to make it the path of least resistance."* This is that
helper. Without it, wiring the journal into `MemoryManager`, `RelationshipManager`
and `GoalManager` would mean each of them importing `AuditService`, building
payloads by hand, and deciding independently what to redact — which is how a
journal becomes both inconsistent and a privacy problem.

Two design rules, both enforced by tests:

**1. Content never enters the journal; only identity and metadata do.**

The journal is the source of truth for *history*; the domain tables are the
source of truth for *current state* (ADR-0008, and V3 §13 warns against strict
event sourcing). So a memory event records that a memory of a given type and
importance was accepted, and its id — **not its text**.

That is not squeamishness. Memory content is the most personal data this system
holds, and the journal is the most widely-readable artifact in it (exported by
`/audit/export`, rendered in the workspace timeline, kept for a year). Copying
content into the journal would double the disclosure surface for no analytical
gain, and it would survive a memory deletion — so "forget this" would stop being
true.

**2. Journaling never breaks the domain operation.**

Every method swallows its own exceptions. A journal outage must not fail a memory
write. This is the deliberate asymmetry from ADR-0008: a missing receipt is an
incident, but it is *not* a reason to lose the user's data. `tests/governance/
test_domain_events.py` asserts it.

Usage from a domain manager:

```python
from genesis.governance.domain_events import get_domain_journal

journal = get_domain_journal()   # no-op when governance is not configured
journal.memory_accepted(mind_id=self.mind_id, memory=memory)
```
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Protocol

from genesis.governance.context import current_correlation_id
from genesis.governance.models import EventType

logger = logging.getLogger(__name__)

__all__ = [
    "DomainJournal",
    "NullDomainJournal",
    "get_domain_journal",
    "set_domain_journal",
    "reset_domain_journal",
]


def _truncate(value: Any, limit: int = 200) -> Optional[str]:
    """A bounded, plain-text rendering of a label. Never used for content."""
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "…"


class DomainJournal(Protocol):  # pragma: no cover - structural typing
    """What domain code may record. Deliberately narrow."""

    def memory_accepted(self, *, mind_id: str, memory: Any) -> None: ...
    def memory_forgotten(self, *, mind_id: str, memory_id: str, reason: str = "") -> None: ...
    def memory_consolidated(self, *, mind_id: str, merged: int, removed: int) -> None: ...
    def relationship_created(self, *, mind_id: str, relationship: Any) -> None: ...
    def relationship_interaction(
        self, *, mind_id: str, relationship_id: str, positive: bool, trust_delta: float = 0.0
    ) -> None: ...
    def goal_created(self, *, mind_id: str, goal: Any) -> None: ...
    def goal_progress(
        self, *, mind_id: str, goal_id: str, progress: float, status: str
    ) -> None: ...
    def goal_completed(self, *, mind_id: str, goal_id: str, title: str = "") -> None: ...
    def goal_abandoned(self, *, mind_id: str, goal_id: str, reason: str = "") -> None: ...
    def record_life_event(self, *, mind_id: str, event_type: str, payload: Any) -> None: ...


class NullDomainJournal:
    """Records nothing. Used when governance is not configured.

    Not a silent failure: it exists so that code paths which legitimately have no
    journal (unit tests of the memory manager, a script using the storage layer
    directly) do not have to grow a conditional at every call site.
    """

    name = "null"

    def memory_accepted(self, *, mind_id: str, memory: Any) -> None:
        return None

    def memory_forgotten(self, *, mind_id: str, memory_id: str, reason: str = "") -> None:
        return None

    def memory_consolidated(self, *, mind_id: str, merged: int, removed: int) -> None:
        return None

    def relationship_created(self, *, mind_id: str, relationship: Any) -> None:
        return None

    def relationship_interaction(
        self, *, mind_id: str, relationship_id: str, positive: bool, trust_delta: float = 0.0
    ) -> None:
        return None

    def goal_created(self, *, mind_id: str, goal: Any) -> None:
        return None

    def goal_progress(
        self, *, mind_id: str, goal_id: str, progress: float, status: str
    ) -> None:
        return None

    def goal_completed(self, *, mind_id: str, goal_id: str, title: str = "") -> None:
        return None

    def goal_abandoned(self, *, mind_id: str, goal_id: str, reason: str = "") -> None:
        return None

    def record_life_event(self, *, mind_id: str, event_type: str, payload: Any) -> None:
        return None


class _RecordingDomainJournal(NullDomainJournal):
    """The real implementation: writes to the audit journal.

    Inherits from the null journal so that a future event family added to the
    protocol cannot silently be missing here — the inherited no-op is explicit
    and reviewable, rather than an AttributeError at runtime.
    """

    name = "audit"

    def __init__(self, audit: Any) -> None:
        self._audit = audit

    # -- internals --------------------------------------------------------- #

    def _record(self, event_type: str, *, mind_id: str, build_payload: Any) -> None:
        """Write one event. Never raises, by construction.

        `build_payload` is a callable rather than a dict on purpose. Building the
        payload *before* entering the guard meant that a domain object with a
        raising property (or any bug in the mapping code) escaped into the caller's
        operation — which is precisely what rule 2 forbids. Passing a callable
        makes evaluating the payload part of the guarded work, so the guarantee
        cannot be broken by a future change to the mapping helpers.

        The exception is logged rather than swallowed, so a persistent journal
        failure is still visible, but it never propagates into the domain
        operation that triggered it.
        """
        try:
            payload = build_payload()
            self._audit.record(
                event_type,
                mind_id=mind_id,
                actor_type="mind",
                actor_id=mind_id,
                # Inherit the turn's correlation id so the timeline joins up
                # (plan item D3). Falls back to a fresh id inside the service
                # when there is no scope, which is correct: an event created
                # outside a turn does not belong to one.
                correlation_id=current_correlation_id(),
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001 - see docstring
            logger.warning(
                "could not journal %s for %s: %s: %s",
                event_type,
                mind_id,
                type(exc).__name__,
                exc,
            )

    @staticmethod
    def _memory_payload(memory: Any) -> dict:
        """Identity and metadata only. Content and text are deliberately absent."""
        memory_type = getattr(memory, "type", None)
        if memory_type is not None and hasattr(memory_type, "value"):
            memory_type = memory_type.value

        payload: dict = {
            "memory_id": str(getattr(memory, "id", "") or ""),
            "memory_type": memory_type,
            "importance": getattr(memory, "importance", None),
        }

        # Scope labels describe where a memory belongs, not what it says, so they
        # are safe and useful for access review.
        for attribute, key in (
            ("relationship_context", "relationship_context"),
            ("environment_id", "environment_id"),
            ("user_email", "user_email"),
        ):
            value = getattr(memory, attribute, None)
            if value:
                payload[key] = _truncate(value)

        tags = getattr(memory, "tags", None)
        if tags:
            payload["tags"] = [_truncate(tag, 60) for tag in list(tags)[:10]]

        # Length is a useful signal for review ("an 11k-character memory") without
        # disclosing the content.
        content = getattr(memory, "content", None)
        if isinstance(content, str):
            payload["content_length"] = len(content)

        return {key: value for key, value in payload.items() if value is not None}

    # -- memory ------------------------------------------------------------ #

    def memory_accepted(self, *, mind_id: str, memory: Any) -> None:
        self._record(
            EventType.MEMORY_ACCEPTED,
            mind_id=mind_id,
            build_payload=lambda: self._memory_payload(memory),
        )

    def memory_forgotten(self, *, mind_id: str, memory_id: str, reason: str = "") -> None:
        self._record(
            EventType.MEMORY_FORGOTTEN,
            mind_id=mind_id,
            build_payload=lambda: {"memory_id": memory_id, "reason": _truncate(reason)},
        )

    def memory_consolidated(self, *, mind_id: str, merged: int, removed: int) -> None:
        self._record(
            EventType.MEMORY_CONSOLIDATED,
            mind_id=mind_id,
            build_payload=lambda: {"merged": merged, "removed": removed},
        )

    # -- relationships ------------------------------------------------------ #

    def relationship_created(self, *, mind_id: str, relationship: Any) -> None:
        def build() -> dict:
            payload: dict = {
                "relationship_id": str(getattr(relationship, "id", "") or ""),
                # The *kind* of relationship, not the entity's name. A person's name
                # attached to every relationship event would make the journal a
                # contact list.
                "relationship_type": _truncate(getattr(relationship, "relationship_type", None)),
                "is_mind": bool(getattr(relationship, "is_mind_relationship", lambda: False)()),
            }
            for attribute in ("trust_level", "bond_strength"):
                value = getattr(relationship, attribute, None)
                if isinstance(value, (int, float)):
                    payload[attribute] = round(float(value), 4)
            return payload

        self._record(EventType.RELATIONSHIP_CREATED, mind_id=mind_id, build_payload=build)

    def relationship_interaction(
        self, *, mind_id: str, relationship_id: str, positive: bool, trust_delta: float = 0.0
    ) -> None:
        self._record(
            EventType.RELATIONSHIP_INTERACTION,
            mind_id=mind_id,
            build_payload=lambda: {
                "relationship_id": relationship_id,
                "positive": bool(positive),
                "trust_delta": round(float(trust_delta), 4),
            },
        )

    # -- goals -------------------------------------------------------------- #

    def goal_created(self, *, mind_id: str, goal: Any) -> None:
        def build() -> dict:
            return {
                "goal_id": str(
                    getattr(goal, "goal_id", "") or getattr(goal, "id", "") or ""
                ),
                "status": _truncate(getattr(goal, "status", None), 40),
                # Truncated because a goal title is a short label; a long body
                # would be content, and content does not belong here.
                "title": _truncate(getattr(goal, "title", None), 120),
            }

        self._record(EventType.GOAL_CREATED, mind_id=mind_id, build_payload=build)

    def goal_progress(
        self, *, mind_id: str, goal_id: str, progress: float, status: str
    ) -> None:
        self._record(
            EventType.GOAL_PROGRESS,
            mind_id=mind_id,
            build_payload=lambda: {
                "goal_id": goal_id,
                "progress": round(float(progress), 4),
                "status": _truncate(status, 40),
            },
        )

    def goal_completed(self, *, mind_id: str, goal_id: str, title: str = "") -> None:
        self._record(
            EventType.GOAL_COMPLETED,
            mind_id=mind_id,
            build_payload=lambda: {"goal_id": goal_id, "title": _truncate(title, 120)},
        )

    def goal_abandoned(self, *, mind_id: str, goal_id: str, reason: str = "") -> None:
        self._record(
            EventType.GOAL_ABANDONED,
            mind_id=mind_id,
            build_payload=lambda: {"goal_id": goal_id, "reason": _truncate(reason)},
        )

    # -- generic ------------------------------------------------------------ #
    #
    # An escape hatch for event families that do not warrant a method each, such
    # as the life-state events (Phase N). Deliberately still routed through
    # `_record`, so the payload is evaluated inside the guard and a caller cannot
    # accidentally bypass the "never raises" guarantee.
    #
    # It does *not* let a caller choose the redaction policy: `_record` passes the
    # payload through the same writer as everything else, so the secret-shape
    # redaction still applies. What a caller can do here is include content, and
    # that is intentional for this path — a commitment's text is journalled on
    # purpose, because an obligation nobody can read is not an obligation. Callers
    # adding new event families should mirror that judgement rather than assume it.
    def record_life_event(self, *, mind_id: str, event_type: str, payload: Any) -> None:
        self._record(
            event_type,
            mind_id=mind_id,
            build_payload=lambda: dict(payload) if payload else {},
        )


_journal: Optional[DomainJournal] = None


def get_domain_journal() -> DomainJournal:
    """The process-wide domain journal.

    Returns a :class:`NullDomainJournal` when the audit service cannot be
    constructed — for example in a unit test of the storage layer with no
    database configured. Domain code therefore never needs to guard the call.
    """
    global _journal
    if _journal is not None:
        return _journal

    try:
        from genesis.governance.audit import get_audit_service

        _journal = _RecordingDomainJournal(get_audit_service())
    except Exception as exc:  # noqa: BLE001 - governance is optional for storage
        logger.debug("domain journal unavailable, using null journal: %s", exc)
        _journal = NullDomainJournal()
    return _journal


def set_domain_journal(journal: Optional[DomainJournal]) -> Optional[DomainJournal]:
    """Install a specific journal (tests, embedded hosts)."""
    global _journal
    _journal = journal
    return _journal


def reset_domain_journal() -> None:
    """Clear the cached journal so the next call re-resolves it."""
    global _journal
    _journal = None
