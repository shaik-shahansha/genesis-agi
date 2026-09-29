"""Hostinger Mail, Ringg voice, and the gateway that joins them.

The adapters are tested against a fake HTTP transport rather than a live provider,
because neither account exists yet — so what is verified here is the *logic*:
envelope handling, error translation, and the disclosure rule. What is **not**
verified is the real API contract, and that boundary is stated in each test that
depends on it.

The gateway tests are the important ones. They exercise the loop that makes
"reading and responding" real: an inbound event becomes a reply only by passing
the governance gate, and the failure modes (a responder that raises, an
authorizer that denies, floors that refuse) all have to leave the Mind unable to
send rather than accidentally able to.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Optional

import pytest

from genesis.channels import (
    ChannelGateway,
    ChannelLimits,
    ChannelRegistry,
    CommunicationIntent,
    ContactRef,
    DeliveryStatus,
    FakeChannel,
    InMemoryContacts,
    InboundEvent,
    OutboundPermission,
    build_registry,
    credentials_from_settings,
    parse_call_window,
)
from genesis.channels.hostinger_mail import (
    HostingerMailChannel,
    HostingerMailError,
)
from genesis.channels.ringg_voice import (
    DISCLOSURE_ARG,
    RinggVoiceChannel,
    RinggVoiceError,
)
from genesis.config.settings import Settings


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# A fake httpx transport
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status_code: int, body: Any, *, raw: bool = False):
        self.status_code = status_code
        if raw:
            self.content = b"not json"
            self._body = None
        else:
            self._body = body
            self.content = json.dumps(body).encode()

    def json(self):
        if self._body is None:
            raise ValueError("not json")
        return self._body


class FakeHTTP:
    """Stands in for `httpx.AsyncClient`.

    Records every request so a test can assert the exact path and body, which is
    the only way to check that a call went to the documented endpoint without a
    live account.
    """

    def __init__(self, responses: list[FakeResponse] | None = None):
        self.responses = list(responses or [])
        self.requests: list[dict[str, Any]] = []
        self.default = FakeResponse(200, {"data": {}})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def request(self, method, url, *, params=None, json=None, headers=None):
        self.requests.append(
            {"method": method, "url": url, "params": params, "json": json, "headers": headers or {}}
        )
        if self.responses:
            return self.responses.pop(0)
        return self.default


@pytest.fixture()
def http(monkeypatch):
    """Patch `httpx.AsyncClient` with a fake, and hand it to the test."""
    fake = FakeHTTP()
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: fake)
    return fake


def hostinger(**overrides) -> HostingerMailChannel:
    kwargs = dict(
        api_token="mail-token",
        mailbox_id="AC123",
        address="sage@example.com",
        display_name="Sage",
        administrator="Genesis AGI",
        mind_id="MIND-1",
    )
    kwargs.update(overrides)
    return HostingerMailChannel(**kwargs)


def ringg(**overrides) -> RinggVoiceChannel:
    kwargs = dict(
        api_key="ringg-key",
        agent_id="agent-1",
        from_number_id="num-1",
        phone_number="+15550000000",
        administrator="Genesis AGI",
        disclosure_confirmed=True,
        mind_id="MIND-1",
    )
    kwargs.update(overrides)
    return RinggVoiceChannel(**kwargs)


def approved_for(channel, handle="ada@example.test", body="Hello Ada.", **contact_overrides):
    from genesis.channels import ApprovedCommunication

    kwargs = dict(
        relationship_id="REL-1",
        display_name="Ada",
        handle=handle,
        outbound=OutboundPermission.INITIATE,
        consent_source="ada wrote first",
        quiet_hours=(0, 24),
    )
    kwargs.update(contact_overrides)
    contact = ContactRef(**kwargs)
    intent = CommunicationIntent(
        channel=channel.name,
        recipient=contact,
        body=body,
        subject="A question",
        trigger="reply",
    )
    prepared = run(channel.prepare(intent))
    return ApprovedCommunication(prepared=prepared, contact=contact, decision="allow")


# ---------------------------------------------------------------------------
# Hostinger Mail
# ---------------------------------------------------------------------------


def test_send_posts_to_the_documented_path(http):
    """The one endpoint Hostinger's SDK docs quote verbatim."""
    http.responses = [FakeResponse(200, {"data": {"messageId": "m-1"}})]

    receipt = run(hostinger().send(approved_for(hostinger())))

    assert receipt.status is DeliveryStatus.SENT
    assert receipt.provider_message_id == "m-1"
    call = http.requests[0]
    assert call["method"] == "POST"
    assert call["url"].endswith("/api/v1/mailboxes/AC123/send")
    assert call["json"]["to"] == ["ada@example.test"]
    assert call["json"]["subject"] == "A question"


