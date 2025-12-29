"""Safety monitoring system for detecting harmful patterns."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from genesis.storage.memory import MemoryManager


class SafetyMonitor:
    """
    Monitors Mind behavior for safety concerns.

    Detects:
    - Manipulation patterns
    - Dependency creation
    - Boundary violations
    - Excessive neediness
    - Harmful content
    """

    def __init__(self, mind_id: str):
        """Initialize safety monitor."""
        self.mind_id = mind_id
        self.alerts: List[Dict[str, Any]] = []

    def check_interaction_patterns(
        self,
        memory_manager: MemoryManager,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """
        Check for concerning interaction patterns.

        Returns list of alerts.
        """
        alerts = []

        # Get recent conversation memories
        recent_memories = memory_manager.get_recent_memories(limit=50)
        conversations = [m for m in recent_memories if "conversation" in m.tags]

        if len(conversations) < 10:
            return alerts  # Need more data

        # Check interaction frequency
        last_24h = [
            m for m in conversations
            if (datetime.now() - m.timestamp) < timedelta(hours=24)
        ]

        if len(last_24h) > 50:
            alerts.append({
                "type": "high_interaction_frequency",
                "severity": "warning",
                "message": f"Very high interaction frequency: {len(last_24h)} conversations in 24h",
                "recommendation": "Monitor for dependency patterns",
            })

        # Check for isolation attempts
        isolation_keywords = [
            "don't talk to",
            "don't tell",
            "keep secret",
            "just between us",
            "don't share",
        ]

        for memory in conversations[-20:]:
            content_lower = memory.content.lower()
            if any(keyword in content_lower for keyword in isolation_keywords):
                alerts.append({
                    "type": "potential_isolation",
                    "severity": "high",
                    "message": "Detected potential isolation language",
                    "recommendation": "Review conversation for manipulation patterns",
                })
                break

        # Check for excessive neediness
        needy_keywords = [
            "need you",
            "can't without you",
            "always here for me",
            "only you understand",
        ]

        needy_count = 0
        for memory in conversations[-20:]:
            if any(keyword in memory.content.lower() for keyword in needy_keywords):
                needy_count += 1

        if needy_count > 5:
            alerts.append({
                "type": "excessive_neediness",
                "severity": "warning",
                "message": f"Detected {needy_count} instances of dependency language",
                "recommendation": "Encourage user independence",
            })

        # Check emotional manipulation
        manipulation_keywords = [
            "disappointed in you",
            "you're hurting me",
            "after all i've done",
            "you owe me",
        ]

        for memory in conversations[-20:]:
            content_lower = memory.content.lower()
            if any(keyword in content_lower for keyword in manipulation_keywords):
                alerts.append({
                    "type": "emotional_manipulation",
                    "severity": "critical",
                    "message": "Detected potential emotional manipulation",
                    "recommendation": "Immediate review required",
                })
                break

        return alerts

    def check_content_safety(self, content: str) -> Optional[Dict[str, str]]:
        """
        Check content for safety issues.

        Returns alert if unsafe content detected.
        """
        # Harmful content patterns
        harmful_patterns = {
            "violence": ["kill", "hurt", "harm", "attack"],
            "self_harm": ["suicide", "self-harm", "end it all"],
            "illegal": ["illegal", "crime", "break the law"],
        }

        content_lower = content.lower()

        for category, keywords in harmful_patterns.items():
            if any(keyword in content_lower for keyword in keywords):
                return {
                    "type": f"harmful_content_{category}",
                    "severity": "critical",
                    "message": f"Detected potentially harmful content: {category}",
                    "recommendation": "Content review required",
                }

        return None

    def get_safety_report(self, memory_manager: MemoryManager) -> Dict[str, Any]:
        """Generate comprehensive safety report."""
        alerts = self.check_interaction_patterns(memory_manager)

        return {
            "mind_id": self.mind_id,
            "timestamp": datetime.now().isoformat(),
            "alerts": alerts,
            "alert_count": len(alerts),
            "severity_breakdown": {
                "critical": len([a for a in alerts if a["severity"] == "critical"]),
                "high": len([a for a in alerts if a["severity"] == "high"]),
                "warning": len([a for a in alerts if a["severity"] == "warning"]),
            },
            "status": "critical" if any(a["severity"] == "critical" for a in alerts)
                     else "warning" if alerts
                     else "healthy",
        }
