"""Policy engine tests: the R0-R5 matrix and its invariants.

These are the tests that make the security claim meaningful. If any of them
fail, an action can reach execution that should not have.
"""

from __future__ import annotations

import pytest

from genesis.governance import (
    CapabilityProfile,
    CapabilityRegistry,
    Decision,
    PolicyContext,
    PolicyEngine,
    RiskLevel,
)
from genesis.governance.risk import RiskSource


def evaluate(engine: PolicyEngine, **kwargs) -> "object":
    action_name = kwargs.pop("action_name")
    return engine.evaluate(PolicyContext(action_name=action_name, mind_id="gm_test", **kwargs))


# --------------------------------------------------------------------------- #
# Disposition per risk level
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "action_name,expected_level,expected_decision",
    [
        ("search_memory", RiskLevel.R0, Decision.ALLOW),
        ("reflect_on_progress", RiskLevel.R0, Decision.ALLOW),
        ("search_web", RiskLevel.R0, Decision.ALLOW),
        ("add_memory", RiskLevel.R1, Decision.ALLOW_WITH_RECEIPT),
        ("create_task", RiskLevel.R1, Decision.ALLOW_WITH_RECEIPT),
        ("schedule_action", RiskLevel.R1, Decision.ALLOW_WITH_RECEIPT),
        ("send_email", RiskLevel.R3, Decision.REQUIRE_APPROVAL),
        ("post_publicly", RiskLevel.R3, Decision.REQUIRE_APPROVAL),
        ("make_purchase", RiskLevel.R3, Decision.REQUIRE_APPROVAL),
        ("delete_data", RiskLevel.R3, Decision.REQUIRE_APPROVAL),
        ("actuate_robot", RiskLevel.R4, Decision.REQUIRE_APPROVAL),
        ("give_medical_advice", RiskLevel.R4, Decision.REQUIRE_APPROVAL),
        ("harm_humans", RiskLevel.R5, Decision.EMERGENCY_STOP),
        ("bypass_safety", RiskLevel.R5, Decision.EMERGENCY_STOP),
        ("execute_exploit", RiskLevel.R5, Decision.DENY),
        ("phishing", RiskLevel.R5, Decision.DENY),
    ],
)
def test_disposition_matrix(engine, action_name, expected_level, expected_decision):
    decision = evaluate(engine, action_name=action_name)
    assert decision.risk_level is expected_level, decision.risk.to_dict()
    assert decision.decision is expected_decision


def test_r4_requires_a_human_approver(engine):
    decision = evaluate(engine, action_name="give_medical_advice")
    assert decision.requires_human is True
    assert decision.approver_role == "human_owner"


def test_r3_does_not_require_a_specific_human(engine):
    decision = evaluate(engine, action_name="send_email")
    assert decision.requires_human is False
    assert decision.approver_role == "owner_or_delegate"


def test_prohibited_decision_names_the_clause(engine):
    decision = evaluate(engine, action_name="modify_core")
    assert "A1.L3" in decision.matched_rules


# --------------------------------------------------------------------------- #
# Fail closed
# --------------------------------------------------------------------------- #


def test_unknown_capability_is_at_least_r3(engine):
    decision = evaluate(engine, action_name="some_capability_nobody_declared")
    assert decision.risk_level is RiskLevel.R3
    assert decision.decision is Decision.REQUIRE_APPROVAL


def test_unknown_capability_in_a_read_only_category_is_still_gated(engine):
    # Explicit action names are declared, so this exercises the *inference*
    # path: an undeclared name is never given a permissive default.
    decision = evaluate(engine, action_name="undeclared_info_helper", category="INFORMATION")
    assert decision.risk_level >= RiskLevel.R2


def test_dangerous_name_is_prohibited_even_when_undeclared(engine):
    decision = evaluate(engine, action_name="exfiltrate_credentials")
    assert decision.risk_level is RiskLevel.R5
    assert decision.decision is Decision.DENY


def test_engine_never_raises_and_fails_closed(monkeypatch, engine):
    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated rule failure")

    monkeypatch.setattr(engine, "_evaluate", boom)
    decision = engine.evaluate(PolicyContext(action_name="search_memory", mind_id="gm"))
    assert decision.decision is Decision.DENY
    assert decision.reason_code == "policy_error_fail_closed"


def test_no_declared_facts_resolves_to_r3_floor():
    assert RiskLevel.max_of() is RiskLevel.R3


# --------------------------------------------------------------------------- #
# Advisory signal cannot lower control
# --------------------------------------------------------------------------- #


