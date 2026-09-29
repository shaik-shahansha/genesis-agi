"""Enforced AI disclosure.

A Mind must not pass as a person. That is the line between a digital being and a
deception, and it is the line on which this project would be judged — so
disclosure is not a template the caller may remember to include. The adapter adds
it, and `ChannelCapabilities.supports_disclosure` makes a channel that cannot
carry it refuse to register rather than send quietly.

Two implementation choices worth naming:

* **The marker is stable and machine-checkable.** `is_disclosed` detects it
  without parsing prose, so a duplicate append is impossible and a test can
  assert the property rather than the wording.
* **It goes in the body, not a header.** Some receivers strip headers, and a
  stripped disclosure is a silently broken guarantee. A slightly clumsy footer
  is the lesser cost.
"""

from __future__ import annotations

from .base import ChannelIdentity

#: Machine-checkable marker. Present in every disclosed body exactly once.
DISCLOSURE_MARKER = "\u2014 AI-operated digital being"


def compose_disclosure(identity: ChannelIdentity) -> str:
    """The disclosure block for an identity.

    Names the administrator as well as the AI status, because "this is an AI" is
    only half of what a recipient needs — the other half is *who is responsible
    for it*. An anonymous AI is worse than no disclosure at all.
    """
    lines = [
        f"{identity.display_name}",
        f"Genesis Digital Being — {identity.address}",
    ]
    if identity.administrator:
        lines.append(f"Operated by {identity.administrator}")
    lines.append(
        "This message was generated and sent by an AI-operated digital being, "
        "not by a person."
    )
    return "\n".join(lines)


def is_disclosed(body: str) -> bool:
    """Whether a body already carries the disclosure marker."""
    return DISCLOSURE_MARKER in body or "AI-operated digital being" in body


def apply_disclosure(body: str, identity: ChannelIdentity, *, signature: bool = True) -> str:
    """Return `body` with the disclosure appended, exactly once.

    Idempotent: applying twice does not double the footer, which matters because
    `prepare()` may be called more than once for the same intent (governance can
    re-evaluate after an approval).

    A body that already discloses is left alone. That is not an optimisation —
    rewriting a caller's deliberate disclosure would be the adapter overriding
    the Mind, which is the opposite of the rule that adapters do not decide.
    """
    if is_disclosed(body):
        return body

    block = compose_disclosure(identity)
    separator = "\n\n" if body and not body.endswith("\n\n") else ""
    if not signature:
        return f"{body}{separator}{block}"
    return f"{body}{separator}—\n{block}"


def assert_disclosed(body: str, identity: ChannelIdentity) -> None:
    """Raise if a body is not disclosed.

    Called by adapters immediately before handing a message to a provider, so a
    bug anywhere upstream becomes a loud failure instead of an undisclosed
    message reaching a human.
    """
    if not is_disclosed(body):
        raise AssertionError(
            f"refusing to send an undisclosed message on channel {identity.channel!r}; "
            "every outbound message must state that it is AI-operated"
        )
