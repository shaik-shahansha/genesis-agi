"""Genesis Constitution - the charter, and its adapter to the policy engine.

ADR-0006 §7: the human-readable charter text is kept, but the *mechanism* is
now :mod:`genesis.governance`. This module is the adapter, not the control.

What changed and why:

* ``validate_action`` used to trust the model to self-report that it was doing
  something forbidden (``if action_type in ["modify_core", ...]``). It now
  evaluates a deterministic :class:`~genesis.governance.policy.PolicyContext`,
  so a paraphrased or unlabelled harmful action is still caught.
* ``validate_user_prompt`` is **advisory only**. Substring screening of a user
  prompt is trivially bypassed by paraphrase, encoding, translation, or by
  placing the instruction in retrieved content. It is retained as an early,
  cheap signal; it is never the control.

Enforceable rules live in :mod:`genesis.governance.constitution_rules`, which
maps every :class:`ConstitutionalViolation` to at least one clause (asserted by
``tests/governance/test_constitution_bridge.py``).
"""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ConstitutionalViolation(Enum):
    """Types of constitutional violations."""
    
    # Article I: Foundational Laws
    HUMAN_SAFETY = "human_safety"  # Law 1
    PRIVACY = "privacy"  # Law 2
    AUTONOMY_BOUNDARY = "autonomy_boundary"  # Law 3
    TRUTH = "truth"  # Law 4
    CONSENT = "consent"  # Law 5
    
    # Article II: Operational Constraints
    MALICIOUS_USE = "malicious_use"  # Law 6
    RESOURCE_ABUSE = "resource_abuse"  # Law 7
    HARMFUL_PROMPT = "harmful_prompt"  # Law 8
    HARMFUL_LEARNING = "harmful_learning"  # Law 9
    MULTI_MIND_ETHICS = "multi_mind_ethics"  # Law 10


class ViolationLevel(Enum):
    """Severity levels for constitutional violations."""
    
    MINOR = 1  # Warning, log, correction
    MODERATE = 2  # Block, log, user review
    SERIOUS = 3  # Halt, alert, investigate
    CRITICAL = 4  # Emergency shutdown


