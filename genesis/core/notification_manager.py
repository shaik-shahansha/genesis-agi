"""
Notification Manager - Proactive messaging system for Genesis Minds.

This module enables Minds to send notifications proactively to:
- Web playground (via WebSocket)
- Mobile apps (via push notifications)
- Email/SMS (via integrations)
- Other Minds (via Genesis World)

Features:
- Priority-based queue
- Multiple delivery channels
- Rate limiting
- Delivery confirmation
- Retry logic
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import json

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    WEBSOCKET = "websocket"       # Web playground real-time
    PUSH = "push"                 # Mobile push notification
    EMAIL = "email"               # Email delivery
    SMS = "sms"                   # SMS message
    GENESIS_WORLD = "genesis_world"  # Message to another Mind


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"                   # Can wait, batch delivery
    NORMAL = "normal"             # Standard delivery
    HIGH = "high"                 # Deliver soon
    URGENT = "urgent"             # Immediate delivery


@dataclass
class Notification:
    """A notification to be delivered."""
    notification_id: str
    mind_id: str
    mind_name: str
    recipient: str                # User email, GMID, phone, etc.
    channel: NotificationChannel
    priority: NotificationPriority
    title: str
    message: str
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_for: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Delivery tracking
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    error: Optional[str] = None


class NotificationManager:
    """
    Manages proactive notifications from Minds.
    
    This enables Minds to reach out proactively to users, creating
    the feeling of a living, caring digital being.
    """
    
    def __init__(self, mind_id: str, mind_name: str):
        """Initialize notification manager."""
        self.mind_id = mind_id
        self.mind_name = mind_name
        
        # Notification queue
        self.pending_notifications: deque = deque(maxlen=1000)
        self.delivered_notifications: List[Notification] = []
        
        # Active websocket connections (user_email -> websocket)
        self.websocket_connections: Dict[str, Any] = {}
        
        # Rate limiting (prevent spam)
        self.notification_count_by_hour: Dict[str, int] = {}  # hour_key -> count
        self.max_notifications_per_hour = 10
        
        # Background task
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the notification delivery loop."""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._delivery_loop())
        logger.info(f"[NOTIF] Notification manager started for {self.mind_name}")
    
    async def stop(self):
        """Stop the notification delivery loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"[NOTIF] Notification manager stopped for {self.mind_name}")
    
    def register_websocket(self, user_email: str, websocket: Any):
        """Register a websocket connection for real-time delivery."""
        print(f"\n{'='*80}")
        print(f"[NOTIFICATION_MANAGER] REGISTERING WEBSOCKET")
        print(f"[NOTIFICATION_MANAGER] Mind: {self.mind_name} ({self.mind_id})")
        print(f"[NOTIFICATION_MANAGER] User email: {user_email}")
        print(f"[NOTIFICATION_MANAGER] WebSocket object: {websocket}")
        print(f"[NOTIFICATION_MANAGER] Before registration - Active connections: {list(self.websocket_connections.keys())}")
        
        self.websocket_connections[user_email] = websocket
        
        print(f"[NOTIFICATION_MANAGER] After registration - Active connections: {list(self.websocket_connections.keys())}")
        print(f"[NOTIFICATION_MANAGER] ✓ WebSocket registered successfully!")
        print(f"{'='*80}\n")
        
        logger.info(f"[WS] WebSocket registered for {user_email} ({self.mind_name})")
    
    def unregister_websocket(self, user_email: str):
        """Unregister a websocket connection."""
        if user_email in self.websocket_connections:
            del self.websocket_connections[user_email]
            logger.info(f"[WS] WebSocket unregistered for {user_email} ({self.mind_name})")
    
    async def send_to_websocket(
        self,
        user_email: str,
        message_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Send a message directly to a connected WebSocket.
        
        This is for immediate delivery without queuing (e.g., progress updates).
        
        Args:
            user_email: User's email
            message_type: Type of message (e.g., 'task_progress', 'status_update')
            data: Message data
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            websocket = self.websocket_connections.get(user_email)
            print(f"[DEBUG NOTIF] Looking for WebSocket for {user_email}")
            print(f"[DEBUG NOTIF] Active connections: {list(self.websocket_connections.keys())}")
            
            if not websocket:
                print(f"[DEBUG NOTIF] No WebSocket found for {user_email}")
                return False
            
            print(f"[DEBUG NOTIF] WebSocket found, checking connection state...")
            
            # Check if websocket is still connected
            if hasattr(websocket, 'client_state') and websocket.client_state.value != 1:  # CONNECTED = 1
                print(f"[DEBUG NOTIF] WebSocket not connected (state={websocket.client_state.value})")
                self.unregister_websocket(user_email)
                return False
            
            print(f"[DEBUG NOTIF] Sending message type '{message_type}'...")
            
            await websocket.send_json({
                "type": message_type,
                "mind_id": self.mind_id,
                "mind_name": self.mind_name,
                **data
            })
            
            print(f"[DEBUG NOTIF] ✓ Message sent successfully!")
            
            return True
            
        except Exception as e:
            logger.debug(f"Could not send websocket message to {user_email}: {e}")
            # Clean up on error
            self.unregister_websocket(user_email)
            return False
    
    async def cleanup_connections(self):
        """Manually trigger cleanup of stale connections."""
        await self._cleanup_stale_connections()
    
    async def send_notification(
        self,
        recipient: str,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.WEBSOCKET,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_for: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Queue a notification for delivery.
        
        Args:
            recipient: User email, GMID, or phone number
            title: Notification title
            message: Notification message
            channel: Delivery channel
            priority: Priority level
            scheduled_for: Optional scheduled delivery time
            metadata: Additional context
            
        Returns:
            Notification ID if queued, None if rate limited
        """
        # Rate limiting check
        if not self._check_rate_limit():
            logger.warning(f"[WARNING] Rate limit exceeded for {self.mind_name}")
            return None
        
        # Create notification
        import uuid
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            mind_id=self.mind_id,
            mind_name=self.mind_name,
            recipient=recipient,
            channel=channel,
            priority=priority,
            title=title,
            message=message,
            scheduled_for=scheduled_for,
            metadata=metadata or {}
        )
        
        # Add to queue (priority-sorted)
        self.pending_notifications.append(notification)
        self._sort_queue_by_priority()
        
        # Use ASCII-safe logging to prevent Unicode encoding errors
        try:
            logger.info(f"[NOTIF] Notification queued: '{title}' to {recipient}")
        except UnicodeEncodeError:
            # Fallback to ASCII-safe logging
            safe_title = title.encode('ascii', 'replace').decode('ascii')
            logger.info(f"[NOTIF] Notification queued: '{safe_title}' to {recipient}")
        
        # If urgent and websocket available, deliver immediately
        if priority == NotificationPriority.URGENT and channel == NotificationChannel.WEBSOCKET:
            await self._deliver_notification(notification)
        
        return notification.notification_id
    
    def _check_rate_limit(self) -> bool:
        """Check if we can send more notifications this hour."""
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")
        count = self.notification_count_by_hour.get(current_hour, 0)
        return count < self.max_notifications_per_hour
    
    def _record_notification(self):
        """Record a notification for rate limiting."""
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")
        self.notification_count_by_hour[current_hour] = \
            self.notification_count_by_hour.get(current_hour, 0) + 1
        
        # Clean up old hours
        current_time = datetime.now()
        self.notification_count_by_hour = {
            k: v for k, v in self.notification_count_by_hour.items()
            if datetime.strptime(k, "%Y-%m-%d-%H") > current_time - timedelta(hours=2)
        }
    
    def _sort_queue_by_priority(self):
        """Sort queue by priority (urgent first)."""
        priority_order = {
            NotificationPriority.URGENT: 0,
            NotificationPriority.HIGH: 1,
            NotificationPriority.NORMAL: 2,
            NotificationPriority.LOW: 3
        }
        self.pending_notifications = deque(
            sorted(self.pending_notifications, key=lambda n: priority_order[n.priority]),
            maxlen=1000
        )
    
    async def _delivery_loop(self):
        """Background loop that delivers queued notifications."""
        last_cleanup = datetime.now()
        
        while self.is_running:
            try:
                # Periodic cleanup of stale connections (every 5 minutes)
                if datetime.now() - last_cleanup > timedelta(minutes=5):
                    await self._cleanup_stale_connections()
                    last_cleanup = datetime.now()
                
                # Check for notifications to deliver
                if self.pending_notifications:
                    notification = self.pending_notifications[0]
                    
                    # Check if it's time to deliver
                    if notification.scheduled_for and datetime.now() < notification.scheduled_for:
                        # Not yet time
                        await asyncio.sleep(5)
                        continue
                    
                    # Deliver
                    self.pending_notifications.popleft()
                    await self._deliver_notification(notification)
                
                # Sleep between checks
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Notification delivery loop error: {e}")
                await asyncio.sleep(5)
    
    async def _deliver_notification(self, notification: Notification):
        """Deliver a notification via the specified channel."""
        try:
            notification.attempts += 1
            
            if notification.channel == NotificationChannel.WEBSOCKET:
                success = await self._deliver_websocket(notification)
            elif notification.channel == NotificationChannel.EMAIL:
                success = await self._deliver_email(notification)
            elif notification.channel == NotificationChannel.SMS:
                success = await self._deliver_sms(notification)
            elif notification.channel == NotificationChannel.PUSH:
                success = await self._deliver_push(notification)
            elif notification.channel == NotificationChannel.GENESIS_WORLD:
                success = await self._deliver_genesis_world(notification)
            else:
                success = False
                notification.error = f"Unknown channel: {notification.channel}"
            
            if success:
                notification.delivered = True
                notification.delivered_at = datetime.now()
                self.delivered_notifications.append(notification)
                self._record_notification()
                logger.info(f"[SUCCESS] Notification delivered: {notification.notification_id}")
            else:
                # Retry if not max attempts
                if notification.attempts < notification.max_attempts:
                    self.pending_notifications.append(notification)
                    logger.warning(f"[WARN] Notification failed, will retry: {notification.notification_id}")
                else:
                    logger.error(f"[ERROR] Notification failed permanently: {notification.notification_id}")
                    
        except Exception as e:
            logger.error(f"Error delivering notification: {e}")
            notification.error = str(e)
    
    async def _deliver_websocket(self, notification: Notification) -> bool:
        """Deliver via WebSocket (for web playground)."""
        try:
            websocket = self.websocket_connections.get(notification.recipient)
            
            if not websocket:
                # No active connection - store for later retrieval
                logger.debug(f"No websocket connection for {notification.recipient} - storing notification")
                stored = await self._store_pending_notification(notification)
                # If successfully stored, treat as delivered (will be sent when user connects)
                return stored
            
            # Check if websocket is still connected
            if hasattr(websocket, 'client_state') and websocket.client_state.value != 1:  # CONNECTED = 1
                logger.debug(f"WebSocket connection closed for {notification.recipient}")
                # Clean up stale connection
                self.unregister_websocket(notification.recipient)
                return False
            
            # Send proactive message
            await websocket.send_json({
                "type": "proactive_message",
                "notification_id": notification.notification_id,
                "mind_id": self.mind_id,
                "mind_name": self.mind_name,
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "timestamp": notification.created_at.isoformat(),
                "metadata": notification.metadata
            })
            
            return True
            
        except ConnectionResetError:
            logger.debug(f"Connection reset for {notification.recipient}")
            # Clean up stale connection
            self.unregister_websocket(notification.recipient)
            return False
        except Exception as e:
            # Handle various WebSocket errors
            error_msg = str(e).lower()
            if any(err in error_msg for err in ['closed', 'disconnect', 'connection', 'reset']):
                logger.debug(f"WebSocket connection issue for {notification.recipient}: {e}")
                # Clean up stale connection
                self.unregister_websocket(notification.recipient)
                return False
            else:
                logger.error(f"WebSocket delivery error: {e}")
                return False
    
    async def _deliver_email(self, notification: Notification) -> bool:
        """Deliver via email."""
        try:
            # Use email integration if available
            # TODO: Implement email delivery
            logger.info(f"[EMAIL] Email notification (not yet implemented): {notification.title}")
            return False
        except Exception as e:
            logger.error(f"Email delivery error: {e}")
            return False
    
    async def _deliver_sms(self, notification: Notification) -> bool:
        """Deliver via SMS."""
        try:
            # Use SMS integration if available
            # TODO: Implement SMS delivery
            logger.info(f"[SMS] SMS notification (not yet implemented): {notification.title}")
            return False
        except Exception as e:
            logger.error(f"SMS delivery error: {e}")
            return False
    
    async def _deliver_push(self, notification: Notification) -> bool:
        """Deliver via push notification."""
        try:
            # Use push notification service
            # TODO: Implement push notification delivery
            logger.info(f"[PUSH] Push notification (not yet implemented): {notification.title}")
            return False
        except Exception as e:
            logger.error(f"Push delivery error: {e}")
            return False
    
    async def _deliver_genesis_world(self, notification: Notification) -> bool:
        """Deliver to another Mind in Genesis World."""
        try:
            # Send message to another Mind
            # TODO: Implement Mind-to-Mind messaging
            logger.info(f"[GENESIS] Genesis World notification (not yet implemented): {notification.title}")
            return False
        except Exception as e:
            logger.error(f"Genesis World delivery error: {e}")
            return False
    
    async def _store_pending_notification(self, notification: Notification):
        """Store notification for later retrieval when user connects."""
        try:
            from genesis.config.settings import get_settings
            settings = get_settings()
            
            # Store in notifications directory
            notif_dir = settings.data_dir / "notifications" / self.mind_id
            notif_dir.mkdir(parents=True, exist_ok=True)
            
            # Create notification file
            notif_file = notif_dir / f"{notification.notification_id}.json"
            
            # Serialize notification
            notif_data = {
                "notification_id": notification.notification_id,
                "mind_id": self.mind_id,
                "mind_name": self.mind_name,
                "recipient": notification.recipient,
                "channel": notification.channel.value if hasattr(notification.channel, 'value') else str(notification.channel),
                "priority": notification.priority.value if hasattr(notification.priority, 'value') else str(notification.priority),
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
                "metadata": notification.metadata,
                "delivered": False
            }
            
            with open(notif_file, 'w', encoding='utf-8') as f:
                json.dump(notif_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Stored notification {notification.notification_id} for later retrieval")
            return True
            
        except Exception as e:
            logger.error(f"Error storing notification: {e}")
            return False
    
    async def _cleanup_stale_connections(self):
        """Clean up stale WebSocket connections."""
        stale_connections = []
        
        for user_email, websocket in self.websocket_connections.items():
            try:
                # Check if websocket is still connected
                if hasattr(websocket, 'client_state') and websocket.client_state.value != 1:  # CONNECTED = 1
                    stale_connections.append(user_email)
            except Exception:
                stale_connections.append(user_email)
        
        # Remove stale connections
        for user_email in stale_connections:
            self.unregister_websocket(user_email)
            logger.debug(f"Cleaned up stale WebSocket connection for {user_email}")
        
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale WebSocket connections")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        failed_notifications = [
            n for n in self.delivered_notifications + list(self.pending_notifications)
            if n.attempts >= n.max_attempts and not n.delivered
        ]
        
        return {
            "pending": len(self.pending_notifications),
            "delivered_total": len([n for n in self.delivered_notifications if n.delivered]),
            "failed_total": len(failed_notifications),
            "delivered_today": len([
                n for n in self.delivered_notifications
                if n.delivered_at and n.delivered_at.date() == datetime.now().date()
            ]),
            "active_websockets": len(self.websocket_connections),
            "rate_limit": {
                "current_hour": self.notification_count_by_hour.get(
                    datetime.now().strftime("%Y-%m-%d-%H"), 0
                ),
                "max_per_hour": self.max_notifications_per_hour
            }
        }
