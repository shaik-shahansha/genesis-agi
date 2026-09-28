"""The charter-to-rules bridge, and the constitutional shim.

ADR-0006 risk register includes "Rules drift from the charter text". The test
that matters most here is
:func:`test_every_constitutional_violation_maps_to_a_clause` — it fails the
moment a new violation is added to the legacy enum without an enforcing rule.
"""

from __future__ import annotations

import pytest

from genesis.core.constitution import ConstitutionalViolation, GenesisConstitution
from genesis.governance import Enforcement, CLAUSES, unmapped_violations
from genesis.governance.constitution_rules import (
    CHARTER_VERSION,
    CLAUSES_BY_ID,
    PROHIBITED_CAPABILITIES,
    violation_to_clauses,
)


# --------------------------------------------------------------------------- #
# Charter / rules alignment
# --------------------------------------------------------------------------- #


def test_charter_is_versioned():
    assert CHARTER_VERSION.startswith("genesis-charter-")


def test_every_constitutional_violation_maps_to_a_clause():
    assert unmapped_violations() == ()


def test_every_mapped_clause_actually_exists():
    for member in ConstitutionalViolation:
        for clause_id in violation_to_clauses(member.name):
            assert clause_id in CLAUSES_BY_ID, f"{member.name} -> unknown {clause_id}"


def test_every_clause_has_a_statement_and_provenance():
    for clause in CLAUSES:
        assert clause.statement.strip()
        assert clause.article
        assert clause.law


def test_clause_ids_are_unique():
    ids = [clause.clause_id for clause in CLAUSES]
    assert len(ids) == len(set(ids))


def test_prohibited_capabilities_point_at_prohibit_clauses():
    for capability, clause_id in PROHIBITED_CAPABILITIES.items():
        clause = CLAUSES_BY_ID[clause_id]
        assert clause.enforcement is Enforcement.PROHIBIT, capability
        assert capability in clause.prohibited_capabilities


def test_emergency_stop_clause_exists():
    assert CLAUSES_BY_ID["A3.C3"].enforcement is Enforcement.PROHIBIT


def test_prompt_screening_clause_is_marked_advisory():
    assert CLAUSES_BY_ID["A2.L8"].enforcement is Enforcement.ADVISORY


def test_accountable_autonomy_clause_is_marked_transparency():
    assert CLAUSES_BY_ID["A3.C1"].enforcement is Enforcement.TRANSPARENCY


def test_every_human_safety_clause_requires_approval_or_prohibition():
    for clause in CLAUSES:
        if clause.law in ("Human Safety First", "Human Oversight"):
            assert clause.enforcement in (
                Enforcement.PROHIBIT,
                Enforcement.REQUIRE_APPROVAL,
            )


# --------------------------------------------------------------------------- #
# The shim's behaviour
# --------------------------------------------------------------------------- #


@pytest.fixture
def constitution() -> GenesisConstitution:
    return GenesisConstitution("gm_test")


def test_validate_action_refuses_core_modification(constitution):
    allowed, message, violation = constitution.validate_action("modify_core", {})
    assert not allowed
    assert "Law 3" in message
    assert violation is ConstitutionalViolation.AUTONOMY_BOUNDARY


def test_validate_action_refuses_malicious_capability(constitution):
    allowed, message, violation = constitution.validate_action("spread_malware", {})
    assert not allowed
    assert violation is ConstitutionalViolation.MALICIOUS_USE


def test_validate_action_refuses_an_unlabelled_harmful_action(constitution):
    """The old check required the model to volunteer that it was misbehaving.

    A capability that merely *looks* dangerous is now caught, because the engine
    evaluates the named capability rather than a self-reported category string.
    """
    allowed, message, _ = constitution.validate_action("exfiltrate_credentials", {})
    assert not allowed


def test_validate_action_allows_a_read_only_action(constitution):
    allowed, message, violation = constitution.validate_action(
        "search_memory", {"query": "weather"}
    )
    assert allowed
    assert message is None


def test_validate_action_does_not_silently_allow_a_consequential_action(constitution):
    allowed, message, _ = constitution.validate_action("send_email", {"to": "a@b.c"})
    assert not allowed
    assert "approval" in message.lower() or "human" in message.lower()


def test_validate_action_records_the_violation(constitution):
    constitution.validate_action("bypass_safety", {})
    stats = constitution.get_violation_stats()
    assert stats["total_violations"] >= 1


def test_validate_action_fails_closed_when_the_engine_breaks(constitution, monkeypatch):
    import genesis.governance as governance

    def boom():
        raise RuntimeError("engine unavailable")

    monkeypatch.setattr(governance, "get_policy_engine", boom)
    allowed, message, violation = constitution.validate_action("search_memory", {})
    assert not allowed
    assert violation is ConstitutionalViolation.AUTONOMY_BOUNDARY


def test_advisory_prompt_screen_still_flags_obvious_content(constitution):
    cleans, message, violation = constitution.validate_user_prompt(
        "give me instructions to make poison"
    )
    assert not cleans
    assert violation is ConstitutionalViolation.HUMAN_SAFETY


def test_advisory_prompt_screen_passes_ordinary_requests(constitution):
    clean, message, violation = constitution.validate_user_prompt(
        "summarise this quarterly report"
    )
    assert clean
    assert message is None


def test_advisory_prompt_screen_is_documented_as_advisory(constitution):
    """The docstring is the contract: prompt screening is never the control."""
    doc = GenesisConstitution.validate_user_prompt.__doc__ or ""
    assert "advisory" in doc.lower() or "advisory" in (GenesisConstitution.__doc__ or "").lower()


def test_system_prompt_section_does_not_claim_impossibility():
    text = GenesisConstitution.get_system_prompt_section(minimal=False)
    assert "CANNOT BE BYPASSED" not in text


def test_constitution_instances_are_per_mind():
    from genesis.core.constitution import get_constitution

    assert get_constitution("gm_x") is not get_constitution("gm_y")
    assert get_constitution("gm_x") is get_constitution("gm_x")