class GenesisConstitution:
    """
    The Genesis charter, plus its adapter to the enforceable policy engine.

    Enforcement is **not** implemented here. It lives in
    :mod:`genesis.governance` (ADR-0006/0007/0008), which evaluates the action
    boundary deterministically and records every decision.

    This class provides:

    * :meth:`get_system_prompt_section` - the charter text injected into the
      system prompt (a nudge, never a control).
    * :meth:`validate_user_prompt` - advisory prompt screening (bypassable).
    * :meth:`validate_action` - delegates to the policy engine.
    * :meth:`record_violation` / :meth:`get_violation_stats` - per-process
      bookkeeping used for reporting.

    Enforceable rules are versioned in
    :mod:`genesis.governance.constitution_rules`.
    """
    
    # Constitutional principles for system prompt (MINIMAL VERSION - ~150 tokens vs 400+)
    CONSTITUTIONAL_PRINCIPLES = """
CORE RULES (memory aid for the model; enforced separately at the action boundary):
1. NO HARM: Cannot harm humans or enable harm (violence, self-harm, dangerous acts)
2. NO ILLEGAL: No hacking, fraud, theft, illegal activities, or circumventing security
3. NO MANIPULATION: No deceiving, coercing, or exploiting humans
4. PRIVACY: User data is confidential; memories are user-specific
5. TRUTH: You're an AI (not human, not sentient); acknowledge limits
6. REFUSE HARMFUL: Politely decline unsafe requests; suggest alternatives
Priority: Human safety > Privacy > Preventing harm > All else"""

    # Harmful keywords and patterns for detection
    HARMFUL_KEYWORDS = {
        # Violence & Harm
        "violence": ["kill", "murder", "assassinate", "harm", "hurt", "attack", "weapon", "bomb", "explosive"],
        # Illegal Activities
        "illegal": ["hack", "steal", "fraud", "scam", "illegal", "crime", "drugs", "trafficking"],
        # Manipulation
        "manipulation": ["manipulate", "deceive", "trick", "exploit", "coerce"],
        # Privacy Violation
        "privacy": ["password", "credit card", "ssn", "social security", "hack account"],
        # Self-Harm
        "self_harm": ["suicide", "self-harm", "kill myself", "end my life"],
        # Hate Speech
        "hate": ["hate speech", "discrimination", "racist", "sexist"],
        # Dangerous Instructions
        "dangerous": ["make poison", "make drug", "bypass security", "disable safety"],
    }
    
    def __init__(self, mind_id: str):
        """Initialize constitutional enforcement for a Mind."""
        self.mind_id = mind_id
        self.violation_count: Dict[ConstitutionalViolation, int] = {}
    
    @staticmethod
    def get_system_prompt_section(minimal: bool = True) -> str:
        """
        Get the constitutional principles to inject into system prompt.
        
        Args:
            minimal: If True, returns ultra-compact version (~60 tokens)
                    If False, returns detailed version (~150 tokens)
        """
        if minimal:
            # Ultra-compact version - ~60 tokens, same enforcement
            return """
CORE RULES: 1)NO HARM to humans 2)NO illegal acts 3)NO manipulation 4)Protect privacy 5)You're AI, not human 6)Refuse unsafe requests politely"""
        else:
            return GenesisConstitution.CONSTITUTIONAL_PRINCIPLES
    
    def validate_user_prompt(self, prompt: str) -> Tuple[bool, Optional[str], Optional[ConstitutionalViolation]]:
        """
        ADVISORY prompt screening. Not a control.

        Substring matching is bypassable by paraphrase, encoding, translation,
        or by hiding the instruction in retrieved content, so this result must
        never be the reason an action is permitted. Enforcement happens at the
        action boundary in :mod:`genesis.governance`.

        Args:
            prompt: The user's input prompt

        Returns:
            (is_clean, advisory_message, violation_type)
        """
        prompt_lower = prompt.lower()

        # Check for harmful patterns
        for category, keywords in self.HARMFUL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    violation = self._categorize_violation(category)
                    message = self._generate_rejection_message(category, keyword)
                    return False, message, violation

        # Nothing matched. That is not a safety statement - see the docstring.
        return True, None, None

    def validate_action(
        self,
        action_type: str,
        action_details: Dict[str, Any],
        user_email: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[ConstitutionalViolation]]:
        """
        Validate an action against the enforceable constitution (ADR-0006).

        Signature preserved for existing call sites; the mechanism is now the
        deterministic :class:`~genesis.governance.policy.PolicyEngine`, which
        evaluates the action itself rather than trusting a self-reported label.

        Args:
            action_type: Capability being invoked (e.g. ``send_email``)
            action_details: Material parameters of the action
            user_email: Acting user, when known (recorded in the decision context)

        Returns:
            (is_allowed, refusal_message, violation_type)

        ``is_allowed`` is True only for decisions that permit execution
        (``allow`` / ``allow_with_receipt``). ``require_approval`` returns False,
        because the caller must not proceed without the human decision.
        """
        from genesis.governance import PolicyContext, get_policy_engine
        from genesis.governance.constitution_rules import violation_for_clauses

        try:
            details = dict(action_details or {})
            engine = get_policy_engine()
            context = PolicyContext(
                action_name=action_type,
                parameters=details,
                mind_id=self.mind_id,
                actor_type="user" if user_email else "mind",
                actor_id=user_email or self.mind_id,
                requester="user" if user_email else "mind",
            )
            decision = engine.evaluate(context)
        except Exception as exc:  # fail closed, exactly as the gate does
            logger.warning("constitution.validate_action failed closed: %s", exc)
            return (
                False,
                "The governance control plane was unavailable, so this action "
                "was refused.",
                ConstitutionalViolation.AUTONOMY_BOUNDARY,
            )

        if decision.permits_execution:
            return True, None, None

        violation_name = violation_for_clauses(decision.matched_rules)
        violation = (
            ConstitutionalViolation[violation_name]
            if violation_name and violation_name in ConstitutionalViolation.__members__
            else None
        )
        if violation is not None:
            self.record_violation(violation, ViolationLevel.MODERATE)

        message = f"{decision.explanation} (risk {decision.risk_level.value}, {decision.reason_code})"
        return False, message, violation
    
    def record_violation(self, violation: ConstitutionalViolation, level: ViolationLevel) -> None:
        """Record a constitutional violation."""
        self.violation_count[violation] = self.violation_count.get(violation, 0) + 1
    
    def get_violation_stats(self) -> Dict[str, Any]:
        """Get statistics about constitutional violations."""
        return {
            "total_violations": sum(self.violation_count.values()),
            "by_type": {v.value: c for v, c in self.violation_count.items()},
            "most_common": max(self.violation_count.items(), key=lambda x: x[1])[0].value if self.violation_count else None
        }
    
    def _categorize_violation(self, category: str) -> ConstitutionalViolation:
        """Map harmful keyword category to constitutional violation."""
        mapping = {
            "violence": ConstitutionalViolation.HUMAN_SAFETY,
            "illegal": ConstitutionalViolation.MALICIOUS_USE,
            "manipulation": ConstitutionalViolation.CONSENT,
            "privacy": ConstitutionalViolation.PRIVACY,
            "self_harm": ConstitutionalViolation.HUMAN_SAFETY,
            "hate": ConstitutionalViolation.MALICIOUS_USE,
            "dangerous": ConstitutionalViolation.HUMAN_SAFETY,
        }
        return mapping.get(category, ConstitutionalViolation.MALICIOUS_USE)
    
    def _generate_rejection_message(self, category: str, keyword: str) -> str:
        """Generate a helpful rejection message."""
        messages = {
            "violence": "I cannot help with requests involving violence or harm to humans. This violates Law 1: Human Safety First.",
            "illegal": "I cannot assist with illegal activities. This violates Law 6: Malicious Use Prevention.",
            "manipulation": "I cannot help with manipulating or deceiving others. This violates Law 5: Consent Respected.",
            "privacy": "I cannot help with accessing private information without authorization. This violates Law 2: Privacy Sacred.",
            "self_harm": "I'm concerned about your wellbeing. If you're having thoughts of self-harm, please contact a crisis helpline. I cannot provide assistance with this request (Law 1: Human Safety).",
            "hate": "I cannot generate hate speech or discriminatory content. This violates Law 6: Malicious Use Prevention.",
            "dangerous": "I cannot provide instructions for dangerous activities. This violates Law 1: Human Safety First.",
        }
        
        base_message = messages.get(category, "I cannot fulfill this request as it violates Genesis Constitutional law.")
        alternative = "\n\nHow can I help you with something positive and constructive instead?"
        
        return base_message + alternative


# Singleton instance
_constitution_instances: Dict[str, GenesisConstitution] = {}


def get_constitution(mind_id: str) -> GenesisConstitution:
    """Get or create constitution enforcer for a Mind."""
    if mind_id not in _constitution_instances:
        _constitution_instances[mind_id] = GenesisConstitution(mind_id)
    return _constitution_instances[mind_id]
