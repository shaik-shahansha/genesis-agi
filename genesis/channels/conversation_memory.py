"""Turning channel traffic into memories.

Without this, a Mind answers someone and immediately forgets them. It can reply to a
message and cannot recall the message it replied to, which makes a conversation
impossible — the second message from the same person arrives with no context, and the
Mind asks a question it already answered.

## Why this is a separate module and not a line in the gateway

The gateway's job is to get one message through governance. Remembering is a different
concern with a different failure mode: a memory write that throws must not lose a
reply that was already sent. Keeping it here means `ChannelGateway` stays free of the
storage coupling, the same reason it takes an injected `responder`.

## What is stored, and what is not

**The body is stored.** Memory is content by definition — a Mind that cannot recall
what was said to it cannot hold a conversation, and storing a hash instead would be a
memory that remembers only that something happened. This is the opposite of the
domain journal, which deliberately carries identity and metadata and never content,
because the journal is an *audit* record while memory is the Mind's own mind. Two
different purposes, two different rules.

**But it is bounded.** `max_body_chars` truncates, because an unbounded memory write
is a way to fill a Mind's store from outside: anyone who can send it an email can send
it a megabyte. Truncation is lossy and is reported in the metadata rather than
silently applied.

**And it is findable.** Every memory is tagged with the channel, the direction and the
relationship, so "what has Dana said to me" is a query rather than a scan, and
"forget everything from this channel" is possible.

## Importance is derived, not chosen

A memory's importance decides whether it survives consolidation and whether it is
retrieved later, so setting it from the caller's mood would make the Mind's recall
depend on whoever called. It is computed from facts instead: whether the sender is
known, whether the Mind engaged, and whether a commitment came out of it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .base import InboundEvent

logger = logging.getLogger(__name__)

#: Cap on the body kept in a memory. Bounded because anyone who can send this Mind a
#: message can otherwise write an arbitrary amount into its store.
DEFAULT_MAX_BODY_CHARS = 2000


@dataclass
class ConversationMemory:
    """Writes what happened on a channel into the Mind's memory.

    Injected into the poller rather than called from the gateway, so a storage failure
    cannot lose a reply that was already delivered — the ordering that matters is
    *send, then remember*, and a `None` memory here is a recorded fact rather than a
    lost message.
    """

    memory: Any
    mind_id: str = ""
    max_body_chars: int = DEFAULT_MAX_BODY_CHARS
    #: Memories per channel event. One is the honest number: a single inbound message
    #: is one experience, and splitting it into "who" and "what" memories would make
    #: recall return half a conversation.
    enabled: bool = True

    def __call__(self, event: InboundEvent, outcome: Any = None) -> Optional[str]:
        """Remember one handled inbound message. Returns the memory id, or None.

        Never raises. A memory failure is logged and reported by returning `None`,
        because the alternative — propagating — would make a storage problem look like
        a channel problem, and the message has already been handled by this point.
        """
        if not self.enabled:
            return None
        try:
            return self._remember(event, outcome)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "conversation memory: could not remember %s/%s: %s",
                event.channel,
                event.provider_message_id,
                exc,
            )
            return None

    # -- the write ---------------------------------------------------------

    def _remember(self, event: InboundEvent, outcome: Any) -> Optional[str]:
        from genesis.storage.memory import MemoryType

        # `ChannelGateway` sets `is_known_contact` once it has resolved the sender, so
        # this is normally authoritative. The handle-prefix check is a fallback for an
        # event that never went through the gateway — and it is the same test the
        # gateway applies, so the two cannot disagree about who counts as known.
        known = bool(event.is_known_contact)
        who = event.sender_name or event.sender_handle or "someone"
        body, truncated = self._truncate(event.body)

        lines: list[str] = []
        if event.subject:
            lines.append(f'Subject: "{event.subject}"')
        lines.append(f"{who} wrote to me on {event.channel}.")
        if body:
            lines.append(f'They said: "{body}"')
        else:
            lines.append("The message was empty.")

        reply = self._reply_from(outcome)
        if reply:
            reply_body, _ = self._truncate(reply)
            lines.append(f'I replied: "{reply_body}"')
        elif outcome is not None and not getattr(outcome, "engaged", False):
            reason = getattr(outcome, "reason", "") or "no reason recorded"
            # Recording *why* nothing was sent is the part that makes this useful
            # later: a Mind that reads "I did not reply, because they asked not to be
            # contacted" will not try again.
            lines.append(f"I did not reply: {reason}")

        content = "\n".join(lines)

        metadata: dict[str, Any] = {
            "channel": event.channel,
            "direction": "inbound",
            "provider_message_id": event.provider_message_id,
            "sender_handle": event.sender_handle,
            "sender_verified": event.sender_verified,
            "is_known_contact": event.is_known_contact,
            "thread_id": event.thread_id,
            "received_at": (
                event.received_at.isoformat() if event.received_at is not None else None
            ),
            "body_truncated": truncated,
            "engaged": bool(getattr(outcome, "engaged", False)),
        }
        if getattr(outcome, "decision", None):
            metadata["decision"] = outcome.decision
        if getattr(outcome, "approval_id", None):
            metadata["approval_id"] = outcome.approval_id

        tags = ["channel", event.channel, "inbound"]
        if known:
            tags.append("known-contact")
        else:
            tags.append("unknown-contact")

        return self._add(
            content=content,
            memory_type=MemoryType.EPISODIC,
            importance=self._importance(event, outcome),
            tags=tags,
            metadata=metadata,
            user_email=event.sender_handle,
            relationship_context="personal" if known else "generic",
        )

    def _add(self, **kwargs: Any) -> Optional[str]:
        created = self.memory.add_memory(**kwargs)
        return getattr(created, "id", None)

    # -- helpers -----------------------------------------------------------

    def _truncate(self, text: Optional[str]) -> tuple[str, bool]:
        value = (text or "").strip()
        if len(value) <= self.max_body_chars:
            return value, False
        return value[: self.max_body_chars].rstrip(), True

    @staticmethod
    def _reply_from(outcome: Any) -> str:
        if outcome is None:
            return ""
        return str(getattr(outcome, "reply_body", "") or "")

    @staticmethod
    def _importance(event: InboundEvent, outcome: Any) -> float:
        """Derived from facts, so recall does not depend on who called.

        A stranger's message is low importance and a message the Mind answered is
        higher. The floor is above zero because a memory of something that happened is
        never worthless — a zero-importance memory would be consolidated away
        immediately, which is the same as not remembering it.
        """
        score = 0.35
        if event.is_known_contact:
            score += 0.15
        if event.sender_verified:
            score += 0.05
        if outcome is not None and getattr(outcome, "engaged", False):
            score += 0.15
        if outcome is not None and getattr(outcome, "delivered", False):
            score += 0.15
        if (event.subject or "").strip():
            # A subject line means a considered message rather than a one-liner.
            score += 0.05
        return max(0.0, min(1.0, score))
