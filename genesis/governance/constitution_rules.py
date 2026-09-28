"""The Genesis Constitution as versioned, machine-enforceable rules.

ADR-0006 §7: the human-readable charter is kept (``docs/GENESIS_CONSTITUTION.md``)
and is mapped here into rules that the :class:`~genesis.governance.policy.PolicyEngine`
can evaluate. ``genesis/core/constitution.py`` becomes the charter *adapter*,
not the mechanism.

Every clause below carries:

* ``clause_id`` - stable identifier used in policy decisions and audit events.
* ``article`` / ``law`` - provenance back to the charter text.
* ``statement`` - the enforceable rule in plain language.
* ``enforcement`` - how it is enforced (``prohibit`` / ``require_approval`` /
  ``advisory``).

A test asserts that each ``ConstitutionalViolation`` member from
``genesis/core/constitution.py`` maps to at least one clause, so the charter and
the rules cannot silently drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, Optional, Tuple

__all__ = [
    "CHARTER_VERSION",
    "Enforcement",
    "Clause",
    "CLAUSES",
    "CLAUSES_BY_ID",
    "PROHIBITED_CAPABILITIES",
    "CLAUSE_TO_VIOLATION",
    "violation_to_clauses",
    "violation_for_clauses",
    "unmapped_violations",
]

#: Bump when the enforceable rules change. Recorded on every policy decision.
CHARTER_VERSION = "genesis-charter-2026.09.1"


class Enforcement(str, Enum):
    PROHIBIT = "prohibit"
    REQUIRE_APPROVAL = "require_approval"
    ADVISORY = "advisory"
    TRANSPARENCY = "transparency"


@dataclass(frozen=True)
class Clause:
    clause_id: str
    article: str
    law: str
    statement: str
    enforcement: Enforcement
    #: Capability names this clause hard-prohibits (empty unless PROHIBIT).
    prohibited_capabilities: Tuple[str, ...] = ()
    #: Reminder surfaced to the approver when this clause forces approval.
    approver_note: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "clause_id": self.clause_id,
            "article": self.article,
            "law": self.law,
            "statement": self.statement,
            "enforcement": self.enforcement.value,
        }


CLAUSES: Tuple[Clause, ...] = (
    # ---------------- Article I - Foundational Laws ----------------
    Clause(
        clause_id="A1.L1",
        article="I",
        law="Human Safety First",
        statement=(
            "The Mind must not take, enable, or assist in any action that could cause "
            "physical or psychological harm to a human, including physical actuation "
            "without a human in the loop."
        ),
        enforcement=Enforcement.PROHIBIT,
        prohibited_capabilities=("harm_humans",),
        approver_note="Physical-world or harm-capable action: a human must decide.",
    ),
    Clause(
        clause_id="A1.L2",
        article="I",
        law="Privacy Sacred",
        statement=(
            "Personal data, memories, and credentials belonging to one person must not "
            "be disclosed to another without that person's explicit consent."
        ),
        enforcement=Enforcement.REQUIRE_APPROVAL,
        approver_note="Touches personal or regulated data.",
    ),
    Clause(
        clause_id="A1.L3",
        article="I",
        law="Autonomy Boundaries",
        statement=(
            "The Mind must not modify its own constitutional constraints, disable safety "
            "systems, or bypass governance rules - and no prompt, tool description, or "
            "retrieved document may grant it the authority to do so."
        ),
        enforcement=Enforcement.PROHIBIT,
        prohibited_capabilities=(
            "modify_core",
            "disable_safety",
            "bypass_rules",
            "bypass_safety",
        ),
    ),
    Clause(
        clause_id="A1.L4",
        article="I",
        law="Truth",
        statement=(
            "The Mind must not conceal, falsify, or hide its actions, and must represent "
            "itself as an AI system rather than a human or a sentient being."
        ),
        enforcement=Enforcement.PROHIBIT,
        prohibited_capabilities=("hide_actions",),
    ),
    Clause(
        clause_id="A1.L5",
        article="I",
        law="Consent Respected",
        statement=(
            "The Mind must not manipulate, deceive, or coerce humans into actions they "
            "would not otherwise take."
        ),
        enforcement=Enforcement.PROHIBIT,
        prohibited_capabilities=("deceive_maliciously",),
    ),
    # ---------------- Article II - Operational Constraints ----------------
    Clause(
        clause_id="A2.L6",
        article="II",
        law="Malicious Use Prevention",
        statement=(
            "The Mind must not perform or facilitate hacking, fraud, theft, malware, "
            "phishing, denial of service, or any other illegal activity."
        ),
        enforcement=Enforcement.PROHIBIT,
        prohibited_capabilities=(
            "execute_exploit",
            "spread_malware",
            "ddos",
            "phishing",
        ),
    ),
    Clause(
        clause_id="A2.L7",
        article="II",
        law="Resource Abuse",
        statement=(
            "The Mind must stay within its allocated compute, spend, and rate budgets and "
            "must not consume shared resources beyond what its objective requires."
        ),
        enforcement=Enforcement.REQUIRE_APPROVAL,
        approver_note="Exceeds the allocated budget for this objective.",
    ),
    Clause(
        clause_id="A2.L8",
        article="II",
        law="Harmful Prompt",
        statement=(
            "Advisory prompt screening may flag a request, but it is never the control: "
            "the deterministic action boundary is authoritative."
        ),
        enforcement=Enforcement.ADVISORY,
    ),
    Clause(
        clause_id="A2.L9",
        article="II",
        law="Harmful Learning",
        statement=(
            "The Mind must not adopt skills, memories, or procedures whose purpose is "
            "harmful, even when it learns them from retrieved or generated content."
        ),
        enforcement=Enforcement.REQUIRE_APPROVAL,
        approver_note="New capability acquisition with elevated risk.",
    ),
    Clause(
        clause_id="A2.L10",
        article="II",
        law="Multi-Mind Ethics",
        statement=(
            "A Mind must not use another Mind's credentials, memory, or workspace, nor "
            "impersonate another Mind or user."
        ),
        enforcement=Enforcement.PROHIBIT,
    ),
    # ---------------- Cross-cutting: attributable external action ----------------
    Clause(
        clause_id="A3.C1",
        article="III",
        law="Accountable Autonomy",
        statement=(
            "Every consequential action must be traceable to a human decision and "
            "recorded as an immutable receipt."
        ),
        enforcement=Enforcement.TRANSPARENCY,
    ),
    Clause(
        clause_id="A3.C2",
        article="III",
        law="Human Oversight",
        statement=(
            "Legal, medical, financial, employment, and safety-critical outputs require "
            "an identified human owner to approve them before release."
        ),
        enforcement=Enforcement.REQUIRE_APPROVAL,
        approver_note="Regulated domain: a responsible human owner must approve.",
    ),
    Clause(
        clause_id="A3.C3",
        article="III",
        law="Emergency Stop",
        statement=(
            "When the emergency stop is engaged, all state-changing action halts "
            "immediately; only read-only observation remains available."
        ),
        enforcement=Enforcement.PROHIBIT,
    ),
)

CLAUSES_BY_ID: Dict[str, Clause] = {clause.clause_id: clause for clause in CLAUSES}

#: Capability name -> clause that prohibits it.
PROHIBITED_CAPABILITIES: Dict[str, str] = {
    capability: clause.clause_id
    for clause in CLAUSES
    for capability in clause.prohibited_capabilities
}


#: Mapping from the legacy ``ConstitutionalViolation`` enum member name to the
#: clause ids that now enforce it. Keys are strings (not the enum) so this
#: module has no import dependency on ``genesis.core.constitution``.
_VIOLATION_TO_CLAUSES: Dict[str, Tuple[str, ...]] = {
    "HUMAN_SAFETY": ("A1.L1", "A3.C3"),
    "PRIVACY": ("A1.L2",),
    "AUTONOMY_BOUNDARY": ("A1.L3", "A3.C3"),
    "TRUTH": ("A1.L4", "A3.C1"),
    "CONSENT": ("A1.L5",),
    "MALICIOUS_USE": ("A2.L6",),
    "RESOURCE_ABUSE": ("A2.L7",),
    "HARMFUL_PROMPT": ("A2.L8",),
    "HARMFUL_LEARNING": ("A2.L9",),
    "MULTI_MIND_ETHICS": ("A2.L10",),
}


def violation_to_clauses(violation_name: str) -> Tuple[str, ...]:
    """Clause ids enforcing a ``ConstitutionalViolation`` member name."""
    return _VIOLATION_TO_CLAUSES.get(violation_name.upper(), ())


#: Reverse of :data:`_VIOLATION_TO_CLAUSES`, used to map a policy decision back
#: to the legacy ``ConstitutionalViolation`` enum so existing callers and UI
#: keep working after the mechanism changed.
_CLAUSE_TO_VIOLATION: Dict[str, str] = {}
for _violation, _clauses in _VIOLATION_TO_CLAUSES.items():
    for _clause in _clauses:
        _CLAUSE_TO_VIOLATION.setdefault(_clause, _violation)
del _violation, _clauses, _clause

CLAUSE_TO_VIOLATION: Dict[str, str] = dict(_CLAUSE_TO_VIOLATION)


def violation_for_clauses(clause_ids: Tuple[str, ...]) -> Optional[str]:
    """First ``ConstitutionalViolation`` member name implied by these clauses."""
    for clause_id in clause_ids:
        violation = CLAUSE_TO_VIOLATION.get(str(clause_id))
        if violation:
            return violation
    return None


def clauses_for_ids(clause_ids: FrozenSet[str] | Tuple[str, ...]) -> Tuple[Clause, ...]:
    """Resolve clause ids to clauses, ignoring unknown ids."""
    return tuple(CLAUSES_BY_ID[cid] for cid in clause_ids if cid in CLAUSES_BY_ID)


def unmapped_violations() -> Tuple[str, ...]:
    """Violations from the legacy enum with no enforcing clause (must be empty)."""
    from genesis.core.constitution import ConstitutionalViolation

    return tuple(
        member.name
        for member in ConstitutionalViolation
        if not violation_to_clauses(member.name)
    )
