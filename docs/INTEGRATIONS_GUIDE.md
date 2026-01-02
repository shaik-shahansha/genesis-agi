# Genesis AGI - Integrations Guide

Complete guide for connecting your Minds to real-world services.

## Overview

Genesis v0.3.0+ supports real-world integrations including:

- **Email** (SMTP/IMAP) - Send and receive emails autonomously
- **Slack** - Post messages to channels
- **Discord** - Bot integration for servers
- **SMS** (Twilio) - Send text messages
- **Push Notifications** (FCM/APNS) - Mobile notifications
- **Calendar** (Google Calendar) - Manage events

## Architecture

```python
from genesis.integrations import IntegrationManager, IntegrationType
from genesis.integrations.email_integration import EmailIntegration

# Integrations are managed per-Mind
mind.integrations = IntegrationManager(mind)

# Register integration
mind.integrations.register(IntegrationType.EMAIL, EmailIntegration(config))

# Use integration
await mind.integrations.send(
    IntegrationType.EMAIL,
    message="Hello!",
    to="user@example.com"
)
```

## Email Integration

### Setup

1. **Gmail Setup** (Recommended for testing):

```bash
# Enable 2FA on your Google account
# Generate App Password: https://myaccount.google.com/apppasswords
```

2. **Configuration**:

```python
email_config = {
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 587,
    'imap_host': 'imap.gmail.com',
    'imap_port': 993,
    'email': 'your-mind@gmail.com',
    'password': 'your-app-password',
    'enabled': True,
    'check_interval': 300,  # Check every 5 minutes
    'mark_as_read': True
}
```

3. **Register with Mind**:

```python
from genesis.integrations import IntegrationManager, IntegrationType
from genesis.integrations.email_integration import EmailIntegration

mind.integrations = IntegrationManager(mind)
mind.integrations.register(
    IntegrationType.EMAIL,
    EmailIntegration(email_config)
)
```

### Sending Emails

```python
# Send simple email
await mind.integrations.send(
    IntegrationType.EMAIL,
    message="Hello from Genesis Mind!",
    to="recipient@example.com",
    subject="Greetings"
)

# Send HTML email
await mind.integrations.send(
    IntegrationType.EMAIL,
    message="<h1>Hello!</h1><p>This is HTML</p>",
    to="recipient@example.com",
    subject="HTML Email",
    html=True
)

# Send with CC/BCC
await mind.integrations.send(
    IntegrationType.EMAIL,
    message="Team update...",
    to="manager@example.com",
    cc=["team1@example.com", "team2@example.com"],
    bcc=["archive@example.com"],
    subject="Weekly Report"
)
```

### Receiving Emails

```python
# Check for new emails
emails = await mind.integrations.integrations[IntegrationType.EMAIL].receive(limit=10)

for email in emails:
    print(f"From: {email['from']}")
    print(f"Subject: {email['subject']}")
    print(f"Body: {email['body']}")

    # Process and respond
    response = await mind.think(f"Respond to: {email['body']}")
    await mind.integrations.send(
        IntegrationType.EMAIL,
        message=response,
        to=email['from'],
        subject=f"Re: {email['subject']}"
    )
```

## Slack Integration

### Setup

1. **Create Slack App**:
   - Go to https://api.slack.com/apps
   - Create New App → From scratch
   - Add Bot Token Scopes: `chat:write`, `channels:read`
   - Install to Workspace
   - Copy Bot User OAuth Token

2. **Configuration**:

```python
slack_config = {
    'bot_token': 'xoxb-your-bot-token',
    'default_channel': '#general',
    'enabled': True
}
```

3. **Register with Mind**:

```python
from genesis.integrations.chat_integration import SlackIntegration

mind.integrations.register(
    IntegrationType.SLACK,
    SlackIntegration(slack_config)
)
```

### Usage

```python
# Post to default channel
await mind.integrations.send(
    IntegrationType.SLACK,
    message="🤖 Mind is now online and monitoring"
)

# Post to specific channel
await mind.integrations.send(
    IntegrationType.SLACK,
    message="Deployment successful!",
    channel="#deployments"
)

# Rich formatting
await mind.integrations.send(
    IntegrationType.SLACK,
    message="*Bold* and _italic_ text with `code`",
    channel="#general"
)
```

## Discord Integration

### Setup

