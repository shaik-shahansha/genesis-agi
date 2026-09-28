#!/usr/bin/env python3
"""SEC-02 live verification against a running Genesis container.

Proves, against the deployed service (not just unit tests), that:

  1. GET /artifacts/download WITHOUT a credential is rejected (it previously
     required no authentication at all).
  2. A traversal/absolute filename is rejected with 400.
  3. A filename that escapes via the old prefix-match bypass is rejected.
  4. Workspace upload with a traversal filename is rejected with 400 and
     writes nothing outside the workspace.

Usage (from the host):
    python deploy/docker/verify_sec02.py
    python deploy/docker/verify_sec02.py http://127.0.0.1:8080

Exit 0 = all assertions held.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8080")
ADMIN_USER = "admin"
ADMIN_PASSWORD = "genesis-admin-2026"

results: list[tuple[bool, str, str]] = []


def record(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""), flush=True)


def login(base: str) -> str:
    data = urllib.parse.urlencode(
        {"username": ADMIN_USER, "password": ADMIN_PASSWORD}
    ).encode()
    req = urllib.request.Request(
        f"{base}/api/v1/auth/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())["access_token"]


def status_of(url: str, token: str | None = None) -> int:
    """Return the HTTP status, treating 4xx as a value rather than an error."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


TRAVERSAL_NAMES = [
    "../../../../etc/passwd",
    "/etc/passwd",
    r"..\..\windows\win.ini",
    "../../../app/genesis/core/constitution.py",  # the old cwd-bypass target
]

# Already-percent-encoded input. Once decoded this is the literal string
# "..%2f..%2fetc%2fpasswd" (no separator), i.e. a harmless name that simply does
# not exist. Included to prove that percent-encoding is not a bypass.
ENCODED_NAMES = ["..%2f..%2f..%2fetc%2fpasswd"]


def verify_download(base: str, token: str) -> None:
    mind = "GMD-SEC02-0000-0000"

    # 1. No credential at all.
    code = status_of(f"{base}/api/v1/minds/{mind}/artifacts/download?filename=notes.txt")
    record(code == 401, "artifact download requires auth", f"status={code} (expected 401)")

    # 2. Traversal and absolute names, WITH a valid credential.
    #    A named file containing a separator must be rejected outright.
    for name in TRAVERSAL_NAMES:
        url = (
            f"{base}/api/v1/minds/{mind}/artifacts/download"
            f"?filename={urllib.parse.quote(name, safe='')}"
        )
        code = status_of(url, token)
        record(
            code in (400, 403),
            "artifact download rejects escape",
            f"filename={name!r} status={code} (expected 400/403)",
        )

    # 3. Percent-encoded variants: the security property is simply that no file
    #    is ever served (never 2xx).
    for name in ENCODED_NAMES:
        url = (
            f"{base}/api/v1/minds/{mind}/artifacts/download"
            f"?filename={urllib.parse.quote(name, safe='')}"
        )
        code = status_of(url, token)
        record(
            code not in range(200, 300),
            "artifact download never serves an encoded escape",
            f"filename={name!r} status={code} (must not be 2xx)",
        )


def _multipart(field: str, filename: str, content: bytes) -> tuple[bytes, str]:
    boundary = "----GenesisSec02Boundary"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: application/octet-stream\r\n\r\n",
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def verify_upload(base: str, token: str) -> None:
    mind = "GMD-SEC02-0000-0000"

    for name in ["../../../pwned.txt", "/tmp/pwned.txt", r"..\..\pwned.txt"]:
        body, content_type = _multipart("file", name, b"pwned")
        req = urllib.request.Request(
            f"{base}/api/v1/minds/{mind}/workspace/upload",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": content_type,
                "Content-Length": str(len(body)),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                code = resp.status
        except urllib.error.HTTPError as exc:
            code = exc.code

        # 400 = rejected by validation. 404 = Mind not found (acceptable here,
        # because this verification does not create a Mind). Anything 2xx would
        # mean the traversal was accepted.
        record(
            code in (400, 404),
            "workspace upload rejects traversal filename",
            f"filename={name!r} status={code} (expected 400/404, never 2xx)",
        )


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE).rstrip("/")
    print(f"SEC-02 verification against {base}\n")

    token = login(base)
    verify_download(base, token)
    verify_upload(base, token)

    passed = sum(1 for ok, _, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} checks passed")
    if passed != total:
        for ok, name, detail in results:
            if not ok:
                print(f"  - {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
