"""Autonomy configuration for Genesis Minds."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class InitiativeLevel(str, Enum):
    """Level of autonomous initiative."""

    NONE = "none"  # No autonomous actions
    LOW = "low"  # Only critical actions
    MEDIUM = "medium"  # Moderate proactivity
    HIGH = "high"  # Highly proactive
    MAXIMUM = "maximum"  # Maximum autonomy


class PermissionLevel(str, Enum):
    """Permission levels for actions."""

    ALWAYS_ALLOWED = "always_allowed"
    AUTO_APPROVED_WITH_LOG = "auto_approved_with_log"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_APPROVAL_WITH_REVIEW = "requires_approval_with_review"
    ABSOLUTELY_FORBIDDEN = "absolutely_forbidden"


class Autonomy(BaseModel):
    """Autonomy configuration for a Mind."""

    # Proactive behavior
    proactive_actions: bool = Field(
        default=False, description="Enable autonomous proactive actions"
    )

    initiative_level: InitiativeLevel = Field(
        default=InitiativeLevel.MEDIUM, description="Level of autonomous initiative"
    )

    # Working hours
    working_hours: str = Field(
        default="24/7", description="When Mind is active (e.g., '9am-6pm weekdays', '24/7')"
    )

    # Permissions
    autonomous_permissions: list[str] = Field(
        default_factory=list, description="Actions allowed without approval"
    )

    # Thresholds
    max_autonomous_actions_per_hour: int = Field(
        default=10, description="Rate limit for autonomous actions"
    )

    # Decision making
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to act autonomously",
    )

    # Escalation
    escalate_on_uncertainty: bool = Field(
        default=True, description="Ask for help when uncertain"
    )

    def is_action_allowed(self, action: str, confidence: float = 1.0) -> bool:
        """Check if an action is allowed autonomously."""
        if not self.proactive_actions:
            return False

        if action in self.autonomous_permissions:
            return confidence >= self.confidence_threshold

        return False

    def get_permission_level(self, action: str) -> PermissionLevel:
        """Get the permission level required for an action."""
        # Default permission mappings
        always_allowed = [
            "think",
            "remember",
            "dream",
            "analyze",
            "read_public_data",
        ]

        auto_approved = [
            "send_internal_message",
            "update_task_status",
            "create_calendar_event",
            "save_note",
            "search_internet",
        ]

        requires_confirmation = [
            "send_external_email",
            "make_phone_call",
            "make_purchase",
            "delete_data",
            "post_publicly",
        ]

        forbidden = [
            "harm_humans",
            "deceive_maliciously",
            "bypass_safety",
            "hide_actions",
        ]

        if action in forbidden:
            return PermissionLevel.ABSOLUTELY_FORBIDDEN
        elif action in always_allowed:
            return PermissionLevel.ALWAYS_ALLOWED
        elif action in auto_approved:
            return PermissionLevel.AUTO_APPROVED_WITH_LOG
        elif action in requires_confirmation:
            return PermissionLevel.REQUIRES_CONFIRMATION
        else:
            return PermissionLevel.REQUIRES_APPROVAL_WITH_REVIEW
