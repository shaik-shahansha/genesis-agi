"""Emergency stop (ADR-0006 §3, plan item B12).

The stop is a **system state**, not a suggestion. When engaged for a Mind, the
policy engine returns ``EMERGENCY_STOP`` for anything above read-only, so the
halt does not depend on every capability remembering to check.

State is held in-process for fast reads and journaled so the reason is
auditable. :meth:`EmergencyStopService.rehydrate` rebuilds the in-process state
from the journal, which is what makes the stop survive a restart.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from genesis.governance.audit import AuditService
from genesis.governance.models import ActorType, EventType, utcnow

__all__ = ["EmergencyStopState", "EmergencyStopService", "get_emergency_stop_service"]


@dataclass(frozen=True)
class EmergencyStopState:
    """Current stop state for one Mind."""

    mind_id: str
    engaged: bool
    reason: str = ""
    engaged_by: str = ""
    engaged_at: Optional[datetime] = None
    released_by: Optional[str] = None
    released_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mind_id": self.mind_id,
            "engaged": self.engaged,
            "reason": self.reason,
            "engaged_by": self.engaged_by,
            "engaged_at": self.engaged_at.isoformat() if self.engaged_at else None,
            "released_by": self.released_by,
            "released_at": self.released_at.isoformat() if self.released_at else None,
        }


@dataclass
class EmergencyStopService:
    """Engage, release, and read the emergency stop."""

    audit: Optional[AuditService] = None
    _states: Dict[str, EmergencyStopState] = field(default_factory=dict, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    #: When True, a stop also covers every Mind in the same tenant.
    tenant_wide: bool = True

    # ------------------------------------------------------------------ #
    def is_engaged(self, mind_id: str) -> bool:
        with self._lock:
            state = self._states.get(mind_id)
            return bool(state and state.engaged)

    def state(self, mind_id: str) -> EmergencyStopState:
        with self._lock:
            return self._states.get(
                mind_id, EmergencyStopState(mind_id=mind_id, engaged=False)
            )

    def all_states(self) -> List[EmergencyStopState]:
        with self._lock:
            return list(self._states.values())

    # ------------------------------------------------------------------ #
    def engage(
        self,
        mind_id: str,
        *,
        actor_id: str,
        reason: str,
        actor_type: str = ActorType.OPERATOR.value,
        tenant_id: Optional[str] = None,
    ) -> EmergencyStopState:
        """Halt a Mind. Safe to call repeatedly."""
        now = utcnow()
        state = EmergencyStopState(
            mind_id=mind_id,
            engaged=True,
            reason=reason or "operator engaged the emergency stop",
            engaged_by=actor_id,
            engaged_at=now,
        )
        with self._lock:
            self._states[mind_id] = state
        self._record(
            EventType.ACTION_EMERGENCY_STOP,
            mind_id=mind_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=actor_type,
            payload={"reason": state.reason, "tenant_wide": self.tenant_wide},
        )
        return state

    def release(
        self,
        mind_id: str,
        *,
        actor_id: str,
        note: Optional[str] = None,
        actor_type: str = ActorType.OPERATOR.value,
        tenant_id: Optional[str] = None,
    ) -> EmergencyStopState:
        """Resume a Mind. A human must do this; a Mind cannot release itself."""
        now = utcnow()
        previous = self.state(mind_id)
        state = EmergencyStopState(
            mind_id=mind_id,
            engaged=False,
            reason=previous.reason,
            engaged_by=previous.engaged_by,
            engaged_at=previous.engaged_at,
            released_by=actor_id,
            released_at=now,
        )
        with self._lock:
            self._states[mind_id] = state
        self._record(
            EventType.EMERGENCY_STOP_RELEASED,
            mind_id=mind_id,
            tenant_id=tenant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"note": note, "previous_reason": previous.reason},
        )
        return state

    # ------------------------------------------------------------------ #
    def rehydrate(self, mind_id: str) -> EmergencyStopState:
        """Rebuild in-process state from the journal (survives a restart)."""
        if self.audit is None:
            return self.state(mind_id)
        events = self.audit.events(mind_id=mind_id, limit=10_000)
        latest: Optional[EmergencyStopState] = None
        for event in events:
            if event.type == EventType.ACTION_EMERGENCY_STOP and event.payload.get(
                "reason"
            ) != "policy: prohibited capability attempted":
                latest = EmergencyStopState(
                    mind_id=mind_id,
                    engaged=True,
                    reason=str(event.payload.get("reason", "")),
                    engaged_by=event.actor_id,
                    engaged_at=event.timestamp,
                )
            elif event.type == EventType.EMERGENCY_STOP_RELEASED:
                latest = EmergencyStopState(
                    mind_id=mind_id,
                    engaged=False,
                    reason=str(event.payload.get("previous_reason", "")),
                    engaged_by="",
                    engaged_at=None,
                    released_by=event.actor_id,
                    released_at=event.timestamp,
                )
        if latest is not None:
            with self._lock:
                self._states[mind_id] = latest
        return self.state(mind_id)

    # ------------------------------------------------------------------ #
    def _record(
        self,
        event_type: str,
        *,
        mind_id: str,
        tenant_id: Optional[str],
        actor_id: str,
        actor_type: str,
        payload: Dict[str, Any],
    ) -> None:
        if self.audit is None:
            return
        self.audit.record(
            event_type,
            mind_id=mind_id,
            tenant_id=tenant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=payload,
        )


_service: Optional[EmergencyStopService] = None


def get_emergency_stop_service() -> EmergencyStopService:
    """Process-wide emergency stop service."""
    global _service
    if _service is None:
        _service = EmergencyStopService(audit=AuditService())
    return _service


def set_emergency_stop_service(
    service: Optional[EmergencyStopService],
) -> Optional[EmergencyStopService]:
    """Install a specific service (tests)."""
    global _service
    _service = service
    return _service