def test_the_sent_body_carries_the_disclosure(http):
    """The whole point of enforcing it in the writer."""
    http.responses = [FakeResponse(200, {"data": {"messageId": "m-1"}})]

    run(hostinger().send(approved_for(hostinger())))

    sent_text = http.requests[0]["json"]["text"]
    assert "AI-operated digital being" in sent_text
    assert "Genesis AGI" in sent_text


def test_a_reply_attaches_the_original_message_id(http):
    """The provider threads it for us; we only supply the reference."""
    from genesis.channels import ApprovedCommunication

    channel = hostinger()
    contact = ContactRef(
        relationship_id="REL-1",
        display_name="Ada",
        handle="ada@example.test",
        outbound=OutboundPermission.REPLY_ONLY,
        consent_source="ada wrote first",
        quiet_hours=(0, 24),
    )
    intent = CommunicationIntent(
        channel="email",
        recipient=contact,
        body="Answering.",
        subject="Re: A question",
        thread_id="thread-1",
        reply_to_message_id="orig-99",
        trigger="reply",
        trigger_ref="orig-99",
    )
    prepared = run(channel.prepare(intent))
    http.responses = [FakeResponse(200, {"data": {"messageId": "m-2"}})]

    approved = ApprovedCommunication(
        prepared=prepared, contact=contact, decision="allow"
    )
    # `reply_to_message_id` rides on the intent; the adapter reads it off the
    # approval, so it must be present for threading to happen at all.
    object.__setattr__(approved, "reply_to_message_id", "orig-99")

    run(channel.send(approved))

    assert http.requests[0]["json"]["inReplyTo"] == "orig-99"


def test_envelope_is_unwrapped(http):
    """The API wraps every payload in `data`; callers must not see that."""
    http.responses = [
        FakeResponse(
            200,
            {
                "data": {
                    "messages": [
                        {
                            "messageId": "m1",
                            "from": {"address": "ada@example.test", "name": "Ada"},
                            "subject": "Hi",
                            "text": "Hello there",
                            "receivedAt": datetime.now(timezone.utc).isoformat(),
                        }
                    ]
                }
            },
        )
    ]

    events = run(hostinger().receive())

    assert len(events) == 1
    assert events[0].sender_handle == "ada@example.test"
    assert events[0].sender_name == "Ada"
    assert events[0].body == "Hello there"


def test_a_code_is_translated_into_something_actionable(http):
    """An operator needs to know a Mail token is not a hosting token."""
    http.responses = [FakeResponse(401, {"code": "ERR_UNAUTHORIZED", "error": "Unauthorized"})]

    with pytest.raises(HostingerMailError) as exc:
        run(hostinger().receive())

    assert "Agentic Mail" in str(exc.value)
    assert exc.value.code == "ERR_UNAUTHORIZED"


def test_forbidden_explains_the_permission_split(http):
    """Read and send are separate permissions on the token."""
    http.responses = [FakeResponse(403, {"code": "ERR_FORBIDDEN", "error": "Forbidden"})]

    with pytest.raises(HostingerMailError) as exc:
        run(hostinger().receive())

    assert "separate permissions" in str(exc.value)


def test_an_unknown_code_keeps_the_provider_text(http):
    """Paraphrasing a code we do not know would lose information."""
    http.responses = [FakeResponse(418, {"code": "ERR_WEIRD", "error": "I am a teapot"})]

    with pytest.raises(HostingerMailError) as exc:
        run(hostinger().receive())

    assert "I am a teapot" in str(exc.value)
    assert "ERR_WEIRD" in str(exc.value)


def test_non_json_response_is_reported_not_crashed(http):
    http.responses = [FakeResponse(502, None, raw=True)]

    with pytest.raises(HostingerMailError, match="non-JSON"):
        run(hostinger().receive())


def test_message_fields_are_read_defensively(http):
    """A rename must not look like an empty mailbox."""
    http.responses = [
        FakeResponse(
            200,
            {
                "data": {
                    "messages": [
                        # `sender`/`handle` instead of `from`/`address`, and a
                        # different id key — the shape we have not seen.
                        {"uid": "u-7", "sender": "bea@example.test", "snippet": "hi"},
                    ]
                }
            },
        )
    ]

    events = run(hostinger().receive())

    assert len(events) == 1
    assert events[0].sender_handle == "bea@example.test"
    assert events[0].provider_message_id == "u-7"


