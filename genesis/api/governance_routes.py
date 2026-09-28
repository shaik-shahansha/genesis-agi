"""Governance API: approvals, receipts, event timeline, and the emergency stop.

These endpoints exist because accountable autonomy is a *product* feature, not
just compliance machinery (ADR-0008 §2: "Receipts are user-visible in the Mind
Workspace"). The web playground renders them directly.

Authorization model:

* **Read** (timeline, receipts, pending approvals) follows the same access rules
  as the rest of the Mind API: admin, explicit grant, public Mind, or creator.
* **Write** (approve, reject, engage/release the emergency stop) requires the
  Mind's creator or an admin. A public Mind does not make its approval queue
  public, and a Mind can never approve its own request (enforced by
  ``ApprovalService``, which rejects a ``mind`` actor for human-required
  actions).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from genesis.api.auth import User, UserRole, get_current_active_user, require_write_access

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Services ==================== #


def _gate():
    from genesis.governance import get_governance_gate

    return get_governance_gate()


def _approvals():
    return _gate().approvals


def _audit():
    return _gate().audit


def _estop():
    return _gate().emergency_stop


# ==================== Access control ==================== #


def _load_mind_record(gmid: str):
    from genesis.database.manager import MetaverseDB

    record = None
    try:
        record = MetaverseDB().get_mind(gmid)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("could not load Mind %s for governance check: %s", gmid, exc)
    return record


def _creator_email(record: Any) -> str:
    if record is None:
        return ""
    for attribute in ("creator_email", "creator"):
        value = getattr(record, attribute, None)
        if value:
            return str(value).strip().lower()
    return ""


async def assert_mind_read_access(gmid: str, user: User) -> None:
    """Raise 403 unless ``user`` may read governance data for ``gmid``."""
    if user.role == UserRole.ADMIN:
        return

    email = (user.email or user.username or "").strip().lower()

    try:
        from genesis.database.manager import MetaverseDB

        db = MetaverseDB()
        allowed = {str(item).strip().lower() for item in (db.get_mind_allowed_users(gmid) or [])}
        if email and email in allowed:
            return
        if db.get_mind_is_public(gmid):
            return
    except Exception as exc:
        # Fail closed: a broken access check never grants access.
        logger.error("governance access check failed for %s: %s", gmid, exc)
        raise HTTPException(status_code=503, detail="Access check unavailable") from exc

    record = _load_mind_record(gmid)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Mind '{gmid}' not found")
    if email and _creator_email(record) == email:
        return

    raise HTTPException(status_code=403, detail="You do not have access to this Mind")


async def assert_mind_owner(gmid: str, user: User) -> None:
    """Raise 403 unless ``user`` may make decisions for ``gmid``."""
    if user.role == UserRole.ADMIN:
        return

    record = _load_mind_record(gmid)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Mind '{gmid}' not found")

    email = (user.email or user.username or "").strip().lower()
    if email and _creator_email(record) == email:
        return
    raise HTTPException(
        status_code=403,
        detail="Only the Mind's creator can approve or reject its actions",
    )


# ==================== Models ==================== #


class ApprovalDecisionRequest(BaseModel):
    """Approve or reject a pending action."""

    note: Optional[str] = Field(default=None, max_length=2000)
    #: How long the issued grant stays redeemable, in seconds.
    ttl_seconds: Optional[int] = Field(default=None, ge=10, le=86_400)


class EmergencyStopRequest(BaseModel):
    """Engage or release the emergency stop."""

    engage: bool
    reason: str = Field(default="", max_length=2000)


# ==================== Endpoints ==================== #


@router.get("/{mind_id}/approvals", summary="Pending approvals (approval inbox)")
async def list_approvals(
    mind_id: str,
    status: Optional[str] = Query(default=None, description="PROPOSED, WAITING_FOR_APPROVAL, ..."),
    limit: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Approvals as plain-language cards: what, why, what it costs, what reverses."""
    await assert_mind_read_access(mind_id, current_user)
    service = _approvals()

    if status is None or status == "WAITING_FOR_APPROVAL":
        items = service.inbox(mind_id=mind_id, limit=limit)
    else:
        items = [
            item.to_dict()
            for item in service.store.list_approvals(
                mind_id=mind_id, status=status, limit=limit
            )
        ]
    return {"mind_id": mind_id, "count": len(items), "approvals": items}


