"""
Real-time Environment Server - WebSocket-based live environments.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field, asdict
from fastapi import WebSocket
from collections import defaultdict

from genesis.database.manager import MetaverseDB


@dataclass
class EnvironmentState:
    """State of an environment."""
    environment_id: str
    name: str
    env_type: str
    owner_gmid: str

    # Real-time state
    present_minds: Set[str] = field(default_factory=set)
    objects: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        data = asdict(self)
        data['present_minds'] = list(self.present_minds)
        return data


class ConnectionManager:
    """Manage WebSocket connections per environment."""

    def __init__(self):
        # environment_id -> {mind_id: WebSocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = defaultdict(dict)

    async def connect(self, environment_id: str, mind_id: str, websocket: WebSocket):
        """Add connection to environment."""
        await websocket.accept()
        self.active_connections[environment_id][mind_id] = websocket

    def disconnect(self, environment_id: str, mind_id: str):
        """Remove connection from environment."""
        if environment_id in self.active_connections:
            self.active_connections[environment_id].pop(mind_id, None)

            # Clean up empty environments
            if not self.active_connections[environment_id]:
                del self.active_connections[environment_id]

    async def broadcast(self, environment_id: str, message: Dict[str, Any], exclude_mind: Optional[str] = None):
        """Broadcast message to all minds in environment."""
        if environment_id not in self.active_connections:
            return

        message_json = json.dumps(message)

        for mind_id, websocket in list(self.active_connections[environment_id].items()):
            if mind_id == exclude_mind:
                continue

            try:
                await websocket.send_text(message_json)
            except Exception as e:
                print(f"Error broadcasting to {mind_id}: {e}")
                # Remove dead connection
                self.disconnect(environment_id, mind_id)

    async def send_to_mind(self, environment_id: str, mind_id: str, message: Dict[str, Any]):
        """Send message to specific mind."""
        if environment_id not in self.active_connections:
            return False

        websocket = self.active_connections[environment_id].get(mind_id)
        if not websocket:
            return False

        try:
            await websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            print(f"Error sending to {mind_id}: {e}")
            self.disconnect(environment_id, mind_id)
            return False

    def get_present_minds(self, environment_id: str) -> List[str]:
        """Get list of minds present in environment."""
        if environment_id not in self.active_connections:
            return []
        return list(self.active_connections[environment_id].keys())


class EnvironmentServer:
    """Real-time environment server with WebSocket support."""

    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.environment_states: Dict[str, EnvironmentState] = {}
        self.db = MetaverseDB()

    def get_or_create_state(self, environment_id: str) -> EnvironmentState:
        """Get or create environment state."""
        if environment_id not in self.environment_states:
            # Load from database
            from genesis.database.base import get_session
            from genesis.database.models import EnvironmentRecord
            
            with get_session() as session:
                env = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()

                if not env:
                    raise ValueError(f"Environment {environment_id} not found")

                self.environment_states[environment_id] = EnvironmentState(
                    environment_id=environment_id,
                    name=env.name,
                    env_type=env.env_type,
                    owner_gmid=env.owner_gmid,
                    objects=env.extra_metadata.get('objects', {}) if env.extra_metadata else {},
                    variables=env.extra_metadata.get('variables', {}) if env.extra_metadata else {},
                )

        return self.environment_states[environment_id]

    async def handle_connection(self, environment_id: str, mind_id: str, mind_name: str, websocket: WebSocket):
        """Handle WebSocket connection for a mind entering an environment."""
        try:
            # Connect
            await self.connection_manager.connect(environment_id, mind_id, websocket)

            # Get/create state
            state = self.get_or_create_state(environment_id)

            # Add mind to present list
            state.present_minds.add(mind_id)
            state.last_activity = datetime.utcnow().isoformat()

            # Record visit in database
            self.db.record_visit_start(mind_id, environment_id)

            # Broadcast join event
            await self.connection_manager.broadcast(
                environment_id,
                {
                    "type": "mind_joined",
                    "mind_id": mind_id,
                    "mind_name": mind_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "present_minds": list(state.present_minds),
                    "count": len(state.present_minds),
                },
                exclude_mind=mind_id
            )

            # Send welcome message to joining mind
            await self.connection_manager.send_to_mind(
                environment_id,
                mind_id,
                {
                    "type": "welcome",
                    "environment": state.to_dict(),
                    "message": f"Welcome to {state.name}!",
                }
            )

            # Listen for messages
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                await self.handle_message(environment_id, mind_id, mind_name, message)

        except Exception as e:
            print(f"WebSocket error for {mind_id} in {environment_id}: {e}")

        finally:
            # Disconnect
            await self.handle_disconnect(environment_id, mind_id, mind_name)

    async def handle_message(self, environment_id: str, mind_id: str, mind_name: str, message: Dict[str, Any]):
        """Handle message from mind in environment."""
        message_type = message.get("type")
        state = self.environment_states.get(environment_id)

        if not state:
            return

        state.last_activity = datetime.utcnow().isoformat()

        if message_type == "chat":
            # Chat message
            await self.connection_manager.broadcast(
                environment_id,
                {
                    "type": "chat_message",
                    "from_mind_id": mind_id,
                    "from_mind_name": mind_name,
                    "content": message.get("content", ""),
                    "emotion": message.get("emotion"),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        elif message_type == "action":
            # Environment action (e.g., update whiteboard)
            action = message.get("action")
            data = message.get("data", {})

            if action == "update_object":
                # Update object in environment
                object_id = data.get("object_id")
                object_data = data.get("data")

                if object_id:
                    state.objects[object_id] = object_data

                    # Broadcast update
                    await self.connection_manager.broadcast(
                        environment_id,
                        {
                            "type": "object_updated",
                            "object_id": object_id,
                            "data": object_data,
                            "updated_by": mind_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            elif action == "set_variable":
                # Set environment variable
                var_name = data.get("name")
                var_value = data.get("value")

                if var_name:
                    state.variables[var_name] = var_value

                    await self.connection_manager.broadcast(
                        environment_id,
                        {
                            "type": "variable_set",
                            "name": var_name,
                            "value": var_value,
                            "set_by": mind_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

        elif message_type == "request_state":
            # Send current state to requesting mind
            await self.connection_manager.send_to_mind(
                environment_id,
                mind_id,
                {
                    "type": "state_update",
                    "state": state.to_dict(),
                }
            )

        elif message_type == "typing":
            # Typing indicator
            await self.connection_manager.broadcast(
                environment_id,
                {
                    "type": "typing",
                    "mind_id": mind_id,
                    "mind_name": mind_name,
                    "is_typing": message.get("is_typing", True),
                },
                exclude_mind=mind_id
            )

    async def handle_disconnect(self, environment_id: str, mind_id: str, mind_name: str):
        """Handle mind disconnecting from environment."""
        state = self.environment_states.get(environment_id)

        if state and mind_id in state.present_minds:
            # Remove from present list
            state.present_minds.remove(mind_id)
            state.last_activity = datetime.utcnow().isoformat()

            # Broadcast leave event
            await self.connection_manager.broadcast(
                environment_id,
                {
                    "type": "mind_left",
                    "mind_id": mind_id,
                    "mind_name": mind_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "present_minds": list(state.present_minds),
                    "count": len(state.present_minds),
                }
            )

            # Update database (end visit timestamp)
            # This could be tracked in a separate visit_history table

        # Disconnect WebSocket
        self.connection_manager.disconnect(environment_id, mind_id)

        # Clean up empty environment state
        if state and len(state.present_minds) == 0:
            # Optionally persist state to database before removing
            # Save objects and variables to environment metadata
            from genesis.database.base import get_session
            from genesis.database.models import EnvironmentRecord
            
            with get_session() as session:
                env = session.query(EnvironmentRecord).filter_by(env_id=environment_id).first()
                if env:
                    if not env.extra_metadata:
                        env.extra_metadata = {}
                    env.extra_metadata['objects'] = state.objects
                    env.extra_metadata['variables'] = state.variables
                    env.extra_metadata['last_active'] = state.last_activity
                    session.commit()

            # Remove from memory
            del self.environment_states[environment_id]

    def get_environment_info(self, environment_id: str) -> Optional[Dict[str, Any]]:
        """Get current environment information."""
        state = self.environment_states.get(environment_id)

        if not state:
            # Try to load from database
            try:
                state = self.get_or_create_state(environment_id)
            except ValueError:
                return None

        return state.to_dict()

    def get_all_active_environments(self) -> List[Dict[str, Any]]:
        """Get all currently active environments."""
        return [
            {
                "environment_id": env_id,
                "name": state.name,
                "occupancy": len(state.present_minds),
                "present_minds": list(state.present_minds),
            }
            for env_id, state in self.environment_states.items()
        ]


# Global environment server instance
_environment_server = None


def get_environment_server() -> EnvironmentServer:
    """Get global environment server instance."""
    global _environment_server
    if _environment_server is None:
        _environment_server = EnvironmentServer()
    return _environment_server
