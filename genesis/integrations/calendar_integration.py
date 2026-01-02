"""Google Calendar integration."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from genesis.integrations.base import Integration, IntegrationType

logger = logging.getLogger(__name__)


class CalendarIntegration(Integration):
    """Google Calendar integration."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not GOOGLE_AVAILABLE:
            logger.error("Google API client not installed. Install with: pip install google-api-python-client")
            self.enabled = False
            return
        try:
            creds = Credentials.from_authorized_user_file(
                config['token_path'],
                ['https://www.googleapis.com/auth/calendar']
            )
            self.service = build('calendar', 'v3', credentials=creds)
            self.calendar_id = config.get('calendar_id', 'primary')
            self.events_created = 0
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar: {e}")
            self.enabled = False

    async def send(
        self,
        message: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        **kwargs
    ) -> bool:
        if not self.enabled:
            return False
        try:
            if not end_time:
                end_time = start_time + timedelta(hours=1)

            event = {
                'summary': kwargs.get('title', 'Genesis Event'),
                'description': message,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
            }

            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            self.events_created += 1
            logger.info(f"[Done] Calendar event created: {created_event['id']}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create calendar event: {e}")
            return False

    async def receive(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        try:
            now = datetime.utcnow()
            time_max = now + timedelta(days=days_ahead)

            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            parsed_events = []
            for event in events:
                parsed_events.append({
                    'id': event['id'],
                    'title': event.get('summary'),
                    'description': event.get('description'),
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                })

            logger.info(f"📅 Found {len(parsed_events)} upcoming events")
            return parsed_events
        except Exception as e:
            logger.error(f"❌ Failed to get calendar events: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        return {
            'type': IntegrationType.CALENDAR,
            'enabled': self.enabled,
            'calendar_id': self.calendar_id,
            'events_created': self.events_created
        }
