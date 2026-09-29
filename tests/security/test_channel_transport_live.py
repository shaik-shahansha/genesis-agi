"""The Hostinger adapter over **real HTTP**, against a local server.

This file exists because of a specific gap, and it is worth being precise about what
it does and does not close.

## The gap

Every other adapter test in this suite runs against a fake transport: a class that
patches `httpx.AsyncClient` and returns dicts I wrote. That verifies the adapter's
*logic* and nothing about its *plumbing*. A fake I wrote to match my own code cannot
tell me that:

* the request method, URL or headers are wrong
* `httpx` is used in a way that only fails against a real socket
* the JSON actually parses — `response.json()` on a real body, not a dict I handed it
* a non-ASCII body survives encoding
* an error status arrives as an exception rather than a parsed payload
* a redirect, a missing `Content-Type`, or a chunked response breaks the parse

Those are the failures that show up on first contact with a real API, and a fake
transport is structurally incapable of producing them.

## What this closes, and what it does not

**Closed:** the transport. A real `http.server` on a real port, real `httpx`, real
bytes on a real socket. Every request the adapter makes is asserted against what the
server actually received, including headers.

**Not closed:** the *contract*. The local server implements the paths and envelope I
inferred from Hostinger's documentation, so it agrees with me by construction. If the
real API puts messages somewhere else, this file will pass and the adapter will still
fail. That gap can only be closed by credentials, and it is stated here rather than
left for someone to assume otherwise.

So this is a genuine step and not a substitute for the real thing. It is what can be
verified without an account.
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import pytest

from genesis.channels import (
    ApprovedCommunication,
    CommunicationIntent,
    ContactRef,
    OutboundPermission,
)
from genesis.channels.hostinger_mail import HostingerMailChannel


# ---------------------------------------------------------------------------
# A real HTTP server
# ---------------------------------------------------------------------------


class _Recorder:
    """What the server actually received."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def last(self) -> dict[str, Any]:
        assert self.requests, "the adapter made no request"
        return self.requests[-1]


def _make_handler(recorder: _Recorder, routes: dict[str, Any]):
    class Handler(BaseHTTPRequestHandler):
        # Silenced: the default writes every request to stderr, which would bury
        # the test output.
        def log_message(self, *args):  # noqa: D102
            return

        def _respond(self, status: int, payload: Any, *, raw: Optional[bytes] = None):
            body = raw if raw is not None else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _handle(self, method: str):
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(length) if length else b""

            recorder.requests.append(
                {
                    "method": method,
                    "path": parsed.path,
                    "query": parse_qs(parsed.query),
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body": json.loads(raw_body.decode("utf-8")) if raw_body else None,
                }
            )

            route = routes.get(parsed.path)
            if route is None:
                self._respond(404, {"code": "ERR_NOT_FOUND", "error": "no such path"})
                return
            if callable(route):
                status, payload = route(parsed, method)
                self._respond(status, payload)
                return
            self._respond(200, route)

        def do_GET(self):  # noqa: N802
            self._handle("GET")

        def do_POST(self):  # noqa: N802
            self._handle("POST")

    return Handler