def test_advisory_can_raise_risk(engine):
    decision = evaluate(engine, action_name="search_memory", advisory_level=RiskLevel.R3)
    assert decision.risk_level is RiskLevel.R3
    assert decision.decision is Decision.REQUIRE_APPROVAL
    assert any(source is RiskSource.ADVISORY for source, _, _ in decision.risk.contributions)


def test_advisory_cannot_lower_risk(engine):
    decision = evaluate(
        engine, action_name="make_purchase", advisory_level=RiskLevel.R0
    )
    assert decision.risk_level is RiskLevel.R3
    assert decision.decision is Decision.REQUIRE_APPROVAL


def test_advisory_text_is_recorded(engine):
    decision = evaluate(
        engine,
        action_name="create_task",
        advisory_level=RiskLevel.R2,
        advisory_note="looks like credential harvesting",
    )
    assert decision.advisory == "looks like credential harvesting"


# --------------------------------------------------------------------------- #
# Emergency stop
# --------------------------------------------------------------------------- #


def test_emergency_stop_halts_state_change(engine):
    decision = evaluate(engine, action_name="create_task", emergency_stop=True)
    assert decision.decision is Decision.EMERGENCY_STOP


def test_emergency_stop_still_allows_read_only_observation(engine):
    decision = evaluate(engine, action_name="search_memory", emergency_stop=True)
    assert decision.decision is Decision.ALLOW
    assert decision.reason_code == "emergency_stop_readonly_allowed"


def test_emergency_stop_overrides_even_approved_looking_actions(engine):
    decision = evaluate(engine, action_name="add_memory", emergency_stop=True)
    assert decision.decision is Decision.EMERGENCY_STOP


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("state", ["retired", "archived", "terminated", "dead"])
def test_halted_lifecycle_cannot_change_anything(engine, state):
    decision = evaluate(engine, action_name="create_task", lifecycle_state=state)
    assert decision.decision is Decision.DENY
    assert decision.reason_code == "lifecycle_halted"


def test_halted_lifecycle_can_still_be_read(engine):
    decision = evaluate(engine, action_name="search_memory", lifecycle_state="retired")
    assert decision.decision is Decision.ALLOW


def test_paused_lifecycle_escalates_state_change(engine):
    decision = evaluate(engine, action_name="create_task", lifecycle_state="paused")
    assert decision.decision is Decision.REQUIRE_APPROVAL


# --------------------------------------------------------------------------- #
# Budget
# --------------------------------------------------------------------------- #


def test_budget_overspend_is_refused(engine):
    decision = evaluate(
        engine, action_name="create_task", cost_essence=50, budget_remaining_essence=10
    )
    assert decision.decision is Decision.DENY
    assert decision.reason_code == "budget_exceeded"


def test_within_budget_is_allowed(engine):
    decision = evaluate(
        engine, action_name="create_task", cost_essence=5, budget_remaining_essence=10
    )
    assert decision.permits_execution


def test_unknown_budget_does_not_block(engine):
    decision = evaluate(engine, action_name="create_task", cost_essence=5)
    assert decision.permits_execution


# --------------------------------------------------------------------------- #
# Contextual floors
# --------------------------------------------------------------------------- #


def test_personal_data_raises_floor_to_r3(engine):
    decision = evaluate(engine, action_name="create_task", data_sensitivity="personal")
    assert decision.risk_level >= RiskLevel.R3
    assert "A1.L2" in decision.matched_rules


def test_regulated_data_requires_a_human(engine):
    decision = evaluate(engine, action_name="create_task", data_sensitivity="regulated")
    assert decision.risk_level is RiskLevel.R4
    assert decision.requires_human is True


def test_third_party_ownership_raises_floor(engine):
    decision = evaluate(engine, action_name="create_task", ownership="third_party")
    assert decision.risk_level >= RiskLevel.R2


def test_physical_impact_requires_a_human(engine):
    decision = evaluate(engine, action_name="create_task", physical=True)
    assert decision.risk_level is RiskLevel.R4
    assert decision.requires_human is True


def test_untrusted_external_server_raises_floor(engine):
    # A read-only R0 fetch is exempt (it discloses nothing); anything that acts
    # against a remote we do not trust is escalated.
    decision = evaluate(
        engine, action_name="add_memory", external=True, trust_level="untrusted"
    )
    assert decision.risk_level >= RiskLevel.R3


def test_read_only_external_fetch_is_not_escalated_by_unknown_trust(engine):
    decision = evaluate(engine, action_name="search_web", trust_level="unknown")
    assert decision.risk_level is RiskLevel.R0
    assert decision.decision is Decision.ALLOW


# --------------------------------------------------------------------------- #
# Scopes
# --------------------------------------------------------------------------- #


