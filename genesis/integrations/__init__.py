"""Genesis Integrations - Real-world connections for Minds.

This package provides integrations for Minds to interact with:
- Email (SMTP/IMAP)
- SMS (Twilio)
- Push Notifications (Firebase, APNS)
- Chat platforms (Slack, Discord)
- Calendars (Google Calendar)
- And more...

Example:
    from genesis.integrations import IntegrationManager, IntegrationType
    from genesis.integrations.email_integration import EmailIntegration

    # Add to Mind
    mind.integrations = IntegrationManager(mind)

    # Register email
    mind.integrations.register(
        IntegrationType.EMAIL,
        EmailIntegration(config)
    )

    # Send email
    await mind.integrations.send(
        IntegrationType.EMAIL,
        message="Hello!",
        to="user@example.com"
    )
"""

from genesis.integrations.base import (
    Integration,
    IntegrationType,
    IntegrationManager
)

__all__ = [
    'Integration',
    'IntegrationType',
    'IntegrationManager'
]