@router.get("/{mind_id}/approvals/{approval_id}", summary="One approval in full")
async def get_approval(
    mind_id: str,
    approval_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    await assert_mind_read_access(mind_id, current_user)
    try:
        approval = _approvals().get(approval_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")
    if approval.mind_id != mind_id:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")
    return approval.to_dict()


@router.post("/{mind_id}/approvals/{approval_id}/approve", summary="Approve a pending action")
async def approve_action(
    mind_id: str,
    approval_id: str,
    body: ApprovalDecisionRequest,
    current_user: User = Depends(require_write_access),
) -> Dict[str, Any]:
    """Issue a parameter-bound, single-use, expiring grant for this exact action."""
    await assert_mind_owner(mind_id, current_user)
    service = _approvals()
    try:
        approval = service.get(approval_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")
    if approval.mind_id != mind_id:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")

    approver = current_user.email or current_user.username or "unknown"
    ttl = timedelta(seconds=body.ttl_seconds) if body.ttl_seconds else None
    try:
        grant = service.approve(
            approval_id, approver_id=approver, note=body.note, ttl=ttl
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "success": True,
        "approval": service.get(approval_id).to_dict(),
        "grant": grant.to_dict(),
        "note": (
            "The Mind can now perform exactly this action, once, before the grant "
            "expires. Changing any material parameter invalidates it."
        ),
    }


@router.post("/{mind_id}/approvals/{approval_id}/reject", summary="Reject a pending action")
async def reject_action(
    mind_id: str,
    approval_id: str,
    body: ApprovalDecisionRequest,
    current_user: User = Depends(require_write_access),
) -> Dict[str, Any]:
    await assert_mind_owner(mind_id, current_user)
    service = _approvals()
    try:
        approval = service.get(approval_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")
    if approval.mind_id != mind_id:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")

    approver = current_user.email or current_user.username or "unknown"
    try:
        updated = service.reject(approval_id, approver_id=approver, note=body.note)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"success": True, "approval": updated.to_dict()}


@router.get("/{mind_id}/receipts", summary="Action receipts")
async def list_receipts(
    mind_id: str,
    outcome: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Immutable record of every action attempt, including refused ones."""
    await assert_mind_read_access(mind_id, current_user)
    receipts = _audit().receipts(mind_id=mind_id, limit=limit, outcome=outcome)
    return {
        "mind_id": mind_id,
        "count": len(receipts),
        "receipts": [receipt.to_dict() for receipt in receipts],
    }


@router.get("/{mind_id}/receipts/{receipt_id}", summary="One action receipt")
async def get_receipt(
    mind_id: str,
    receipt_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    await assert_mind_read_access(mind_id, current_user)
    receipt = _audit().receipt(receipt_id)
    if receipt is None or receipt.mind_id != mind_id:
        raise HTTPException(status_code=404, detail=f"Receipt '{receipt_id}' not found")
    return receipt.to_dict()


@router.get("/{mind_id}/timeline", summary="Event journal timeline")
async def list_timeline(
    mind_id: str,
    event_type: Optional[str] = Query(default=None, description="Filter, e.g. action.blocked"),
    hours: int = Query(default=24, ge=1, le=24 * 365),
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """The Mind's account of what happened, redacted at write time."""
    await assert_mind_read_access(mind_id, current_user)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    events = _audit().events(
        mind_id=mind_id, event_type=event_type, since=since, limit=limit
    )
    return {
        "mind_id": mind_id,
        "since": since.isoformat(),
        "count": len(events),
        "events": [event.to_dict() for event in events],
    }


@router.get("/{mind_id}/journal/verify", summary="Verify the audit chain")
async def verify_journal(
    mind_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Re-walk the hash chain. Reports the first broken link, if any."""
    await assert_mind_read_access(mind_id, current_user)
    return _audit().verify_journal(mind_id=mind_id).to_dict()


@router.get("/{mind_id}/audit/export", summary="Full accountability export")
async def export_audit(
    mind_id: str,
    days: int = Query(default=30, ge=1, le=3650),
    current_user: User = Depends(require_write_access),
) -> Dict[str, Any]:
    """Events plus receipts and a chain verification, for review or compliance."""
    await assert_mind_owner(mind_id, current_user)
    until = datetime.now(timezone.utc)
    return _audit().export(mind_id=mind_id, since=until - timedelta(days=days), until=until)


@router.get("/{mind_id}/emergency-stop", summary="Emergency stop state")
async def get_emergency_stop(
    mind_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    await assert_mind_read_access(mind_id, current_user)
    return _estop().state(mind_id).to_dict()


@router.post("/{mind_id}/emergency-stop", summary="Engage or release the emergency stop")
async def set_emergency_stop(
    mind_id: str,
    body: EmergencyStopRequest,
    current_user: User = Depends(require_write_access),
) -> Dict[str, Any]:
    """Halt or resume a Mind.

    Engaging is available to anyone with access so a concerned user can stop a
    Mind immediately; releasing requires the owner, so a Mind cannot be quietly
    restarted by a bystander.
    """
    actor = current_user.email or current_user.username or "unknown"

    if body.engage:
        await assert_mind_read_access(mind_id, current_user)
        state = _estop().engage(mind_id, actor_id=actor, reason=body.reason or "user requested")
        return {"success": True, "state": state.to_dict()}

    await assert_mind_owner(mind_id, current_user)
    state = _estop().release(mind_id, actor_id=actor, note=body.reason)
    return {"success": True, "state": state.to_dict()}


@router.get("/{mind_id}/governance", summary="Governance summary")
async def governance_summary(
    mind_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """One call for the workspace header: stop state, pending count, recent refusals."""
    await assert_mind_read_access(mind_id, current_user)
    approvals = _approvals()
    audit = _audit()
    estop = _estop()

    from genesis.governance import EventType, POLICY_VERSION, CHARTER_VERSION

    pending = approvals.inbox(mind_id=mind_id, limit=200)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    events = audit.events(mind_id=mind_id, since=since, limit=1000)

    def count(event_type: str) -> int:
        return sum(1 for event in events if event.type == event_type)

    return {
        "mind_id": mind_id,
        "policy_version": POLICY_VERSION,
        "charter_version": CHARTER_VERSION,
        "emergency_stop": estop.state(mind_id).to_dict(),
        "pending_approvals": len(pending),
        "last_24h": {
            "events": len(events),
            "policy_evaluations": count(EventType.ACTION_POLICY_EVALUATED),
            "executed": count(EventType.ACTION_EXECUTED),
            "failed": count(EventType.ACTION_FAILED),
            "blocked": count(EventType.ACTION_BLOCKED),
            "emergency_stops": count(EventType.ACTION_EMERGENCY_STOP),
        },
        "journal": audit.verify_journal(mind_id=mind_id).to_dict(),
    }


@router.get("/{mind_id}/capabilities", summary="Declared risk for each capability")
async def list_capabilities(
    mind_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """What this Mind can do, and what each capability is allowed to do without help."""
    await assert_mind_read_access(mind_id, current_user)
    from genesis.governance import get_capability_registry

    registry = get_capability_registry()
    capabilities: List[Dict[str, Any]] = []
    for name in registry.names():
        profile = registry.get(name)
        if profile is None:  # pragma: no cover - names() comes from the registry
            continue
        capabilities.append(profile.to_dict())
    capabilities.sort(key=lambda item: (str(item["risk"]), str(item["name"])))
    return {"mind_id": mind_id, "count": len(capabilities), "capabilities": capabilities}
