"""Environment Server - WebSocket-based real-time environment hosting.

Provides WebSocket server for real-time Mind interactions in shared environments.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """Configuration for environment server."""
    host: str = "0.0.0.0"
    port: int = 8765
    max_connections: int = 1000
    ping_interval: int = 20  # seconds
    ping_timeout: int = 10  # seconds


class EnvironmentServer:
    """WebSocket server for real-time environments.

    Manages WebSocket connections, message routing, and state synchronization
    for all connected Minds across different environments.
    """

    def __init__(self, config: Optional[EnvironmentConfig] = None):
        """Initialize environment server.

        Args:
            config: Server configuration
        """
        self.config = config or EnvironmentConfig()
        self.connections: Dict[str, WebSocketServerProtocol] = {}  # mind_id -> websocket
        self.mind_environments: Dict[str, str] = {}  # mind_id -> environment_id
        self.environment_minds: Dict[str, Set[str]] = {}  # environment_id -> set of mind_ids
        self.environment_state: Dict[str, Dict[str, Any]] = {}  # environment_id -> state
        self.server: Optional[websockets.WebSocketServer] = None
        self.running = False

    async def start(self):
        """Start the WebSocket server."""
        try:
            self.server = await websockets.serve(
                self._handle_connection,
                self.config.host,
                self.config.port,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout
            )
            self.running = True
            logger.info(f"Environment server started on {self.config.host}:{self.config.port}")

        except Exception as e:
            logger.error(f"Failed to start environment server: {e}")
            raise

    async def stop(self):
        """Stop the WebSocket server."""
        self.running = False

        # Close all connections
        for ws in list(self.connections.values()):
            await ws.close()

        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("Environment server stopped")

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection.

        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        mind_id = None

        try:
            # Wait for authentication message
            auth_msg = await websocket.recv()
            auth_data = json.loads(auth_msg)

            if auth_data.get("type") != "auth":
                await websocket.send(json.dumps({"type": "error", "message": "Authentication required"}))
                return

            mind_id = auth_data.get("mind_id")
            if not mind_id:
                await websocket.send(json.dumps({"type": "error", "message": "mind_id required"}))
                return

            # Register connection
            self.connections[mind_id] = websocket
            logger.info(f"Mind {mind_id} connected")

            # Send success
            await websocket.send(json.dumps({"type": "auth_success", "mind_id": mind_id}))

            # Handle messages
            async for message in websocket:
                await self._handle_message(mind_id, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Mind {mind_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling connection for {mind_id}: {e}")
        finally:
            # Cleanup
            if mind_id:
                await self._handle_disconnect(mind_id)

    async def _handle_message(self, mind_id: str, message: str):
        """Handle incoming WebSocket message.

        Args:
            mind_id: Mind ID
            message: JSON message
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "join":
                await self._handle_join(mind_id, data)
            elif msg_type == "leave":
                await self._handle_leave(mind_id, data)
            elif msg_type == "message":
                await self._handle_broadcast(mind_id, data)
            elif msg_type == "state_update":
                await self._handle_state_update(mind_id, data)
            elif msg_type == "get_state":
                await self._handle_get_state(mind_id, data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {mind_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from {mind_id}: {e}")

    async def _handle_join(self, mind_id: str, data: Dict[str, Any]):
        """Handle Mind joining an environment.

        Args:
            mind_id: Mind ID
            data: Join message data
        """
        environment_id = data.get("environment_id")
        if not environment_id:
            return

        # Leave current environment if any
        if mind_id in self.mind_environments:
            await self._handle_leave(mind_id, {"environment_id": self.mind_environments[mind_id]})

        # Join new environment
        self.mind_environments[mind_id] = environment_id

        if environment_id not in self.environment_minds:
            self.environment_minds[environment_id] = set()
            self.environment_state[environment_id] = {}

        self.environment_minds[environment_id].add(mind_id)

        logger.info(f"Mind {mind_id} joined environment {environment_id}")

        # Notify Mind of join success
        await self._send_to_mind(mind_id, {
            "type": "joined",
            "environment_id": environment_id,
            "present_minds": list(self.environment_minds[environment_id]),
            "state": self.environment_state.get(environment_id, {})
        })

        # Notify other Minds in environment
        await self._broadcast_to_environment(environment_id, {
            "type": "mind_joined",
            "mind_id": mind_id,
            "timestamp": datetime.now().isoformat()
        }, exclude=mind_id)

    async def _handle_leave(self, mind_id: str, data: Dict[str, Any]):
        """Handle Mind leaving an environment.

        Args:
            mind_id: Mind ID
            data: Leave message data
        """
        environment_id = data.get("environment_id") or self.mind_environments.get(mind_id)
        if not environment_id:
            return

        # Remove from environment
        if mind_id in self.mind_environments:
            del self.mind_environments[mind_id]

        if environment_id in self.environment_minds:
            self.environment_minds[environment_id].discard(mind_id)

            # Clean up empty environments
            if not self.environment_minds[environment_id]:
                del self.environment_minds[environment_id]
                del self.environment_state[environment_id]

        logger.info(f"Mind {mind_id} left environment {environment_id}")

        # Notify other Minds
        await self._broadcast_to_environment(environment_id, {
            "type": "mind_left",
            "mind_id": mind_id,
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_broadcast(self, mind_id: str, data: Dict[str, Any]):
        """Handle broadcast message to environment.

        Args:
            mind_id: Mind ID sending message
            data: Message data
        """
        environment_id = self.mind_environments.get(mind_id)
        if not environment_id:
            logger.warning(f"Mind {mind_id} not in any environment")
            return

        content = data.get("content", "")
        target = data.get("target", "all")  # "all" or specific mind_id

        message = {
            "type": "message",
            "from": mind_id,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        if target == "all":
            await self._broadcast_to_environment(environment_id, message, exclude=mind_id)
        else:
            # Direct message to specific Mind
            await self._send_to_mind(target, message)

    async def _handle_state_update(self, mind_id: str, data: Dict[str, Any]):
        """Handle environment state update.

        Args:
            mind_id: Mind ID updating state
            data: State update data
        """
        environment_id = self.mind_environments.get(mind_id)
        if not environment_id:
            return

        updates = data.get("updates", {})

        # Update environment state
        if environment_id not in self.environment_state:
            self.environment_state[environment_id] = {}

        self.environment_state[environment_id].update(updates)

        # Broadcast state update to all Minds
        await self._broadcast_to_environment(environment_id, {
            "type": "state_updated",
            "updates": updates,
            "updated_by": mind_id,
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_get_state(self, mind_id: str, data: Dict[str, Any]):
        """Handle request for current environment state.

        Args:
            mind_id: Mind ID requesting state
            data: Request data
        """
        environment_id = self.mind_environments.get(mind_id)
        if not environment_id:
            return

        state = self.environment_state.get(environment_id, {})

        await self._send_to_mind(mind_id, {
            "type": "state",
            "environment_id": environment_id,
            "state": state,
            "present_minds": list(self.environment_minds.get(environment_id, set()))
        })

    async def _handle_disconnect(self, mind_id: str):
        """Handle Mind disconnection.

        Args:
            mind_id: Mind ID that disconnected
        """
        # Leave environment if in one
        if mind_id in self.mind_environments:
            environment_id = self.mind_environments[mind_id]
            await self._handle_leave(mind_id, {"environment_id": environment_id})

        # Remove connection
        if mind_id in self.connections:
            del self.connections[mind_id]

    async def _send_to_mind(self, mind_id: str, message: Dict[str, Any]):
        """Send message to specific Mind.

        Args:
            mind_id: Target Mind ID
            message: Message to send
        """
        websocket = self.connections.get(mind_id)
        if websocket:
            try:
                await websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to {mind_id}: {e}")

    async def _broadcast_to_environment(
        self,
        environment_id: str,
        message: Dict[str, Any],
        exclude: Optional[str] = None
    ):
        """Broadcast message to all Minds in environment.

        Args:
            environment_id: Environment ID
            message: Message to broadcast
            exclude: Optional Mind ID to exclude
        """
        minds = self.environment_minds.get(environment_id, set())

        for mind_id in minds:
            if mind_id != exclude:
                await self._send_to_mind(mind_id, message)

    def get_environment_info(self, environment_id: str) -> Dict[str, Any]:
        """Get information about an environment.

        Args:
            environment_id: Environment ID

        Returns:
            Environment information
        """
        return {
            "environment_id": environment_id,
            "present_minds": list(self.environment_minds.get(environment_id, set())),
            "state": self.environment_state.get(environment_id, {}),
            "mind_count": len(self.environment_minds.get(environment_id, set()))
        }

    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics.

        Returns:
            Server statistics
        """
        return {
            "running": self.running,
            "total_connections": len(self.connections),
            "total_environments": len(self.environment_minds),
            "environments": {
                env_id: len(minds)
                for env_id, minds in self.environment_minds.items()
            }
        }
