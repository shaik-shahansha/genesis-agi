"""The durable contact store: who a Mind knows, and what it may do about it.

This is what turns `ChannelGateway` from a tested loop into something that can run:
without it the only resolver is `InMemoryContacts`, so a Mind forgets everyone
between restarts and every sender is a stranger forever.

Three decisions worth stating, because each of them is a place where a plausible
simplification would remove a control:

1. **Consent is per channel.** A row is one way to reach someone, not one verdict
   about them. Someone who gave an email address has not agreed to be telephoned,
   and a schema that stores "this contact consents" once would let a Mind upgrade
   an email address into a phone call. That is why the permission lives on the
   channel row and there is a uniqueness constraint making the question "may I
   call this person?" have exactly one answer.

2. **A stranger is reply-only, and the store returns them anyway.** Returning
   `None` would stop the gateway before it could record why nothing happened. So an
   unknown sender is returned with `REPLY_ONLY` and **no** `consent_source`, which
   `ContactRef.may_initiate()` refuses. The permission is deliberately not the
   control — a row can be edited by anything with database access, and
   `consent_source` is what makes an initiation a recorded fact rather than an
   assertion.

3. **Nothing here decides anything.** No gate, no approval, no quiet-hours check.
   This store answers two questions — who is this, and what does their record say —
   and every enforcement stays in the adapter and the governance plane. A store
   that also enforced would be a second place for the rules to live and a second
   place for them to be wrong.

Failure mode to keep in mind: a database error is **not** treated as "no consent".
It propagates. Turning an outage into a permission decision would mean a store
that is down silently degrades everyone to a stranger, and the honest reading of
"I could not check" is not "the answer is no" — it is that the question was not
answered, so nothing should act on it.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from .base import ContactRef, OutboundPermission

logger = logging.getLogger(__name__)

#: Channels whose addresses are case-insensitive. Storing and matching these
#: case-insensitively is not cosmetic: `Sage@Example.com` and `sage@example.com`
#: are the same mailbox, so treating them as two contacts would mean two consent
#: records for one person — and an opt-out recorded against one would not stop the
#: other. Phone numbers are excluded because E.164 is already normalised and
#: lowercasing digits is a no-op that would hide a malformed number.
_CASE_INSENSITIVE_CHANNELS = frozenset({"email"})


def normalise_handle(channel: str, handle: str) -> str:
    """Normalise an address for storage and lookup.

    Also strips the surrounding whitespace and angle brackets a copy-paste from an
    email header leaves behind (`<sage@example.com>`). Left in place, those produce
    a contact that looks distinct from the same person stored cleanly — and the
    opt-out recorded against one of them silently does not apply to the other.
    """
    text = (handle or "").strip().strip("<>").strip()
    if channel.strip().lower() in _CASE_INSENSITIVE_CHANNELS:
        return text.lower()
    return text


class DatabaseContacts:
    """A `ContactResolver` backed by the `contacts` / `contact_channels` tables.

    Bound to one Mind at construction, and exposes `mind_id` so `ChannelGateway`
    can refuse a resolver that belongs to a different one. Consent is per-Mind, so
    a shared resolver would answer with another Mind's permission.
    """

    def __init__(self, *, mind_id: str, session_factory: Optional[Any] = None):
        self.mind_id = mind_id
        self._session_factory = session_factory

    # -- plumbing ----------------------------------------------------------

    def _session(self):
        """A session for one operation.

        Resolved lazily so importing this module does not require a database, which
        keeps it usable in a test that only wants `normalise_handle`.
        """
        if self._session_factory is not None:
            return self._session_factory()
        from genesis.database.base import get_session_factory

        return get_session_factory()()

    def _using_session(self):
        """Context manager yielding a committed-or-rolled-back session."""
        from contextlib import contextmanager

        @contextmanager
        def _cm():
            session = self._session()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        return _cm()

    # -- the protocol ------------------------------------------------------

    def resolve(
        self, *, channel: str, handle: str, display_name: str = ""
    ) -> Optional[ContactRef]:
        """Who sent this, and what does their record say.

        Returns a reply-only stranger when the handle is unknown, so the loop can
        continue to the decision and record it. Returns `None` only when the store
        itself raised nothing but produced an unusable row — a contact with no id —
        which the gateway reports as "sender could not be resolved" rather than
        inventing either a permission or a refusal.
        """
        from genesis.database.models import ContactChannelRecord, ContactRecord

        normalised = normalise_handle(channel, handle)
        if not normalised:
            return None

        with self._using_session() as session:
            row = (
                session.query(ContactChannelRecord)
                .join(ContactRecord, ContactChannelRecord.contact_id == ContactRecord.id)
                .filter(
                    ContactRecord.mind_id == self.mind_id,
                    ContactChannelRecord.channel == channel,
                    ContactChannelRecord.address == normalised,
                )
                .one_or_none()
            )

            if row is None:
                # The stranger path. Not an error: someone writing for the first
                # time is the normal case, and it is the case most worth getting
                # right.
                return ContactRef(
                    relationship_id=f"unknown:{channel}:{normalised}",
                    display_name=display_name or normalised,
                    handle=normalised,
                    outbound=OutboundPermission.REPLY_ONLY,
                    consent_source="",
                )

            contact = row.contact
            if contact is None or not contact.relationship_id:
                logger.warning(
                    "contact store: channel row %s has no usable contact; treating as unresolved",
                    row.id,
                )
                return None

            return self._to_contact_ref(contact, row)

    @staticmethod
    def _to_contact_ref(contact: Any, row: Any) -> ContactRef:
        """Build the `ContactRef`, refusing to guess at anything absent."""
        raw_permission = (row.outbound or "").strip().lower()
        try:
            outbound = OutboundPermission(raw_permission)
        except ValueError:
            # An unrecognised value in the column is a corrupt row, and the safe
            # reading of a permission we cannot parse is the most restrictive one.
            logger.warning(
                "contact store: %r is not a known outbound permission; treating as none",
                row.outbound,
            )
            outbound = OutboundPermission.NONE

        quiet_hours = (8, 20)
        stored_hours = contact.quiet_hours
        if isinstance(stored_hours, (list, tuple)) and len(stored_hours) == 2:
            try:
                quiet_hours = (int(stored_hours[0]), int(stored_hours[1]))
            except (TypeError, ValueError):
                logger.warning(
                    "contact store: quiet_hours %r is not two integers; using the default",
                    stored_hours,
                )

        trust: dict[str, float] = {}
        if isinstance(contact.trust, dict):
            for domain, score in contact.trust.items():
                try:
                    trust[str(domain)] = float(score)
                except (TypeError, ValueError):
                    # Skipping is the fail-closed choice: `trust_in` returns 0.0 for
                    # a domain that is absent, so a score we cannot read becomes
                    # untrusted rather than trusted.
                    logger.warning(
                        "contact store: trust for %r is not a number; treating as untrusted",
                        domain,
                    )

        max_outbound = contact.max_outbound_per_week
        if max_outbound is None:
            max_outbound = 3
        else:
            try:
                max_outbound = int(max_outbound)
            except (TypeError, ValueError):
                logger.warning(
                    "contact store: max_outbound_per_week %r is not an integer; using 3",
                    contact.max_outbound_per_week,
                )
                max_outbound = 3

        boundaries = contact.boundaries
        if not isinstance(boundaries, list):
            boundaries = []

        return ContactRef(
            relationship_id=contact.relationship_id,
            display_name=contact.display_name or row.address,
            handle=row.address,
            outbound=outbound,
            consent_source=row.consent_source or "",
            quiet_hours=quiet_hours,
            max_outbound_per_week=max_outbound,
            boundaries=[str(b) for b in boundaries],
            trust=trust,
            timezone_offset_hours=int(contact.timezone_offset_hours or 0),
        )

    # -- writing -----------------------------------------------------------

    def remember(
        self,
        *,
        channel: str,
        handle: str,
        display_name: str = "",
        relationship_id: Optional[str] = None,
        outbound: OutboundPermission = OutboundPermission.REPLY_ONLY,
        consent_source: str = "",
    ) -> Optional[str]:
        """Record that this person can be reached on this channel.

        Idempotent: a handle already known returns its existing
        `relationship_id` and has its permission **raised only to the level asked
        for**, never quietly lowered. The asymmetry is deliberate — a routine
        "I saw this address again" must not revoke a permission a human granted —
        and lowering it is what `forget` and `set_permission` are for.

        Returns the `relationship_id`, or `None` when the input is unusable.
        """
        from genesis.database.models import ContactChannelRecord, ContactRecord

        normalised = normalise_handle(channel, handle)
        if not normalised:
            return None

        with self._using_session() as session:
            existing_row = (
                session.query(ContactChannelRecord)
                .join(ContactRecord, ContactChannelRecord.contact_id == ContactRecord.id)
                .filter(
                    ContactRecord.mind_id == self.mind_id,
                    ContactChannelRecord.channel == channel,
                    ContactChannelRecord.address == normalised,
                )
                .one_or_none()
            )

            if existing_row is not None:
                contact = existing_row.contact
                if display_name and contact is not None and not contact.display_name:
                    contact.display_name = display_name
                    contact.updated_at = datetime.utcnow()
                self._raise_permission(existing_row, outbound, consent_source)
                return contact.relationship_id if contact is not None else None

            rid = relationship_id or f"{channel}:{normalised}"
            contact_row = (
                session.query(ContactRecord)
                .filter(
                    ContactRecord.mind_id == self.mind_id,
                    ContactRecord.relationship_id == rid,
                )
                .one_or_none()
            )
            if contact_row is None:
                contact_row = ContactRecord(
                    mind_id=self.mind_id,
                    relationship_id=rid,
                    display_name=display_name or normalised,
                )
                session.add(contact_row)
                session.flush()

            session.add(
                ContactChannelRecord(
                    contact_id=contact_row.id,
                    channel=channel,
                    address=normalised,
                    outbound=outbound.value,
                    consent_source=consent_source,
                )
            )
            return rid

    @staticmethod
    def _raise_permission(row: Any, outbound: OutboundPermission, consent_source: str) -> None:
        """Raise a permission, recording provenance, never lowering it.

        A raise to `initiate` with no `consent_source` is stored but grants nothing,
        because `ContactRef.may_initiate()` checks the source separately. Refusing
        the write instead would lose the operator's intent and produce a row that
        looks identical to "nobody ever asked" — so the row is written and the
        permission simply does not take effect until the reason is there.
        """
        order = {
            OutboundPermission.NONE.value: 0,
            OutboundPermission.REPLY_ONLY.value: 1,
            OutboundPermission.INITIATE.value: 2,
        }
        current = order.get((row.outbound or "").strip().lower(), 0)
        wanted = order.get(outbound.value, 0)
        if wanted > current:
            row.outbound = outbound.value
        if consent_source and not (row.consent_source or "").strip():
            row.consent_source = consent_source

    def set_permission(
        self,
        *,
        channel: str,
        handle: str,
        outbound: OutboundPermission,
        consent_source: str = "",
    ) -> bool:
        """Set a permission explicitly, in either direction.

        Separate from `remember` on purpose: lowering a permission is a deliberate
        act and should be a named method rather than a side effect of seeing an
        address again.

        Refuses a raise to `initiate` with no `consent_source`, because storing a
        permission that cannot take effect is worse than refusing it: the operator
        would see `initiate` in the database and conclude contact is permitted.
        """
        from genesis.database.models import ContactChannelRecord, ContactRecord

        if outbound is OutboundPermission.INITIATE and not consent_source.strip():
            raise ValueError(
                "an initiate permission needs a consent_source: permission without "
                "provenance is an assertion, and may_initiate() would refuse it anyway"
            )

        normalised = normalise_handle(channel, handle)
        if not normalised:
            return False

        with self._using_session() as session:
            row = (
                session.query(ContactChannelRecord)
                .join(ContactRecord, ContactChannelRecord.contact_id == ContactRecord.id)
                .filter(
                    ContactRecord.mind_id == self.mind_id,
                    ContactChannelRecord.channel == channel,
                    ContactChannelRecord.address == normalised,
                )
                .one_or_none()
            )
            if row is None:
                return False
            row.outbound = outbound.value
            if consent_source:
                row.consent_source = consent_source
            row.contact.updated_at = datetime.utcnow()
            return True

    def revoke(
        self, *, channel: str, handle: str, reason: str = ""
    ) -> bool:
        """Stop all outbound on this channel for this handle.

        Sets `outbound` to `none` rather than deleting the row, and sets the
        consent source to the reason. Deleting would make the next inbound message
        look like a first contact from a stranger — reply-only and re-invitable
        once someone else raises the permission. Keeping the row with `none`
        records that a decision was made and which decision it was.
        """
        from genesis.database.models import ContactChannelRecord, ContactRecord

        normalised = normalise_handle(channel, handle)
        if not normalised:
            return False

        with self._using_session() as session:
            row = (
                session.query(ContactChannelRecord)
                .join(ContactRecord, ContactChannelRecord.contact_id == ContactRecord.id)
                .filter(
                    ContactRecord.mind_id == self.mind_id,
                    ContactChannelRecord.channel == channel,
                    ContactChannelRecord.address == normalised,
                )
                .one_or_none()
            )
            if row is None:
                return False
            row.outbound = OutboundPermission.NONE.value
            row.consent_source = reason or "revoked"
            return True

    def mark_verified(self, *, channel: str, handle: str) -> bool:
        """Record that the handle was proven to belong to the person.

        Separate from `verified` on write because the two arrive at different
        times: a settings screen records an address, and a reply from it is what
        proves the mailbox is theirs.
        """
        from genesis.database.models import ContactChannelRecord, ContactRecord

        normalised = normalise_handle(channel, handle)
        if not normalised:
            return False

        with self._using_session() as session:
            row = (
                session.query(ContactChannelRecord)
                .join(ContactRecord, ContactChannelRecord.contact_id == ContactRecord.id)
                .filter(
                    ContactRecord.mind_id == self.mind_id,
                    ContactChannelRecord.channel == channel,
                    ContactChannelRecord.address == normalised,
                )
                .one_or_none()
            )
            if row is None:
                return False
            row.verified = True
            return True

    def known_handles(self, *, channel: str) -> set[str]:
        """Every handle this Mind can reach on a channel.

        Used by the inbound path to tell "someone I know replied" from "someone new
        wrote to me", which is a different decision and should be a different name.
        """
        from genesis.database.models import ContactChannelRecord, ContactRecord

        with self._using_session() as session:
            rows = (
                session.query(ContactChannelRecord.address)
                .join(ContactRecord, ContactChannelRecord.contact_id == ContactRecord.id)
                .filter(
                    ContactRecord.mind_id == self.mind_id,
                    ContactChannelRecord.channel == channel,
                )
                .all()
            )
            return {address for (address,) in rows}

    def record_inbound(self, *, channel: str, handle: str, display_name: str = "") -> Optional[str]:
        """Learn a sender from an inbound message.

        Any message that reaches a Mind is proof that the address works and that
        someone on the other end expects to be reached by it, which is enough for a
        reply. It is **not** consent to be contacted later, so the permission
        granted is `REPLY_ONLY` and the consent source stays empty. Writing
        `INITIATE` here would be the whole bug: one inbound message would be treated
        as an opt-in to weekly outreach.
        """
        from genesis.database.models import ContactChannelRecord, ContactRecord

        normalised = normalise_handle(channel, handle)
        if not normalised:
            return None

        with self._using_session() as session:
            row = (
                session.query(ContactChannelRecord)
                .join(ContactRecord, ContactChannelRecord.contact_id == ContactRecord.id)
                .filter(
                    ContactRecord.mind_id == self.mind_id,
                    ContactChannelRecord.channel == channel,
                    ContactChannelRecord.address == normalised,
                )
                .one_or_none()
            )
            if row is not None:
                row.verified = True
                return row.contact.relationship_id if row.contact is not None else None

            contact_row = ContactRecord(
                mind_id=self.mind_id,
                relationship_id=f"{channel}:{normalised}",
                display_name=display_name or normalised,
            )
            session.add(contact_row)
            session.flush()
            session.add(
                ContactChannelRecord(
                    contact_id=contact_row.id,
                    channel=channel,
                    address=normalised,
                    outbound=OutboundPermission.REPLY_ONLY.value,
                    consent_source="",
                    verified=True,
                )
            )
            return contact_row.relationship_id
