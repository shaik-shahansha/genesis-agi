"""Sessions Plugin - Structured interaction management for Genesis Minds.

Enables Minds to manage bounded interaction contexts like:
- Class sessions (for teachers)
- Meetings (for business)
- Consultations (for advisors)
- Work sessions (for productivity)

Features:
- Create/start/pause/resume/end sessions
- Track participants and interactions
- Session-specific context and memory
- Session continuity across time
- Automatic environment switching
- Session analytics

Example:
    from genesis.plugins.sessions import SessionsPlugin

    config = MindConfig()
    config.add_plugin(SessionsPlugin())
    mind = Mind.birth("Maria", config=config)

    # Start a class session
    session = await mind.sessions.start_session(
        session_type="class",
        title="Biology 101 - Photosynthesis",
        participants=["student_1", "student_2", "student_3"],
        environment_id="classroom_a"
    )

    # Session automatically loads relevant context
    # Mind remembers where it left off from last session
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from genesis.plugins.base import Plugin

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class SessionType(str, Enum):
    """Types of sessions."""
    CLASS = "class"
    MEETING = "meeting"
    CONSULTATION = "consultation"
    WORK = "work"
    TRAINING = "training"
    SOCIAL = "social"
    CUSTOM = "custom"


class SessionStatus(str, Enum):
    """Session status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class SessionInteraction:
    """Represents an interaction within a session."""
    interaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    participant_id: str = ""
    interaction_type: str = "message"  # message, question, answer, action
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """Represents a session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_type: SessionType = SessionType.CUSTOM
    title: str = ""
    description: str = ""
    participants: List[str] = field(default_factory=list)
    environment_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: SessionStatus = SessionStatus.ACTIVE
    context: Dict[str, Any] = field(default_factory=dict)
    interactions: List[SessionInteraction] = field(default_factory=list)
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    previous_session_id: Optional[str] = None  # For continuity


class SessionManager:
    """Manages sessions for a Mind."""

    def __init__(self, mind: "Mind"):
        """Initialize session manager.

        Args:
            mind: Mind instance
        """
        self.mind = mind
        self.sessions: Dict[str, Session] = {}
        self.active_session: Optional[Session] = None
        self.session_history: List[str] = []  # Session IDs in chronological order

    async def start_session(
        self,
        session_type: SessionType,
        title: str,
        description: str = "",
        participants: Optional[List[str]] = None,
        environment_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        continue_from: Optional[str] = None  # Previous session ID
    ) -> Session:
        """Start a new session.

        Args:
            session_type: Type of session
            title: Session title
            description: Session description
            participants: List of participant IDs
            environment_id: Environment to use
            tags: Session tags
            continue_from: Previous session ID for continuity

        Returns:
            Created session
        """
        # End current active session if exists
        if self.active_session:
            await self.end_session()

        # Create session
        session = Session(
            session_type=session_type,
            title=title,
            description=description,
            participants=participants or [],
            environment_id=environment_id,
            tags=tags or [],
            previous_session_id=continue_from
        )

        # Load context from previous session if continuing
        if continue_from and continue_from in self.sessions:
            prev_session = self.sessions[continue_from]
            session.context = prev_session.context.copy()
            session.context["continued_from"] = continue_from

            logger.info(f"Continuing from previous session: {prev_session.title}")

        # Store session
        self.sessions[session.session_id] = session
        self.active_session = session
        self.session_history.append(session.session_id)

        logger.info(f"Started session: {title} ({session_type})")

        # Load relevant memories
        await self._load_session_context(session)

        # Switch environment if specified
        if environment_id:
            await self._switch_environment(environment_id)

        return session

    async def _load_session_context(self, session: Session):
        """Load relevant context for session.

        Args:
            session: Session to load context for
        """
        if not hasattr(self.mind, "memory"):
            return

        # Search for relevant memories
        search_query = f"{session.title} {session.description} {' '.join(session.tags)}"
        memories = await self.mind.memory.search_memories(search_query, limit=20)

        session.context["relevant_memories"] = [
            {
                "content": mem.content,
                "timestamp": mem.timestamp.isoformat(),
                "importance": mem.importance
            }
            for mem in memories
        ]

        logger.info(f"Loaded {len(memories)} relevant memories for session")

    async def _switch_environment(self, environment_id: str):
        """Switch to specified environment.

        Args:
            environment_id: Environment ID
        """
        # TODO: Integrate with environment system
        logger.info(f"Switched to environment: {environment_id}")

    async def pause_session(self) -> bool:
        """Pause the active session.

        Returns:
            True if paused successfully
        """
        if not self.active_session:
            logger.warning("No active session to pause")
            return False

        self.active_session.status = SessionStatus.PAUSED

        logger.info(f"Paused session: {self.active_session.title}")

        return True

    async def resume_session(self, session_id: Optional[str] = None) -> bool:
        """Resume a paused session.

        Args:
            session_id: Session ID to resume (default: active session)

        Returns:
            True if resumed successfully
        """
        if session_id:
            session = self.sessions.get(session_id)
            if not session:
                logger.error(f"Session not found: {session_id}")
                return False

            # End current active session
            if self.active_session:
                await self.end_session()

            self.active_session = session

        if not self.active_session:
            logger.warning("No session to resume")
            return False

        self.active_session.status = SessionStatus.ACTIVE

        logger.info(f"Resumed session: {self.active_session.title}")

        # Reload context
        await self._load_session_context(self.active_session)

        return True

    async def end_session(self, summary: Optional[str] = None) -> bool:
        """End the active session.

        Args:
            summary: Optional session summary

        Returns:
            True if ended successfully
        """
        if not self.active_session:
            logger.warning("No active session to end")
            return False

        self.active_session.end_time = datetime.now()
        self.active_session.status = SessionStatus.COMPLETED

        # Generate summary if not provided
        if not summary and len(self.active_session.interactions) > 0:
            summary = await self._generate_summary(self.active_session)

        self.active_session.summary = summary or ""

        logger.info(f"Ended session: {self.active_session.title}")

        # Store session summary in memory
        if hasattr(self.mind, "memory"):
            await self.mind.memory.add_memory(
                f"Completed session: {self.active_session.title}. {self.active_session.summary}",
                memory_type="episodic",
                importance=0.7,
                metadata={"session_id": self.active_session.session_id}
            )

        self.active_session = None

        return True

    async def _generate_summary(self, session: Session) -> str:
        """Generate session summary.

        Args:
            session: Session to summarize

        Returns:
            Session summary
        """
        # Simple summary based on interactions
        interaction_count = len(session.interactions)
        duration = (session.end_time or datetime.now()) - session.start_time

        summary = (
            f"Session lasted {duration.total_seconds() / 60:.1f} minutes "
            f"with {interaction_count} interactions. "
            f"Participants: {', '.join(session.participants)}."
        )

        return summary

    async def add_interaction(
        self,
        participant_id: str,
        interaction_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add an interaction to the active session.

        Args:
            participant_id: Participant ID
            interaction_type: Type of interaction
            content: Interaction content
            metadata: Additional metadata

        Returns:
            True if added successfully
        """
        if not self.active_session:
            logger.warning("No active session")
            return False

        interaction = SessionInteraction(
            participant_id=participant_id,
            interaction_type=interaction_type,
            content=content,
            metadata=metadata or {}
        )

        self.active_session.interactions.append(interaction)

        return True

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session or None if not found
        """
        return self.sessions.get(session_id)

    def get_sessions(
        self,
        session_type: Optional[SessionType] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 50
    ) -> List[Session]:
        """Get sessions with optional filters.

        Args:
            session_type: Filter by session type
            status: Filter by status
            limit: Maximum number of sessions

        Returns:
            List of sessions
        """
        sessions = list(self.sessions.values())

        if session_type:
            sessions = [s for s in sessions if s.session_type == session_type]

        if status:
            sessions = [s for s in sessions if s.status == status]

        # Sort by start time (most recent first)
        sessions.sort(key=lambda s: s.start_time, reverse=True)

        return sessions[:limit]

    def get_session_analytics(self) -> Dict[str, Any]:
        """Get session analytics.

        Returns:
            Analytics dictionary
        """
        total_sessions = len(self.sessions)
        completed_sessions = len([s for s in self.sessions.values() if s.status == SessionStatus.COMPLETED])

        total_duration = timedelta()
        for session in self.sessions.values():
            if session.end_time:
                total_duration += session.end_time - session.start_time

        avg_duration = total_duration / completed_sessions if completed_sessions > 0 else timedelta()

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "active_sessions": len([s for s in self.sessions.values() if s.status == SessionStatus.ACTIVE]),
            "average_duration_minutes": avg_duration.total_seconds() / 60,
            "total_interactions": sum(len(s.interactions) for s in self.sessions.values())
        }


class SessionsPlugin(Plugin):
    """Plugin for session management.

    Enables structured interaction management with continuity.
    """

    def __init__(self, **config):
        """Initialize sessions plugin."""
        super().__init__(**config)
        self.manager: Optional[SessionManager] = None

    def get_name(self) -> str:
        return "sessions"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Structured session management with continuity"

    def on_init(self, mind: "Mind") -> None:
        """Initialize session manager."""
        self.manager = SessionManager(mind)
        mind.sessions = self.manager
        logger.info("Initialized session manager")

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add sessions context to system prompt."""
        if not self.manager:
            return ""

        sections = []

        # Current session info
        if self.manager.active_session:
            session = self.manager.active_session
            sections.append(f"📋 ACTIVE SESSION: {session.title}")
            sections.append(f"  Type: {session.session_type.value}")
            sections.append(f"  Participants: {', '.join(session.participants)}")
            sections.append(f"  Duration: {(datetime.now() - session.start_time).total_seconds() / 60:.0f} minutes")

            if session.context.get("relevant_memories"):
                sections.append(f"  Relevant memories loaded: {len(session.context['relevant_memories'])}")

            sections.append("")

        # Session capabilities
        sections.append("SESSION MANAGEMENT:")
        sections.append("- You can start/pause/resume/end sessions")
        sections.append("- Sessions maintain context and continuity")
        sections.append("- Previous session context is automatically loaded")
        sections.append("- All interactions are tracked")

        analytics = self.manager.get_session_analytics()
        sections.append(f"\nSession Stats: {analytics['completed_sessions']} completed, {analytics['total_interactions']} total interactions")

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save sessions state."""
        if not self.manager:
            return {}

        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "session_type": s.session_type.value,
                    "title": s.title,
                    "description": s.description,
                    "participants": s.participants,
                    "environment_id": s.environment_id,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "status": s.status.value,
                    "context": s.context,
                    "summary": s.summary,
                    "tags": s.tags,
                    "previous_session_id": s.previous_session_id,
                    "interaction_count": len(s.interactions)
                }
                for s in self.manager.sessions.values()
            ],
            "active_session_id": self.manager.active_session.session_id if self.manager.active_session else None,
            "session_history": self.manager.session_history
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore sessions state."""
        self.on_init(mind)

        if not self.manager:
            return

        # Restore sessions
        if "sessions" in data:
            for session_data in data["sessions"]:
                session = Session(
                    session_id=session_data["session_id"],
                    session_type=SessionType(session_data["session_type"]),
                    title=session_data["title"],
                    description=session_data.get("description", ""),
                    participants=session_data.get("participants", []),
                    environment_id=session_data.get("environment_id"),
                    start_time=datetime.fromisoformat(session_data["start_time"]),
                    end_time=datetime.fromisoformat(session_data["end_time"]) if session_data.get("end_time") else None,
                    status=SessionStatus(session_data["status"]),
                    context=session_data.get("context", {}),
                    summary=session_data.get("summary", ""),
                    tags=session_data.get("tags", []),
                    previous_session_id=session_data.get("previous_session_id")
                )

                self.manager.sessions[session.session_id] = session

        # Restore active session
        if "active_session_id" in data and data["active_session_id"]:
            self.manager.active_session = self.manager.sessions.get(data["active_session_id"])

        # Restore session history
        if "session_history" in data:
            self.manager.session_history = data["session_history"]

    def get_status(self) -> Dict[str, Any]:
        """Get sessions status."""
        status = super().get_status()

        if self.manager:
            analytics = self.manager.get_session_analytics()
            status.update(analytics)
            status["has_active_session"] = self.manager.active_session is not None

        return status