class LocalProvider:
    """A real HTTP server on a real port, for the duration of a test."""

    def __init__(self, routes: dict[str, Any]):
        self.recorder = _Recorder()
        self._server = ThreadingHTTPServer(
            ("127.0.0.1", 0), _make_handler(self.recorder, routes)
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "LocalProvider":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


# ---------------------------------------------------------------------------
# The documented shapes
# ---------------------------------------------------------------------------

MAILBOX = "AC1a2b3c4d5e6f7g"
VERSION = "v1"
BASE = f"/api/{VERSION}/mailboxes/{MAILBOX}"
MESSAGES = f"{BASE}/folders/INBOX/messages"
SEND = f"{BASE}/send"


def envelope(data: Any) -> dict[str, Any]:
    """The `{data, pagination}` wrapper the API is documented to use."""
    return {"data": data, "pagination": {"page": 1, "perPage": 25, "total": 1}}


def a_message(uid: str = "42") -> dict[str, Any]:
    """A message with several plausible field spellings.

    The adapter reads field names defensively because the message shape is not
    documented. Sending all the spellings at once proves the defensive reads do not
    break when a real payload is richer than expected — which it will be.
    """
    return {
        "uid": uid,
        "messageId": uid,
        "id": uid,
        "from": {"address": "dana@example.test", "name": "Dana"},
        "fromAddress": "dana@example.test",
        "fromName": "Dana",
        "subject": "Question about Friday",
        "body": "Are we still on for Friday?",
        "text": "Are we still on for Friday?",
        "preview": "Are we still on for Friday?",
        "receivedAt": "2026-09-29T08:00:00Z",
        "date": "2026-09-29T08:00:00Z",
        "threadId": "thread-1",
        "references": "<orig@example.test>",
    }


def make_channel(base_url: str, **kwargs) -> HostingerMailChannel:
    return HostingerMailChannel(
        api_token="test-token",
        mailbox_id=MAILBOX,
        address="sage@example.test",
        display_name="Sage",
        administrator="Genesis AGI",
        base_url=base_url,
        mind_id="MIND-H",
        **kwargs,
    )


def a_contact() -> ContactRef:
    return ContactRef(
        relationship_id="email:dana@example.test",
        display_name="Dana",
        handle="dana@example.test",
        outbound=OutboundPermission.INITIATE,
        consent_source="asked us to follow up",
    )


def an_intent(body: str = "Yes, still on.") -> CommunicationIntent:
    return CommunicationIntent(
        channel="email",
        recipient=a_contact(),
        body=body,
        subject="Re: Question about Friday",
    )


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# The transport actually works
# ---------------------------------------------------------------------------


def test_a_read_over_real_http_returns_events():
    """The whole point: real bytes, real parse, real socket."""
    routes = {MESSAGES: envelope([a_message()])}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        events = run(channel.receive())

    assert len(events) == 1
    assert events[0].sender_handle == "dana@example.test"
    assert "still on for Friday" in events[0].body


def test_the_request_carries_the_bearer_token():
    """A header the fake transport could not check, because it never saw one."""
    routes = {MESSAGES: envelope([a_message()])}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        run(channel.receive())
        headers = server.recorder.last()["headers"]

    assert headers.get("authorization") == "Bearer test-token"


def test_the_request_goes_to_the_mailbox_scoped_path():
    """The documented convention is that the mailbox resource id comes first. If the
    adapter dropped it, every read would hit the wrong scope."""
    routes = {MESSAGES: envelope([a_message()])}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        run(channel.receive())
        path = server.recorder.last()["path"]

    assert path == MESSAGES
    assert MAILBOX in path


def test_the_version_is_honoured_in_the_path():
    routes = {f"/api/v2/mailboxes/{MAILBOX}/folders/INBOX/messages": envelope([])}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url, api_version="v2")
        run(channel.receive())
        path = server.recorder.last()["path"]

    assert path.startswith("/api/v2/")


def test_a_non_ascii_body_survives_the_round_trip():
    """Real encoding, which a fake transport skips entirely. A Mind writing to a
    person in another language is the normal case, not an edge case."""
    message = a_message()
    message["body"] = "Está bien — nos vemos el viernes. ¿Confirmas? 🎉"
    message["text"] = message["body"]
    message["preview"] = message["body"]

    routes = {MESSAGES: envelope([message])}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        events = run(channel.receive())

    assert "Está bien" in events[0].body
    assert "🎉" in events[0].body


def test_a_non_ascii_outbound_body_survives():
    routes = {SEND: {"data": {"messageId": "sent-1"}}}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        prepared = run(channel.prepare(an_intent("Sí, claro — hasta el viernes.")))
        approved = ApprovedCommunication(
            prepared=prepared, contact=a_contact(), decision="allow"
        )
        receipt = run(channel.send(approved))
        sent = server.recorder.last()["body"]

    assert receipt.ok
    assert "Sí, claro" in json.dumps(sent, ensure_ascii=False)


def test_an_empty_inbox_is_not_an_error():
    """Zero messages and a broken mailbox are different facts, and this is the
    transport half of that distinction."""
    routes = {MESSAGES: envelope([])}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        events = run(channel.receive())

    assert events == []


def test_a_404_arrives_as_a_typed_error_not_a_parse_failure():
    """Over a real socket an error status is a different code path from a fake that
    returns a dict. If this raised `JSONDecodeError` the operator would see a parse
    bug instead of "no such path"."""
    from genesis.channels.hostinger_mail import HostingerMailError

    with LocalProvider({}) as server:
        channel = make_channel(server.base_url)
        with pytest.raises(HostingerMailError) as caught:
            run(channel.receive())

    assert "ERR_NOT_FOUND" in str(caught.value) or "404" in str(caught.value)


def test_a_401_is_translated_for_the_operator():
    """The token is scoped to one order, so "unauthorized" usually means the wrong
    token rather than a broken one — which is the difference between a five-second
    fix and an hour.

    The assertion is on the *translation*, not on the raw code: `_ACTIONABLE_CODES`
    replaces the provider's wording deliberately, and a test that looked for
    `ERR_UNAUTHORIZED` would fail while the behaviour was correct.
    """
    from genesis.channels.hostinger_mail import HostingerMailError

    routes = {
        MESSAGES: lambda parsed, method: (
            401,
            {"code": "ERR_UNAUTHORIZED", "error": "invalid token"},
        )
    }
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        with pytest.raises(HostingerMailError) as caught:
            run(channel.receive())

    message = str(caught.value)
    assert "token" in message.lower()
    assert caught.value.code == "ERR_UNAUTHORIZED"
    assert caught.value.status == 401