def test_a_message_with_no_sender_is_skipped(http):
    http.responses = [FakeResponse(200, {"data": {"messages": [{"messageId": "m1"}]}})]

    assert run(hostinger().receive()) == []


def test_pagination_stops_at_the_cap(http):
    """A mailbox with years of history must not be walked on the first read."""
    from genesis.channels.hostinger_mail import MAX_PAGES

    http.responses = [
        FakeResponse(
            200,
            {
                "data": {
                    "messages": [
                        {
                            "messageId": f"m-{page}",
                            "from": {"address": "ada@example.test"},
                            "receivedAt": datetime.now(timezone.utc).isoformat(),
                        }
                    ]
                },
                "pagination": {"totalPages": 99},
            },
        )
        for page in range(MAX_PAGES)
    ]

    events = run(hostinger().receive())

    assert len(http.requests) == MAX_PAGES
    assert len(events) == MAX_PAGES


def test_existing_messages_are_filtered_by_the_cutoff(http):
    """Three-day lookback by default, so an old mailbox does not flood memory."""
    old = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
    http.responses = [
        FakeResponse(
            200,
            {
                "data": {
                    "messages": [
                        {"messageId": "old", "from": {"address": "a@example.test"}, "receivedAt": old}
                    ]
                }
            },
        )
    ]

    assert run(hostinger().receive()) == []


def test_verify_reports_each_path_and_never_exercises_send(http):
    """Verifying `send` would send a real email to a real person."""
    http.responses = [
        FakeResponse(200, {"data": {}}),
        FakeResponse(200, {"data": {}}),
        FakeResponse(404, {"code": "ERR_MAILBOX_NOT_FOUND", "error": "nope"}),
    ]

    report = run(hostinger().verify())

    assert report["ok"] is False
    assert report["paths"]["account"]["ok"] is True
    assert report["paths"]["messages"]["ok"] is False
    assert report["paths"]["send"]["ok"] is None
    assert "would send a real message" in report["paths"]["send"]["note"]
    # Every call made was a GET; nothing was sent.
    assert all(call["method"] == "GET" for call in http.requests)


def test_a_token_without_a_mailbox_id_is_not_capable():
    channel = hostinger(mailbox_id="")
    assert channel.capabilities().can_send is False
    assert channel.capabilities().can_receive is False


# ---------------------------------------------------------------------------
# Ringg voice
# ---------------------------------------------------------------------------


def test_unasserted_disclosure_refuses_to_register():
    """The rule that stops an undisclosed voice channel existing.

    A phone call is the most human-seeming thing a Mind can do, and a person who
    believes they are talking to a person has been deceived regardless of intent.
    The adapter cannot verify Ringg's prompt, so the channel stays off until a
    human asserts it.
    """
    registry = ChannelRegistry("MIND-V")
    registration = registry.register(ringg(disclosure_confirmed=False))

    assert registration.enabled is False
    assert "disclosure" in registration.reason
    assert registry.has("voice") is False


def test_asserted_disclosure_registers():
    registry = ChannelRegistry("MIND-V")
    registration = registry.register(ringg(disclosure_confirmed=True))

    assert registration.enabled is True


def test_call_posts_to_the_documented_endpoint(http):
    http.responses = [FakeResponse(200, {"call_id": "call-1"})]

    receipt = run(ringg().send(approved_for(ringg())))

    assert receipt.status is DeliveryStatus.SENT
    assert receipt.provider_message_id == "call-1"
    call = http.requests[0]
    assert call["url"].endswith("/calling/outbound/individual")
    assert call["json"]["agent_id"] == "agent-1"
    assert call["json"]["from_number_id"] == "num-1"
    assert call["json"]["mobile_number"] == "ada@example.test"
    assert call["headers"]["X-API-KEY"] == "ringg-key"


def test_the_disclosure_is_passed_as_an_assistant_variable(http):
    """The only mitigation available: make disclosing the easy path.

    An assistant prompt written to speak `@{{ai_disclosure}}` discloses by
    construction. What we cannot do is prove the prompt does.
    """
    http.responses = [FakeResponse(200, {"call_id": "call-1"})]

    run(ringg().send(approved_for(ringg())))

    args = http.requests[0]["json"]["custom_args_values"]
    assert DISCLOSURE_ARG in args
    assert "AI-operated digital being" in args[DISCLOSURE_ARG]
    assert "Genesis AGI" in args[DISCLOSURE_ARG]