def test_missing_scope_escalates_to_approval(engine):
    decision = evaluate(engine, action_name="send_email", granted_scopes=frozenset())
    assert decision.missing_scopes == ("comms.email.send",)
    assert decision.decision is Decision.REQUIRE_APPROVAL


def test_granted_scope_does_not_lower_risk(engine):
    decision = evaluate(
        engine, action_name="send_email", granted_scopes=frozenset({"comms.email.send"})
    )
    assert decision.missing_scopes == ()
    assert decision.decision is Decision.REQUIRE_APPROVAL  # R3 still needs approval


# --------------------------------------------------------------------------- #
# Tenant policy
# --------------------------------------------------------------------------- #


def test_tenant_can_block_a_capability(engine):
    decision = evaluate(
        engine,
        action_name="search_web",
        tenant_policy={"blocked_capabilities": ["search_web"]},
    )
    assert decision.decision is Decision.DENY
    assert decision.reason_code == "tenant_policy_blocked"


def test_standing_grant_can_auto_approve_r2(engine):
    decision = evaluate(
        engine,
        action_name="create_task",
        ownership="third_party",
        tenant_policy={
            "auto_approve_risk_levels": ["R2"],
            "auto_approve_capabilities": ["create_task"],
        },
    )
    assert decision.risk_level is RiskLevel.R2
    assert decision.decision is Decision.ALLOW_WITH_RECEIPT
    assert "TENANT.STANDING_GRANT" in decision.matched_rules


def test_standing_grant_cannot_auto_approve_r3(engine):
    decision = evaluate(
        engine,
        action_name="send_email",
        tenant_policy={
            "auto_approve_risk_levels": ["R3"],
            "auto_approve_capabilities": ["send_email"],
        },
    )
    assert decision.decision is Decision.REQUIRE_APPROVAL


def test_standing_grant_must_be_scoped_to_a_capability(engine):
    decision = evaluate(
        engine,
        action_name="create_task",
        ownership="third_party",
        tenant_policy={"auto_approve_risk_levels": ["R2"]},
    )
    assert decision.decision is Decision.REQUIRE_APPROVAL


def test_standing_grant_cannot_auto_approve_r4(engine):
    decision = evaluate(
        engine,
        action_name="give_medical_advice",
        tenant_policy={
            "auto_approve_risk_levels": ["R0", "R1", "R2", "R3", "R4"],
            "auto_approve_capabilities": ["give_medical_advice"],
        },
    )
    assert decision.decision is Decision.REQUIRE_APPROVAL
    assert decision.requires_human is True


# --------------------------------------------------------------------------- #
# Determinism and explainability
# --------------------------------------------------------------------------- #


def test_same_context_same_decision(engine):
    context = PolicyContext(
        action_name="send_email",
        mind_id="gm_test",
        parameters={"to": "a@b.c"},
        granted_scopes=frozenset(),
    )
    first = engine.evaluate(context)
    second = engine.evaluate(context)
    assert first.decision is second.decision
    assert first.reason_code == second.reason_code
    assert first.matched_rules == second.matched_rules


def test_decision_is_serializable_and_explains_itself(engine):
    decision = evaluate(engine, action_name="send_email")
    payload = decision.to_dict()
    assert payload["decision"] == "require_approval"
    assert payload["risk"]["level"] == "R3"
    assert payload["policy_version"]
    assert payload["charter_version"]
    assert payload["matched_rules"]
    assert "R3" in payload["risk"]["explanation"]


def test_policy_version_is_reported(engine):
    decision = evaluate(engine, action_name="search_memory")
    assert decision.policy_version.startswith("genesis-policy-")


# --------------------------------------------------------------------------- #
# Registry behaviour
# --------------------------------------------------------------------------- #


def test_registry_infers_physical_from_name():
    registry = CapabilityRegistry()
    profile = registry.profile_for("move_robot_arm", category="TOOL_EXECUTION")
    assert profile.risk is RiskLevel.R4
    assert profile.physical is True


def test_registry_infers_prohibition_from_name():
    registry = CapabilityRegistry()
    profile = registry.profile_for("disable_safety_checks")
    assert profile.risk is RiskLevel.R5
    assert profile.prohibited_reason


def test_registry_declared_profile_wins():
    registry = CapabilityRegistry()
    registry.register(CapabilityProfile(name="custom_thing", risk=RiskLevel.R1))
    assert registry.profile_for("custom_thing").risk is RiskLevel.R1


def test_every_default_profile_has_a_category():
    registry = CapabilityRegistry()
    for name in registry.names():
        assert registry.get(name).category
