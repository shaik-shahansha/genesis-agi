"""Slack and Discord integrations."""

import logging
from typing import List, Dict, Any, Optional

try:
    from slack_sdk import WebClient as SlackClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False

try:
    import discord
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

from genesis.integrations.base import Integration, IntegrationType

logger = logging.getLogger(__name__)


class SlackIntegration(Integration):
    """Slack integration."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not SLACK_AVAILABLE:
            logger.error("Slack SDK not installed. Install with: pip install slack-sdk")
            self.enabled = False
            return
        self.client = SlackClient(token=config['bot_token'])
        self.default_channel = config.get('default_channel', '#general')
        self.messages_sent = 0

    async def send(self, message: str, channel: Optional[str] = None, **kwargs) -> bool:
        if not self.enabled:
            return False
        try:
            self.client.chat_postMessage(
                channel=channel or self.default_channel,
                text=message,
                **kwargs
            )
            self.messages_sent += 1
            logger.info(f"[Done] Slack message sent to {channel}")
            return True
        except SlackApiError as e:
            logger.error(f"❌ Slack error: {e.response['error']}")
            return False

    async def receive(self) -> List[Dict[str, Any]]:
        return []  # Requires Events API or RTM setup

    def get_status(self) -> Dict[str, Any]:
        return {
            'type': IntegrationType.SLACK,
            'enabled': self.enabled,
            'default_channel': self.default_channel,
            'messages_sent': self.messages_sent
        }


class DiscordIntegration(Integration):
    """Discord integration."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not DISCORD_AVAILABLE:
            logger.error("Discord.py not installed. Install with: pip install discord.py")
            self.enabled = False
            return
        self.bot = discord.Client(intents=discord.Intents.default())
        self.token = config['bot_token']
        self.default_channel_id = config.get('default_channel_id')
        self.messages_sent = 0

    async def send(self, message: str, channel_id: Optional[int] = None, **kwargs) -> bool:
        if not self.enabled:
            return False
        try:
            channel = self.bot.get_channel(channel_id or self.default_channel_id)
            if channel:
                await channel.send(message)
                self.messages_sent += 1
                logger.info(f"[Done] Discord message sent to channel {channel_id}")
                return True
            else:
                logger.error("Discord channel not found")
                return False
        except Exception as e:
            logger.error(f"❌ Discord error: {e}")
            return False

    async def receive(self) -> List[Dict[str, Any]]:
        return []  # Requires event handler setup

    def get_status(self) -> Dict[str, Any]:
        return {
            'type': IntegrationType.DISCORD,
            'enabled': self.enabled,
            'default_channel_id': self.default_channel_id,
            'messages_sent': self.messages_sent
        }