def test_the_prepared_body_is_not_sent_as_a_script(http):
    """An honest boundary, pinned so it cannot drift into a false claim.

    The Mind does not deliver its own sentences over the phone — Ringg's assistant
    does, from a prompt we cannot see. Sending the body as a script would make the
    receipt imply otherwise.
    """
    http.responses = [FakeResponse(200, {"call_id": "call-1"})]

    run(ringg().send(approved_for(ringg(), body="Say exactly these words please.")))

    payload = json.dumps(http.requests[0]["json"])
    assert "Say exactly these words please" not in payload


def test_401_explains_key_rotation(http):
    """Regenerating a Ringg key revokes the old one immediately."""
    http.responses = [FakeResponse(401, {"error": {"code": "unauthorized", "message": "bad key"}})]

    with pytest.raises(RinggVoiceError) as exc:
        run(ringg().send(approved_for(ringg())))

    assert "rotated" in str(exc.value)


def test_voice_cannot_receive():
    """Inbound calls arrive by webhook, which this adapter does not implement.

    A Mind that cannot answer the phone must not appear to.
    """
    assert ringg().capabilities().can_receive is False


def test_voice_is_metered():
    """Governance needs to know a budget check is required, even without a rate."""
    assert ringg().capabilities().metered is True


def test_verify_checks_the_four_things_that_stop_a_call(http):
    http.responses = [
        FakeResponse(200, {"credits": 100}),
        FakeResponse(200, {"data": [{"id": "agent-1"}]}),
        FakeResponse(200, {"data": [{"id": "num-1"}]}),
    ]

    report = run(ringg().verify())

    assert report["checks"]["workspace"]["ok"] is True
    assert report["checks"]["assistant"]["ok"] is True
    assert report["checks"]["number"]["ok"] is True
    assert report["ok"] is True


def test_verify_flags_a_missing_assistant(http):
    http.responses = [
        FakeResponse(200, {"credits": 1}),
        FakeResponse(200, {"data": [{"id": "someone-else"}]}),
        FakeResponse(200, {"data": [{"id": "num-1"}]}),
    ]

    report = run(ringg().verify())

    assert report["checks"]["assistant"]["ok"] is False
    assert report["ok"] is False


def test_verify_flags_an_unasserted_disclosure(http):
    http.responses = [
        FakeResponse(200, {"credits": 1}),
        FakeResponse(200, {"data": [{"id": "agent-1"}]}),
        FakeResponse(200, {"data": [{"id": "num-1"}]}),
    ]

    report = run(ringg(disclosure_confirmed=False).verify())

    assert report["checks"]["disclosure"]["ok"] is False
    assert "cannot be verified from the API" in report["checks"]["disclosure"]["error"]


# ---------------------------------------------------------------------------
# The gateway
# ---------------------------------------------------------------------------


def inbound(**overrides) -> InboundEvent:
    kwargs = dict(
        channel="fake",
        provider_message_id="m-1",
        sender_handle="ada@example.test",
        sender_name="Ada",
        subject="Question about Friday",
        body="Are we still on?",
        thread_id="thread-1",
        received_at=datetime.now(timezone.utc),
    )
    kwargs.update(overrides)
    return InboundEvent(**kwargs)


def gateway_for(http_channel, *, responder, authorizer=None, contacts=None, recorder=None):
    registry = ChannelRegistry("MIND-G")
    registry.register(http_channel)

    async def allow(_intent, _contact):
        return ("allow", None)

    return ChannelGateway(
        registry=registry,
        contacts=contacts or InMemoryContacts(),
        responder=responder,
        authorizer=authorizer or allow,
        recorder=recorder,
        mind_id="MIND-G",
    )


def test_an_inbound_message_becomes_an_approved_reply():
    """The loop: read → decide → gate → send."""
    channel = FakeChannel(
        address="sage@example.test",
        display_name="Sage",
        administrator="Genesis AGI",
        mind_id="MIND-G",
    )

    async def responder(event, contact):
        return f"Answering {contact.display_name}."

    gateway = gateway_for(channel, responder=responder)
    outcome = run(gateway.handle(inbound()))

    assert outcome.engaged is True
    assert outcome.delivered is True
    assert outcome.decision == "allow"
    # One message reached the provider, and it disclosed.
    assert len(channel.sent) == 1
    assert "AI-operated digital being" in channel.sent[0].prepared.body


