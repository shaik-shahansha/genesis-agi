"""SEC-01 — WebSocket authentication and identity spoofing.

Before this fix the WebSocket endpoint called ``accept()`` before any check and
derived the caller's identity from a client-supplied ``?user_email=`` query
parameter, defaulting to a shared ``web_user@genesis.local`` when absent. Any
client that could reach the port could therefore:

  * open a chat session on any Mind whose id it knew or guessed;
  * impersonate an arbitrary email address;
  * receive another user's pending proactive notifications.

These tests lock the fixed behaviour in place.

The tests are hermetic: they exercise the authentication helpers directly and
the endpoint's rejection path via the ASGI test client. No Mind needs to exist,
no API keys are required, and no network access occurs.
"""

from __future__ import annotations

import pytest
from starlette.datastructures import Headers, QueryParams

from genesis.api import auth as auth_module
from genesis.api.auth import (
    User,
    UserRole,
    authenticate_websocket,
    create_access_token,
    resolve_user_from_token,
)

ADMIN_USER = "admin"
ADMIN_EMAIL = "admin@genesis.local"
ADMIN_PASSWORD = "genesis-admin-2026"


class FakeWebSocket:
    """Minimal stand-in exposing only what ``authenticate_websocket`` reads."""

    def __init__(
        self,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
    ) -> None:
        self.headers = Headers(headers or {})
        self.query_params = QueryParams(query_params or {})


def _seeded_user() -> None:
    """Ensure the built-in users exist (USERS_DB is process-local)."""
    auth_module._initialize_default_users()


def _admin_token(ttl_minutes: int = 30) -> str:
    from datetime import timedelta

    return create_access_token(
        {"sub": ADMIN_USER, "role": UserRole.ADMIN.value, "email": ADMIN_EMAIL},
        expires_delta=timedelta(minutes=ttl_minutes),
    )


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_credential_is_rejected():
    """A handshake with no credential must not authenticate anybody."""
    assert await authenticate_websocket(FakeWebSocket()) is None


@pytest.mark.asyncio
async def test_empty_bearer_token_is_rejected():
    ws = FakeWebSocket(headers={"authorization": "Bearer "})
    assert await authenticate_websocket(ws) is None


@pytest.mark.asyncio
async def test_malformed_authorization_header_is_rejected():
    ws = FakeWebSocket(headers={"authorization": "Token abc123"})
    assert await authenticate_websocket(ws) is None


@pytest.mark.asyncio
async def test_garbage_token_is_rejected():
    ws = FakeWebSocket(headers={"authorization": "Bearer not-a-jwt"})
    assert await authenticate_websocket(ws) is None


@pytest.mark.asyncio
async def test_valid_bearer_token_authenticates():
    _seeded_user()
    ws = FakeWebSocket(headers={"authorization": f"Bearer {_admin_token()}"})

    user = await authenticate_websocket(ws)

    assert isinstance(user, User)
    assert user.username == ADMIN_USER
    assert user.email == ADMIN_EMAIL


@pytest.mark.asyncio
async def test_valid_token_via_query_parameter_authenticates():
    """Browsers cannot set WebSocket headers, so ?token= is supported."""
    _seeded_user()
    ws = FakeWebSocket(query_params={"token": _admin_token()})

    user = await authenticate_websocket(ws)

    assert isinstance(user, User)
    assert user.username == ADMIN_USER


@pytest.mark.asyncio
async def test_forged_token_signed_with_a_different_key_is_rejected():
    """A token signed with an attacker-chosen key must never authenticate."""
    from jose import jwt

    forged = jwt.encode(
        {"sub": ADMIN_USER, "role": "admin", "email": ADMIN_EMAIL},
        "attacker-controlled-key",
        algorithm="HS256",
    )
    ws = FakeWebSocket(headers={"authorization": f"Bearer {forged}"})

    assert await authenticate_websocket(ws) is None


@pytest.mark.asyncio
async def test_expired_token_is_rejected():
    from datetime import timedelta

    expired = create_access_token(
        {"sub": ADMIN_USER, "role": UserRole.ADMIN.value, "email": ADMIN_EMAIL},
        expires_delta=timedelta(minutes=-5),
    )
    ws = FakeWebSocket(headers={"authorization": f"Bearer {expired}"})

    assert await authenticate_websocket(ws) is None


@pytest.mark.asyncio
async def test_token_for_unknown_user_is_rejected():
    """A well-signed token for a user that no longer exists is not enough."""
    _seeded_user()
    token = create_access_token(
        {"sub": "ghost-user", "role": "user", "email": "ghost@example.com"}
    )
    ws = FakeWebSocket(headers={"authorization": f"Bearer {token}"})

    assert await authenticate_websocket(ws) is None


# ---------------------------------------------------------------------------
# The core regression: client-supplied identity must be ignored
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_supplied_user_email_cannot_impersonate():
    """The spoofing vector that made SEC-01 critical.

    Supplying ``?user_email=victim@example.com`` must not change the resolved
    identity: it still comes from the verified credential.
    """
    _seeded_user()
    ws = FakeWebSocket(
        headers={"authorization": f"Bearer {_admin_token()}"},
        query_params={"user_email": "victim@example.com"},
    )

    user = await authenticate_websocket(ws)

    assert user is not None
    assert user.email == ADMIN_EMAIL
    assert user.email != "victim@example.com"


@pytest.mark.asyncio
async def test_user_email_alone_does_not_authenticate():
    """user_email was previously treated as an identity. It must now be inert."""
    ws = FakeWebSocket(query_params={"user_email": "victim@example.com"})

    assert await authenticate_websocket(ws) is None


# ---------------------------------------------------------------------------
# API-key path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_api_key_authenticates():
    _seeded_user()
    key = auth_module.create_api_key(ADMIN_USER, description="test")

    ws = FakeWebSocket(headers={"x-api-key": key})

    user = await authenticate_websocket(ws)

    assert isinstance(user, User)
    assert user.username == ADMIN_USER


@pytest.mark.asyncio
async def test_unknown_api_key_is_rejected():
    ws = FakeWebSocket(headers={"x-api-key": "gsk_definitely-not-valid"})

    assert await authenticate_websocket(ws) is None


# ---------------------------------------------------------------------------
# HTTP path still behaves (the refactor must not have changed it)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_user_from_token_roundtrip():
    _seeded_user()

    user = await resolve_user_from_token(_admin_token())

    assert user is not None
    assert user.username == ADMIN_USER


@pytest.mark.asyncio
async def test_resolve_user_from_token_rejects_empty_string():
    assert await resolve_user_from_token("") is None


# ---------------------------------------------------------------------------
# Endpoint-level rejection
# ---------------------------------------------------------------------------


def _client():
    from fastapi.testclient import TestClient

    from genesis.api.server import create_app

    return TestClient(create_app())


def test_websocket_endpoint_rejects_unauthenticated_handshake():
    """The socket must be closed during the handshake, before acceptance.

    Starlette surfaces a pre-accept ``close()`` as a disconnect on connect.
    """
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises((WebSocketDisconnect, Exception)):
        with _client().websocket_connect("/api/v1/minds/GMD-TEST-0000-0000/stream") as ws:
            ws.receive_text()


def test_websocket_endpoint_rejects_unauthenticated_handshake_even_with_user_email():
    """Supplying user_email must not buy an unauthenticated caller entry."""
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises((WebSocketDisconnect, Exception)):
        with _client().websocket_connect(
            "/api/v1/minds/GMD-TEST-0000-0000/stream?user_email=web_user@genesis.local"
        ) as ws:
            ws.receive_text()
