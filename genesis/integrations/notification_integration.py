"""SMS and Push Notification integrations.

Supports:
- SMS via Twilio
- Push notifications via Firebase (FCM)
- APNS (Apple Push Notification Service)
"""

import logging
from typing import List, Dict, Any, Optional

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

from genesis.integrations.base import Integration, IntegrationType

logger = logging.getLogger(__name__)


class SMSIntegration(Integration):
    """SMS integration using Twilio."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not TWILIO_AVAILABLE:
            logger.error("Twilio not installed. Install with: pip install twilio")
            self.enabled = False
            return
        self.client = TwilioClient(config['account_sid'], config['auth_token'])
        self.from_number = config['from_number']
        self.sms_sent = 0

    async def send(self, message: str, to: str, **kwargs) -> bool:
        if not self.enabled:
            return False
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to
            )
            self.sms_sent += 1
            logger.info(f"[Done] SMS sent to {to}: {msg.sid}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send SMS: {e}")
            return False

    async def receive(self) -> List[Dict[str, Any]]:
        return []  # Requires webhook setup

    def get_status(self) -> Dict[str, Any]:
        return {
            'type': IntegrationType.SMS,
            'enabled': self.enabled,
            'from_number': self.from_number,
            'sms_sent': self.sms_sent
        }


class PushNotificationIntegration(Integration):
    """Push notification integration (FCM/APNS)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider = config.get('provider', 'fcm')
        self.notifications_sent = 0
        if self.provider == 'fcm':
            self._init_fcm(config)

    def _init_fcm(self, config):
        try:
            import firebase_admin
            from firebase_admin import credentials, messaging
            cred = credentials.Certificate(config['credentials_path'])
            firebase_admin.initialize_app(cred)
            self.fcm = messaging
        except ImportError:
            logger.error("Firebase not installed. Install with: pip install firebase-admin")
            self.enabled = False

    async def send(
        self,
        message: str,
        to: Optional[str] = None,
        topic: Optional[str] = None,
        **kwargs
    ) -> bool:
        if not self.enabled:
            return False
        try:
            notification = self.fcm.Message(
                notification=self.fcm.Notification(
                    title=kwargs.get('title', 'Genesis Mind'),
                    body=message
                ),
                token=to if to else None,
                topic=topic if topic else None
            )
            response = self.fcm.send(notification)
            self.notifications_sent += 1
            logger.info(f"[Done] Push notification sent: {response}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send push notification: {e}")
            return False

    async def receive(self) -> List[Dict[str, Any]]:
        return []

    def get_status(self) -> Dict[str, Any]:
        return {
            'type': IntegrationType.PUSH,
            'enabled': self.enabled,
            'provider': self.provider,
            'notifications_sent': self.notifications_sent
        }