def test_a_403_explains_that_read_and_send_are_separate_permissions():
    """A Mail token is not a hosting token, and read and send are chosen separately
    when it is created. That is the most likely cause of a 403 and the least likely
    to be guessed from "Forbidden"."""
    from genesis.channels.hostinger_mail import HostingerMailError

    routes = {
        MESSAGES: lambda parsed, method: (
            403,
            {"code": "ERR_FORBIDDEN", "error": "not your mailbox"},
        )
    }
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        with pytest.raises(HostingerMailError) as caught:
            run(channel.receive())

    message = str(caught.value).lower()
    assert "permission" in message
    assert "separate" in message


def test_a_rate_limit_tells_the_operator_to_back_off():
    from genesis.channels.hostinger_mail import HostingerMailError

    routes = {
        MESSAGES: lambda parsed, method: (
            429,
            {"code": "ERR_RATE_LIMITED", "error": "slow down"},
        )
    }
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        with pytest.raises(HostingerMailError) as caught:
            run(channel.receive())

    assert "rate limit" in str(caught.value).lower()
    assert caught.value.status == 429


def test_a_server_error_does_not_read_as_an_empty_inbox():
    """The failure this guards: a 500 reported as "no new mail" would make a broken
    mailbox indistinguishable from a quiet one."""
    from genesis.channels.hostinger_mail import HostingerMailError

    routes = {MESSAGES: lambda parsed, method: (500, {"error": "boom"})}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        with pytest.raises(HostingerMailError):
            run(channel.receive())


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------


def test_a_send_posts_the_documented_shape():
    routes = {SEND: {"data": {"messageId": "sent-1"}}}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        prepared = run(channel.prepare(an_intent()))
        approved = ApprovedCommunication(
            prepared=prepared, contact=a_contact(), decision="allow"
        )
        receipt = run(channel.send(approved))
        request = server.recorder.last()

    assert request["method"] == "POST"
    assert request["path"] == SEND
    assert request["body"]["subject"] == "Re: Question about Friday"
    assert "dana@example.test" in json.dumps(request["body"])
    assert receipt.status.value == "sent"


def test_the_sent_body_carries_the_disclosure_over_the_wire():
    """The structural guarantee, checked against the bytes that actually left the
    process rather than against an object."""
    routes = {SEND: {"data": {"messageId": "sent-1"}}}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        prepared = run(channel.prepare(an_intent()))
        approved = ApprovedCommunication(
            prepared=prepared, contact=a_contact(), decision="allow"
        )
        run(channel.send(approved))
        sent = server.recorder.last()["body"]

    assert "AI-operated digital being" in json.dumps(sent, ensure_ascii=False)
    assert "Genesis AGI" in json.dumps(sent, ensure_ascii=False)


def test_a_reply_attaches_the_original_message_id():
    """Threading is what makes a reply a reply, and it is the thing that silently
    stops working when a header is assembled by hand."""
    routes = {SEND: {"data": {"messageId": "sent-1"}}}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        intent = CommunicationIntent(
            channel="email",
            recipient=a_contact(),
            body="Yes, still on.",
            subject="Re: Question about Friday",
            thread_id="thread-1",
            in_reply_to="orig@example.test",
            reply_to_message_id="orig@example.test",
        )
        prepared = run(channel.prepare(intent))
        approved = ApprovedCommunication(
            prepared=prepared, contact=a_contact(), decision="allow"
        )
        run(channel.send(approved))
        sent = server.recorder.last()["body"]

    assert "orig@example.test" in json.dumps(sent)


def test_a_send_failure_raises_a_typed_error():
    """A provider refusal raises `HostingerMailError` rather than returning a failed
    receipt.

    That is the established pattern — `FakeChannel.fail_next_with` raises too — and a
    raise is the safer of the two: a failed receipt is a value a caller can forget to
    check, whereas an exception cannot be ignored. The failure is caught one level up
    by `ChannelPoller`, which records the message as failed and keeps the claim.
    """
    from genesis.channels.hostinger_mail import HostingerMailError

    routes = {
        SEND: lambda parsed, method: (422, {"code": "ERR_INVALID", "error": "bad body"})
    }
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        prepared = run(channel.prepare(an_intent()))
        approved = ApprovedCommunication(
            prepared=prepared, contact=a_contact(), decision="allow"
        )
        with pytest.raises(HostingerMailError) as caught:
            run(channel.send(approved))

    assert "ERR_INVALID" in str(caught.value)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


