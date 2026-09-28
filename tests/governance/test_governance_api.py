"""Governance API surface tests.

Focus: the routes exist, and access control fails closed. The approval and audit
logic itself is covered by the service-level tests.
"""

from __future__ import annotations

import pytest

from genesis.api.auth import User, UserRole
from genesis.api.governance_routes import (
    assert_mind_owner,
    assert_mind_read_access,
)


class StubRecord:
    def __init__(self, creator: str) -> None:
        self.creator = creator


class StubDB:
    def __init__(self, *, creator: str = "owner@example.com", public: bool = False, allowed=()):
        self._creator = creator
        self._public = public
        self._allowed = list(allowed)

    def get_mind(self, gmid: str):
        return StubRecord(self._creator)

    def get_mind_allowed_users(self, gmid: str):
        return self._allowed

    def get_mind_is_public(self, gmid: str):
        return self._public


def make_user(email: str, role: UserRole = UserRole.USER) -> User:
    return User(username=email.split("@")[0], email=email, role=role)


@pytest.fixture
def patched_db(monkeypatch):
    holder = {"db": StubDB()}

    import genesis.database.manager as manager

    monkeypatch.setattr(manager, "MetaverseDB", lambda *a, **k: holder["db"])

    import genesis.api.governance_routes as routes

    monkeypatch.setattr(routes, "_load_mind_record", lambda gmid: holder["db"].get_mind(gmid))
    return holder


# --------------------------------------------------------------------------- #
# Read access
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_creator_can_read(patched_db):
    await assert_mind_read_access("gm_1", make_user("owner@example.com"))


@pytest.mark.asyncio
async def test_admin_can_read(patched_db):
    await assert_mind_read_access("gm_1", make_user("someone@else.com", UserRole.ADMIN))


@pytest.mark.asyncio
async def test_explicitly_allowed_user_can_read(patched_db):
    patched_db["db"] = StubDB(allowed=["friend@example.com"])
    await assert_mind_read_access("gm_1", make_user("friend@example.com"))


@pytest.mark.asyncio
async def test_public_mind_is_readable(patched_db):
    patched_db["db"] = StubDB(public=True)
    await assert_mind_read_access("gm_1", make_user("stranger@example.com"))


@pytest.mark.asyncio
async def test_stranger_is_refused(patched_db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        await assert_mind_read_access("gm_1", make_user("stranger@example.com"))
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_access_check_fails_closed_when_the_db_breaks(patched_db, monkeypatch):
    from fastapi import HTTPException

    def boom(*args, **kwargs):
        raise RuntimeError("database unreachable")

    import genesis.database.manager as manager

    monkeypatch.setattr(manager, "MetaverseDB", boom)
    with pytest.raises(HTTPException) as excinfo:
        await assert_mind_read_access("gm_1", make_user("owner@example.com"))
    assert excinfo.value.status_code == 503


# --------------------------------------------------------------------------- #
# Write access
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_creator_is_an_owner(patched_db):
    await assert_mind_owner("gm_1", make_user("owner@example.com"))


@pytest.mark.asyncio
async def test_an_allowed_reader_is_not_an_owner(patched_db):
    from fastapi import HTTPException

    patched_db["db"] = StubDB(allowed=["friend@example.com"])
    with pytest.raises(HTTPException) as excinfo:
        await assert_mind_owner("gm_1", make_user("friend@example.com"))
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_a_public_mind_does_not_make_its_approval_queue_public(patched_db):
    from fastapi import HTTPException

    patched_db["db"] = StubDB(public=True)
    with pytest.raises(HTTPException) as excinfo:
        await assert_mind_owner("gm_1", make_user("stranger@example.com"))
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_is_an_owner(patched_db):
    await assert_mind_owner("gm_1", make_user("admin@example.com", UserRole.ADMIN))


@pytest.mark.asyncio
async def test_unknown_mind_is_a_404(patched_db, monkeypatch):
    from fastapi import HTTPException

    import genesis.api.governance_routes as routes

    monkeypatch.setattr(routes, "_load_mind_record", lambda gmid: None)
    with pytest.raises(HTTPException) as excinfo:
        await assert_mind_owner("gm_missing", make_user("owner@example.com"))
    assert excinfo.value.status_code == 404


# --------------------------------------------------------------------------- #
# Route registration
# --------------------------------------------------------------------------- #


def test_governance_endpoints_are_mounted():
    from genesis.api.server import create_app

    paths = set(create_app().openapi()["paths"])
    expected = {
        "/api/v1/minds/{mind_id}/approvals",
        "/api/v1/minds/{mind_id}/approvals/{approval_id}",
        "/api/v1/minds/{mind_id}/approvals/{approval_id}/approve",
        "/api/v1/minds/{mind_id}/approvals/{approval_id}/reject",
        "/api/v1/minds/{mind_id}/receipts",
        "/api/v1/minds/{mind_id}/receipts/{receipt_id}",
        "/api/v1/minds/{mind_id}/timeline",
        "/api/v1/minds/{mind_id}/journal/verify",
        "/api/v1/minds/{mind_id}/audit/export",
        "/api/v1/minds/{mind_id}/emergency-stop",
        "/api/v1/minds/{mind_id}/governance",
        "/api/v1/minds/{mind_id}/capabilities",
    }
    assert expected <= paths


def test_approve_endpoint_requires_write_access():
    """Approving is a write, so it must not be reachable read-only."""
    from genesis.api.server import create_app

    schema = create_app().openapi()
    operation = schema["paths"]["/api/v1/minds/{mind_id}/approvals/{approval_id}/approve"]["post"]
    assert operation["summary"].lower().startswith("approve")
    # The dependency is enforced in code; this guards the route from being
    # copied to a public path without its dependency.
    import inspect

    from genesis.api.governance_routes import approve_action

    source = inspect.getsource(approve_action)
    assert "require_write_access" in source
    assert "assert_mind_owner" in source
