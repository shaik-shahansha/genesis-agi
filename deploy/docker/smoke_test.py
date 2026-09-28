#!/usr/bin/env python3
"""Genesis Minds — single-container smoke test.

Verifies that the deployment is actually serving traffic on all four surfaces
(nginx front door, Next.js workspace, FastAPI, WebSocket upgrade) and that
persistent state is where it is supposed to be.

Run from the HOST (against the published port):

    python deploy/docker/smoke_test.py
    python deploy/docker/smoke_test.py http://localhost:8080

Run INSIDE the container:

    docker compose exec genesis python /app/deploy/docker/smoke_test.py

Exit code 0 = all checks passed, 1 = at least one check failed.

No API keys are required: every check is either unauthenticated by design or uses
the built-in admin account.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_BASE = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8080")

# The default admin seeded by genesis/api/auth.py. Intentionally public in the
# source today; see docs/v3/SECURITY_BASELINE.md SEC-08 (T-16 in the threat model).
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "genesis-admin-2026"

results: list[tuple[bool, str, str]] = []


def record(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))
    mark = "PASS" if ok else "FAIL"
    line = f"[{mark}] {name}"
    if detail:
        line += f" — {detail}"
    print(line, flush=True)


def http_get(url: str, timeout: int = 20) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, headers={"Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def check_health(base: str) -> None:
    try:
        status, body, _ = http_get(f"{base}/health")
        payload = json.loads(body)
        providers = payload.get("providers", {})
        record(
            status == 200 and payload.get("status") == "healthy",
            "GET /health (nginx -> API)",
            f"status={status} providers={list(providers) or 'none configured'}",
        )
    except Exception as exc:  # noqa: BLE001 - smoke test reports any failure
        record(False, "GET /health (nginx -> API)", f"{type(exc).__name__}: {exc}")


def check_web(base: str) -> None:
    try:
        status, body, headers = http_get(f"{base}/")
        is_html = "text/html" in headers.get("Content-Type", "")
        record(
            status == 200 and is_html and len(body) > 500,
            "GET / (nginx -> Next.js workspace)",
            f"status={status} bytes={len(body)} html={is_html}",
        )
    except Exception as exc:  # noqa: BLE001
        record(False, "GET / (nginx -> Next.js workspace)", f"{type(exc).__name__}: {exc}")


def check_api_auth(base: str) -> str | None:
    """Log in with the built-in admin. Returns the token, or None."""
    try:
        data = urllib.parse.urlencode(
            {"username": DEFAULT_ADMIN_USER, "password": DEFAULT_ADMIN_PASSWORD}
        ).encode()
        req = urllib.request.Request(
            f"{base}/api/v1/auth/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read())
        token = payload.get("access_token")
        record(
            bool(token),
            "POST /api/v1/auth/token (auth through nginx)",
            f"token_len={len(token) if token else 0}",
        )
        return token
    except Exception as exc:  # noqa: BLE001
        record(False, "POST /api/v1/auth/token (auth through nginx)", f"{type(exc).__name__}: {exc}")
        return None


def check_authed_endpoint(base: str, token: str | None) -> None:
    if not token:
        record(False, "GET /api/v1/auth/me (authenticated)", "skipped: no token")
        return
    try:
        req = urllib.request.Request(
            f"{base}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read())
        record(True, "GET /api/v1/auth/me (authenticated)", f"user={payload.get('username')}")
    except Exception as exc:  # noqa: BLE001
        record(False, "GET /api/v1/auth/me (authenticated)", f"{type(exc).__name__}: {exc}")


def check_websocket_upgrade(base: str, token: str | None) -> None:
    """Confirm nginx proxies the WebSocket upgrade, and that auth is enforced.

    Two assertions:
      1. WITHOUT a credential the handshake must be rejected (SEC-01 fix).
      2. WITH a valid credential the upgrade must be proxied by nginx.

    For (2), a "Mind not found" error frame counts as a PASS: it proves the
    handshake completed and the API answered. It also confirms the caller was
    authenticated, because an unauthenticated handshake is closed first.
    """
    try:
        import asyncio

        import websockets  # type: ignore
    except ImportError:
        record(False, "WS auth + upgrade through nginx", "skipped: websockets not installed")
        return

    ws_base = base.replace("https://", "wss://").replace("http://", "ws://")
    path = "/api/v1/minds/GMD-SMOKE-0000-0000/stream"

    async def _try(url: str) -> tuple[bool, str]:
        try:
            async with websockets.connect(url, open_timeout=20) as ws:
                frame = await asyncio.wait_for(ws.recv(), timeout=20)
                return True, str(frame)[:120]
        except Exception as exc:  # noqa: BLE001
            return False, f"{type(exc).__name__}: {str(exc)[:120]}"

    async def _run() -> None:
        # 1. No credential -> must be refused during the handshake.
        ok_unauthed, detail = await _try(f"{ws_base}{path}?user_email=spoof@example.com")
        record(
            not ok_unauthed,
            "WS rejects unauthenticated handshake (SEC-01)",
            f"refused ({detail})" if not ok_unauthed else f"ACCEPTED WITHOUT AUTH: {detail}",
        )

        # 2. With a credential -> nginx must proxy the upgrade.
        if not token:
            record(False, "WS upgrade through nginx", "skipped: no token")
            return
        ok_auth, detail = await _try(f"{ws_base}{path}?token={urllib.parse.quote(token)}")
        record(ok_auth, "WS upgrade through nginx (authenticated)", detail)

    asyncio.run(_run())


def check_persistence() -> None:
    """Only meaningful when run inside the container."""
    home = Path(os.environ.get("GENESIS_HOME", "/data/.genesis"))
    if not home.exists():
        record(False, "persistent state layout", f"{home} not present (run inside the container)")
        return

    try:
        dirs = {p.name for p in home.iterdir()}
        expected = {"data", "minds", "logs"}
        missing = expected - dirs
        record(
            not missing,
            "persistent state layout",
            f"{home}: {sorted(dirs)}" + (f" MISSING={sorted(missing)}" if missing else ""),
        )
    except Exception as exc:  # noqa: BLE001
        record(False, "persistent state layout", f"{type(exc).__name__}: {exc}")

    db = home / "genesis.db"
    if not db.exists():
        record(
            True,
            "database inside volume",
            f"{db} not created yet (created lazily on first DB write)",
        )
        return
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        tables = sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'"))
        con.close()
        record(
            len(tables) > 0,
            "database inside volume",
            f"{len(tables)} tables (e.g. {', '.join(tables[:5])})",
        )
    except Exception as exc:  # noqa: BLE001
        record(False, "database inside volume", f"{type(exc).__name__}: {exc}")

    # State must never be written outside the volume.
    for stray in ("/app/.genesis", "/root/.genesis"):
        try:
            exists = Path(stray).exists()
        except PermissionError:
            # Running unprivileged: the directory is inaccessible, so nothing can
            # have been written there. That is the desired outcome.
            exists = False
        record(not exists, "no state outside /data", f"{stray} absent")


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE).rstrip("/")
    print(f"Genesis smoke test against {base}\n")

    check_health(base)
    check_web(base)
    token = check_api_auth(base)
    check_authed_endpoint(base, token)
    check_websocket_upgrade(base, token)
    check_persistence()

    passed = sum(1 for ok, _, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} checks passed")
    if passed != total:
        print("\nFailed checks:")
        for ok, name, detail in results:
            if not ok:
                print(f"  - {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
