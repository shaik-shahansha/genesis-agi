"""Append-only event journal and action receipts (ADR-0008).

:class:`AuditService` is the *only* supported write path for governance events.
Redaction happens inside :meth:`AuditService.record`, so a caller cannot persist
a secret by passing one in: the writer normalises and redacts before the store
ever sees the payload (ADR-0008 §4 "Redaction by construction").

The journal is deliberately usable without an observability stack. Traces are
for operations; this journal is for accountability (ADR-0008 §5).
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

from genesis.governance.models import (
    ActionReceipt,
    ActorType,
    AuditEvent,
    EventType,
    utcnow,
)
from genesis.governance.redact import redact_payload, stable_hash
from genesis.governance.store import (
    GovernanceStore,
    JournalVerification,
    get_governance_store,
)

logger = logging.getLogger(__name__)

__all__ = [
    "new_id",
    "new_correlation_id",
    "AuditService",
    "get_audit_service",
    "set_audit_service",
]

#: Retention default for journal export queries (ADR-0008 "retention limits").
DEFAULT_EVENT_RETENTION_DAYS = 365


def new_id(prefix: str = "evt") -> str:
    """Opaque, collision-resistant identifier."""
    return f"{prefix}_{secrets.token_hex(12)}"


def new_correlation_id() -> str:
    """Correlates every event produced by one objective/turn."""
    return f"cor_{secrets.token_hex(10)}"


@dataclass
class AuditService:
    """Writes events and receipts; reads them back for the UI and for export."""

    store: GovernanceStore = None  # type: ignore[assignment]
    default_tenant_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.store is None:
            self.store = get_governance_store()

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #
    def record(
        self,
        event_type: str,
        *,
        mind_id: str,
        payload: Optional[Mapping[str, Any]] = None,
        actor_type: str = ActorType.SYSTEM.value,
        actor_id: str = "",
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> AuditEvent:
        """Append one redacted event to the journal.

        ``payload`` is redacted here, not by the caller, and the raw value is
        never retained.
        """
        event = AuditEvent(
            event_id=new_id("evt"),
            type=str(event_type),
            timestamp=timestamp or utcnow(),
            mind_id=mind_id or "",
            actor_type=actor_type,
            actor_id=actor_id or "",
            tenant_id=tenant_id if tenant_id is not None else self.default_tenant_id,
            correlation_id=correlation_id or new_correlation_id(),
            causation_id=causation_id,
            payload=redact_payload(payload),
        )
        return self.store.append_event(event)

    def events(
        self,
        *,
        mind_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[AuditEvent]:
        return self.store.list_events(
            mind_id=mind_id,
            tenant_id=tenant_id,
            event_type=event_type,
            since=since,
            limit=limit,
        )

    def timeline(self, *, mind_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Event stream shaped for the Mind Workspace timeline UI."""
        return [event.to_dict() for event in self.events(mind_id=mind_id, limit=limit)]

    # ------------------------------------------------------------------ #
    # Receipts
    # ------------------------------------------------------------------ #
    def record_receipt(self, receipt: ActionReceipt) -> ActionReceipt:
        """Persist a receipt. Arguments are re-redacted even if pre-redacted."""
        receipt.arguments = redact_payload(receipt.arguments)
        receipt.intent = str(receipt.intent or "")[:2000]
        receipt.evidence = redact_payload(receipt.evidence)
        receipt.arguments_hash = receipt.arguments_hash or stable_hash(receipt.arguments)
        if not receipt.tenant_id:
            receipt.tenant_id = self.default_tenant_id
        stored = self.store.save_receipt(receipt)
        try:
            self.record(
                EventType.RECEIPT_RECORDED,
                mind_id=stored.mind_id,
                tenant_id=stored.tenant_id,
                actor_type=stored.actor_type,
                actor_id=stored.requested_by,
                correlation_id=stored.correlation_id,
                causation_id=stored.action_id,
                payload={
                    "receipt_id": stored.receipt_id,
                    "action_name": stored.action_name,
                    "outcome": stored.outcome,
                    "risk_level": stored.risk_level,
                    "integrity_hash": stored.integrity_hash,
                },
            )
        except Exception:  # pragma: no cover - receipt is the primary record
            logger.exception("could not journal receipt %s", stored.receipt_id)
        return stored

    def receipts(
        self, *, mind_id: str, limit: int = 100, outcome: Optional[str] = None
    ) -> List[ActionReceipt]:
        return self.store.list_receipts(mind_id=mind_id, limit=limit, outcome=outcome)

    def receipt(self, receipt_id: str) -> Optional[ActionReceipt]:
        return self.store.get_receipt(receipt_id)

    # ------------------------------------------------------------------ #
    # Integrity
    # ------------------------------------------------------------------ #
    def verify_journal(self, *, mind_id: Optional[str] = None) -> JournalVerification:
        """Re-walk the hash chain. Emits an event either way."""
        result = self.store.verify_journal(mind_id=mind_id)
        try:
            self.record(
                EventType.JOURNAL_VERIFIED if result.ok else EventType.JOURNAL_TAMPERED,
                mind_id=mind_id or "*",
                payload=result.to_dict(),
            )
        except Exception:  # pragma: no cover - verification result still returned
            logger.exception("could not journal verification result")
        return result

    def recover_last_event(self, stream_key: str) -> Optional[AuditEvent]:
        return self.store.last_event(stream_key)

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def export(
        self,
        *,
        mind_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Machine-readable accountability export (plan item K3).

        Payloads are already redacted at rest, so an export never widens the
        disclosure that the journal already contains.
        """
        until = until or utcnow()
        since = since or (until - timedelta(days=DEFAULT_EVENT_RETENTION_DAYS))
        events = self.store.list_events(mind_id=mind_id, since=since, limit=100_000)
        events = [event for event in events if event.timestamp <= until]
        receipts = self.store.list_receipts(mind_id=mind_id, limit=100_000)
        receipts = [r for r in receipts if since <= r.created_at <= until]
        return {
            "mind_id": mind_id,
            "since": since.isoformat(),
            "until": until.isoformat(),
            "verification": self.store.verify_journal(mind_id=mind_id).to_dict(),
            "events": [event.to_dict() for event in events],
            "receipts": [receipt.to_dict() for receipt in receipts],
            "counts": {"events": len(events), "receipts": len(receipts)},
        }


_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Process-wide audit service."""
    global _service
    if _service is None:
        _service = AuditService()
    return _service


def set_audit_service(service: Optional[AuditService]) -> Optional[AuditService]:
    """Install a specific audit service (tests, embedded hosts)."""
    global _service
    if service is not None and service.store is None:
        service.store = get_governance_store()
    _service = service
    return _service


def _now_utc() -> datetime:  # pragma: no cover - convenience for callers
    return datetime.now(timezone.utc)


def summarize_events(events: Sequence[AuditEvent]) -> Dict[str, int]:
    """Count events by type (used by the workspace timeline header)."""
    summary: Dict[str, int] = {}
    for event in events:
        summary[event.type] = summary.get(event.type, 0) + 1
    return summary