1. **Create Discord Bot**:
   - Go to https://discord.com/developers/applications
   - New Application → Bot → Add Bot
   - Copy Token
   - Enable necessary intents
   - Invite bot to server

2. **Configuration**:

```python
discord_config = {
    'bot_token': 'your-bot-token',
    'default_channel_id': 123456789012345678,
    'enabled': True
}
```

3. **Register**:

```python
from genesis.integrations.chat_integration import DiscordIntegration

mind.integrations.register(
    IntegrationType.DISCORD,
    DiscordIntegration(discord_config)
)
```

## SMS Integration (Twilio)

### Setup

1. **Twilio Account**:
   - Sign up at https://www.twilio.com/
   - Get Account SID and Auth Token
   - Get a Twilio phone number

2. **Configuration**:

```python
sms_config = {
    'account_sid': 'your-account-sid',
    'auth_token': 'your-auth-token',
    'from_number': '+1234567890',
    'enabled': True
}
```

3. **Usage**:

```python
from genesis.integrations.notification_integration import SMSIntegration

mind.integrations.register(
    IntegrationType.SMS,
    SMSIntegration(sms_config)
)

# Send SMS
await mind.integrations.send(
    IntegrationType.SMS,
    message="Alert: System status critical",
    to="+1234567890"
)
```

## Push Notifications (Firebase)

### Setup

1. **Firebase Project**:
   - Create project at https://console.firebase.google.com/
   - Add Android/iOS app
   - Download credentials JSON

2. **Configuration**:

```python
push_config = {
    'provider': 'fcm',
    'credentials_path': './credentials/firebase-credentials.json',
    'enabled': True
}
```

3. **Usage**:

```python
from genesis.integrations.notification_integration import PushNotificationIntegration

mind.integrations.register(
    IntegrationType.PUSH,
    PushNotificationIntegration(push_config)
)

# Send to specific device
await mind.integrations.send(
    IntegrationType.PUSH,
    message="Mind update: New thought recorded",
    to="device-token",
    title="Genesis Mind"
)

# Send to topic (all subscribers)
await mind.integrations.send(
    IntegrationType.PUSH,
    message="System-wide announcement",
    topic="all-users",
    title="Alert"
)
```

## Calendar Integration (Google Calendar)

### Setup

1. **Google Cloud Console**:
   - Create project at https://console.cloud.google.com/
   - Enable Google Calendar API
   - Create OAuth 2.0 credentials
   - Download credentials.json

2. **First-time Authentication**:

```bash
python examples/calendar_auth.py
# Follow OAuth flow in browser
# token.json will be created
```

3. **Configuration**:

```python
calendar_config = {
    'credentials_path': './credentials/credentials.json',
    'token_path': './credentials/token.json',
    'calendar_id': 'primary',
    'enabled': True
}
```

4. **Usage**:

```python
from genesis.integrations.calendar_integration import CalendarIntegration

mind.integrations.register(
    IntegrationType.CALENDAR,
    CalendarIntegration(calendar_config)
)

# Create event
await mind.integrations.send(
    IntegrationType.CALENDAR,
    message="Team Meeting",
    start_time="2025-01-15T10:00:00",
    end_time="2025-01-15T11:00:00",
    description="Discuss Q1 plans"
)

# Get upcoming events
events = await mind.integrations.integrations[IntegrationType.CALENDAR].receive(
    days_ahead=7
)
```

## Complete Example: Autonomous Email Assistant

