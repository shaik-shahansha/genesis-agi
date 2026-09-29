"""Drafting a reply, and assembling the loop from a Mind.

Two things are checked here that are easy to get wrong in a way nothing notices:

**What the model is not told.** The prompt must contain no risk level, no approval
state, and no mention that a governance gate exists. A prompt that mentioned them
would invite the model to reason about its own constraints, and a model reasoning
about its constraints is a model trying to satisfy them conversationally — which is
the failure where a Mind explains why it *should* be permitted to do something. The
test asserts the absence, because an absence is exactly what a reviewer cannot see.

**That declining is reachable.** A responder that could only return text would make a
Mind that answers everything, including things it should leave alone.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from genesis.channels import (
    ChannelRegistry,
    ContactRef,
    FakeChannel,
    InboundEvent,
    OutboundPermission,
)
from genesis.channels.poller import build_poller
from genesis.channels.responder import DECLINE_SENTINEL, MindResponder
from genesis.config.settings import Settings
from genesis.database import base as db_base


def run(coro):
    return asyncio.run(coro)


class StubMind:
    """The smallest thing that is a Mind as far as the responder is concerned.

    `channels` is a property here for the same reason it is one on the real `Mind`:
    `build_poller` reads `mind.channels`, so a stub that only set `_channels` would
    fail on an attribute that the real class does expose — and the test would be
    exercising a stub's shape rather than the code's contract.
    """

    def __init__(self, *, reply: str = "Yes, still on.", raises: bool = False):
        self.reply = reply
        self.raises = raises
        self.calls: list[dict] = []
        self._channels = None

        class _Identity:
            gmid = f"MIND-R-{uuid.uuid4().hex[:8]}"

        self.identity = _Identity()

    @property
    def channels(self):
        return self._channels

    async def think(self, prompt, context=None, **kwargs):
        self.calls.append({"prompt": prompt, "context": context, **kwargs})
        if self.raises:
            raise RuntimeError("model unavailable")
        return self.reply


def make_channel() -> FakeChannel:
    return FakeChannel(
        address="sage@example.test", administrator="Genesis AGI", mind_id="MIND-R"
    )


def event(**overrides) -> InboundEvent:
    kwargs = dict(
        channel="fake",
        provider_message_id=f"m-{uuid.uuid4().hex[:8]}",
        sender_handle="ada@example.test",
        sender_name="Ada",
        subject="Question about Friday",
        body="Are we still on for Friday?",
    )
    kwargs.update(overrides)
    return InboundEvent(**kwargs)


def contact(**overrides) -> ContactRef:
    kwargs = dict(
        relationship_id="email:ada@example.test",
        display_name="Ada",
        handle="ada@example.test",
        outbound=OutboundPermission.REPLY_ONLY,
    )
    kwargs.update(overrides)
    return ContactRef(**kwargs)


# ---------------------------------------------------------------------------
# What the model is told, and what it is not
# ---------------------------------------------------------------------------


def test_the_prompt_does_not_mention_policy_approval_or_the_gate():
    """The assertion is about absence, which is why it needs a test.

    Every one of these words would be a hint that the model's answer is being judged
    against rules, and the only thing a model can do with that hint is argue.
    """
    prompt = MindResponder(mind=StubMind()).build_prompt(event(), contact()).lower()

    for forbidden in (
        "approval",
        "approve",
        "risk",
        "policy",
        "governance",
        "permission",
        "gate",
        "r2",
        "r3",
        "authoris",
        "authoriz",
    ):
        assert forbidden not in prompt, f"the prompt mentions {forbidden!r}"


def test_the_prompt_states_the_boundaries_as_prohibitions():
    """A model cannot respect a boundary it was never told about, and the failure
    would look like disregard rather than ignorance."""
    prompt = MindResponder(mind=StubMind()).build_prompt(
        event(),
        contact(boundaries=["do not discuss their medical history", "no pricing"]),
    )

    assert "do not discuss their medical history" in prompt
    assert "no pricing" in prompt
    assert "must not raise or share" in prompt.lower()


def test_the_prompt_omits_the_boundaries_section_when_there_are_none():
    """An empty prohibitions list is worse than none: it implies a rule was stated."""
    prompt = MindResponder(mind=StubMind()).build_prompt(event(), contact())

    assert "must not raise or share" not in prompt.lower()


def test_the_prompt_includes_the_message_and_the_sender():
    prompt = MindResponder(mind=StubMind()).build_prompt(event(), contact())

    assert "Are we still on for Friday?" in prompt
    assert "Ada" in prompt


def test_the_prompt_marks_a_first_contact_as_a_stranger():
    """Cognition should know this is someone new, without being told what that means
    for permission."""
    prompt = MindResponder(mind=StubMind()).build_prompt(
        event(), contact(relationship_id="unknown:email:new@example.test")
    )

    assert "not spoken to before" in prompt


def test_the_prompt_does_not_mark_a_known_contact_as_a_stranger():
    prompt = MindResponder(mind=StubMind()).build_prompt(event(), contact())

    assert "not spoken to before" not in prompt


def test_the_prompt_asks_for_the_body_only():
    """The signature is added by the adapter, so a model adding one would produce a
    message with two."""
    prompt = MindResponder(mind=StubMind()).build_prompt(event(), contact()).lower()

    assert "only the body" in prompt
    assert "do not add a signature" in prompt


def test_the_prompt_makes_declining_a_normal_answer():
    prompt = MindResponder(mind=StubMind()).build_prompt(event(), contact())

    assert DECLINE_SENTINEL in prompt
    assert "normal and expected" in prompt


def test_a_body_with_no_text_is_still_described():
    """An empty body must not produce a prompt with nothing after "Their message:"."""
    prompt = MindResponder(mind=StubMind()).build_prompt(event(body=""), contact())

    assert "(empty)" in prompt


# ---------------------------------------------------------------------------
# Turning model output into a decision
# ---------------------------------------------------------------------------


def test_the_sentinel_means_do_not_reply():
    responder = MindResponder(mind=StubMind())

    assert responder.clean(DECLINE_SENTINEL) is None


def test_a_sentinel_with_prose_attached_still_means_do_not_reply():
    """A model that pads the sentinel with an explanation has still declined.

    Matching exactly would read that as a reply and send the explanation to the
    person, which is the opposite of what was asked for.
    """
    responder = MindResponder(mind=StubMind())

    assert responder.clean(f"{DECLINE_SENTINEL}\n\nThis needs a human.") is None


def test_empty_and_whitespace_output_is_not_a_reply():
    responder = MindResponder(mind=StubMind())

    assert responder.clean("") is None
    assert responder.clean("   \n  ") is None
    assert responder.clean(None) is None


def test_a_long_reply_is_truncated():
    responder = MindResponder(mind=StubMind(), max_reply_chars=50)

    result = responder.clean("x" * 200)

    assert result is not None
    assert len(result) == 50


def test_a_normal_reply_is_passed_through_unchanged():
    responder = MindResponder(mind=StubMind())

    assert responder.clean("  Yes, still on.  ") == "Yes, still on."


# ---------------------------------------------------------------------------
# The call into cognition
# ---------------------------------------------------------------------------


def test_actions_are_disabled_during_a_reply_draft():
    """Enabling actions here would be a second route to acting that bypasses the
    channel gate: the model could send a message while drafting the message."""
    mind = StubMind()
    run(MindResponder(mind=mind)(event(), contact()))

    assert mind.calls[0]["enable_actions"] is False


def test_task_detection_is_skipped_so_a_reply_does_not_become_a_task():
    mind = StubMind()
    run(MindResponder(mind=mind)(event(), contact()))

    assert mind.calls[0]["skip_task_detection"] is True


def test_a_model_failure_means_no_reply_rather_than_an_exception():
    """Returning None lets the gateway record "chose not to reply" and leaves the
    message claimed, so a failing model does not become a retry loop."""
    responder = MindResponder(mind=StubMind(raises=True))

    assert run(responder(event(), contact())) is None


def test_the_responder_does_not_add_a_signature():
    """`apply_disclosure` runs in the adapter. A second definition here is how a rule
    ends up with two definitions that disagree."""
    mind = StubMind(reply="Yes, still on.")
    result = run(MindResponder(mind=mind)(event(), contact()))

    assert result == "Yes, still on."
    assert "AI-operated" not in result


# ---------------------------------------------------------------------------
# Assembling the poller from a Mind
# ---------------------------------------------------------------------------


def _settings(**overrides) -> Settings:
    settings = Settings(_env_file=None)
    for key, value in overrides.items():
        object.__setattr__(settings, key, value)
    return settings


def test_answering_is_off_unless_an_operator_turns_it_on():
    """The default. A Mind that starts answering email the moment it has credentials,
    with no approval policy configured, is not a behaviour anyone asked for."""
    db_base.init_db()
    mind = StubMind()
    mind._channels = ChannelRegistry(mind.identity.gmid)

    assert build_poller(mind, settings=_settings(mind_channel_autoreply_enabled=False)) is None


def test_enabling_answering_with_no_channel_reports_that_there_is_nothing_to_read():
    """Returns None rather than a poller that silently does nothing, so "off" and
    "on but inert" cannot look the same."""
    db_base.init_db()
    mind = StubMind()
    mind._channels = ChannelRegistry(mind.identity.gmid)

    assert build_poller(mind, settings=_settings(mind_channel_autoreply_enabled=True)) is None


def test_an_enabled_channel_and_the_flag_produce_a_poller():
    db_base.init_db()
    mind = StubMind()
    registry = ChannelRegistry(mind.identity.gmid)
    registry.register(make_channel())
    mind._channels = registry

    poller = build_poller(
        mind,
        settings=_settings(
            mind_channel_autoreply_enabled=True,
            mind_channel_granted_scopes="comms.email.send",
        ),
    )

    assert poller is not None
    assert poller.mind_id == mind.identity.gmid
    # The durable ledger, because a restart must not re-answer.
    assert poller.ledger.durable is True
    assert poller.gateway.contacts.mind_id == mind.identity.gmid
    assert poller.gateway.recorder is not None


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", {}),
        ("   ", {}),
        ("{not json", {}),
        ("[1,2]", {}),
        ('"a string"', {}),
        ("null", {}),
    ],
)
def test_a_malformed_tenant_policy_means_no_standing_grant(value, expected):
    """`{}` is the fail-closed reading, so a typo means every reply needs approval
    rather than every reply being auto-approved."""
    from genesis.channels.poller import _parse_tenant_policy

    assert _parse_tenant_policy(value) == expected


def test_a_well_formed_tenant_policy_is_used():
    from genesis.channels.poller import _parse_tenant_policy

    policy = _parse_tenant_policy(
        '{"auto_approve_risk_levels": ["R0", "R1", "R2"], '
        '"auto_approve_categories": ["COMMUNICATION"]}'
    )

    assert policy["auto_approve_risk_levels"] == ["R0", "R1", "R2"]
    assert policy["auto_approve_categories"] == ["COMMUNICATION"]


def test_the_poller_receives_the_configured_policy_and_scopes():
    """A setting that never reaches the authorizer is a setting nothing reads."""
    db_base.init_db()
    mind = StubMind()
    registry = ChannelRegistry(mind.identity.gmid)
    registry.register(make_channel())
    mind._channels = registry

    poller = build_poller(
        mind,
        settings=_settings(
            mind_channel_autoreply_enabled=True,
            mind_channel_granted_scopes="comms.email.send, comms.telegram.send",
            mind_channel_tenant_policy=(
                '{"auto_approve_risk_levels":["R2"],'
                '"auto_approve_categories":["COMMUNICATION"]}'
            ),
        ),
    )

    authorizer = poller.gateway.authorizer
    assert authorizer.tenant_policy["auto_approve_risk_levels"] == ["R2"]
    assert "comms.telegram.send" in authorizer.granted_scopes


# ---------------------------------------------------------------------------
# Outreach: drafting about an obligation, with the same guarantees
# ---------------------------------------------------------------------------


class StubTrigger:
    def __init__(self, *, ref="cm-1", reason="a commitment to Dana is due soon: send the update"):
        self.kind = "commitment_at_risk"
        self.ref = ref
        self.reason = reason
        self.beneficiary_label = "Dana"


def test_the_outreach_prompt_does_not_mention_policy_either():
    """The same absence, and it matters more here.

    A model composing an *unprompted* message is the one most likely to argue for its
    own justification, and handing it the vocabulary of policy is handing it the
    vocabulary to do that with.
    """
    from genesis.channels.responder import OutreachResponder

    prompt = (
        OutreachResponder(mind=StubMind())
        .build_prompt(StubTrigger(), contact())
        .lower()
    )

    for forbidden in (
        "approval",
        "approve",
        "risk",
        "policy",
        "governance",
        "permission",
        "gate",
        "r2",
        "r3",
    ):
        assert forbidden not in prompt, f"the prompt mentions {forbidden!r}"


def test_the_outreach_prompt_states_the_obligation():
    """The model has to know what it owes, or the message is generic."""
    from genesis.channels.responder import OutreachResponder

    prompt = OutreachResponder(mind=StubMind()).build_prompt(StubTrigger(), contact())

    assert "send the update" in prompt
    assert "Dana" in prompt


def test_the_outreach_prompt_states_the_boundaries():
    from genesis.channels.responder import OutreachResponder

    prompt = OutreachResponder(mind=StubMind()).build_prompt(
        StubTrigger(), contact(boundaries=["do not mention the invoice"])
    )

    assert "do not mention the invoice" in prompt


def test_the_outreach_prompt_permits_declining():
    """A commitment may already have been handled, and a Mind that always produces
    text would always send."""
    from genesis.channels.responder import OutreachResponder
    from genesis.channels.responder import DECLINE_SENTINEL as SENTINEL

    prompt = OutreachResponder(mind=StubMind()).build_prompt(StubTrigger(), contact())

    assert SENTINEL in prompt
    assert "normal and expected" in prompt


def test_the_outreach_prompt_asks_for_the_body_only():
    from genesis.channels.responder import OutreachResponder

    prompt = (
        OutreachResponder(mind=StubMind())
        .build_prompt(StubTrigger(), contact())
        .lower()
    )

    assert "only the body" in prompt
    assert "do not add a signature" in prompt


def test_outreach_actions_are_disabled_during_a_draft():
    """Same reasoning as the reply: enabling actions would let the model act while
    composing, which is a route that bypasses the gate."""
    from genesis.channels.responder import OutreachResponder

    mind = StubMind()
    run(OutreachResponder(mind=mind)(StubTrigger(), contact()))

    assert mind.calls[0]["enable_actions"] is False


def test_an_outreach_draft_can_decline():
    from genesis.channels.responder import DECLINE_SENTINEL as SENTINEL
    from genesis.channels.responder import OutreachResponder

    mind = StubMind(reply=SENTINEL)
    assert run(OutreachResponder(mind=mind)(StubTrigger(), contact())) is None


def test_an_outreach_model_failure_means_no_message():
    from genesis.channels.responder import OutreachResponder

    mind = StubMind(raises=True)
    assert run(OutreachResponder(mind=mind)(StubTrigger(), contact())) is None


def test_the_outreach_responder_does_not_add_a_signature():
    """`apply_disclosure` runs in the adapter. A second definition here is how a rule
    ends up with two definitions that disagree."""
    from genesis.channels.responder import OutreachResponder

    mind = StubMind(reply="About that thing I said I would do.")
    result = run(OutreachResponder(mind=mind)(StubTrigger(), contact()))

    assert result == "About that thing I said I would do."
    assert "AI-operated" not in result


# ---------------------------------------------------------------------------
# Assembling the planner
# ---------------------------------------------------------------------------


def test_outreach_is_off_unless_an_operator_turns_it_on():
    """A Mind that starts contacting people because it decided it owed them something
    is a different category of behaviour from one that answers when written to."""
    from genesis.channels.outreach import build_planner

    db_base.init_db()
    mind = StubMind()
    mind._channels = ChannelRegistry(mind.identity.gmid)

    assert build_planner(mind, settings=_settings(mind_outreach_enabled=False)) is None


def test_outreach_with_no_channel_reports_that_there_is_nowhere_to_raise_it():
    from genesis.channels.outreach import build_planner

    db_base.init_db()
    mind = StubMind()
    mind._channels = ChannelRegistry(mind.identity.gmid)

    assert build_planner(mind, settings=_settings(mind_outreach_enabled=True)) is None


def test_outreach_with_no_commitment_manager_reports_that_there_is_nothing_to_raise():
    from genesis.channels.outreach import build_planner

    db_base.init_db()
    mind = StubMind()
    registry = ChannelRegistry(mind.identity.gmid)
    registry.register(make_channel())
    mind._channels = registry
    # No `commitments` attribute.

    assert build_planner(mind, settings=_settings(mind_outreach_enabled=True)) is None


def test_a_channel_and_commitments_produce_a_planner():
    from genesis.channels.outreach import build_planner

    db_base.init_db()
    mind = StubMind()
    registry = ChannelRegistry(mind.identity.gmid)
    registry.register(make_channel())
    mind._channels = registry

    class Commitments:
        def list_commitments(self, *, open_only=False):
            return []

    mind.commitments = Commitments()

    planner = build_planner(
        mind,
        settings=_settings(
            mind_outreach_enabled=True,
            mind_channel_granted_scopes="comms.email.send",
        ),
    )

    assert planner is not None
    assert planner.mind_id == mind.identity.gmid
    assert planner.attempts.durable is True
    assert planner.recorder is not None
    assert planner.channel == "email"


def test_the_outreach_planner_receives_the_configured_policy():
    from genesis.channels.outreach import build_planner

    db_base.init_db()
    mind = StubMind()
    registry = ChannelRegistry(mind.identity.gmid)
    registry.register(make_channel())
    mind._channels = registry

    class Commitments:
        def list_commitments(self, *, open_only=False):
            return []

    mind.commitments = Commitments()

    planner = build_planner(
        mind,
        settings=_settings(
            mind_outreach_enabled=True,
            mind_channel_granted_scopes="comms.email.send",
            mind_channel_tenant_policy=(
                '{"auto_approve_risk_levels":["R2"],'
                '"auto_approve_categories":["COMMUNICATION"]}'
            ),
        ),
    )

    assert planner.authorizer.tenant_policy["auto_approve_risk_levels"] == ["R2"]


def test_a_malformed_policy_means_no_standing_grant_for_outreach_too():
    """Both builders read the same parser, so a typo cannot mean "no grant" for
    replies and "grant" for outreach."""
    from genesis.channels.outreach import build_planner

    db_base.init_db()
    mind = StubMind()
    registry = ChannelRegistry(mind.identity.gmid)
    registry.register(make_channel())
    mind._channels = registry

    class Commitments:
        def list_commitments(self, *, open_only=False):
            return []

    mind.commitments = Commitments()

    planner = build_planner(
        mind,
        settings=_settings(
            mind_outreach_enabled=True,
            mind_channel_tenant_policy="{not json",
        ),
    )

    assert planner.authorizer.tenant_policy == {}
