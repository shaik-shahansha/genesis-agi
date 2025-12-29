"""Environment Client - WebSocket client for Minds to connect to environments."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
import websockets

logger = logging.getLogger(__name__)


class EnvironmentClient:
    """WebSocket client for Mind to connect to environment server."""

    def __init__(self, mind_id: str, server_url: str = "ws://localhost:8765"):
        """Initialize environment client.

        Args:
            mind_id: Mind ID
            server_url: WebSocket server URL
        """
        self.mind_id = mind_id
        self.server_url = server_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.current_environment: Optional[str] = None
        self.connected = False
        self.message_handlers: Dict[str, Callable] = {}
        self.receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """Connect to environment server.

        Returns:
            True if connected successfully
        """
        try:
            self.websocket = await websockets.connect(self.server_url)

            # Authenticate
            auth_msg = {"type": "auth", "mind_id": self.mind_id}
            await self.websocket.send(json.dumps(auth_msg))

            # Wait for auth response
            response = await self.websocket.recv()
            data = json.loads(response)

            if data.get("type") == "auth_success":
                self.connected = True
                logger.info(f"Mind {self.mind_id} connected to environment server")

                # Start receiving messages
                self.receive_task = asyncio.create_task(self._receive_messages())

                return True
            else:
                logger.error(f"Authentication failed: {data}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def disconnect(self):
        """Disconnect from environment server."""
        if self.current_environment:
            await self.leave(self.current_environment)

        if self.receive_task:
            self.receive_task.cancel()

        if self.websocket:
            await self.websocket.close()

        self.connected = False
        logger.info(f"Mind {self.mind_id} disconnected")

    async def join(self, environment_id: str) -> bool:
        """Join an environment.

        Args:
            environment_id: Environment ID to join

        Returns:
            True if joined successfully
        """
        if not self.connected:
            logger.error("Not connected to server")
            return False

        try:
            await self.websocket.send(json.dumps({
                "type": "join",
                "environment_id": environment_id
            }))

            self.current_environment = environment_id
            return True

        except Exception as e:
            logger.error(f"Failed to join environment: {e}")
            return False

    async def leave(self, environment_id: Optional[str] = None) -> bool:
        """Leave current or specified environment.

        Args:
            environment_id: Environment ID to leave (default: current)

        Returns:
            True if left successfully
        """
        if not self.connected:
            return False

        env_id = environment_id or self.current_environment
        if not env_id:
            return False

        try:
            await self.websocket.send(json.dumps({
                "type": "leave",
                "environment_id": env_id
            }))

            if env_id == self.current_environment:
                self.current_environment = None

            return True

        except Exception as e:
            logger.error(f"Failed to leave environment: {e}")
            return False

    async def broadcast(self, content: str, target: str = "all"):
        """Broadcast message to environment.

        Args:
            content: Message content
            target: Target ("all" or specific mind_id)
        """
        if not self.connected or not self.current_environment:
            logger.error("Not in an environment")
            return

        try:
            await self.websocket.send(json.dumps({
                "type": "message",
                "content": content,
                "target": target
            }))

        except Exception as e:
            logger.error(f"Failed to broadcast: {e}")

    async def update_state(self, updates: Dict[str, Any]):
        """Update environment state.

        Args:
            updates: State updates
        """
        if not self.connected or not self.current_environment:
            return

        try:
            await self.websocket.send(json.dumps({
                "type": "state_update",
                "updates": updates
            }))

        except Exception as e:
            logger.error(f"Failed to update state: {e}")

    async def get_state(self) -> Optional[Dict[str, Any]]:
        """Get current environment state.

        Returns:
            Environment state
        """
        if not self.connected or not self.current_environment:
            return None

        try:
            await self.websocket.send(json.dumps({"type": "get_state"}))
            # State will be received via message handler
            return None

        except Exception as e:
            logger.error(f"Failed to get state: {e}")
            return None

    def on(self, event_type: str, handler: Callable):
        """Register event handler.

        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        self.message_handlers[event_type] = handler

    async def _receive_messages(self):
        """Receive and handle messages from server."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get("type")

                # Call registered handler if exists
                if msg_type in self.message_handlers:
                    handler = self.message_handlers[msg_type]
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
