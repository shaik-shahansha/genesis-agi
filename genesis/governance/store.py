"""Persistence for the governance control plane.

Two implementations behind one interface:

* :class:`InMemoryGovernanceStore` - hermetic, used by tests.
* :class:`SqlAlchemyGovernanceStore` - the production store (ADR-0002: the
  canonical store is Postgres; SQLite is supported for single-node installs).

**Hash chaining lives in the store, not the caller.** That is deliberate: the
sequence number and ``prev_hash`` must be assigned atomically with the insert,
otherwise two concurrent writers could fork the chain. A journal whose integrity
depends on callers behaving well is not an integrity guarantee.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple

from genesis.governance.models import (
    GENESIS_EPOCH_HASH,
    ActionReceipt,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    PermissionGrant,
)
from genesis.governance.redact import hash_chain, stable_hash

__all__ = [
    "JournalVerification",
    "GovernanceStoreError",
    "GovernanceStore",
    "InMemoryGovernanceStore",
    "SqlAlchemyGovernanceStore",
    "get_governance_store",
    "reset_governance_store",
    "set_governance_store",
    "VALID_STORES",
]


class GovernanceStoreError(RuntimeError):
    """Raised when the governance store cannot be used safely."""


@dataclass(frozen=True)
class JournalVerification:
    """Result of re-walking a hash chain."""

    ok: bool
    checked: int
    broken_at: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "broken_at": self.broken_at,
            "reason": self.reason,
        }


class GovernanceStore(Protocol):  # pragma: no cover - structural typing
    """Interface consumed by :mod:`genesis.governance.audit` and ``approval``."""

    def append_event(self, event: AuditEvent) -> AuditEvent: ...
    def list_events(
        self,
        *,
        mind_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[AuditEvent]: ...
    def last_event(self, stream_key: str) -> Optional[AuditEvent]: ...
    def verify_journal(self, *, mind_id: Optional[str] = None, limit: int = 10_000) -> JournalVerification: ...
    def save_receipt(self, receipt: ActionReceipt) -> ActionReceipt: ...
    def get_receipt(self, receipt_id: str) -> Optional[ActionReceipt]: ...
    def list_receipts(
        self, *, mind_id: str, limit: int = 100, outcome: Optional[str] = None
    ) -> List[ActionReceipt]: ...
    def save_approval(self, approval: ApprovalRequest) -> ApprovalRequest: ...
    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]: ...
    def list_approvals(
        self,
        *,
        mind_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[ApprovalRequest]: ...
    def save_grant(self, grant: PermissionGrant) -> PermissionGrant: ...
    def get_grant(self, grant_id: str) -> Optional[PermissionGrant]: ...
    def list_grants(
        self,
        *,
        mind_id: str,
        action_name: Optional[str] = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> List[PermissionGrant]: ...


# --------------------------------------------------------------------------- #
# Datetime helpers
# --------------------------------------------------------------------------- #


def _to_db(value: Optional[datetime]) -> Optional[datetime]:
    """Store naive UTC so SQLite and Postgres agree."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _from_db(value: Optional[datetime]) -> Optional[datetime]:
    """Read back as timezone-aware UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _chained_event(event: AuditEvent, previous: Optional[AuditEvent]) -> AuditEvent:
    """Assign sequence, payload hash, prev_hash and integrity_hash."""
    event.sequence = (previous.sequence + 1) if previous else 1
    event.prev_hash = previous.integrity_hash if previous else GENESIS_EPOCH_HASH
    event.payload_hash = stable_hash(event.payload)
    event.integrity_hash = hash_chain(event.prev_hash, event.hashable_body())
    return event


def _chained_receipt(receipt: ActionReceipt, previous: Optional[ActionReceipt]) -> ActionReceipt:
    receipt.sequence = (previous.sequence + 1) if previous else 1
    receipt.prev_hash = previous.integrity_hash if previous else GENESIS_EPOCH_HASH
    receipt.payload_hash = stable_hash(receipt.arguments)
    receipt.integrity_hash = hash_chain(receipt.prev_hash, receipt.hashable_body())
    return receipt


# --------------------------------------------------------------------------- #
# In-memory store
# --------------------------------------------------------------------------- #


class InMemoryGovernanceStore:
    """Process-local store. Used by tests and by ``GENESIS_GOVERNANCE_STORE=memory``.

    Thread-safe (a single re-entrant lock guards all mutations), which keeps the
    hash chain linear even when the API server and a background task both write.
    """

    name = "memory"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._events: List[AuditEvent] = []
        self._receipts: List[ActionReceipt] = []
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._grants: Dict[str, PermissionGrant] = {}

    # -- events --------------------------------------------------------- #
    def append_event(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            previous = self._last_event_locked(event.stream_key)
            _chained_event(event, previous)
            self._events.append(event)
            return event

    def _last_event_locked(self, stream_key: str) -> Optional[AuditEvent]:
        for candidate in reversed(self._events):
            if candidate.stream_key == stream_key:
                return candidate
        return None

    def last_event(self, stream_key: str) -> Optional[AuditEvent]:
        with self._lock:
            return self._last_event_locked(stream_key)

    def list_events(
        self,
        *,
        mind_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[AuditEvent]:
        with self._lock:
            events = list(self._events)
        result = [
            event
            for event in events
            if (mind_id is None or event.mind_id == mind_id)
            and (tenant_id is None or event.tenant_id == tenant_id)
            and (event_type is None or event.type == event_type)
            and (since is None or event.timestamp >= since)
        ]
        result.sort(key=lambda item: item.timestamp)
        return result[-limit:]

    def verify_journal(
        self, *, mind_id: Optional[str] = None, limit: int = 10_000
    ) -> JournalVerification:
        with self._lock:
            events = [e for e in self._events if mind_id is None or e.mind_id == mind_id]
        events.sort(key=lambda item: (item.stream_key, item.sequence))
        return _verify_stream(events, limit=limit)

    # -- receipts -------------------------------------------------------- #
    def save_receipt(self, receipt: ActionReceipt) -> ActionReceipt:
        with self._lock:
            previous = next(
                (
                    candidate
                    for candidate in reversed(self._receipts)
                    if candidate.stream_key == receipt.stream_key
                ),
                None,
            )
            _chained_receipt(receipt, previous)
            self._receipts.append(receipt)
            return receipt

    def get_receipt(self, receipt_id: str) -> Optional[ActionReceipt]:
        with self._lock:
            return next((r for r in self._receipts if r.receipt_id == receipt_id), None)

    def list_receipts(
        self, *, mind_id: str, limit: int = 100, outcome: Optional[str] = None
    ) -> List[ActionReceipt]:
        with self._lock:
            receipts = [
                item
                for item in self._receipts
                if item.mind_id == mind_id and (outcome is None or item.outcome == outcome)
            ]
        receipts.sort(key=lambda item: item.created_at, reverse=True)
        return receipts[:limit]

    # -- approvals ------------------------------------------------------- #
    def save_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        with self._lock:
            self._approvals[approval.approval_id] = approval
            return approval

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
            return self._approvals.get(approval_id)

    def list_approvals(
        self,
        *,
        mind_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[ApprovalRequest]:
        with self._lock:
            approvals = [
                item
                for item in self._approvals.values()
                if (mind_id is None or item.mind_id == mind_id)
                and (status is None or item.status == status)
            ]
        approvals.sort(key=lambda item: item.requested_at, reverse=True)
        return approvals[:limit]

    # -- grants ---------------------------------------------------------- #
    def save_grant(self, grant: PermissionGrant) -> PermissionGrant:
        with self._lock:
            self._grants[grant.grant_id] = grant
            return grant

    def get_grant(self, grant_id: str) -> Optional[PermissionGrant]:
        with self._lock:
            return self._grants.get(grant_id)

    def list_grants(
        self,
        *,
        mind_id: str,
        action_name: Optional[str] = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> List[PermissionGrant]:
        now = datetime.now(timezone.utc)
        with self._lock:
            grants = [
                item
                for item in self._grants.values()
                if item.mind_id == mind_id
                and (action_name is None or item.action_name == action_name)
            ]
        if active_only:
            grants = [
                item
                for item in grants
                if not item.is_consumed and not item.is_revoked and not item.is_expired(now)
            ]
        grants.sort(key=lambda item: item.issued_at, reverse=True)
        return grants[:limit]


def _verify_stream(events: Sequence[AuditEvent], *, limit: int) -> JournalVerification:
    """Re-walk one or more ordered streams and confirm every hash link."""
    checked = 0
    expected_prev: Dict[str, str] = {}
    last_sequence: Dict[str, int] = {}
    for event in events:
        if checked >= limit:
            break
        checked += 1
        stream = event.stream_key
        prev = expected_prev.get(stream, GENESIS_EPOCH_HASH)
        if event.prev_hash != prev:
            return JournalVerification(
                ok=False,
                checked=checked,
                broken_at=event.event_id,
                reason=f"prev_hash mismatch on {stream}",
            )
        if event.sequence != last_sequence.get(stream, 0) + 1:
            return JournalVerification(
                ok=False,
                checked=checked,
                broken_at=event.event_id,
                reason=f"sequence gap on {stream}",
            )
        if stable_hash(event.payload) != event.payload_hash:
            return JournalVerification(
                ok=False,
                checked=checked,
                broken_at=event.event_id,
                reason="payload was modified after it was written",
            )
        recomputed = hash_chain(event.prev_hash, event.hashable_body())
        if recomputed != event.integrity_hash:
            return JournalVerification(
                ok=False,
                checked=checked,
                broken_at=event.event_id,
                reason="integrity hash mismatch",
            )
        expected_prev[stream] = event.integrity_hash
        last_sequence[stream] = event.sequence
    return JournalVerification(ok=True, checked=checked)


# --------------------------------------------------------------------------- #
# SQLAlchemy store
# --------------------------------------------------------------------------- #


class SqlAlchemyGovernanceStore:
    """Durable store backed by the canonical database (ADR-0002)."""

    name = "sql"

    #: Retries when two writers race on the same stream.
    _MAX_CHAIN_RETRIES = 3

    def _models(self):
        from genesis.database import governance_models as models

        return models

    # -- events --------------------------------------------------------- #
    def append_event(self, event: AuditEvent) -> AuditEvent:
        from sqlalchemy import func, select

        from genesis.database.base import get_session

        models = self._models()
        stream = event.stream_key

        for attempt in range(self._MAX_CHAIN_RETRIES):
            try:
                with get_session() as session:
                    last = session.execute(
                        select(models.GovernanceEventRecord)
                        .where(models.GovernanceEventRecord.stream_key == stream)
                        .order_by(models.GovernanceEventRecord.sequence.desc())
                        .limit(1)
                    ).scalar_one_or_none()

                    previous = _record_to_event(last) if last is not None else None
                    _chained_event(event, previous)

                    session.add(
                        models.GovernanceEventRecord(
                            event_id=event.event_id,
                            stream_key=stream,
                            sequence=event.sequence,
                            type=event.type,
                            schema_version=event.schema_version,
                            timestamp=_to_db(event.timestamp),
                            tenant_id=event.tenant_id,
                            mind_id=event.mind_id,
                            actor_type=event.actor_type,
                            actor_id=event.actor_id,
                            correlation_id=event.correlation_id,
                            causation_id=event.causation_id,
                            payload=event.payload,
                            payload_hash=event.payload_hash,
                            prev_hash=event.prev_hash,
                            integrity_hash=event.integrity_hash,
                        )
                    )
                return event
            except Exception as exc:  # noqa: BLE001 - retried below
                if attempt == self._MAX_CHAIN_RETRIES - 1:
                    raise GovernanceStoreError(
                        f"could not append governance event: {type(exc).__name__}"
                    ) from exc
                # Duplicate sequence => another writer won the race; re-read.
                _ = func  # keep the import meaningful for type checkers
                continue

        raise GovernanceStoreError("could not append governance event")  # pragma: no cover

    def last_event(self, stream_key: str) -> Optional[AuditEvent]:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        with get_session() as session:
            record = session.execute(
                select(models.GovernanceEventRecord)
                .where(models.GovernanceEventRecord.stream_key == stream_key)
                .order_by(models.GovernanceEventRecord.sequence.desc())
                .limit(1)
            ).scalar_one_or_none()
            return _record_to_event(record) if record is not None else None

    def list_events(
        self,
        *,
        mind_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[AuditEvent]:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        statement = select(models.GovernanceEventRecord)
        if mind_id is not None:
            statement = statement.where(models.GovernanceEventRecord.mind_id == mind_id)
        if tenant_id is not None:
            statement = statement.where(models.GovernanceEventRecord.tenant_id == tenant_id)
        if event_type is not None:
            statement = statement.where(models.GovernanceEventRecord.type == event_type)
        if since is not None:
            statement = statement.where(
                models.GovernanceEventRecord.timestamp >= _to_db(since)
            )
        statement = statement.order_by(
            models.GovernanceEventRecord.timestamp.desc(),
            models.GovernanceEventRecord.sequence.desc(),
        ).limit(limit)

        # Convert INSIDE the session block. `get_session()` commits and closes on
        # exit, and SQLAlchemy expires instances on commit, so accessing an
        # attribute of a returned row afterwards raises DetachedInstanceError.
        # This only reproduces once rows exist, which is why it survived the
        # in-memory test suite and surfaced the first time the journal had a
        # single event in it.
        with get_session() as session:
            records = session.execute(statement).scalars().all()
            events = [_record_to_event(record) for record in records]
        events.reverse()
        return events

    def verify_journal(
        self, *, mind_id: Optional[str] = None, limit: int = 10_000
    ) -> JournalVerification:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        statement = select(models.GovernanceEventRecord)
        if mind_id is not None:
            statement = statement.where(models.GovernanceEventRecord.mind_id == mind_id)
        statement = statement.order_by(
            models.GovernanceEventRecord.stream_key,
            models.GovernanceEventRecord.sequence,
        ).limit(limit)

        with get_session() as session:
            records = session.execute(statement).scalars().all()
            events = [_record_to_event(record) for record in records]
        return _verify_stream(events, limit=limit)

    # -- receipts -------------------------------------------------------- #
    def save_receipt(self, receipt: ActionReceipt) -> ActionReceipt:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        stream = receipt.stream_key
        with get_session() as session:
            last = session.execute(
                select(models.ActionReceiptRecord)
                .where(models.ActionReceiptRecord.mind_id == receipt.mind_id)
                .where(models.ActionReceiptRecord.tenant_id == receipt.tenant_id)
                .order_by(models.ActionReceiptRecord.sequence.desc())
                .limit(1)
            ).scalar_one_or_none()
            _ = stream
            previous = _record_to_receipt(last) if last is not None else None
            _chained_receipt(receipt, previous)
            session.add(_receipt_to_record(receipt, models))
        return receipt

    def get_receipt(self, receipt_id: str) -> Optional[ActionReceipt]:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        with get_session() as session:
            record = session.execute(
                select(models.ActionReceiptRecord).where(
                    models.ActionReceiptRecord.receipt_id == receipt_id
                )
            ).scalar_one_or_none()
            return _record_to_receipt(record) if record is not None else None

    def list_receipts(
        self, *, mind_id: str, limit: int = 100, outcome: Optional[str] = None
    ) -> List[ActionReceipt]:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        statement = select(models.ActionReceiptRecord).where(
            models.ActionReceiptRecord.mind_id == mind_id
        )
        if outcome is not None:
            statement = statement.where(models.ActionReceiptRecord.outcome == outcome)
        statement = statement.order_by(models.ActionReceiptRecord.created_at.desc()).limit(limit)

        with get_session() as session:
            records = session.execute(statement).scalars().all()
            return [_record_to_receipt(record) for record in records]

    # -- approvals -------------------------------------------------------- #
    def save_approval(self, approval: ApprovalRequest) -> ApprovalRequest:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        with get_session() as session:
            record = session.execute(
                select(models.ApprovalRequestRecord).where(
                    models.ApprovalRequestRecord.approval_id == approval.approval_id
                )
            ).scalar_one_or_none()
            if record is None:
                session.add(_approval_to_record(approval, models))
            else:
                _apply_approval(record, approval)
        return approval

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        with get_session() as session:
            record = session.execute(
                select(models.ApprovalRequestRecord).where(
                    models.ApprovalRequestRecord.approval_id == approval_id
                )
            ).scalar_one_or_none()
            return _record_to_approval(record) if record is not None else None

    def list_approvals(
        self,
        *,
        mind_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[ApprovalRequest]:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        statement = select(models.ApprovalRequestRecord)
        if mind_id is not None:
            statement = statement.where(models.ApprovalRequestRecord.mind_id == mind_id)
        if status is not None:
            statement = statement.where(models.ApprovalRequestRecord.status == status)
        statement = statement.order_by(
            models.ApprovalRequestRecord.requested_at.desc()
        ).limit(limit)

        with get_session() as session:
            records = session.execute(statement).scalars().all()
            return [_record_to_approval(record) for record in records]

    # -- grants ----------------------------------------------------------- #
    def save_grant(self, grant: PermissionGrant) -> PermissionGrant:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        with get_session() as session:
            record = session.execute(
                select(models.PermissionGrantRecord).where(
                    models.PermissionGrantRecord.grant_id == grant.grant_id
                )
            ).scalar_one_or_none()
            if record is None:
                session.add(_grant_to_record(grant, models))
            else:
                _apply_grant(record, grant)
        return grant

    def get_grant(self, grant_id: str) -> Optional[PermissionGrant]:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        with get_session() as session:
            record = session.execute(
                select(models.PermissionGrantRecord).where(
                    models.PermissionGrantRecord.grant_id == grant_id
                )
            ).scalar_one_or_none()
            return _record_to_grant(record) if record is not None else None

    def list_grants(
        self,
        *,
        mind_id: str,
        action_name: Optional[str] = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> List[PermissionGrant]:
        from sqlalchemy import select

        from genesis.database.base import get_session

        models = self._models()
        statement = select(models.PermissionGrantRecord).where(
            models.PermissionGrantRecord.mind_id == mind_id
        )
        if action_name is not None:
            statement = statement.where(
                models.PermissionGrantRecord.action_name == action_name
            )
        if active_only:
            statement = statement.where(models.PermissionGrantRecord.consumed_at.is_(None))
            statement = statement.where(models.PermissionGrantRecord.revoked_at.is_(None))
        statement = statement.order_by(models.PermissionGrantRecord.issued_at.desc()).limit(limit)

        with get_session() as session:
            records = session.execute(statement).scalars().all()
            return [_record_to_grant(record) for record in records]


# --------------------------------------------------------------------------- #
# Row <-> dataclass conversion
# --------------------------------------------------------------------------- #


def _record_to_event(record: Any) -> AuditEvent:
    return AuditEvent(
        event_id=record.event_id,
        type=record.type,
        timestamp=_from_db(record.timestamp) or datetime.now(timezone.utc),
        mind_id=record.mind_id or "",
        actor_type=record.actor_type or "system",
        actor_id=record.actor_id or "",
        tenant_id=record.tenant_id,
        correlation_id=record.correlation_id or "",
        causation_id=record.causation_id,
        payload=dict(record.payload or {}),
        payload_hash=record.payload_hash or "",
        prev_hash=record.prev_hash or GENESIS_EPOCH_HASH,
        integrity_hash=record.integrity_hash or "",
        sequence=record.sequence or 0,
        schema_version=record.schema_version or 1,
    )


def _receipt_to_record(receipt: ActionReceipt, models: Any) -> Any:
    return models.ActionReceiptRecord(
        receipt_id=receipt.receipt_id,
        action_id=receipt.action_id,
        action_name=receipt.action_name,
        mind_id=receipt.mind_id,
        tenant_id=receipt.tenant_id,
        objective_id=receipt.objective_id,
        outcome=receipt.outcome,
        created_at=_to_db(receipt.created_at),
        requested_by=receipt.requested_by,
        actor_type=receipt.actor_type,
        intent=receipt.intent,
        selected_skill=receipt.selected_skill,
        arguments=receipt.arguments,
        arguments_hash=receipt.arguments_hash,
        risk_level=receipt.risk_level,
        policy_decision=receipt.policy_decision,
        matched_rules=list(receipt.matched_rules),
        approval_id=receipt.approval_id,
        approver_id=receipt.approver_id,
        approved_at=_to_db(receipt.approved_at),
        started_at=_to_db(receipt.started_at),
        completed_at=_to_db(receipt.completed_at),
        duration_ms=receipt.duration_ms,
        affected_resources=list(receipt.affected_resources),
        artifacts=[dict(item) for item in receipt.artifacts],
        evidence=receipt.evidence,
        model_invocations=receipt.model_invocations,
        cost_essence=receipt.cost_essence,
        error_class=receipt.error_class,
        error_message=receipt.error_message,
        rollback=receipt.rollback,
        correlation_id=receipt.correlation_id,
        payload_hash=receipt.payload_hash,
        prev_hash=receipt.prev_hash,
        integrity_hash=receipt.integrity_hash,
        sequence=receipt.sequence,
        schema_version=receipt.schema_version,
    )


def _record_to_receipt(record: Any) -> ActionReceipt:
    return ActionReceipt(
        receipt_id=record.receipt_id,
        action_id=record.action_id,
        action_name=record.action_name,
        mind_id=record.mind_id,
        outcome=record.outcome,
        created_at=_from_db(record.created_at) or datetime.now(timezone.utc),
        tenant_id=record.tenant_id,
        objective_id=record.objective_id,
        requested_by=record.requested_by or "",
        actor_type=record.actor_type or "mind",
        intent=record.intent or "",
        selected_skill=record.selected_skill,
        arguments=dict(record.arguments or {}),
        arguments_hash=record.arguments_hash or "",
        risk_level=record.risk_level or "",
        policy_decision=dict(record.policy_decision or {}),
        matched_rules=tuple(record.matched_rules or ()),
        approval_id=record.approval_id,
        approver_id=record.approver_id,
        approved_at=_from_db(record.approved_at),
        started_at=_from_db(record.started_at),
        completed_at=_from_db(record.completed_at),
        duration_ms=record.duration_ms,
        affected_resources=tuple(record.affected_resources or ()),
        artifacts=tuple(record.artifacts or ()),
        evidence=dict(record.evidence or {}),
        model_invocations=record.model_invocations or 0,
        cost_essence=record.cost_essence or 0,
        error_class=record.error_class,
        error_message=record.error_message,
        rollback=record.rollback,
        correlation_id=record.correlation_id or "",
        payload_hash=record.payload_hash or "",
        prev_hash=record.prev_hash or GENESIS_EPOCH_HASH,
        integrity_hash=record.integrity_hash or "",
        sequence=record.sequence or 0,
        schema_version=record.schema_version or 1,
    )


def _approval_to_record(approval: ApprovalRequest, models: Any) -> Any:
    record = models.ApprovalRequestRecord(approval_id=approval.approval_id)
    _apply_approval(record, approval)
    return record


def _apply_approval(record: Any, approval: ApprovalRequest) -> None:
    record.action_id = approval.action_id
    record.action_name = approval.action_name
    record.mind_id = approval.mind_id
    record.tenant_id = approval.tenant_id
    record.objective_id = approval.objective_id
    record.status = approval.status
    record.risk_level = approval.risk_level
    record.requested_at = _to_db(approval.requested_at)
    record.expires_at = _to_db(approval.expires_at)
    record.resolved_at = _to_db(approval.resolved_at)
    record.parameters = approval.parameters
    record.parameters_hash = approval.parameters_hash
    record.summary = approval.summary
    record.reason = approval.reason
    record.expected_impact = approval.expected_impact
    record.data_accessed = list(approval.data_accessed)
    record.recipient = approval.recipient
    record.financial_cost_essence = approval.financial_cost_essence
    record.reversibility = approval.reversibility
    record.requested_duration = approval.requested_duration
    record.scope = approval.scope
    record.proposed_rollback = approval.proposed_rollback
    record.evidence = approval.evidence
    record.policy_decision = approval.policy_decision
    record.matched_rules = list(approval.matched_rules)
    record.policy_version = approval.policy_version
    record.requires_human = approval.requires_human
    record.approver_role = approval.approver_role
    record.requested_by = approval.requested_by
    record.actor_type = approval.actor_type
    record.approver_id = approval.approver_id
    record.resolution_note = approval.resolution_note
    record.correlation_id = approval.correlation_id
    record.transition_log = [dict(item) for item in approval.transition_log]


def _record_to_approval(record: Any) -> ApprovalRequest:
    return ApprovalRequest(
        approval_id=record.approval_id,
        action_id=record.action_id,
        action_name=record.action_name,
        mind_id=record.mind_id,
        status=record.status,
        requested_at=_from_db(record.requested_at) or datetime.now(timezone.utc),
        risk_level=record.risk_level or "",
        parameters=dict(record.parameters or {}),
        parameters_hash=record.parameters_hash or "",
        tenant_id=record.tenant_id,
        objective_id=record.objective_id,
        summary=record.summary or "",
        reason=record.reason or "",
        expected_impact=record.expected_impact or "",
        data_accessed=tuple(record.data_accessed or ()),
        recipient=record.recipient,
        financial_cost_essence=record.financial_cost_essence or 0,
        reversibility=record.reversibility or "unknown",
        requested_duration=record.requested_duration or "one-off",
        scope=record.scope or "",
        proposed_rollback=record.proposed_rollback or "",
        evidence=dict(record.evidence or {}),
        policy_decision=dict(record.policy_decision or {}),
        matched_rules=tuple(record.matched_rules or ()),
        policy_version=record.policy_version or "",
        requires_human=bool(record.requires_human),
        approver_role=record.approver_role,
        requested_by=record.requested_by or "",
        actor_type=record.actor_type or "mind",
        approver_id=record.approver_id,
        resolved_at=_from_db(record.resolved_at),
        resolution_note=record.resolution_note,
        expires_at=_from_db(record.expires_at),
        correlation_id=record.correlation_id or "",
        transition_log=tuple(record.transition_log or ()),
    )


def _grant_to_record(grant: PermissionGrant, models: Any) -> Any:
    record = models.PermissionGrantRecord(grant_id=grant.grant_id)
    _apply_grant(record, grant)
    return record


def _apply_grant(record: Any, grant: PermissionGrant) -> None:
    record.approval_id = grant.approval_id
    record.mind_id = grant.mind_id
    record.tenant_id = grant.tenant_id
    record.objective_id = grant.objective_id
    record.action_name = grant.action_name
    record.parameters_hash = grant.parameters_hash
    record.scope = grant.scope
    record.issued_by = grant.issued_by
    record.issued_at = _to_db(grant.issued_at)
    record.expires_at = _to_db(grant.expires_at)
    record.single_use = grant.single_use
    record.max_uses = grant.max_uses
    record.consumed_at = _to_db(grant.consumed_at)
    record.revoked_at = _to_db(grant.revoked_at)
    record.revoked_by = grant.revoked_by


def _record_to_grant(record: Any) -> PermissionGrant:
    return PermissionGrant(
        grant_id=record.grant_id,
        approval_id=record.approval_id,
        mind_id=record.mind_id,
        action_name=record.action_name,
        parameters_hash=record.parameters_hash,
        issued_at=_from_db(record.issued_at) or datetime.now(timezone.utc),
        expires_at=_from_db(record.expires_at),
        issued_by=record.issued_by or "",
        tenant_id=record.tenant_id,
        scope=record.scope or "",
        objective_id=record.objective_id,
        single_use=bool(record.single_use),
        max_uses=record.max_uses or 1,
        consumed_at=_from_db(record.consumed_at),
        revoked_at=_from_db(record.revoked_at),
        revoked_by=record.revoked_by,
    )


# --------------------------------------------------------------------------- #
# Process-wide store selection
# --------------------------------------------------------------------------- #

VALID_STORES = ("sql", "memory")
_MEMORY_ALLOWED_ENVS = ("test", "development")

_store: Optional[GovernanceStore] = None


def get_governance_store(explicit: Optional[str] = None) -> GovernanceStore:
    """Return the configured governance store (cached per process).

    Fails closed: an unknown name raises, and the in-memory store refuses to
    activate outside test/development, because a non-durable journal silently
    breaks the accountability guarantee the product depends on.
    """
    global _store

    name = (
        explicit or os.environ.get("GENESIS_GOVERNANCE_STORE") or "sql"
    ).strip().lower()

    if name not in VALID_STORES:
        raise GovernanceStoreError(
            f"Unknown governance store '{name}'. Valid options: {', '.join(VALID_STORES)}"
        )

    if name == "memory":
        env = os.environ.get("GENESIS_ENV", "").strip().lower()
        if env not in _MEMORY_ALLOWED_ENVS:
            raise GovernanceStoreError(
                "The in-memory governance store is not durable and must not be used "
                f"outside test/development (GENESIS_ENV is '{env or 'unset'}'). "
                "Set GENESIS_GOVERNANCE_STORE=sql instead."
            )

    if _store is None or getattr(_store, "name", None) != name:
        _store = InMemoryGovernanceStore() if name == "memory" else SqlAlchemyGovernanceStore()

    return _store


def set_governance_store(store: Optional[GovernanceStore]) -> Optional[GovernanceStore]:
    """Install a specific store (tests, embedded hosts)."""
    global _store
    _store = store
    return _store


def reset_governance_store() -> None:
    """Clear the cached store."""
    global _store
    _store = None
