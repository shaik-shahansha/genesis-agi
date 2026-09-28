"""Commitments: what a Mind owes, to whom, by when.

**Phase N1–N4.** See `docs/v3/DIGITAL_LIFE_STATE.md` for the reasoning.

The distinction from memory is the whole point, and it is worth restating in the
code:

| Memory | Commitment |
|---|---|
| Describes | Obliges |
| Fades when irrelevant | **Must not fade** — forgetting an obligation is a failure |
| Nobody is accountable | Has a named beneficiary |
| Private to the Mind | Visible to the person owed |

Three design decisions follow from that, and each is enforced here rather than
left to callers:

**1. The beneficiary is a relationship, not a string.** A free-text name cannot be
notified, cannot be asked to renegotiate, and cannot be shown what it is owed.
``beneficiary_id`` references a relationship; ``beneficiary_label`` exists only for
display and is never the source of truth.

**2. Missing a commitment is an event, not an expiry.** ``mark_missed`` records
``commitment.missed`` in the journal. A being that quietly drops its obligations is
worse than one that never made them, and a silent deadline lapse is
indistinguishable from a decision to abandon.

**3. Creation is gated.** A commitment that binds a third party reaches outside the
being (R3 per ADR-0006), so it needs a human decision. When a governance gate is
supplied, creation consults it: an R1 commitment to the owner is created directly,
an R3 one is created in ``PROPOSED`` and waits. Without a gate the manager is
usable standalone (unit tests, scripts), which is why the gate is optional — but
the *capability names* and risk declarations live in the registry either way, so
the classification is not a caller's choice.

Not implemented here, deliberately: autonomous commitment creation. A Mind that
invents obligations is a liability, and a test asserts nothing in this module
creates a commitment without an explicit call.
"""

from __future__ import annotations

import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from genesis.governance.models import EventType

logger = logging.getLogger(__name__)