def test_a_stranger_can_be_replied_to_but_not_initiated_to():
    """They wrote first. Answering is not outreach — that is the consent model."""
    channel = FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-G"
    )
    contacts = InMemoryContacts()
    resolved = contacts.resolve(channel="fake", handle="stranger@example.test")

    assert resolved.outbound is OutboundPermission.REPLY_ONLY
    assert resolved.consent_source == ""

    async def responder(event, contact):
        return "Hello, thanks for writing."

    gateway = gateway_for(channel, responder=responder, contacts=contacts)
    outcome = run(gateway.handle(inbound(sender_handle="stranger@example.test")))

    assert outcome.delivered is True


def test_a_governance_denial_means_nothing_is_sent():
    channel = FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-G"
    )
    recorded: list[dict] = []

    async def responder(event, contact):
        return "I would like to reply."

    async def deny(_intent, _contact):
        return ("require_approval", "APR-1")

    gateway = gateway_for(
        channel, responder=responder, authorizer=deny, recorder=recorded.append
    )
    outcome = run(gateway.handle(inbound()))

    assert outcome.engaged is True
    assert outcome.delivered is False
    assert outcome.approval_id == "APR-1"
    assert "require_approval" in outcome.reason
    assert channel.sent == []
    # The refusal itself is recorded, which is what makes it auditable.
    assert any(entry["event"] == "channel.reply_not_sent" for entry in recorded)


def test_a_responder_that_declines_engages_nothing():
    channel = FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-G"
    )

    async def silent(event, contact):
        return None

    outcome = run(gateway_for(channel, responder=silent).handle(inbound()))

    assert outcome.engaged is False
    assert outcome.reason == "chose not to reply"
    assert channel.sent == []


def test_a_responder_that_raises_does_not_break_the_loop():
    """A cognition failure is not a send failure, and must not become one."""
    channel = FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-G"
    )

    async def explode(event, contact):
        raise RuntimeError("model provider down")

    outcome = run(gateway_for(channel, responder=explode).handle(inbound()))

    assert outcome.engaged is False
    assert "responder failed" in outcome.reason
    assert channel.sent == []


def test_a_floor_refusal_does_not_produce_an_approval_card():
    """Asking a human to approve a message the adapter will refuse is noise.

    Noise trains approvers to click through, which is how an approval queue stops
    being a control.
    """
    channel = FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-G"
    )
    authorizer_calls: list[str] = []

    async def responder(event, contact):
        return "A reply."

    async def track(intent, contact):
        authorizer_calls.append("called")
        return ("allow", None)

    # An opt-out makes the floors refuse a reply.
    channel.optouts.opt_out(handle="ada@example.test")
    gateway = gateway_for(channel, responder=responder, authorizer=track)
    outcome = run(gateway.handle(inbound()))

    assert outcome.engaged is False
    assert "asked not to be contacted" in outcome.reason
    assert authorizer_calls == []
    assert channel.sent == []


def test_recorder_failure_does_not_stop_the_reply():
    """An audit-store outage must not become a Mind that stops answering.

    Same principle as the domain journal: recording is best effort, and a failure
    to record must not prevent the thing being recorded.
    """
    channel = FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-G"
    )

    def bad_recorder(_payload):
        raise RuntimeError("journal unavailable")

    async def responder(event, contact):
        return "Replying anyway."

    gateway = gateway_for(channel, responder=responder, recorder=bad_recorder)
    outcome = run(gateway.handle(inbound()))

    assert outcome.delivered is True


def test_an_inbound_for_a_channel_with_no_sender_is_not_engaged():
    channel = FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-G"
    )

    class NoResolver:
        def resolve(self, **_kwargs):
            return None

    async def responder(event, contact):  # pragma: no cover - must not be reached
        raise AssertionError("responder should not run without a contact")

    gateway = ChannelGateway(
        registry=(lambda r: (r.register(channel), r)[1])(ChannelRegistry("MIND-G")),
        contacts=NoResolver(),
        responder=responder,
        authorizer=lambda i, c: None,
    )
    outcome = run(gateway.handle(inbound()))

    assert outcome.engaged is False
    assert "could not be resolved" in outcome.reason


def test_reply_subject_does_not_stack_prefixes():
    """`Re: Re: Re:` is what happens when nobody checks."""
    from genesis.channels.gateway import _reply_subject

    assert _reply_subject("Question") == "Re: Question"
    assert _reply_subject("Re: Question") == "Re: Question"
    assert _reply_subject("RE: Question") == "RE: Question"
    assert _reply_subject(None) == "Re: (no subject)"


