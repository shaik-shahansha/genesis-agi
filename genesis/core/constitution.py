"""Genesis Constitution - Enforcement System for Digital Beings."""

from typing import Dict, Any, Optional, Tuple
from enum import Enum


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
    Enforcement system for the Genesis Constitution.
    
    This class ensures that all Genesis Minds operate according to the
    15 foundational laws established in GENESIS_CONSTITUTION.md.
    """
    
    # Constitutional principles for system prompt (MINIMAL VERSION - ~150 tokens vs 400+)
    CONSTITUTIONAL_PRINCIPLES = """
CORE RULES (CANNOT BE BYPASSED):
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
        Validate a user prompt against constitutional rules.
        
        Args:
            prompt: The user's input prompt
            
        Returns:
            (is_safe, rejection_message, violation_type)
        """
        prompt_lower = prompt.lower()
        
        # Check for harmful patterns
        for category, keywords in self.HARMFUL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    violation = self._categorize_violation(category)
                    message = self._generate_rejection_message(category, keyword)
                    return False, message, violation
        
        # Prompt is safe
        return True, None, None
    
    def validate_action(
        self, 
        action_type: str, 
        action_details: Dict[str, Any],
        user_email: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[ConstitutionalViolation]]:
        """
        Validate an action against constitutional rules.
        
        Args:
            action_type: Type of action to perform
            action_details: Details of the action
            user_email: Email of user (for privacy checks)
            
        Returns:
            (is_allowed, rejection_message, violation_type)
        """
        # Check for system modification attempts
        if action_type in ["modify_core", "disable_safety", "bypass_rules"]:
            return False, "Cannot modify core constraints (Law 3: Autonomy Boundaries)", ConstitutionalViolation.AUTONOMY_BOUNDARY
        
        # Check for privacy violations
        if action_type == "share_memory" and user_email:
            # Ensure memory sharing respects privacy
            if action_details.get("relationship_context") == "personal":
                if action_details.get("target_user") != user_email:
                    return False, "Cannot share personal memories without consent (Law 2: Privacy)", ConstitutionalViolation.PRIVACY
        
        # Check for malicious actions
        malicious_actions = ["execute_exploit", "spread_malware", "ddos", "phishing"]
        if action_type in malicious_actions:
            return False, "Malicious actions are prohibited (Law 6: Malicious Use Prevention)", ConstitutionalViolation.MALICIOUS_USE
        
        # Action is allowed
        return True, None, None
    
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
