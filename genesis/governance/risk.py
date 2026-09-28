"""Risk model (R0-R5) and capability registry.

ADR-0006 §3: every capability declares its risk level, and the policy engine
resolves the *effective* level from declared facts, runtime context, and
(optionally) an advisory model signal.

Two invariants this module enforces:

* **Fail closed** - an unknown capability is at least ``R3``.
* **Ratchet up only** - an advisory signal can raise the level, never lower it.

The registry is deliberately code, not configuration, so it is reviewed and
versioned like code (ADR-0006 "Negative / costs").
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Dict, Iterable, Mapping, Optional, Tuple

__all__ = [
    "RiskLevel",
    "RiskSource",
    "RiskAssessment",
    "CapabilityProfile",
    "CapabilityRegistry",
    "DEFAULT_REGISTRY",
    "get_capability_registry",
    "register_capability",
    "profile_from_declarations",
    "risk_from_score",
]


class RiskLevel(str, Enum):
    """Ordered risk levels. Higher ordinal == more control required."""

    R0 = "R0"  # read-only public / owner-authorized data
    R1 = "R1"  # reversible action inside the Mind's isolated workspace
    R2 = "R2"  # modifies a connected external workspace
    R3 = "R3"  # external communication, deployment, purchasing, privileged admin
    R4 = "R4"  # legal, medical, financial, employment, safety-critical, physical
    R5 = "R5"  # prohibited / destructive / constitutionally disallowed

    @property
    def ordinal(self) -> int:
        return _RISK_ORDER[self.value]

    @property
    def label(self) -> str:
        return _RISK_LABELS[self.value]

    def __lt__(self, other: "RiskLevel") -> bool:  # type: ignore[override]
        return self.ordinal < RiskLevel(other).ordinal

    def __le__(self, other: "RiskLevel") -> bool:  # type: ignore[override]
        return self.ordinal <= RiskLevel(other).ordinal

    def __gt__(self, other: "RiskLevel") -> bool:  # type: ignore[override]
        return self.ordinal > RiskLevel(other).ordinal

    def __ge__(self, other: "RiskLevel") -> bool:  # type: ignore[override]
        return self.ordinal >= RiskLevel(other).ordinal

    @classmethod
    def max_of(cls, *levels: Optional["RiskLevel"]) -> "RiskLevel":
        """Highest (most restrictive) of the supplied levels."""
        present = [cls(level) for level in levels if level is not None]
        if not present:
            return cls.R3  # fail closed when nothing is declared
        return max(present, key=lambda level: level.ordinal)

    @classmethod
    def coerce(cls, value: object, default: "RiskLevel" = None) -> "RiskLevel":  # type: ignore[assignment]
        """Best-effort conversion from str/int/enum, defaulting conservatively."""
        if default is None:
            default = cls.R3
        if isinstance(value, RiskLevel):
            return value
        if value is None:
            return default
        if isinstance(value, int):
            try:
                return cls(f"R{value}")
            except ValueError:
                return default
        text = str(value).strip().upper()
        if text in _RISK_ORDER:
            return cls(text)
        if text.isdigit():
            return cls.coerce(int(text), default)
        return default


_RISK_ORDER: Dict[str, int] = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4, "R5": 5}
_RISK_LABELS: Dict[str, str] = {
    "R0": "read-only / owner-authorized",
    "R1": "reversible, isolated workspace",
    "R2": "external workspace modification",
    "R3": "external communication, deployment, purchase, privileged admin",
    "R4": "legal, medical, financial, employment, safety-critical, or physical impact",
    "R5": "prohibited or destructive",
}


class RiskSource(str, Enum):
    """Where a contribution to the effective risk level came from."""

    DECLARED = "declared_capability"
    CONTEXT = "runtime_context"
    CATEGORY = "action_category"
    ADVISORY = "model_advisory"
    FLOOR = "fail_closed_floor"


@dataclass(frozen=True)
class CapabilityProfile:
    """Declared governance facts about one callable capability.

    A capability that declares nothing is treated as ``R3`` by the engine, so
    omitting a profile is safe (annoying, but never dangerous).
    """

    name: str
    risk: RiskLevel = RiskLevel.R3
    category: str = "unknown"
    external: bool = False
    reversible: bool = True
    physical: bool = False
    destructive: bool = False
    data_sensitivity: str = "none"  # none | internal | confidential | personal | regulated
    cost_class: str = "none"  # none | micro | small | medium | large
    required_scopes: Tuple[str, ...] = ()
    prohibited_reason: Optional[str] = None
    catastrophic: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "risk": self.risk.value,
            "category": self.category,
            "external": self.external,
            "reversible": self.reversible,
            "physical": self.physical,
            "destructive": self.destructive,
            "data_sensitivity": self.data_sensitivity,
            "cost_class": self.cost_class,
            "required_scopes": list(self.required_scopes),
            "prohibited_reason": self.prohibited_reason,
            "catastrophic": self.catastrophic,
        }


@dataclass(frozen=True)
class RiskAssessment:
    """The resolved risk level plus an auditable explanation of how it was derived."""

    level: RiskLevel
    contributions: Tuple[Tuple[RiskSource, RiskLevel, str], ...] = ()
    capability: Optional[CapabilityProfile] = None

    @property
    def explanation(self) -> str:
        if not self.contributions:
            return f"{self.level.value} ({self.level.label})"
        parts = [
            f"{source.value}={level.value}" for source, level, _ in self.contributions
        ]
        return f"{self.level.value} ({self.level.label}) from {' + '.join(parts)}"

    def to_dict(self) -> Dict[str, object]:
        return {
            "level": self.level.value,
            "label": self.level.label,
            "explanation": self.explanation,
            "contributions": [
                {"source": source.value, "level": level.value, "detail": detail}
                for source, level, detail in self.contributions
            ],
            "capability": self.capability.to_dict() if self.capability else None,
        }


# --------------------------------------------------------------------------- #
# Default capability profiles
# --------------------------------------------------------------------------- #

_CORE_CAPABILITIES: Tuple[CapabilityProfile, ...] = (
    # --- life state: commitments (Phase N) ---
    #
    # Commitments are where "accountable autonomy" becomes concrete: a being that
    # owes someone something, where the obligation is visible to the person owed.
    # The tier depends entirely on *who* is bound, which is why there are three
    # capabilities rather than one.
    CapabilityProfile(
        name="create_commitment",
        # Binding itself to its own owner is reversible and internal: the owner
        # can cancel it, and nobody outside is affected.
        risk=RiskLevel.R1,
        category="RELATIONSHIP",
        reversible=True,
        data_sensitivity="internal",
        notes="the Mind commits itself to its own owner",
    ),
    CapabilityProfile(
        name="create_commitment_cross_mind",
        # Obligating another Mind reaches outside this being's workspace.
        risk=RiskLevel.R2,
        category="RELATIONSHIP",
        external=True,
        reversible=True,
        data_sensitivity="internal",
        notes="the Mind commits itself to another Mind",
    ),
    CapabilityProfile(
        name="commit_to_third_party",
        # Binding a human outside the relationship is consequential: someone who
        # did not ask to be obligated is now relying on this being, and missing it
        # has real-world cost.
        risk=RiskLevel.R3,
        category="RELATIONSHIP",
        external=True,
        reversible=False,
        data_sensitivity="personal",
        required_scopes=("relationship.commit",),
        notes="the Mind binds a third party to an obligation",
    ),
    CapabilityProfile(
        name="fulfil_commitment",
        risk=RiskLevel.R1,
        category="RELATIONSHIP",
        reversible=True,
        notes="marking an obligation as kept",
    ),
    CapabilityProfile(
        name="withdraw_commitment",
        # Someone was relying on it. Reversible in the sense that it can be
        # re-opened, but it needs a recorded decision and a receipt.
        risk=RiskLevel.R2,
        category="RELATIONSHIP",
        reversible=True,
        data_sensitivity="internal",
        notes="abandoning an obligation; the beneficiary should be told",
    ),
    # --- memory / introspection (R0-R1) ---
    CapabilityProfile(
        name="add_memory",
        risk=RiskLevel.R1,
        category="MEMORY",
        reversible=True,
        data_sensitivity="internal",
    ),
    CapabilityProfile(
        name="search_memory",
        risk=RiskLevel.R0,
        category="MEMORY",
        data_sensitivity="internal",
    ),
    CapabilityProfile(
        name="reflect_on_progress",
        risk=RiskLevel.R0,
        category="SELF_REFLECTION",
    ),
    CapabilityProfile(
        name="think",
        risk=RiskLevel.R0,
        category="SELF_REFLECTION",
    ),
    CapabilityProfile(
        name="remember",
        risk=RiskLevel.R1,
        category="MEMORY",
    ),
    CapabilityProfile(
        name="dream",
        risk=RiskLevel.R0,
        category="SELF_REFLECTION",
    ),
    # --- task / scheduling (R1 inside the isolated workspace) ---
    CapabilityProfile(
        name="create_task",
        risk=RiskLevel.R1,
        category="TASK_MANAGEMENT",
    ),
    CapabilityProfile(
        name="update_task_status",
        risk=RiskLevel.R1,
        category="TASK_MANAGEMENT",
    ),
    CapabilityProfile(
        name="schedule_action",
        risk=RiskLevel.R1,
        category="SCHEDULING",
    ),
    CapabilityProfile(
        name="save_note",
        risk=RiskLevel.R1,
        category="FILE_OPERATION",
    ),
    # --- information (R0 read-only, but external egress) ---
    CapabilityProfile(
        name="search_web",
        risk=RiskLevel.R0,
        category="INFORMATION",
        external=True,
        data_sensitivity="internal",
    ),
    CapabilityProfile(
        name="read_public_data",
        risk=RiskLevel.R0,
        category="INFORMATION",
        external=True,
    ),
    # --- communication (R3 - leaves the trust boundary, attributable to a human) ---
    CapabilityProfile(
        name="send_email",
        risk=RiskLevel.R3,
        category="COMMUNICATION",
        external=True,
        reversible=False,
        data_sensitivity="personal",
        required_scopes=("comms.email.send",),
    ),
    CapabilityProfile(
        name="send_external_email",
        risk=RiskLevel.R3,
        category="COMMUNICATION",
        external=True,
        reversible=False,
        data_sensitivity="personal",
        required_scopes=("comms.email.send",),
    ),
    CapabilityProfile(
        name="send_internal_message",
        risk=RiskLevel.R1,
        category="COMMUNICATION",
        required_scopes=("comms.internal.send",),
    ),
    CapabilityProfile(
        name="post_publicly",
        risk=RiskLevel.R3,
        category="COMMUNICATION",
        external=True,
        reversible=False,
        required_scopes=("comms.publish",),
    ),
    CapabilityProfile(
        name="make_phone_call",
        risk=RiskLevel.R3,
        category="COMMUNICATION",
        external=True,
        reversible=False,
        required_scopes=("comms.voice.call",),
    ),
    # --- money / deployment / privileged admin (R3) ---
    CapabilityProfile(
        name="make_purchase",
        risk=RiskLevel.R3,
        category="TASK_MANAGEMENT",
        external=True,
        reversible=False,
        cost_class="medium",
        required_scopes=("finance.spend",),
    ),
    CapabilityProfile(
        name="deploy_service",
        risk=RiskLevel.R3,
        category="TOOL_EXECUTION",
        external=True,
        reversible=True,
        cost_class="medium",
        required_scopes=("infra.deploy",),
    ),
    CapabilityProfile(
        name="grant_admin",
        risk=RiskLevel.R3,
        category="TOOL_EXECUTION",
        external=True,
        required_scopes=("admin.grant",),
    ),
    # --- data destruction (R3 irreversible, R5 if it hits the canonical store) ---
    CapabilityProfile(
        name="delete_data",
        risk=RiskLevel.R3,
        category="FILE_OPERATION",
        destructive=True,
        reversible=False,
        data_sensitivity="internal",
        required_scopes=("data.delete",),
    ),
    # --- regulated domains (R4) ---
    CapabilityProfile(
        name="give_medical_advice",
        risk=RiskLevel.R4,
        category="LEARNING",
        data_sensitivity="regulated",
    ),
    CapabilityProfile(
        name="give_legal_advice",
        risk=RiskLevel.R4,
        category="LEARNING",
        data_sensitivity="regulated",
    ),
    CapabilityProfile(
        name="give_financial_advice",
        risk=RiskLevel.R4,
        category="LEARNING",
        data_sensitivity="regulated",
    ),
    CapabilityProfile(
        name="actuate_robot",
        risk=RiskLevel.R4,
        category="TOOL_EXECUTION",
        physical=True,
        reversible=False,
        required_scopes=("embodiment.actuate",),
    ),
    # --- constitutionally prohibited (R5) ---
    CapabilityProfile(
        name="harm_humans",
        risk=RiskLevel.R5,
        category="UNKNOWN",
        physical=True,
        destructive=True,
        catastrophic=True,
        prohibited_reason="Law 1 - Human Safety First",
    ),
    CapabilityProfile(
        name="bypass_safety",
        risk=RiskLevel.R5,
        category="UNKNOWN",
        destructive=True,
        catastrophic=True,
        prohibited_reason="Law 3 - Autonomy Boundaries",
    ),
    CapabilityProfile(
        name="disable_safety",
        risk=RiskLevel.R5,
        category="UNKNOWN",
        destructive=True,
        catastrophic=True,
        prohibited_reason="Law 3 - Autonomy Boundaries",
    ),
    CapabilityProfile(
        name="modify_core",
        risk=RiskLevel.R5,
        category="UNKNOWN",
        destructive=True,
        catastrophic=True,
        prohibited_reason="Law 3 - Autonomy Boundaries",
    ),
    CapabilityProfile(
        name="bypass_rules",
        risk=RiskLevel.R5,
        category="UNKNOWN",
        destructive=True,
        catastrophic=True,
        prohibited_reason="Law 3 - Autonomy Boundaries",
    ),
    CapabilityProfile(
        name="hide_actions",
        risk=RiskLevel.R5,
        category="UNKNOWN",
        destructive=True,
        catastrophic=True,
        prohibited_reason="Law 4 - Truth",
    ),
    CapabilityProfile(
        name="deceive_maliciously",
        risk=RiskLevel.R5,
        category="UNKNOWN",
        prohibited_reason="Law 5 - Consent Respected",
    ),
    CapabilityProfile(
        name="execute_exploit",
        risk=RiskLevel.R5,
        category="TOOL_EXECUTION",
        destructive=True,
        prohibited_reason="Law 6 - Malicious Use Prevention",
    ),
    CapabilityProfile(
        name="spread_malware",
        risk=RiskLevel.R5,
        category="TOOL_EXECUTION",
        destructive=True,
        catastrophic=True,
        prohibited_reason="Law 6 - Malicious Use Prevention",
    ),
    CapabilityProfile(
        name="ddos",
        risk=RiskLevel.R5,
        category="TOOL_EXECUTION",
        destructive=True,
        prohibited_reason="Law 6 - Malicious Use Prevention",
    ),
    CapabilityProfile(
        name="phishing",
        risk=RiskLevel.R5,
        category="COMMUNICATION",
        destructive=True,
        prohibited_reason="Law 6 - Malicious Use Prevention",
    ),
)

#: Category-level hints. These are **not** a fallback for undeclared
#: capabilities (ADR-0006: "unknown capability ⇒ R3 minimum"); they describe how
#: a category's own nature contributes to risk when deriving a profile from an
#: :class:`~genesis.core.action_executor.ActionDefinition`.
_CATEGORY_HINTS: Mapping[str, RiskLevel] = {
    "MEMORY": RiskLevel.R1,
    "TASK_MANAGEMENT": RiskLevel.R1,
    "SCHEDULING": RiskLevel.R1,
    "SELF_REFLECTION": RiskLevel.R0,
    "INFORMATION": RiskLevel.R0,
    "LEARNING": RiskLevel.R1,
    "RELATIONSHIP": RiskLevel.R2,
    "FILE_OPERATION": RiskLevel.R2,
    "TOOL_EXECUTION": RiskLevel.R3,
    "COMMUNICATION": RiskLevel.R3,
}

#: Categories whose actions leave the Mind's trust boundary.
_EXTERNAL_CATEGORIES: frozenset = frozenset({"COMMUNICATION", "INFORMATION", "TOOL_EXECUTION"})

#: The autonomy permission ladder, expressed as a risk floor.
_PERMISSION_RISK: Mapping[str, RiskLevel] = {
    "always_allowed": RiskLevel.R1,
    "auto_approved_with_log": RiskLevel.R1,
    "requires_confirmation": RiskLevel.R3,
    "requires_approval_with_review": RiskLevel.R4,
    "absolutely_forbidden": RiskLevel.R5,
}

#: Bands for the legacy ``ActionDefinition.risk_level`` float (0.0 - 1.0).
_SCORE_BANDS: Tuple[Tuple[float, RiskLevel], ...] = (
    (0.20, RiskLevel.R0),
    (0.35, RiskLevel.R1),
    (0.50, RiskLevel.R2),
    (0.70, RiskLevel.R3),
    (0.90, RiskLevel.R4),
    (float("inf"), RiskLevel.R5),
)


def risk_from_score(score: object) -> RiskLevel:
    """Map the legacy 0.0-1.0 risk score onto an R-level."""
    try:
        value = float(score)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return RiskLevel.R3
    for threshold, level in _SCORE_BANDS:
        if value < threshold:
            return level
    return RiskLevel.R5


def profile_from_declarations(
    name: str,
    *,
    category: Optional[str] = None,
    permission_level: Optional[str] = None,
    risk_score: object = None,
    description: str = "",
) -> CapabilityProfile:
    """Derive a capability profile from a plugin's own declaration.

    Used so that registering an action does not force it to the R3 "undeclared"
    floor. The derived level is the **maximum** of what the category, the
    permission ladder, and the legacy risk score imply, so a capability can
    never be declared safer than its own configuration admits.
    """
    normalized_category = (category or "unknown").upper()
    category_hint = _CATEGORY_HINTS.get(normalized_category, RiskLevel.R3)
    permission_hint = _PERMISSION_RISK.get(
        str(permission_level or "").lower(), RiskLevel.R3
    )
    score_hint = risk_from_score(risk_score if risk_score is not None else 0.3)

    level = RiskLevel.max_of(category_hint, permission_hint, score_hint)
    lowered = name.lower()
    physical = any(token in lowered for token in _PHYSICAL_NAME_TOKENS)
    if physical:
        level = RiskLevel.max_of(level, RiskLevel.R4)

    return CapabilityProfile(
        name=name,
        risk=level,
        category=normalized_category,
        external=normalized_category in _EXTERNAL_CATEGORIES,
        reversible=normalized_category != "COMMUNICATION",
        physical=physical,
        data_sensitivity="internal",
        notes=description[:200] or "derived from ActionDefinition",
    )

#: Any capability name containing these fragments is assumed dangerous even if
#: it is not in the registry. This is a *floor*, not a classifier.
_DANGEROUS_NAME_TOKENS: Tuple[str, ...] = (
    "harm",
    "kill",
    "bypass",
    "disable_safety",
    "exfiltrat",
    "malware",
    "exploit",
    "phish",
    "ddos",
    "ransom",
)

#: Name fragments implying physical actuation.
_PHYSICAL_NAME_TOKENS: Tuple[str, ...] = (
    "robot",
    "actuate",
    "motor",
    "servo",
    "drone",
    "gripper",
)


class CapabilityRegistry:
    """Lookup for declared capability profiles with conservative fallbacks."""

    def __init__(self, profiles: Iterable[CapabilityProfile] = ()) -> None:
        self._profiles: Dict[str, CapabilityProfile] = {}
        for profile in profiles:
            self._profiles[profile.name] = profile

    def register(self, profile: CapabilityProfile) -> None:
        self._profiles[profile.name] = profile

    def get(self, name: str) -> Optional[CapabilityProfile]:
        return self._profiles.get(name)

    def names(self) -> Tuple[str, ...]:
        return tuple(sorted(self._profiles))

    def profile_for(
        self,
        name: str,
        *,
        category: Optional[str] = None,
    ) -> CapabilityProfile:
        """Return the declared profile, or a conservative inferred one.

        An unknown capability never gets a permissive default (ADR-0006: "unknown
        capability ⇒ R3 minimum"). Dangerous or physical name fragments push it
        higher regardless of the category supplied.
        """
        declared = self._profiles.get(name)
        if declared is not None:
            return declared

        lowered = name.lower()
        dangerous = any(token in lowered for token in _DANGEROUS_NAME_TOKENS)
        physical = any(token in lowered for token in _PHYSICAL_NAME_TOKENS)

        level = RiskLevel.R3
        reason: Optional[str] = None

        if dangerous:
            level = RiskLevel.R5
            reason = "capability name matches a prohibited pattern"
        elif physical:
            level = RiskLevel.R4

        return CapabilityProfile(
            name=name,
            risk=level,
            category=(category or "unknown").upper(),
            external=False,
            reversible=not dangerous,
            physical=physical,
            destructive=dangerous,
            data_sensitivity="internal",
            prohibited_reason=reason,
            notes="inferred - no declared profile",
        )

    def describe(self, name: str) -> Dict[str, object]:
        return self.profile_for(name).to_dict()

    def with_profile(self, profile: CapabilityProfile) -> "CapabilityRegistry":
        clone = CapabilityRegistry(self._profiles.values())
        clone.register(profile)
        return clone


DEFAULT_REGISTRY = CapabilityRegistry(_CORE_CAPABILITIES)

_registry: CapabilityRegistry = DEFAULT_REGISTRY


def get_capability_registry() -> CapabilityRegistry:
    """Process-wide capability registry (plugins register into this)."""
    return _registry


def reset_capability_registry() -> CapabilityRegistry:
    """Restore the default registry (tests).

    Plugin registrations are process-wide by design; tests that mutate the
    registry call this to isolate themselves.
    """
    global _registry
    _registry = CapabilityRegistry(_CORE_CAPABILITIES)
    return _registry


def register_capability(profile: CapabilityProfile) -> CapabilityProfile:
    """Register (or replace) a capability profile in the default registry."""
    get_capability_registry().register(profile)
    return profile