def test_a_second_page_is_fetched_and_merged():
    """Two pages over real HTTP, with the query parameters a real server reads.

    The route is keyed on the *path*, so the page has to be read from the query
    string — which is also what proves the adapter sends one.
    """

    def messages_route(parsed, method):
        page = int(parse_qs(parsed.query).get("page", ["1"])[0])
        return (
            200,
            {
                "data": [a_message(str(page))],
                "pagination": {"page": page, "perPage": 1, "totalPages": 2},
            },
        )

    routes = {MESSAGES: messages_route}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        events = run(channel.receive())
        # `recorder` stores the query already parsed, so calling `parse_qs` on it
        # again raises rather than returning nothing.
        pages_requested = [
            r["query"].get("page", ["1"])[0] for r in server.recorder.requests
        ]

    assert len(events) == 2
    assert "1" in pages_requested and "2" in pages_requested


def test_pagination_does_not_loop_forever():
    """A server that always claims another page must not spin. The adapter caps pages,
    and a hang here would be a daemon that stops answering everything."""

    def always_more(parsed, method):
        return (
            200,
            {
                "data": [a_message()],
                "pagination": {"page": 99, "perPage": 1, "totalPages": 10_000},
            },
        )

    routes = {MESSAGES: always_more}
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        events = run(channel.receive())
        request_count = len(server.recorder.requests)

    assert request_count <= 10, f"the adapter made {request_count} requests"
    assert len(events) <= 10


# ---------------------------------------------------------------------------
# verify() against a real server
# ---------------------------------------------------------------------------


def test_verify_reports_each_read_path_over_real_http():
    """`verify()` is what an operator runs before the first real send, so it has to
    work against a real socket rather than only in a unit test."""
    routes = {
        f"/api/{VERSION}/account": envelope({"id": MAILBOX, "address": "sage@example.test"}),
        f"{BASE}/folders": envelope([{"name": "INBOX"}]),
        MESSAGES: envelope([a_message()]),
    }
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        report = run(channel.verify())

    assert report["ok"] is True
    # `paths` is a **dict** keyed by path name, not a list of records. Iterating it
    # expecting records yields strings and raises `TypeError`.
    assert isinstance(report["paths"], dict)
    assert set(report["paths"]) == {"account", "folders", "messages", "send"}


def test_verify_reports_a_path_that_does_not_work():
    """The honest half: a path that 404s must be reported as failing, with the
    provider's own error code, rather than swallowed."""
    routes = {
        f"/api/{VERSION}/account": envelope({"id": MAILBOX}),
        f"{BASE}/folders": envelope([]),
        # MESSAGES deliberately absent -> 404
    }
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        report = run(channel.verify())

    assert report["ok"] is False
    assert report["paths"]["messages"]["ok"] is False
    assert report["paths"]["messages"]["status"] == 404


def test_verify_never_sends_a_message():
    """`verify()` checks read paths only, because verifying `send` would send a real
    message to a real person."""
    routes = {
        f"/api/{VERSION}/account": envelope({"id": MAILBOX}),
        f"{BASE}/folders": envelope([]),
        MESSAGES: envelope([]),
        SEND: {"data": {"messageId": "should-not-happen"}},
    }
    with LocalProvider(routes) as server:
        channel = make_channel(server.base_url)
        report = run(channel.verify())
        methods = {(r["method"], r["path"]) for r in server.recorder.requests}

    assert not any(method == "POST" and path == SEND for method, path in methods)
    # And it says so, rather than reporting a silent pass.
    assert report["paths"]["send"]["ok"] is None
    assert "not exercised" in report["paths"]["send"]["note"]


# ---------------------------------------------------------------------------
# What this file does not prove
# ---------------------------------------------------------------------------


def test_the_local_server_agrees_with_the_adapter_by_construction():
    """A test that documents its own limit.

    The routes here are the paths the adapter asks for. If Hostinger's real API puts
    messages somewhere else, every test in this file still passes and the adapter
    still fails — because the server and the adapter share one assumption.

    This is not a defect in the file; it is the boundary of what can be verified
    without an account. It is asserted so the boundary is visible to whoever reads
    the suite and wonders whether "real HTTP" means "verified against the provider".
    """
    channel = make_channel("http://127.0.0.1:1")
    documented = channel.default_paths()

    # The server in this file implements exactly these, and nothing else.
    assert documented["messages"].format(
        version=VERSION, mailbox=MAILBOX, folder="INBOX"
    ) == MESSAGES
    assert documented["send"].format(version=VERSION, mailbox=MAILBOX) == SEND
