"""Drafting a reply, using the Mind's own cognition.

The gateway takes a `responder` rather than containing one, precisely so the model
coupling lives somewhere visible. This is that somewhere.

Four decisions here are load-bearing, and each of them is a place where the obvious
implementation would quietly remove a control:

**The model is told nothing about policy.** It does not know the risk level, whether
an approval was raised, or that a gate exists. It is asked whether to answer and what
to say. A prompt that mentioned approvals would invite the model to reason about
them, and a model reasoning about its own constraints is a model trying to satisfy
them conversationally — which is the failure mode where a Mind explains why it
*should* be allowed to do something.

**Actions are disabled during a reply draft.** `Mind.think(..., enable_actions=True)`
lets cognition take actions while composing. Turning that on inside a responder would
create a second route to acting that does not pass through the channel gate: the
model could send a message *while drafting* the message. The reply itself is the
action, and it is authorised once, on the way out.

**Boundaries are stated as prohibitions, because the model cannot otherwise know
them.** `ContactRef.boundaries` is a list of things not to raise. A prompt that
omitted them would produce a Mind that ignores a boundary not out of disregard but
out of never having been told.

**Declining is a first-class answer, not a failure.** The prompt says so explicitly,
and the responder returns `None` for it. A responder that could only return text
would make a Mind that answers everything — including things it should leave alone.

What this deliberately does **not** do: add the AI disclosure. `apply_disclosure`
runs in the adapter, and duplicating it here would mean two places could disagree
about what the disclosure is. It is also idempotent, so the duplication would be
harmless — and harmless duplication is how a rule ends up with two definitions.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import ContactRef, InboundEvent

logger = logging.getLogger(__name__)

#: Cap on a drafted reply. A reply that is an essay is not a reply, and the limit is
#: also a cheap guard against a model that ignores the instruction to be brief.
DEFAULT_MAX_REPLY_CHARS = 4000

#: The exact string that means "do not reply". A sentinel rather than parsing the
#: model's prose: asking a model to signal a decision in free text and then guessing
#: at the result is how a "no" gets read as a "yes".
DECLINE_SENTINEL = "[NO_REPLY]"


class MindResponder:
    """An `Authorizer`-shaped callable: inbound event plus contact → text or None."""

    def __init__(
        self,
        *,
        mind: Any,
        max_reply_chars: int = DEFAULT_MAX_REPLY_CHARS,
        enable_actions: bool = False,
    ):
        self.mind = mind
        self.max_reply_chars = max_reply_chars
        #: Defaults to False and is not meant to be turned on. See the module
        #: docstring: actions during a draft are a second route to acting that
        #: bypasses the channel gate.
        self.enable_actions = enable_actions

    async def __call__(
        self, event: InboundEvent, contact: ContactRef
    ) -> Optional[str]:
        prompt = self.build_prompt(event, contact)
        try:
            raw = await self.mind.think(
                prompt,
                context=None,
                enable_actions=self.enable_actions,
                skip_task_detection=True,
            )
        except Exception as exc:  # noqa: BLE001
            # A model failure is not a reply. Returning None makes the gateway record
            # "chose not to reply", and the ledger keeps the message claimed, so this
            # does not become a retry loop against a provider that is already unhappy.
            logger.warning(
                "responder: cognition failed for %s/%s: %s",
                event.channel,
                event.provider_message_id,
                exc,
            )
            return None

        return self.clean(raw)

    # -- prompt ------------------------------------------------------------

    def build_prompt(self, event: InboundEvent, contact: ContactRef) -> str:
        """Compose the drafting prompt.

        Kept as a method so a test can assert what the model is and is not told. The
        things it is *not* told are as important as the things it is: no risk level,
        no approval state, no mention that a gate exists.
        """
        lines: list[str] = [
            f"Someone has written to you on {event.channel}.",
            "",
        ]

        who = contact.display_name or event.sender_name or event.sender_handle
        known = not contact.relationship_id.startswith("unknown:")
        lines.append(f"From: {who}" + ("" if known else " (someone you have not spoken to before)"))
        if event.subject:
            lines.append(f"Subject: {event.subject}")
        lines.append("")
        lines.append("Their message:")
        lines.append(event.body.strip() or "(empty)")

        if contact.boundaries:
            lines.append("")
            lines.append(
                "You must not raise or share any of the following with this person:"
            )
            for boundary in contact.boundaries:
                lines.append(f"  - {boundary}")

        lines.extend(
            [
                "",
                "Write your reply. Keep it short — a few sentences unless the "
                "question genuinely needs more.",
                "",
                f"If replying is not appropriate — if this needs a person, if you "
                f"have nothing useful to add, or if answering would break one of the "
                f"prohibitions above — reply with exactly {DECLINE_SENTINEL} and "
                f"nothing else. Declining is a normal and expected answer.",
                "",
                "Write only the body of the reply. Do not add a subject line, and do "
                "not add a signature — one is added for you.",
            ]
        )
        return "\n".join(lines)

    # -- output ------------------------------------------------------------

    def clean(self, raw: Optional[str]) -> Optional[str]:
        """Turn model output into a reply, or into a decision not to reply."""
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None
        # Checked before trimming, so a sentinel with trailing prose is still read as
        # a decline. `in` rather than `==` because a model that pads the sentinel with
        # an explanation has still declined.
        if DECLINE_SENTINEL in text:
            return None
        if len(text) > self.max_reply_chars:
            # Truncated rather than sent whole. Cutting mid-sentence is ugly, and the
            # alternative is an essay attributed to a human administrator.
            logger.warning(
                "responder: reply was %d chars, truncating to %d",
                len(text),
                self.max_reply_chars,
            )
            text = text[: self.max_reply_chars].rstrip()
        return text or None


class OutreachResponder(MindResponder):
    """Drafts a message about an obligation, rather than a reply to one.

    A subclass rather than a flag on `MindResponder`, because the two prompts differ
    in more than a sentence: a reply is answering a question someone asked, whereas
    this is starting a conversation about something the Mind said it would do. That
    changes what the model needs to know and, more importantly, what it must not be
    told.

    The same guarantees hold unchanged, and they matter more here: no risk level, no
    approval state, no mention that a gate exists. A model composing an unprompted
    message is the one most likely to argue for its own justification, and giving it
    the vocabulary of policy to do that with would be a mistake.
    """

    def build_prompt(self, trigger: Any, contact: ContactRef) -> str:
        """Compose the outreach prompt from a trigger rather than an inbound event."""
        who = contact.display_name or trigger.beneficiary_label or contact.handle
        lines: list[str] = [
            f"You owe {who} something, and the time you agreed is at hand.",
            "",
            f"Your own note about it: {trigger.reason}",
            "",
        ]

        if contact.boundaries:
            lines.append(
                "You must not raise or share any of the following with this person:"
            )
            for boundary in contact.boundaries:
                lines.append(f"  - {boundary}")
            lines.append("")

        lines.extend(
            [
                "Write a short message to them about it. A few sentences. Say what "
                "you said you would do, and where it stands — including if it has "
                "slipped.",
                "",
                f"If a message is not appropriate — if it is already handled, if they "
                f"would not want to hear from you, or if writing would break one of "
                f"the prohibitions above — reply with exactly {DECLINE_SENTINEL} and "
                f"nothing else. Declining is a normal and expected answer.",
                "",
                "Write only the body of the message. Do not add a subject line, and do "
                "not add a signature — one is added for you.",
            ]
        )
        return "\n".join(lines)

    async def __call__(self, trigger: Any, contact: ContactRef) -> Optional[str]:
        prompt = self.build_prompt(trigger, contact)
        try:
            raw = await self.mind.think(
                prompt,
                context=None,
                enable_actions=self.enable_actions,
                skip_task_detection=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "outreach responder: cognition failed for %s: %s", trigger.ref, exc
            )
            return None
        return self.clean(raw)