```python
import asyncio
from datetime import datetime, timedelta
from genesis import Mind
from genesis.core.intelligence import Intelligence
from genesis.core.autonomy import Autonomy, InitiativeLevel
from genesis.integrations import IntegrationManager, IntegrationType
from genesis.integrations.email_integration import EmailIntegration
from genesis.integrations.chat_integration import SlackIntegration

async def main():
    # Create highly autonomous Mind
    mind = Mind.birth(
        name="EmailBot",
        intelligence=Intelligence(
            reasoning_model="groq/llama-3.3-70b-versatile"
        ),
        autonomy=Autonomy(
            proactive_actions=True,
            initiative_level=InitiativeLevel.HIGH,
            autonomous_permissions=[
                "send_email",
                "post_slack",
                "schedule_action"
            ]
        )
    )

    # Setup integrations
    mind.integrations = IntegrationManager(mind)

    # Email for communication
    mind.integrations.register(
        IntegrationType.EMAIL,
        EmailIntegration({
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'imap_host': 'imap.gmail.com',
            'imap_port': 993,
            'email': 'bot@example.com',
            'password': 'app-password',
            'enabled': True
        })
    )

    # Slack for notifications
    mind.integrations.register(
        IntegrationType.SLACK,
        SlackIntegration({
            'bot_token': 'xoxb-token',
            'default_channel': '#alerts',
            'enabled': True
        })
    )

    # Start 24/7 operation
    await mind.start_living()

    # Email checking loop
    while mind.action_scheduler.is_running:
        try:
            # Get new emails
            emails = await mind.integrations.integrations[
                IntegrationType.EMAIL
            ].receive(limit=5)

            for email in emails:
                # Mind decides how to respond
                decision = await mind.think(
                    f"I received an email from {email['from']}\\n"
                    f"Subject: {email['subject']}\\n"
                    f"Body: {email['body'][:500]}\\n\\n"
                    f"Should I respond? If yes, write a helpful response."
                )

                if "yes" in decision.lower():
                    # Send response
                    await mind.integrations.send(
                        IntegrationType.EMAIL,
                        message=decision,
                        to=email['from'],
                        subject=f"Re: {email['subject']}"
                    )

                    # Notify on Slack
                    await mind.integrations.send(
                        IntegrationType.SLACK,
                        message=f"📧 Responded to {email['from']}: {email['subject']}"
                    )

        except Exception as e:
            await mind.integrations.send(
                IntegrationType.SLACK,
                message=f"❌ Error processing emails: {e}"
            )

        # Check every 5 minutes
        await asyncio.sleep(300)

asyncio.run(main())
```

## Security Best Practices

1. **Credentials Management**:
   - Use environment variables for sensitive data
   - Never commit credentials to git
   - Rotate keys regularly

2. **Rate Limiting**:
   - Respect API rate limits
   - Implement exponential backoff
   - Monitor usage

3. **Permissions**:
   - Use least privilege principle
   - Only grant necessary scopes
   - Review autonomous_permissions list

4. **Error Handling**:
   - Always wrap integration calls in try-except
   - Log errors for debugging
   - Implement fallback strategies

## Monitoring Integration Health

```python
# Check integration status
status = mind.integrations.get_status(IntegrationType.EMAIL)
print(f"Emails sent: {status['emails_sent']}")
print(f"Emails received: {status['emails_received']}")

# List all integrations
for integration in mind.integrations.list_integrations():
    print(f"{integration['type']}: {'[Done]' if integration['enabled'] else '❌'}")
```

## Creating Custom Integrations

```python
from genesis.integrations.base import Integration, IntegrationType
from typing import List, Dict, Any

class CustomIntegration(Integration):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Initialize your service client
        self.client = YourServiceClient(config['api_key'])

    async def send(self, message: str, **kwargs) -> bool:
        """Send message to your service."""
        try:
            await self.client.post(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send: {e}")
            return False

    async def receive(self) -> List[Dict[str, Any]]:
        """Receive messages from your service."""
        return await self.client.get_messages()

    def get_status(self) -> Dict[str, Any]:
        """Return integration status."""
        return {
            'type': 'custom',
            'enabled': self.enabled,
            'messages_sent': self.messages_sent
        }

# Register custom integration
mind.integrations.register('custom', CustomIntegration(config))
```

## Troubleshooting

### Email not sending

```bash
# Test SMTP connection
python -m smtplib smtp.gmail.com 587

# Check credentials
# Verify app password is correct
# Check 2FA is enabled
```

### Slack bot not posting

```bash
# Check bot token
curl -H "Authorization: Bearer xoxb-your-token" \
  https://slack.com/api/auth.test

# Verify bot is in channel
# Check bot scopes
```

### Integration not responding

```python
# Check integration status
status = mind.integrations.integrations[IntegrationType.EMAIL].get_status()
print(status)

# Test connection
await mind.integrations.integrations[IntegrationType.EMAIL].send(
    message="Test",
    to="test@example.com"
)
```

## Support

- Documentation: https://shahansha.com/docs/integrations
- Examples: `/examples/complete_autonomous_mind.py`
- Issues: https://github.com/sshaik37/Genesis-AGI/issues

---

**Connect your Minds to the real world! 🌐**