__all__ = [
    "CommitmentStatus",
    "Commitment",
    "CommitmentError",
    "CommitmentNotFoundError",
    "CommitmentTransitionError",
    "CommitmentManager",
    "capability_for_beneficiary",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CommitmentError(RuntimeError):
    """Base class for commitment failures."""


class CommitmentNotFoundError(CommitmentError):
    """No commitment exists for the given id."""


class CommitmentTransitionError(CommitmentError):
    """An illegal status transition was attempted."""


class CommitmentStatus(str, Enum):
    """Lifecycle. ``PROPOSED`` exists because a binding commitment needs a human."""

    PROPOSED = "PROPOSED"
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    #: Terminal states
    FULFILLED = "FULFILLED"
    MISSED = "MISSED"
    RENEGOTIATED = "RENEGOTIATED"
    WITHDRAWN = "WITHDRAWN"

    @property
    def is_terminal(self) -> bool:
        return self in (
            CommitmentStatus.FULFILLED,
            CommitmentStatus.MISSED,
            CommitmentStatus.RENEGOTIATED,
            CommitmentStatus.WITHDRAWN,
        )

    @property
    def is_open(self) -> bool:
        return self in (CommitmentStatus.OPEN, CommitmentStatus.IN_PROGRESS)


#: Legal transitions. Anything absent is refused, which makes this a control
#: rather than a convention (the same approach as the approval state machine).
TRANSITIONS: Dict[CommitmentStatus, frozenset] = {
    CommitmentStatus.PROPOSED: frozenset(
        {CommitmentStatus.OPEN, CommitmentStatus.WITHDRAWN, CommitmentStatus.MISSED}
    ),
    CommitmentStatus.OPEN: frozenset(
        {
            CommitmentStatus.IN_PROGRESS,
            CommitmentStatus.FULFILLED,
            CommitmentStatus.MISSED,
            CommitmentStatus.RENEGOTIATED,
            CommitmentStatus.WITHDRAWN,
        }
    ),
    CommitmentStatus.IN_PROGRESS: frozenset(
        {
            CommitmentStatus.FULFILLED,
            CommitmentStatus.MISSED,
            CommitmentStatus.RENEGOTIATED,
            CommitmentStatus.WITHDRAWN,
        }
    ),
    # A renegotiated commitment is re-opened with a new deadline.
    CommitmentStatus.RENEGOTIATED: frozenset({CommitmentStatus.OPEN}),
    CommitmentStatus.FULFILLED: frozenset(),
    CommitmentStatus.MISSED: frozenset({CommitmentStatus.RENEGOTIATED}),
    CommitmentStatus.WITHDRAWN: frozenset(),
}


def can_transition(current: CommitmentStatus, target: CommitmentStatus) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


#: Beneficiary kinds, and the capability each maps to. The manager picks the name;
#: the policy engine decides the risk. Callers do not get to choose the level.
BENEFICIARY_OWNER = "owner"
BENEFICIARY_THIRD_PARTY = "third_party"
BENEFICIARY_SELF = "self"
BENEFICIARY_MIND = "mind"


def capability_for_beneficiary(beneficiary_kind: str) -> str:
    """The governance capability name for creating a commitment to this kind.

    - owner / self: ``create_commitment`` — R1, reversible, internal
    - another Mind: ``create_commitment_cross_mind`` — R2, reaches outside
    - third party: ``commit_to_third_party`` — R3, a human must decide
    """
    kind = (beneficiary_kind or "").strip().lower()
    if kind in (BENEFICIARY_SELF, BENEFICIARY_OWNER, ""):
        return "create_commitment"
    if kind == BENEFICIARY_MIND:
        return "create_commitment_cross_mind"
    return "commit_to_third_party"


@dataclass
class Commitment:
    """One thing a Mind owes one beneficiary.

    ``what`` is the obligation in the being's own words, and unlike memory content
    it *is* journalled — an obligation nobody can read is not an obligation. That
    is a deliberate exception to the domain-journal rule that content never leaves
    the domain table: a commitment is expected to be shown to the person owed.

    ``provenance`` records what created it, so "why did the Mind promise this?" is
    answerable. It is required, not optional: a commitment with no traceable
    origin is exactly the autonomous obligation the design forbids.
    """

    commitment_id: str
    mind_id: str
    beneficiary_id: str
    beneficiary_label: str
    what: str
    provenance: str
    created_at: datetime
    status: str = CommitmentStatus.OPEN.value
    beneficiary_kind: str = BENEFICIARY_OWNER
    deadline: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_note: str = ""
    #: Optional link to an objective or action that will satisfy it.
    objective_id: Optional[str] = None
    correlation_id: Optional[str] = None
    #: Extended only through the explicit transitions below.
    transition_log: List[Dict[str, Any]] = field(default_factory=list)

    # -- properties -------------------------------------------------------- #

    @property
    def status_enum(self) -> CommitmentStatus:
        return CommitmentStatus(self.status)

    @property
    def is_open(self) -> bool:
        return self.status_enum.is_open

    @property
    def is_overdue(self) -> bool:
        """Open, and past its deadline. Not the same as MISSED.

        An overdue commitment has not been decided about yet — the honour path is
        for the Mind (or its owner) to fulfil it, renegotiate, or explicitly mark
        it missed. Treating lateness as automatic failure would erase the
        distinction between "late" and "abandoned", which is the one a beneficiary
        cares about.
        """
        if not self.is_open or self.deadline is None:
            return False
        return _utcnow() > self.deadline

    @property
    def is_at_risk(self) -> bool:
        """Open, not yet overdue, and due within 24 hours."""
        if not self.is_open or self.deadline is None:
            return False
        return timedelta(0) <= (self.deadline - _utcnow()) <= timedelta(hours=24)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commitment_id": self.commitment_id,
            "mind_id": self.mind_id,
            "beneficiary_id": self.beneficiary_id,
            "beneficiary_label": self.beneficiary_label,
            "beneficiary_kind": self.beneficiary_kind,
            "what": self.what,
            "status": self.status,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_note": self.resolution_note,
            "provenance": self.provenance,
            "objective_id": self.objective_id,
            "correlation_id": self.correlation_id,
            "is_overdue": self.is_overdue,
            "is_at_risk": self.is_at_risk,
            "transition_log": [dict(entry) for entry in self.transition_log],
        }


