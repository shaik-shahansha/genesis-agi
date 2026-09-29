"""Durable ledgers for the contactability floors.

`limits.py` holds the floors and the in-memory defaults. This module holds the
implementations that survive a restart, because a cap that a restart removes is not
a cap.

## Why the outbound ledger had to become durable

For *replies* the in-memory ledger was nearly harmless: a reply is not capped, so
losing the counts changed nothing a person could observe. For *initiated* contact it
was the entire control. The weekly cap and the minimum gap were held in a
process-local list, so a Mind that had already used its three messages this week
could start over by restarting — and "the being that contacted you four times in a
week" is exactly what the cap exists to prevent. The failure was invisible from the
outside: nothing looked broken, the limit was simply gone.

## The timezone trap this module exists to get right

`channels.base.utcnow()` returns a **timezone-aware** datetime, and every other
datetime in this codebase (`datetime.utcnow`) is **naive**. SQLite's `DateTime`
stores no offset, so an aware value written to this table comes back naive.

That combination raises `TypeError: can't compare offset-naive and offset-aware
datetimes` — but only on the *second* run, because the first write has nothing to
compare against. So the bug would appear to work in testing and fail on the second
week of real use, which is the worst possible place to find it.

The fix is explicit in both directions rather than relying on a coincidence:
`_as_naive_utc` normalises on the way in, and `_as_aware_utc` restores the offset on
the way out, so callers always compare aware to aware.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _as_naive_utc(value: datetime) -> datetime:
    """Convert to naive UTC for storage.

    An aware value is converted, not stripped: `datetime.replace(tzinfo=None)` on an
    aware value keeps the *local* wall-clock time and silently shifts the instant,
    which would move a message into or out of the weekly window depending on the
    offset the caller happened to use.
    """
    if value.tzinfo is None:
        # Already naive. Assumed UTC, which is what every other writer in this
        # codebase produces.
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _as_aware_utc(value: datetime) -> datetime:
    """Restore the UTC offset on the way out, so callers compare like with like."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class DatabaseOutboundLedger:
    """Counts initiated messages in the `outbound_messages` table.

    Only initiated messages are recorded — `BaseChannel.send` records a row only
    when `prepared.is_reply` is False. Replies are excluded because answering
    someone who wrote first is not outreach, and counting it would make a Mind
    unable to hold a conversation.

    A database error **propagates**. It is tempting to return `0` or `None` on
    failure, and that would be the worst available choice: `0` means "this person has
    received nothing", so a database outage would read as unlimited allowance and the
    cap would be silently removed at exactly the moment the system is least healthy.
    Failing loudly means a send is refused instead, which is recoverable.
    """

    def __init__(self, *, session_factory: Optional[Any] = None):
        self._session_factory = session_factory

    @property
    def durable(self) -> bool:
        return True

    def _session(self):
        if self._session_factory is not None:
            return self._session_factory()
        from genesis.database.base import get_session_factory

        return get_session_factory()()

    # -- writes ------------------------------------------------------------

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
        """Record one initiated message.

        Commits immediately and independently of any other work, because this is a
        rate-limit record: if it were rolled back with a later failure, allowance
        would be handed back for a message that was actually delivered.

        `trigger` and `trigger_ref` say *why*, and `trigger_ref` doubles as the
        idempotence key for proactive outreach — see `already_reached_out`.
        """
        from genesis.database.models import OutboundMessageRecord

        session = self._session()
        try:
            session.add(
                OutboundMessageRecord(
                    mind_id=mind_id,
                    relationship_id=relationship_id,
                    channel=channel,
                    sent_at=_as_naive_utc(at),
                    trigger=trigger or "manual",
                    trigger_ref=trigger_ref,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def already_reached_out(
        self, *, mind_id: str, trigger: str, trigger_ref: str
    ) -> bool:
        """Whether this Mind has already contacted someone about this trigger.

        The idempotence check that makes proactive outreach safe to run on a loop.

        Without it, a commitment that is at risk for 24 hours would be noticed on
        every poll — 1,440 times a day — and the floors would then permit three
        reminders in a week, all about the same obligation, all saying the same
        thing. The rate limit would be doing its job and the behaviour would still
        be wrong, because the person is being nagged about one thing rather than
        being contacted about three.

        Keyed on the trigger *and* its ref, so a new commitment with a new id
        produces a new reminder while the same one does not repeat. This is the
        same class of failure as the duplicate reply the inbound ledger prevents:
        each individual send is compliant, and the aggregate is the harm.
        """
        from genesis.database.models import OutboundMessageRecord

        if not trigger_ref:
            # No ref means the trigger cannot be identified, so it cannot be
            # deduplicated. Saying "no" here would let an unidentifiable trigger fire
            # repeatedly; saying "yes" would suppress a first contact. Neither is
            # safe, so callers are required to supply a ref — see
            # `OutreachPlanner`, which refuses a trigger without one.
            logger.warning(
                "outbound ledger: %r has no trigger_ref, so it cannot be deduplicated",
                trigger,
            )
            return False

        session = self._session()
        try:
            return (
                session.query(OutboundMessageRecord)
                .filter(
                    OutboundMessageRecord.mind_id == mind_id,
                    OutboundMessageRecord.trigger == trigger,
                    OutboundMessageRecord.trigger_ref == trigger_ref,
                )
                .first()
                is not None
            )
        finally:
            session.close()

    # -- reads -------------------------------------------------------------

    def count_since(
        self, *, mind_id: str, relationship_id: str, since: datetime
    ) -> int:
        """How many initiated messages this person has received since `since`.

        Counts rows rather than distinct timestamps: a retry after an ambiguous
        provider response is two rows, and it should cost two units of allowance. The
        table deliberately has no unique constraint for this reason.
        """
        from genesis.database.models import OutboundMessageRecord

        session = self._session()
        try:
            return (
                session.query(OutboundMessageRecord)
                .filter(
                    OutboundMessageRecord.mind_id == mind_id,
                    OutboundMessageRecord.relationship_id == relationship_id,
                    OutboundMessageRecord.sent_at >= _as_naive_utc(since),
                )
                .count()
            )
        finally:
            session.close()

    def last_outbound_at(
        self, *, mind_id: str, relationship_id: str
    ) -> Optional[datetime]:
        """When this person was last contacted, or None if never.

        Returns an **aware** datetime, so the caller's comparison against
        `utcnow()` does not raise. `None` means "never contacted", which is distinct
        from a stale timestamp and must stay distinguishable — the minimum-gap floor
        is skipped entirely for someone never contacted.
        """
        from genesis.database.models import OutboundMessageRecord

        session = self._session()
        try:
            row = (
                session.query(OutboundMessageRecord.sent_at)
                .filter(
                    OutboundMessageRecord.mind_id == mind_id,
                    OutboundMessageRecord.relationship_id == relationship_id,
                )
                .order_by(OutboundMessageRecord.sent_at.desc())
                .first()
            )
        finally:
            session.close()

        if row is None or row[0] is None:
            return None
        return _as_aware_utc(row[0])

    # -- reporting ---------------------------------------------------------

    def recent(
        self, *, mind_id: str, days: int = 7, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Initiated messages in the last `days`, newest first.

        For an operator answering "why has this Mind gone quiet?" — the honest answer
        is often "it has spent its allowance", and that should be visible rather than
        inferred from a refusal reason.
        """
        from genesis.database.models import OutboundMessageRecord

        cutoff = _as_naive_utc(datetime.now(timezone.utc) - timedelta(days=max(1, days)))
        session = self._session()
        try:
            rows = (
                session.query(OutboundMessageRecord)
                .filter(
                    OutboundMessageRecord.mind_id == mind_id,
                    OutboundMessageRecord.sent_at >= cutoff,
                )
                .order_by(OutboundMessageRecord.sent_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "relationship_id": row.relationship_id,
                    "channel": row.channel,
                    "sent_at": _as_aware_utc(row.sent_at).isoformat(),
                }
                for row in rows
            ]
        finally:
            session.close()


class DatabaseOptOutRegistry:
    """Opt-out that survives a restart, and applies on every channel.

    The in-memory version was the most dangerous non-durable control here. Someone
    says "stop", the daemon restarts, and the Mind writes to them again — the exact
    behaviour they asked to end, repeated, with nothing in the logs to explain it.
    A rate limit that resets is generous; an opt-out that resets is harassment.

    It also has to be **shared** between channels rather than constructed per
    adapter. `BaseChannel.__init__` creates its own registry when none is injected,
    so a registry per channel would mean "stop" on email did not stop Telegram —
    which is what actually happened before `build_registry` was fixed to inject one.

    A database error propagates. Reading "I could not check" as "not opted out"
    would turn an outage into permission to contact someone who asked not to be,
    which is the worst available interpretation of a failed lookup.
    """

    def __init__(self, *, mind_id: str, session_factory: Optional[Any] = None):
        self.mind_id = mind_id
        self._session_factory = session_factory

    @property
    def durable(self) -> bool:
        return True

    def _session(self):
        if self._session_factory is not None:
            return self._session_factory()
        from genesis.database.base import get_session_factory

        return get_session_factory()()

    @staticmethod
    def normalise(handle: str) -> str:
        """Normalise a handle for matching.

        Lowercased and stripped, matching `contacts.normalise_handle`. An opt-out
        recorded against `Dana@Example.com` must catch mail from
        `dana@example.com`, or the mechanism has a one-character bypass.
        """
        return (handle or "").strip().strip("<>").strip().lower()

    def opt_out(self, *, relationship_id: str = "", handle: str = "", reason: str = "") -> None:
        """Record an opt-out against a relationship, a handle, or both.

        Both are recorded when both are known, deliberately. The relationship key
        survives the person changing address; the handle key catches them writing
        from an address the Mind has no contact record for. Storing only one of them
        leaves a route back in.
        """
        from sqlalchemy.exc import IntegrityError

        from genesis.database.models import CommunicationOptOutRecord

        subjects: list[tuple[str, str]] = []
        if relationship_id:
            subjects.append(("relationship", relationship_id))
        normalised = self.normalise(handle)
        if normalised:
            subjects.append(("handle", normalised))
        if not subjects:
            logger.warning("opt-out recorded with neither a relationship nor a handle; ignored")
            return

        session = self._session()
        try:
            for kind, subject in subjects:
                # Insert-and-ignore-conflict rather than check-then-insert: asking
                # twice is one opt-out, and a read-then-write would be a race for no
                # benefit.
                try:
                    with session.begin_nested():
                        session.add(
                            CommunicationOptOutRecord(
                                mind_id=self.mind_id,
                                subject_kind=kind,
                                subject=subject,
                                reason=reason,
                            )
                        )
                except IntegrityError:
                    # Already recorded. Repeating yourself must not be an error.
                    continue
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def is_opted_out(self, *, relationship_id: str = "", handle: str = "") -> bool:
        """Whether this person has asked not to be contacted, by either key."""
        from genesis.database.models import CommunicationOptOutRecord

        keys: list[tuple[str, str]] = []
        if relationship_id:
            keys.append(("relationship", relationship_id))
        normalised = self.normalise(handle)
        if normalised:
            keys.append(("handle", normalised))
        if not keys:
            return False

        session = self._session()
        try:
            query = session.query(CommunicationOptOutRecord).filter(
                CommunicationOptOutRecord.mind_id == self.mind_id
            )
            from sqlalchemy import or_, and_

            query = query.filter(
                or_(
                    *[
                        and_(
                            CommunicationOptOutRecord.subject_kind == kind,
                            CommunicationOptOutRecord.subject == subject,
                        )
                        for kind, subject in keys
                    ]
                )
            )
            return query.first() is not None
        finally:
            session.close()

    def clear(self, *, relationship_id: str) -> bool:
        """Re-enable contact, but only when a person has actually asked again.

        Named `clear` rather than `remove` so it reads as deliberate at a call site,
        and never called from a send path. Returns whether anything changed, so a
        caller clearing an opt-out that was never recorded can tell.
        """
        from genesis.database.models import CommunicationOptOutRecord

        if not relationship_id:
            return False

        session = self._session()
        try:
            deleted = (
                session.query(CommunicationOptOutRecord)
                .filter(
                    CommunicationOptOutRecord.mind_id == self.mind_id,
                    CommunicationOptOutRecord.subject_kind == "relationship",
                    CommunicationOptOutRecord.subject == relationship_id,
                )
                .delete(synchronize_session=False)
            )
            session.commit()
            if deleted:
                # The handle row is left in place on purpose: the Mind does not know
                # whether the handle row refers to the same person, and removing an
                # opt-out keyed to an address on the strength of a relationship-level
                # "actually, it's fine" would be guessing in the permissive direction.
                logger.info(
                    "opt-out cleared for relationship %s; any handle-level opt-out stays",
                    relationship_id,
                )
            return bool(deleted)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def all_opt_outs(self, *, limit: int = 500) -> list[dict[str, Any]]:
        """Every opt-out for this Mind, for an operator to read.

        Exposed because an opt-out is invisible by design — it works by the Mind
        saying nothing — and something that only manifests as an absence is
        impossible to audit from the outside.
        """
        from genesis.database.models import CommunicationOptOutRecord

        session = self._session()
        try:
            rows = (
                session.query(CommunicationOptOutRecord)
                .filter(CommunicationOptOutRecord.mind_id == self.mind_id)
                .order_by(CommunicationOptOutRecord.recorded_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "subject_kind": row.subject_kind,
                    "subject": row.subject,
                    "reason": row.reason,
                    "recorded_at": _as_aware_utc(row.recorded_at).isoformat(),
                }
                for row in rows
            ]
        finally:
            session.close()
