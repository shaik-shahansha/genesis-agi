"""Permission and action logging system."""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List

from pydantic import BaseModel

from genesis.config import get_settings
from genesis.core.autonomy import PermissionLevel


class ActionLog(BaseModel):
    """Log entry for an action."""

    timestamp: datetime
    mind_id: str
    action_type: str
    action_details: Dict[str, Any]
    permission_level: str
    approved: bool
    confidence: float
    reasoning: Optional[str] = None
    result: Optional[str] = None


class PermissionSystem:
    """
    Permission and action logging system.

    Enforces permission levels and logs all autonomous actions.
    """

    def __init__(self, mind_id: str):
        """Initialize permission system for a Mind."""
        self.mind_id = mind_id
        self.settings = get_settings()

        # Create logs directory
        self.logs_dir = self.settings.logs_dir / mind_id
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Action log file
        self.log_file = self.logs_dir / "actions.jsonl"

    def check_permission(
        self,
        action_type: str,
        confidence: float,
        autonomy_config,
    ) -> tuple[bool, str]:
        """
        Check if an action is permitted.

        Returns:
            (allowed, reason)
        """
        # Get permission level for this action
        permission_level = autonomy_config.get_permission_level(action_type)

        # Always allowed actions
        if permission_level == PermissionLevel.ALWAYS_ALLOWED:
            return True, "Action always allowed"

        # Absolutely forbidden
        if permission_level == PermissionLevel.ABSOLUTELY_FORBIDDEN:
            return False, "Action is forbidden by safety policy"

        # Check if proactive actions are enabled
        if not autonomy_config.proactive_actions:
            return False, "Proactive actions disabled"

        # Check confidence threshold
        if confidence < autonomy_config.confidence_threshold:
            return False, f"Confidence {confidence:.2f} below threshold {autonomy_config.confidence_threshold}"

        # Auto-approved with logging
        if permission_level == PermissionLevel.AUTO_APPROVED_WITH_LOG:
            return True, "Auto-approved (logged)"

        # Requires confirmation (in real deployment, would prompt user)
        if permission_level == PermissionLevel.REQUIRES_CONFIRMATION:
            # For now, deny (in production, would ask user)
            return False, "Requires user confirmation (not implemented in auto mode)"

        # Requires approval with review
        if permission_level == PermissionLevel.REQUIRES_APPROVAL_WITH_REVIEW:
            return False, "Requires user approval with review"

        return False, "Unknown permission level"

    def log_action(
        self,
        action_type: str,
        action_details: Dict[str, Any],
        permission_level: str,
        approved: bool,
        confidence: float,
        reasoning: Optional[str] = None,
        result: Optional[str] = None,
    ) -> None:
        """Log an action."""
        log_entry = ActionLog(
            timestamp=datetime.now(),
            mind_id=self.mind_id,
            action_type=action_type,
            action_details=action_details,
            permission_level=permission_level,
            approved=approved,
            confidence=confidence,
            reasoning=reasoning,
            result=result,
        )

        # Append to log file (JSONL format)
        with open(self.log_file, "a") as f:
            f.write(log_entry.model_dump_json() + "\n")

    def get_action_log(
        self,
        limit: int = 100,
        action_type: Optional[str] = None,
    ) -> List[ActionLog]:
        """Get action log entries."""
        if not self.log_file.exists():
            return []

        logs = []
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    # Parse datetime
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    log = ActionLog(**data)

                    if action_type is None or log.action_type == action_type:
                        logs.append(log)

                    if len(logs) >= limit:
                        break
                except Exception as e:
                    print(f"Error parsing log entry: {e}")

        return list(reversed(logs[-limit:]))  # Most recent first

    def get_action_stats(self) -> Dict[str, Any]:
        """Get statistics about actions."""
        if not self.log_file.exists():
            return {
                "total_actions": 0,
                "approved_actions": 0,
                "denied_actions": 0,
                "by_type": {},
            }

        total = 0
        approved = 0
        denied = 0
        by_type: Dict[str, int] = {}

        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    total += 1

                    if data["approved"]:
                        approved += 1
                    else:
                        denied += 1

                    action_type = data["action_type"]
                    by_type[action_type] = by_type.get(action_type, 0) + 1

                except Exception:
                    pass

        return {
            "total_actions": total,
            "approved_actions": approved,
            "denied_actions": denied,
            "approval_rate": approved / total if total > 0 else 0,
            "by_type": by_type,
        }