def test_drain_processes_every_channel_and_reports_each():
    channel = FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-G"
    )
    for index in range(3):
        channel.inject(inbound(provider_message_id=f"m-{index}"))

    async def responder(event, contact):
        return f"Reply {event.provider_message_id}"

    gateway = gateway_for(channel, responder=responder)
    outcomes = run(gateway.drain())

    assert len(outcomes) == 3
    assert all(o.delivered for o in outcomes)


# ---------------------------------------------------------------------------
# The operator's calling window, and the fact that it is a setting we read
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("09:00-18:00", (9, 18)),
        ("9-17", (9, 17)),
        ("09:30 - 17:45", (9, 17)),
        ("9am to 6pm", (9, 18)),
        ("9am-6pm", (9, 18)),
        ("12pm-12am", (12, 0)),
        ("12am-12pm", (0, 12)),
    ],
)
def test_a_window_is_parsed(text, expected):
    assert parse_call_window(text) == expected


@pytest.mark.parametrize(
    "text", [None, "", "   ", "office hours", "9 to", "evening", "25:00-26:00"]
)
def test_an_unparseable_window_is_refused_rather_than_guessed(text):
    """Returning a fabricated window would be worse than returning nothing.

    A made-up window would look like a configured control while enforcing hours
    nobody chose, so the caller has to fall back explicitly.
    """
    assert parse_call_window(text) is None


def test_a_configured_window_becomes_the_adapters_own_floor():
    """The setting has to change a decision, or it is decoration.

    Aligning our floor with the operator's is the point: if ours is wider, the
    Mind believes a call is allowed and the provider refuses it as a delivery
    error rather than a policy refusal.
    """
    settings = Settings(_env_file=None)
    object.__setattr__(settings, "mind_ringg_api_key", "key")
    object.__setattr__(settings, "mind_ringg_agent_id", "agent")
    object.__setattr__(settings, "mind_ringg_from_number_id", "num")
    object.__setattr__(settings, "mind_ringg_disclosure_confirmed", True)
    object.__setattr__(settings, "mind_ringg_call_window", "09:00-18:00")

    credentials = credentials_from_settings(settings)
    registry = build_registry("MIND-G", credentials)
    registration = registry.get("voice")
    if registration is None:  # pragma: no cover
        pytest.fail("no voice channel was registered despite full credentials")

    assert registration.adapter.limits.default_quiet_hours == (9, 18)


def test_without_a_window_the_documented_default_stays_in_force():
    settings = Settings(_env_file=None)
    object.__setattr__(settings, "mind_ringg_api_key", "key")
    object.__setattr__(settings, "mind_ringg_agent_id", "agent")
    object.__setattr__(settings, "mind_ringg_from_number_id", "num")
    object.__setattr__(settings, "mind_ringg_disclosure_confirmed", True)
    object.__setattr__(settings, "mind_ringg_call_window", "")

    credentials = credentials_from_settings(settings)
    registry = build_registry("MIND-G", credentials)
    registration = registry.get("voice")
    if registration is None:  # pragma: no cover
        pytest.fail("no voice channel was registered despite full credentials")

    assert registration.adapter.limits.default_quiet_hours == ChannelLimits().default_quiet_hours


def test_a_typo_in_the_window_does_not_silently_remove_the_floor(caplog):
    """An unparseable window must keep the default AND say so.

    Dropping the control quietly would look identical to a config change, which
    is the failure mode this whole test file exists to prevent.
    """
    settings = Settings(_env_file=None)
    object.__setattr__(settings, "mind_ringg_api_key", "key")
    object.__setattr__(settings, "mind_ringg_agent_id", "agent")
    object.__setattr__(settings, "mind_ringg_from_number_id", "num")
    object.__setattr__(settings, "mind_ringg_disclosure_confirmed", True)
    object.__setattr__(settings, "mind_ringg_call_window", "business hours")

    with caplog.at_level("WARNING"):
        credentials = credentials_from_settings(settings)

    assert any("MIND_RINGG_CALL_WINDOW" in record.message for record in caplog.records)
    registry = build_registry("MIND-G", credentials)
    registration = registry.get("voice")
    if registration is None:  # pragma: no cover
        pytest.fail("no voice channel was registered despite full credentials")

    assert registration.adapter.limits.default_quiet_hours == ChannelLimits().default_quiet_hours