class _Gate(Protocol):  # pragma: no cover - structural typing
    def authorize(self, context: Any, **kwargs: Any) -> Any: ...


class CommitmentManager:
    """Create, track and close commitments for one Mind.

    In-memory by default, mirroring the existing domain managers (goals, tasks,
    relationships) which are serialised with the Mind rather than stored
    relationally. Phase N10 persists them; until then a manager is loaded and
    saved whole, which is why the state is a plain dict of dataclasses.
    """

    def __init__(self, mind_id: str, gate: Optional[_Gate] = None) -> None:
        self.mind_id = mind_id
        self.commitments: Dict[str, Commitment] = {}
        #: True when a governance gate was supplied, so a binding commitment is
        #: queued rather than created. Exposed so a caller can tell the
        #: difference between "nothing to approve" and "no gate to approve it".
        self.gated = gate is not None
        self._gate = gate
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ #
    # Creation
    # ------------------------------------------------------------------ #

    def create(
        self,
        *,
        beneficiary_id: str,
        what: str,
        provenance: str,
        beneficiary_label: str = "",
        beneficiary_kind: str = BENEFICIARY_OWNER,
        deadline: Optional[datetime] = None,
        objective_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Commitment:
        """Record a new commitment.

        Requires explicit provenance (what created it) because a commitment with
        no traceable origin is the autonomous obligation this design forbids.

        When a governance gate is configured and the beneficiary is not the owner,
        the commitment is created in ``PROPOSED`` and an approval is raised. The
        caller sees ``PROPOSED`` rather than ``OPEN``, so nothing is owed until a
        human agrees.
        """
        if not what or not what.strip():
            raise CommitmentError("a commitment must say what is owed")
        if not provenance or not provenance.strip():
            raise CommitmentError(
                "a commitment requires provenance (what created it); an obligation "
                "with no traceable origin is exactly what this design forbids"
            )
        if not beneficiary_id:
            raise CommitmentError("a commitment requires a beneficiary")

        status = CommitmentStatus.OPEN
        approval_id: Optional[str] = None

        if self._gate is not None:
            status_value, approval_id = self._classify(
                beneficiary_kind=beneficiary_kind,
                what=what,
                beneficiary_id=beneficiary_id,
                objective_id=objective_id,
                correlation_id=correlation_id,
            )
            status = status_value

        now = _utcnow()
        commitment = Commitment(
            commitment_id=f"cmt_{secrets.token_hex(8)}",
            mind_id=self.mind_id,
            beneficiary_id=beneficiary_id,
            beneficiary_label=beneficiary_label or beneficiary_id,
            beneficiary_kind=beneficiary_kind,
            what=what.strip(),
            provenance=provenance.strip(),
            deadline=deadline,
            status=status.value,
            objective_id=objective_id,
            correlation_id=correlation_id or self._current_correlation_id(),
            created_at=now,
            transition_log=[
                {
                    "status": status.value,
                    "at": now.isoformat(),
                    "note": (
                        f"awaiting approval {approval_id}" if approval_id else "created"
                    ),
                }
            ],
        )

        with self._lock:
            self.commitments[commitment.commitment_id] = commitment

        self._journal(
            EventType.COMMITMENT_CREATED,
            {
                "commitment_id": commitment.commitment_id,
                "beneficiary_id": beneficiary_id,
                "beneficiary_kind": beneficiary_kind,
                # The obligation itself is journalled, deliberately. Unlike
                # memory content, an obligation nobody can read is not an
                # obligation.
                "what": what.strip()[:500],
                "deadline": deadline.isoformat() if deadline else None,
                "status": status.value,
                "provenance": provenance.strip()[:200],
                "approval_id": approval_id,
            },
        )
        return commitment

    def _classify(self, **kwargs: Any) -> tuple[CommitmentStatus, Optional[str]]:
        """Ask the governance gate what this commitment requires.

        Returns the status the commitment should start in, and the approval id if
        one was raised. Fails closed: if the gate errors, the commitment is
        proposed rather than opened, because creating an obligation is
        consequential and cannot be the thing that happens when the control plane
        is broken.
        """
        capability = capability_for_beneficiary(kwargs["beneficiary_kind"])
        try:
            from genesis.governance import ActorType, PolicyContext

            gate = self._gate
            context = PolicyContext(
                action_name=capability,
                parameters={
                    "beneficiary_id": kwargs["beneficiary_id"],
                    "what": kwargs["what"][:200],
                },
                mind_id=self.mind_id,
                actor_type=ActorType.MIND.value,
                actor_id=self.mind_id,
                requester="mind",
                objective_id=kwargs.get("objective_id"),
                correlation_id=kwargs.get("correlation_id"),
            )
            result = gate.authorize(context, action_id=f"cmt-{secrets.token_hex(4)}")
            if result.allowed:
                return CommitmentStatus.OPEN, None

            approval = getattr(result, "approval", None)
            approval_id = getattr(approval, "approval_id", None)
            logger.info(
                "commitment for %s requires approval (%s)",
                kwargs["beneficiary_id"],
                result.decision.reason_code,
            )
            return CommitmentStatus.PROPOSED, approval_id
        except Exception as exc:  # noqa: BLE001 - fail closed
            logger.warning(
                "governance gate unavailable for %s; proposing rather than opening: %s",
                capability,
                exc,
            )
            return CommitmentStatus.PROPOSED, None

    # ------------------------------------------------------------------ #
    # Transitions
    # ------------------------------------------------------------------ #

    def approve_proposal(self, commitment_id: str, *, approver_id: str = "") -> Commitment:
        """Move a PROPOSED commitment to OPEN after a human decision."""
        return self._transition(
            commitment_id,
            CommitmentStatus.OPEN,
            note=f"approved by {approver_id}" if approver_id else "approved",
        )

    def start(self, commitment_id: str) -> Commitment:
        """Mark work as begun."""
        return self._transition(commitment_id, CommitmentStatus.IN_PROGRESS, note="started")

    def fulfil(self, commitment_id: str, *, note: str = "") -> Commitment:
        return self._transition(
            commitment_id, CommitmentStatus.FULFILLED, note=note or "fulfilled"
        )

    def mark_missed(self, commitment_id: str, *, note: str = "") -> Commitment:
        """Record that a commitment was not kept.

        This is a first-class, journalled outcome, not an expiry. A beneficiary
        checking history should be able to see that a promise was made and not
        kept; treating a lapsed deadline as nothing would make the record
        misleading.
        """
        return self._transition(
            commitment_id, CommitmentStatus.MISSED, note=note or "deadline passed"
        )

    def renegotiate(
        self, commitment_id: str, *, new_deadline: datetime, reason: str = ""
    ) -> Commitment:
        """Record that the beneficiary agreed to a change.

        Only legal from an open, in-progress or missed commitment. A renegotiated
        commitment becomes OPEN again with the new deadline, and the change is
        journalled separately from the fulfilment so the history shows it moved.
        """
        commitment = self._require(commitment_id)
        if commitment.status_enum is CommitmentStatus.OPEN:
            # No transition needed; just move the deadline and record it.
            with self._lock:
                previous = commitment.deadline
                commitment.deadline = new_deadline
                commitment.transition_log.append(
                    {
                        "status": CommitmentStatus.RENEGOTIATED.value,
                        "at": _utcnow().isoformat(),
                        "note": reason
                        or f"deadline moved from {previous} to {new_deadline}",
                    }
                )
            self._journal(
                EventType.COMMITMENT_RENEGOTIATED,
                {
                    "commitment_id": commitment_id,
                    "previous_deadline": previous.isoformat() if previous else None,
                    "new_deadline": new_deadline.isoformat(),
                    "reason": reason[:200],
                },
            )
            return commitment

        updated = self._transition(
            commitment_id, CommitmentStatus.RENEGOTIATED, note=reason or "renegotiated"
        )
        updated.deadline = new_deadline
        return self._transition(
            commitment_id, CommitmentStatus.OPEN, note="reopened after renegotiation"
        )

    def withdraw(self, commitment_id: str, *, reason: str = "") -> Commitment:
        """Withdraw a commitment. The reason is required in spirit, not in type."""
        return self._transition(
            commitment_id, CommitmentStatus.WITHDRAWN, note=reason or "withdrawn"
        )

    def _transition(
        self, commitment_id: str, target: CommitmentStatus, *, note: str
    ) -> Commitment:
        commitment = self._require(commitment_id)
        current = commitment.status_enum

        if current is target:
            return commitment
        if not can_transition(current, target):
            raise CommitmentTransitionError(
                f"cannot move commitment {commitment_id} from {current.value} to "
                f"{target.value}"
            )

        with self._lock:
            commitment.status = target.value
            commitment.transition_log.append(
                {"status": target.value, "at": _utcnow().isoformat(), "note": note}
            )
            if target.is_terminal:
                commitment.resolved_at = _utcnow()
                commitment.resolution_note = note

        # The event type carries the outcome, because MISSED is the one a
        # beneficiary or an auditor will look for.
        event_type = {
            CommitmentStatus.FULFILLED: EventType.COMMITMENT_FULFILLED,
            CommitmentStatus.MISSED: EventType.COMMITMENT_MISSED,
            CommitmentStatus.RENEGOTIATED: EventType.COMMITMENT_RENEGOTIATED,
            CommitmentStatus.WITHDRAWN: EventType.COMMITMENT_WITHDRAWN,
        }.get(target, EventType.COMMITMENT_UPDATED)

        self._journal(
            event_type,
            {
                "commitment_id": commitment_id,
                "beneficiary_id": commitment.beneficiary_id,
                "status": target.value,
                "note": note[:200],
                "deadline": commitment.deadline.isoformat() if commitment.deadline else None,
            },
        )
        return commitment

    def sweep_overdue(self, *, mark_missed: bool = False) -> List[Commitment]:
        """Find overdue commitments, optionally marking them missed.

        ``mark_missed`` defaults to **False**, and that default is the design
        decision: lateness and abandonment are different facts, and a being
        should decide which one applies rather than having a timer decide for it.
        Returns the overdue commitments either way, so a heartbeat can surface
        them.
        """
        overdue = [item for item in self.list_commitments() if item.is_overdue]
        if mark_missed:
            for item in overdue:
                try:
                    self.mark_missed(item.commitment_id, note="deadline passed")
                except CommitmentTransitionError as exc:
                    logger.debug("could not mark %s missed: %s", item.commitment_id, exc)
        return overdue

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def get(self, commitment_id: str) -> Optional[Commitment]:
        return self.commitments.get(commitment_id)

    def _require(self, commitment_id: str) -> Commitment:
        commitment = self.commitments.get(commitment_id)
        if commitment is None:
            raise CommitmentNotFoundError(f"unknown commitment '{commitment_id}'")
        return commitment

    def list_commitments(
        self,
        *,
        status: Optional[str] = None,
        beneficiary_id: Optional[str] = None,
        open_only: bool = False,
    ) -> List[Commitment]:
        with self._lock:
            items = list(self.commitments.values())

        if status is not None:
            items = [item for item in items if item.status == status]
        if beneficiary_id is not None:
            items = [item for item in items if item.beneficiary_id == beneficiary_id]
        if open_only:
            items = [item for item in items if item.is_open]

        # Soonest deadline first; undated commitments last rather than first.
        items.sort(
            key=lambda item: (item.deadline is None, item.deadline or item.created_at)
        )
        return items

    def owed_to(self, beneficiary_id: str) -> List[Commitment]:
        """Open commitments to one beneficiary. Feed this to a UI: "you owe them"."""
        return self.list_commitments(beneficiary_id=beneficiary_id, open_only=True)

    def at_risk(self) -> List[Commitment]:
        """Open commitments due within 24 hours."""
        return [item for item in self.list_commitments(open_only=True) if item.is_at_risk]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            items = list(self.commitments.values())
        by_status: Dict[str, int] = {}
        for item in items:
            by_status[item.status] = by_status.get(item.status, 0) + 1

        return {
            "total": len(items),
            "by_status": by_status,
            "open": sum(1 for item in items if item.is_open),
            "overdue": sum(1 for item in items if item.is_overdue),
            "at_risk": sum(1 for item in items if item.is_at_risk),
            "by_beneficiary": {
                beneficiary: sum(
                    1 for item in items if item.beneficiary_id == beneficiary and item.is_open
                )
                for beneficiary in {item.beneficiary_id for item in items}
            },
        }

    # ------------------------------------------------------------------ #
    # Persistence hooks (Phase N10 moves these to the canonical store)
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mind_id": self.mind_id,
            "commitments": [item.to_dict() for item in self.commitments.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], *, gate: Optional[_Gate] = None) -> "CommitmentManager":
        """Rebuild from a serialised manager.

        Deadlines are parsed back to timezone-aware datetimes. A naive deadline
        would compare incorrectly against ``_utcnow()``, which is how a
        commitment silently becomes perpetually overdue or never overdue.
        """
        manager = cls(data["mind_id"], gate=gate)
        for raw in data.get("commitments", []):
            deadline = raw.get("deadline")
            resolved = raw.get("resolved_at")
            created = raw.get("created_at")
            commitment = Commitment(
                commitment_id=raw["commitment_id"],
                mind_id=raw.get("mind_id", data["mind_id"]),
                beneficiary_id=raw["beneficiary_id"],
                beneficiary_label=raw.get("beneficiary_label", ""),
                beneficiary_kind=raw.get("beneficiary_kind", BENEFICIARY_OWNER),
                what=raw.get("what", ""),
                provenance=raw.get("provenance", ""),
                deadline=_parse_dt(deadline),
                created_at=_parse_dt(created) or _utcnow(),
                resolved_at=_parse_dt(resolved),
                resolution_note=raw.get("resolution_note", ""),
                status=raw.get("status", CommitmentStatus.OPEN.value),
                objective_id=raw.get("objective_id"),
                correlation_id=raw.get("correlation_id"),
                transition_log=list(raw.get("transition_log", [])),
            )
            manager.commitments[commitment.commitment_id] = commitment
        return manager

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _current_correlation_id() -> Optional[str]:
        try:
            from genesis.governance.context import current_correlation_id

            return current_correlation_id()
        except Exception:  # noqa: BLE001 - context is optional
            return None

    def _journal(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a commitment event. Never raises (Phase D rule 2)."""
        try:
            from genesis.governance.domain_events import get_domain_journal

            journal = get_domain_journal()
            recorder = getattr(journal, "record_life_event", None)
            if recorder is not None:
                recorder(mind_id=self.mind_id, event_type=event_type, payload=payload)
                return
            # The generic escape hatch: any event family not modelled as a method.
            from genesis.governance.audit import get_audit_service
            from genesis.governance.context import current_correlation_id

            get_audit_service().record(
                event_type,
                mind_id=self.mind_id,
                actor_type="mind",
                actor_id=self.mind_id,
                correlation_id=current_correlation_id(),
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001 - auditing never blocks an obligation
            logger.warning("could not journal %s: %s", event_type, exc)


def _parse_dt(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp to an aware datetime, or None."""
    if value is None or isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
