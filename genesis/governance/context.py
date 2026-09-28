"""Correlation context for a unit of cognition.

**Why this exists (plan item D1/D3, ADR-0008 §1).**

The journal alone is not enough to answer the question a user actually asks:
*"why did the Mind send that email?"* For that, the events belonging to one
cognitive turn have to be joinable — the turn, the memory retrievals it did, the
plan it formed, the policy decision, the approval, the execution, the receipt.

Each event already carries a ``correlation_id``. What was missing was a way for
*caller* code to say "everything from here is part of the same turn" without
threading an id through every function signature. That is what a context variable
is for.

Usage:

```python
with correlation_scope() as correlation_id:
    # Every event, receipt and approval created in this block inherits
    # `correlation_id` unless one is passed explicitly.
    retrieved = memory.search(...)
    plan = reason(...)
    result = await executor.request_action(...)
```

The consequence is that a timeline query for one ``correlation_id`` returns the
whole causal chain, which is the "single timeline" ADR-0008 §context says was
impossible before.

Notes
-----
* **Nested scopes restore the outer value**, so a sub-task can be traced without
  losing the turn it belongs to.
* **Absent a scope, there is no correlation id.** Events created outside any
  scope get their own (the audit service falls back to a fresh id), rather than
  being attributed to a turn that does not exist.
* Context variables are per-task in asyncio, so concurrent Mind turns do not
  share an id.
"""

from __future__ import annotations

import contextvars
import secrets
from contextlib import contextmanager
from typing import Iterator, Optional

__all__ = [
    "current_correlation_id",
    "set_correlation_id",
    "correlation_scope",
    "new_correlation_id",
    "explain_chain",
]


_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "genesis_correlation_id", default=None
)

#: Optional free-text label for the current scope, e.g. "chat turn" or
#: "autonomous tick". Recorded so a timeline can say what kind of turn this was
#: without parsing the events.
_correlation_label: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "genesis_correlation_label", default=None
)


def new_correlation_id() -> str:
    """A fresh, opaque correlation id."""
    return f"cor_{secrets.token_hex(10)}"


def current_correlation_id() -> Optional[str]:
    """The correlation id of the current scope, if any."""
    return _correlation_id.get()


def current_correlation_label() -> Optional[str]:
    """The label of the current scope, if any."""
    return _correlation_label.get()


def set_correlation_id(correlation_id: Optional[str]) -> None:
    """Set the correlation id without a scope.

    Prefer :func:`correlation_scope`, which restores the previous value. This is
    for the rare case where a value is adopted for the rest of a task.
    """
    _correlation_id.set(correlation_id)


@contextmanager
def correlation_scope(
    correlation_id: Optional[str] = None, *, label: Optional[str] = None
) -> Iterator[str]:
    """Run a block in which everything shares one correlation id.

    Args:
        correlation_id: Reuse an existing id (e.g. resuming a suspended
            objective). A fresh one is generated when omitted.
        label: Free-text description of the turn, for the timeline.

    Yields:
        The correlation id in force inside the block.
    """
    resolved = correlation_id or new_correlation_id()
    token_id = _correlation_id.set(resolved)
    token_label = _correlation_label.set(label)
    try:
        yield resolved
    finally:
        # Restore rather than clear, so nesting preserves the outer turn.
        _correlation_id.reset(token_id)
        _correlation_label.reset(token_label)


def explain_chain(events: list) -> dict:
    """Summarise a set of journal events as a causal chain.

    Takes the events for one ``correlation_id`` (as returned by
    ``AuditService.events``) and produces the shape the workspace timeline needs:
    an ordered list with the decision that caused each step.

    Deliberately tolerant: it accepts ``AuditEvent`` objects or plain dicts, and
    it does not require every event to be present. A partial chain is still
    useful, and an incomplete journal should not make the UI raise.
    """
    def _get(event, key, default=None):
        if isinstance(event, dict):
            return event.get(key, default)
        return getattr(event, key, default)

    ordered = sorted(events, key=lambda event: _get(event, "sequence", 0))

    steps: list[dict] = []
    for event in ordered:
        payload = _get(event, "payload", {}) or {}
        steps.append(
            {
                "event_id": _get(event, "event_id"),
                "type": _get(event, "type"),
                "at": _get(event, "timestamp"),
                "sequence": _get(event, "sequence"),
                "actor_type": _get(event, "actor_type"),
                "actor_id": _get(event, "actor_id"),
                "causation_id": _get(event, "causation_id"),
                # A short, safe summary. The payload is already redacted at
                # write time, so this cannot leak what the journal does not hold.
                "summary": _summarise(payload),
                "payload": payload,
            }
        )

    return {
        "correlation_id": _get(ordered[0], "correlation_id") if ordered else None,
        "steps": steps,
        "count": len(steps),
        "types": [step["type"] for step in steps],
    }


#: Payload keys worth showing in a one-line summary, in preference order.
_SUMMARY_KEYS = (
    "action_name",
    "outcome",
    "decision",
    "reason_code",
    "approval_id",
    "grant_id",
    "receipt_id",
    "memory_type",
    "relationship_id",
    "goal_id",
    "detail",
    "note",
    "reason",
)


def _summarise(payload: dict) -> str:
    """A compact, human-readable line for an event."""
    if not payload:
        return ""
    parts = [f"{key}={payload[key]}" for key in _SUMMARY_KEYS if payload.get(key) is not None]
    if parts:
        return ", ".join(parts[:4])
    # Fall back to the first couple of scalar values, so an unfamiliar event type
    # still shows something rather than nothing.
    scalars = [
        f"{key}={value}"
        for key, value in payload.items()
        if isinstance(value, (str, int, float, bool)) and len(str(value)) < 60
    ]
    return ", ".join(scalars[:3])
