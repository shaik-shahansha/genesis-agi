"""Base integration framework for real-world connections."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class IntegrationType(str, Enum):
    """Types of integrations."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push_notification"
    CALENDAR = "calendar"
    SLACK = "slack"
    DISCORD = "discord"
    GITHUB = "github"
    TWITTER = "twitter"
    WEBHOOK = "webhook"
    MCP = "mcp"  # Model Context Protocol


class Integration(ABC):
    """Base class for all integrations."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize integration with config.

        Args:
            config: Integration configuration dictionary
        """
        self.config = config
        self.enabled = config.get('enabled', True)

    @abstractmethod
    async def send(self, message: str, **kwargs) -> bool:
        """Send a message/notification.

        Args:
            message: Message content
            **kwargs: Integration-specific parameters

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def receive(self) -> List[Dict[str, Any]]:
        """Receive messages/notifications.

        Returns:
            List of received messages
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get integration status.

        Returns:
            Status dictionary
        """
        pass


class IntegrationManager:
    """Manages all integrations for a Mind."""

    def __init__(self, mind):
        """Initialize integration manager.

        Args:
            mind: Mind instance
        """
        self.mind = mind
        self.integrations: Dict[IntegrationType, Integration] = {}

    def register(self, integration_type: IntegrationType, integration: Integration):
        """Register an integration.

        Args:
            integration_type: Type of integration
            integration: Integration instance
        """
        self.integrations[integration_type] = integration
        logger.info(f"Registered {integration_type} integration for {self.mind.name}")

    def unregister(self, integration_type: IntegrationType):
        """Unregister an integration.

        Args:
            integration_type: Type of integration to remove
        """
        if integration_type in self.integrations:
            del self.integrations[integration_type]
            logger.info(f"Unregistered {integration_type} integration")

    async def send(
        self,
        integration_type: IntegrationType,
        message: str,
        **kwargs
    ) -> bool:
        """Send via specific integration.

        Args:
            integration_type: Integration to use
            message: Message to send
            **kwargs: Integration-specific parameters

        Returns:
            True if successful
        """
        integration = self.integrations.get(integration_type)
        if not integration or not integration.enabled:
            logger.warning(f"{integration_type} integration not available")
            return False

        try:
            result = await integration.send(message, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Failed to send via {integration_type}: {e}")
            return False

    async def check_all(self) -> Dict[IntegrationType, List[Dict[str, Any]]]:
        """Check all integrations for new messages.

        Returns:
            Dictionary mapping integration type to received messages
        """
        results = {}

        for int_type, integration in self.integrations.items():
            if integration.enabled:
                try:
                    messages = await integration.receive()
                    if messages:
                        results[int_type] = messages
                        logger.info(f"Received {len(messages)} new {int_type} messages")
                except Exception as e:
                    logger.error(f"Error checking {int_type}: {e}")

        return results

    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all integrations.

        Returns:
            Dictionary with all integration statuses
        """
        return {
            int_type.value: integration.get_status()
            for int_type, integration in self.integrations.items()
        }

    def get_enabled_integrations(self) -> List[IntegrationType]:
        """Get list of enabled integrations.

        Returns:
            List of enabled integration types
        """
        return [
            int_type
            for int_type, integration in self.integrations.items()
            if integration.enabled
        ]
