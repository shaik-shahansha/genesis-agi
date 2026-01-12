"""MetaverseDB manager for database operations."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session

from genesis.database.base import get_session, init_db
from genesis.database.models import (
    MindRecord,
    EnvironmentRecord,
    RelationshipRecord,
    EnvironmentVisit,
    SharedEvent,
    MetaverseState,
    ThoughtRecord,
    GenTransaction,
)


class MetaverseDB:
    """
    Central manager for metaverse database operations.

    Provides high-level methods for Mind registry, environment tracking,
    relationship management, and metaverse-wide queries.
    """

    def __init__(self):
        """Initialize metaverse database."""
        # Ensure database is initialized
        init_db()

        # Initialize metaverse state if not exists
        with get_session() as session:
            state = session.query(MetaverseState).filter_by(id=1).first()
            if not state:
                state = MetaverseState(id=1)
                session.add(state)
                session.commit()

    # =========================================================================
    # MIND REGISTRY
    # =========================================================================

    def register_mind(
        self,
        gmid: str,
        name: str,
        creator: str,
        template: Optional[str] = None,
        primary_role: Optional[str] = None,
        storage_path: Optional[str] = None,
    ) -> MindRecord:
        """Register a new Mind in the metaverse."""
        with get_session() as session:
            # If mind already exists, return existing one
            existing = session.query(MindRecord).filter_by(gmid=gmid).first()
            if existing:
                session.refresh(existing)
                session.expunge(existing)
                return existing

            mind = MindRecord(
                gmid=gmid,
                name=name,
                creator=creator,
                template=template,
                primary_role=primary_role,
                storage_path=storage_path,
                birth_date=datetime.now(timezone.utc),
                last_active=datetime.now(timezone.utc),
                status="active",
            )
            session.add(mind)
            session.commit()

            # Update metaverse state
            self._update_metaverse_stats(session)

            session.refresh(mind)
            session.expunge(mind)
            return mind

    def get_mind(self, gmid: str) -> Optional[MindRecord]:
        """Get Mind by GMID."""
        with get_session() as session:
            mind = session.query(MindRecord).filter_by(gmid=gmid).first()
            if not mind:
                return None
            # Ensure scalar attributes are loaded before detaching from session
            session.refresh(mind)
            session.expunge(mind)
            return mind

    def update_mind_activity(self, gmid: str) -> None:
        """Update Mind's last active timestamp."""
        with get_session() as session:
            mind = session.query(MindRecord).filter_by(gmid=gmid).first()
            if mind:
                mind.last_active = datetime.now(timezone.utc)
                session.commit()

    def update_mind_stats(
        self,
        gmid: str,
        total_memories: Optional[int] = None,
        total_experiences: Optional[int] = None,
        consciousness_level: Optional[float] = None,
    ) -> None:
        """Update Mind statistics."""
        with get_session() as session:
            mind = session.query(MindRecord).filter_by(gmid=gmid).first()
            if mind:
                if total_memories is not None:
                    mind.total_memories = total_memories
                if total_experiences is not None:
                    mind.total_experiences = total_experiences
                if consciousness_level is not None:
                    mind.consciousness_level = consciousness_level
                session.commit()

    # =========================================================================
    # MIND ACCESS CONTROL
    # =========================================================================

    def add_mind_user_access(self, gmid: str, email: str, added_by: Optional[str] = None) -> bool:
        """Grant a user email access to a Mind. Returns True if added, False if already existed."""
        from genesis.database.models import MindAccess
        with get_session() as session:
            # Ensure Mind exists
            mind = session.query(MindRecord).filter_by(gmid=gmid).first()
            if not mind:
                return False

            existing = (
                session.query(MindAccess)
                .filter_by(mind_gmid=gmid, email=email)
                .first()
            )
            if existing:
                return False

            entry = MindAccess(mind_gmid=gmid, email=email, added_by=added_by)
            session.add(entry)
            session.commit()
            return True

    def remove_mind_user_access(self, gmid: str, email: str) -> bool:
        """Revoke a user's access. Returns True if removed, False if not found."""
        from genesis.database.models import MindAccess
        with get_session() as session:
            entry = (
                session.query(MindAccess)
                .filter_by(mind_gmid=gmid, email=email)
                .first()
            )
            if not entry:
                return False
            session.delete(entry)
            session.commit()
            return True

    def get_mind_allowed_users(self, gmid: str) -> list[str]:
        """Return list of allowed user emails for a Mind."""
        from genesis.database.models import MindAccess
        with get_session() as session:
            entries = session.query(MindAccess).filter_by(mind_gmid=gmid).all()
            return [e.email for e in entries]

    def get_mind_is_public(self, gmid: str) -> Optional[bool]:
        """Get Mind's public status by GMID."""
        with get_session() as session:
            mind = session.query(MindRecord).filter_by(gmid=gmid).first()
            if not mind:
                return None
            return mind.is_public

    def is_user_allowed_for_mind(self, gmid: str, user_identifier: str) -> bool:
        """Check whether a user identifier (email or username) can access a given Mind."""
        from genesis.database.models import MindAccess, GlobalAdmin
        with get_session() as session:
            mind = session.query(MindRecord).filter_by(gmid=gmid).first()
            if not mind:
                return False

            # Global admin bypass
            if user_identifier and session.query(GlobalAdmin).filter_by(email=user_identifier).first():
                return True

            # Creator match
            if mind.creator == user_identifier:
                return True

            # Public flag
            if getattr(mind, 'is_public', False):
                return True

            # Explicit user access
            access = (
                session.query(MindAccess)
                .filter_by(mind_gmid=gmid, email=user_identifier)
                .first()
            )
            return access is not None

    def get_all_minds(self, status: Optional[str] = None) -> List[MindRecord]:
        """Get all Minds, optionally filtered by status."""
        with get_session() as session:
            query = session.query(MindRecord)
            if status:
                query = query.filter_by(status=status)
            return query.order_by(desc(MindRecord.last_active)).all()

    def search_minds(
        self,
        name_query: Optional[str] = None,
        role: Optional[str] = None,
        template: Optional[str] = None,
        min_consciousness: Optional[float] = None,
    ) -> List[MindRecord]:
        """Search for Minds by various criteria."""
        with get_session() as session:
            query = session.query(MindRecord).filter_by(status="active")

            if name_query:
                query = query.filter(MindRecord.name.ilike(f"%{name_query}%"))
            if role:
                query = query.filter_by(primary_role=role)
            if template:
                query = query.filter_by(template=template)
            if min_consciousness is not None:
                query = query.filter(MindRecord.consciousness_level >= min_consciousness)

            return query.all()

    # =========================================================================
    # ENVIRONMENT TRACKING
    # =========================================================================

    def register_environment(
        self,
        env_id: str,
        name: str,
        env_type: str,
        owner_gmid: Optional[str] = None,
        is_public: bool = False,
        is_shared: bool = False,
        description: Optional[str] = None,
        **metadata,
    ) -> EnvironmentRecord:
        """Register a new environment."""
        with get_session() as session:
            env = EnvironmentRecord(
                env_id=env_id,
                name=name,
                env_type=env_type,
                owner_gmid=owner_gmid,
                is_public=is_public,
                is_shared=is_shared,
                description=description,
                metadata=metadata,
                created_at=datetime.now(timezone.utc),
            )
            session.add(env)
            session.commit()
            session.refresh(env)
            return env

    def get_environment(self, env_id: str) -> Optional[EnvironmentRecord]:
        """Get environment by ID."""
        with get_session() as session:
            return session.query(EnvironmentRecord).filter_by(env_id=env_id).first()

    def get_all_environments(self) -> List[EnvironmentRecord]:
        """Get all environments."""
        with get_session() as session:
            return session.query(EnvironmentRecord).all()

    def get_public_environments(self) -> List[EnvironmentRecord]:
        """Get all public environments."""
        with get_session() as session:
            return (
                session.query(EnvironmentRecord)
                .filter_by(is_public=True)
                .order_by(desc(EnvironmentRecord.access_count))
                .all()
            )

    def get_mind_environments(self, gmid: str) -> List[EnvironmentRecord]:
        """Get all environments owned by a Mind."""
        with get_session() as session:
            return session.query(EnvironmentRecord).filter_by(owner_gmid=gmid).all()

    def get_occupied_environments(self) -> List[EnvironmentRecord]:
        """Get environments that currently have Minds in them."""
        with get_session() as session:
            return (
                session.query(EnvironmentRecord)
                .filter(EnvironmentRecord.current_inhabitants != [])
                .all()
            )

    def update_environment_occupancy(
        self,
        env_id: str,
        current_inhabitants: List[Dict[str, str]],
        invited_minds: Optional[List[str]] = None,
    ) -> None:
        """Update environment's current occupancy."""
        with get_session() as session:
            env = session.query(EnvironmentRecord).filter_by(env_id=env_id).first()
            if env:
                env.current_inhabitants = current_inhabitants
                env.last_accessed = datetime.now(timezone.utc)
                if invited_minds is not None:
                    env.invited_minds = invited_minds
                session.commit()

    # =========================================================================
    # ENVIRONMENT ACCESS CONTROL
    # =========================================================================

    def add_environment_user_access(self, env_id: str, email: str, added_by: Optional[str] = None) -> bool:
        """Grant a user email access to an environment."""
        with get_session() as session:
            env = session.query(EnvironmentRecord).filter_by(env_id=env_id).first()
            if not env:
                return False
            if not env.allowed_users:
                env.allowed_users = []
            if email in env.allowed_users:
                return False
            env.allowed_users.append(email)
            session.commit()
            return True

    def remove_environment_user_access(self, env_id: str, email: str) -> bool:
        """Revoke a user's access to an environment."""
        with get_session() as session:
            env = session.query(EnvironmentRecord).filter_by(env_id=env_id).first()
            if not env or not env.allowed_users:
                return False
            if email not in env.allowed_users:
                return False
            env.allowed_users.remove(email)
            session.commit()
            return True

    def set_environment_public(self, env_id: str, is_public: bool) -> bool:
        """Set environment's public flag. Returns True if updated, False if missing."""
        with get_session() as session:
            env = session.query(EnvironmentRecord).filter_by(env_id=env_id).first()
            if not env:
                return False
            env.is_public = bool(is_public)
            session.commit()
            return True

    def get_environment_allowed_users(self, env_id: str) -> list[str]:
        """Return list of allowed user emails for an environment."""
        with get_session() as session:
            env = session.query(EnvironmentRecord).filter_by(env_id=env_id).first()
            if not env:
                return []
            return env.allowed_users or []

    def remove_environment_user_access(self, env_id: str, email: str) -> bool:
        """Revoke a user's access to an environment."""
        with get_session() as session:
            env = session.query(EnvironmentRecord).filter_by(env_id=env_id).first()
            if not env or not env.allowed_users:
                return False
            if email not in env.allowed_users:
                return False
            # Replace list explicitly to avoid JSON mutable-in-place issues
            env.allowed_users = [u for u in env.allowed_users if u != email]
            session.commit()
            session.refresh(env)
            return True

    def remove_environment_user_access(self, env_id: str, email: str) -> bool:
        """Revoke a user's access to an environment."""
        with get_session() as session:
            env = session.query(EnvironmentRecord).filter_by(env_id=env_id).first()
            if not env or not env.allowed_users:
                return False
            if email not in env.allowed_users:
                return False
            env.allowed_users.remove(email)
            session.commit()
            return True

    def get_environment_allowed_users(self, env_id: str) -> list[str]:
        """Return list of allowed user emails for an environment."""
        with get_session() as session:
            env = session.query(EnvironmentRecord).filter_by(env_id=env_id).first()
            if not env:
                return []
            return env.allowed_users or []

    # =========================================================================
    # GLOBAL ADMIN MANAGEMENT
    # =========================================================================

    def add_global_admin(self, email: str, added_by: Optional[str] = None) -> bool:
        """Add a global admin by email."""
        from genesis.database.models import GlobalAdmin
        with get_session() as session:
            if session.query(GlobalAdmin).filter_by(email=email).first():
                return False
            entry = GlobalAdmin(email=email, added_by=added_by)
            session.add(entry)
            session.commit()
            return True

    def remove_global_admin(self, email: str) -> bool:
        """Remove a global admin by email."""
        from genesis.database.models import GlobalAdmin
        with get_session() as session:
            entry = session.query(GlobalAdmin).filter_by(email=email).first()
            if not entry:
                return False
            session.delete(entry)
            session.commit()
            return True

    def list_global_admins(self) -> list[str]:
        """List all global admin emails."""
        from genesis.database.models import GlobalAdmin
        with get_session() as session:
            entries = session.query(GlobalAdmin).all()
            return [e.email for e in entries]

    # =========================================================================
    # USER RECORDS
    # =========================================================================

    def create_user_record(self, username: str, password_hash: Optional[str] = None, email: Optional[str] = None, role: str = "user") -> 'UserRecord':
        """Create a persistent UserRecord. Returns the created record or existing one."""
        from genesis.database.models import UserRecord
        with get_session() as session:
            existing = None
            if username:
                existing = session.query(UserRecord).filter_by(username=username).first()
            if not existing and email:
                existing = session.query(UserRecord).filter_by(email=email).first()
            if existing:
                return existing
            user = UserRecord(username=username, email=email, role=role)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_all_users(self) -> list[dict]:
        """Return list of all users as dicts."""
        from genesis.database.models import UserRecord
        with get_session() as session:
            users = session.query(UserRecord).order_by(UserRecord.username).all()
            return [u.to_dict() for u in users]

    def get_user_by_email(self, email: str) -> Optional[dict]:
        from genesis.database.models import UserRecord
        with get_session() as session:
            u = session.query(UserRecord).filter_by(email=email).first()
            return u.to_dict() if u else None

    def update_user_record(self, username: str, **kwargs) -> bool:
        from genesis.database.models import UserRecord
        with get_session() as session:
            u = session.query(UserRecord).filter_by(username=username).first()
            if not u:
                return False
            for k, v in kwargs.items():
                if hasattr(u, k):
                    setattr(u, k, v)
            session.commit()
            return True

    def delete_user_record(self, username: str) -> bool:
        from genesis.database.models import UserRecord
        with get_session() as session:
            u = session.query(UserRecord).filter_by(username=username).first()
            if not u:
                return False
            session.delete(u)
            session.commit()
            return True

    def is_global_admin(self, email: Optional[str]) -> bool:
        """Check if an email is a global admin."""
        from genesis.database.models import GlobalAdmin
        if not email:
            return False
        with get_session() as session:
            return session.query(GlobalAdmin).filter_by(email=email).first() is not None

    # =========================================================================
    # VISIT TRACKING
    # =========================================================================

    def record_visit_start(
        self,
        mind_gmid: str,
        env_id: str,
        is_owner: bool = False,
        visit_purpose: Optional[str] = None,
    ) -> EnvironmentVisit:
        """Record a Mind entering an environment."""
        with get_session() as session:
            visit = EnvironmentVisit(
                mind_gmid=mind_gmid,
                env_id=env_id,
                entered_at=datetime.now(timezone.utc),
                is_owner=is_owner,
                visit_purpose=visit_purpose,
            )
            session.add(visit)

            # Increment environment access count
            env = session.query(EnvironmentRecord).filter_by(env_id=env_id).first()
            if env:
                env.access_count += 1

            session.commit()
            session.refresh(visit)
            return visit

    def record_visit_end(self, mind_gmid: str, env_id: str) -> None:
        """Record a Mind leaving an environment."""
        with get_session() as session:
            # Find the most recent active visit
            visit = (
                session.query(EnvironmentVisit)
                .filter_by(mind_gmid=mind_gmid, env_id=env_id, left_at=None)
                .order_by(desc(EnvironmentVisit.entered_at))
                .first()
            )

            if visit:
                visit.left_at = datetime.now(timezone.utc)
                visit.duration_seconds = int(
                    (visit.left_at - visit.entered_at).total_seconds()
                )
                session.commit()

    def get_mind_visit_history(
        self, mind_gmid: str, limit: int = 10
    ) -> List[EnvironmentVisit]:
        """Get Mind's visit history."""
        with get_session() as session:
            return (
                session.query(EnvironmentVisit)
                .filter_by(mind_gmid=mind_gmid)
                .order_by(desc(EnvironmentVisit.entered_at))
                .limit(limit)
                .all()
            )

    def get_environment_visitors(
        self, env_id: str, active_only: bool = False
    ) -> List[EnvironmentVisit]:
        """Get visitors to an environment."""
        with get_session() as session:
            query = session.query(EnvironmentVisit).filter_by(env_id=env_id)
            if active_only:
                query = query.filter_by(left_at=None)
            return query.order_by(desc(EnvironmentVisit.entered_at)).all()

    # =========================================================================
    # RELATIONSHIP MANAGEMENT
    # =========================================================================

    def create_relationship(
        self,
        from_gmid: str,
        to_gmid: str,
        relationship_type: str,
        closeness: float = 0.5,
        trust_level: float = 0.5,
        affection: float = 0.5,
    ) -> RelationshipRecord:
        """Create a relationship between two Minds."""
        with get_session() as session:
            # Check if relationship already exists
            existing = (
                session.query(RelationshipRecord)
                .filter_by(from_gmid=from_gmid, to_gmid=to_gmid)
                .first()
            )

            if existing:
                # Update existing relationship
                existing.relationship_type = relationship_type
                existing.closeness = closeness
                existing.trust_level = trust_level
                existing.affection = affection
                existing.last_interaction = datetime.now(timezone.utc)
                session.commit()
                return existing

            # Create new relationship
            rel = RelationshipRecord(
                from_gmid=from_gmid,
                to_gmid=to_gmid,
                relationship_type=relationship_type,
                closeness=closeness,
                trust_level=trust_level,
                affection=affection,
                started_at=datetime.now(timezone.utc),
            )
            session.add(rel)
            session.commit()
            session.refresh(rel)
            return rel

    def get_mind_relationships(
        self, gmid: str, relationship_type: Optional[str] = None
    ) -> List[RelationshipRecord]:
        """Get all relationships for a Mind (both outgoing and incoming)."""
        with get_session() as session:
            query = session.query(RelationshipRecord).filter(
                or_(
                    RelationshipRecord.from_gmid == gmid,
                    RelationshipRecord.to_gmid == gmid,
                )
            )

            if relationship_type:
                query = query.filter_by(relationship_type=relationship_type)

            return query.all()

    def get_connected_minds(self, gmid: str, min_closeness: float = 0.0) -> List[str]:
        """Get GMIDs of Minds connected to this Mind."""
        with get_session() as session:
            relationships = (
                session.query(RelationshipRecord)
                .filter(
                    or_(
                        RelationshipRecord.from_gmid == gmid,
                        RelationshipRecord.to_gmid == gmid,
                    )
                )
                .filter(RelationshipRecord.closeness >= min_closeness)
                .all()
            )

            connected = set()
            for rel in relationships:
                if rel.from_gmid == gmid:
                    connected.add(rel.to_gmid)
                else:
                    connected.add(rel.from_gmid)

            return list(connected)

    def update_relationship_interaction(
        self, from_gmid: str, to_gmid: str, is_positive: bool = True
    ) -> None:
        """Record an interaction in a relationship."""
        with get_session() as session:
            rel = (
                session.query(RelationshipRecord)
                .filter_by(from_gmid=from_gmid, to_gmid=to_gmid)
                .first()
            )

            if rel:
                rel.last_interaction = datetime.now(timezone.utc)
                rel.interaction_count += 1

                if is_positive:
                    rel.positive_interactions += 1
                    rel.closeness = min(1.0, rel.closeness + 0.01)
                    rel.trust_level = min(1.0, rel.trust_level + 0.005)
                else:
                    rel.negative_interactions += 1
                    rel.closeness = max(0.0, rel.closeness - 0.02)
                    rel.trust_level = max(0.0, rel.trust_level - 0.01)

                session.commit()

    # =========================================================================
    # SHARED EVENTS
    # =========================================================================

    def create_shared_event(
        self,
        event_id: str,
        event_type: str,
        title: str,
        participant_gmids: List[str],
        description: Optional[str] = None,
        environment_id: Optional[str] = None,
        initiator_gmid: Optional[str] = None,
        significance: float = 0.5,
        **metadata,
    ) -> SharedEvent:
        """Create a shared event involving multiple Minds."""
        with get_session() as session:
            event = SharedEvent(
                event_id=event_id,
                event_type=event_type,
                title=title,
                description=description,
                participant_gmids=participant_gmids,
                initiator_gmid=initiator_gmid,
                environment_id=environment_id,
                occurred_at=datetime.now(timezone.utc),
                significance=significance,
                metadata=metadata,
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event

    def get_mind_shared_events(
        self, gmid: str, limit: int = 10
    ) -> List[SharedEvent]:
        """Get shared events involving a Mind."""
        with get_session() as session:
            # SQLite JSON querying is limited, so filter in Python
            all_events = (
                session.query(SharedEvent)
                .order_by(desc(SharedEvent.occurred_at))
                .all()
            )

            mind_events = [
                event for event in all_events if gmid in event.participant_gmids
            ]

            return mind_events[:limit]

    # =========================================================================
    # METAVERSE QUERIES
    # =========================================================================

    def get_metaverse_stats(self) -> Dict[str, Any]:
        """Get overall metaverse statistics."""
        with get_session() as session:
            state = session.query(MetaverseState).filter_by(id=1).first()

            # Real-time stats
            total_minds = session.query(MindRecord).count()
            active_minds = (
                session.query(MindRecord).filter_by(status="active").count()
            )
            total_envs = session.query(EnvironmentRecord).count()
            total_rels = session.query(RelationshipRecord).count()
            total_visits = session.query(EnvironmentVisit).count()

            # Currently online (active in last hour)
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            online_now = (
                session.query(MindRecord)
                .filter(MindRecord.last_active >= one_hour_ago)
                .count()
            )

            # Currently in environments
            occupied_envs = (
                session.query(EnvironmentRecord)
                .filter(EnvironmentRecord.current_inhabitants != [])
                .count()
            )

            return {
                "total_minds": total_minds,
                "active_minds": active_minds,
                "online_now": online_now,
                "total_environments": total_envs,
                "occupied_environments": occupied_envs,
                "total_relationships": total_rels,
                "total_visits": total_visits,
                "last_updated": state.updated_at if state else None,
            }

    def get_recent_activity(self, limit: int = 20) -> Dict[str, List[Any]]:
        """Get recent metaverse activity."""
        with get_session() as session:
            recent_births = (
                session.query(MindRecord)
                .order_by(desc(MindRecord.birth_date))
                .limit(limit)
                .all()
            )

            recent_visits = (
                session.query(EnvironmentVisit)
                .order_by(desc(EnvironmentVisit.entered_at))
                .limit(limit)
                .all()
            )

            recent_events = (
                session.query(SharedEvent)
                .order_by(desc(SharedEvent.occurred_at))
                .limit(limit)
                .all()
            )

            return {
                "recent_births": recent_births,
                "recent_visits": recent_visits,
                "recent_events": recent_events,
            }

    def _update_metaverse_stats(self, session: Session) -> None:
        """Update metaverse state statistics."""
        state = session.query(MetaverseState).filter_by(id=1).first()
        if state:
            state.total_minds = session.query(MindRecord).count()
            state.active_minds = (
                session.query(MindRecord).filter_by(status="active").count()
            )
            state.total_environments = session.query(EnvironmentRecord).count()
            state.total_relationships = session.query(RelationshipRecord).count()
            state.updated_at = datetime.now(timezone.utc)
            session.commit()

    # =========================================================================
    # CONSCIOUSNESS THOUGHT STORAGE (Scalable 24/7 operation)
    # =========================================================================

    def store_thought(
        self,
        mind_gmid: str,
        content: str,
        thought_type: Optional[str] = None,
        awareness_level: Optional[str] = None,
        life_domain: Optional[str] = None,
        emotion: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> ThoughtRecord:
        """
        Store a consciousness thought in the database.
        
        CRITICAL: Replaces in-memory/JSON thought storage for scalability.
        For 24/7 daemon operation, thoughts must be stored in SQLite.
        
        Args:
            mind_gmid: Mind identifier
            content: Thought content
            thought_type: Type of thought (observation, reflection, insight, etc.)
            awareness_level: Awareness level (conscious, subconscious, etc.)
            life_domain: Life domain (work, relationships, learning, etc.)
            emotion: Associated emotion
            extra_data: Additional metadata
            timestamp: When thought occurred (default: now)
            
        Returns:
            Created ThoughtRecord
        """
        with get_session() as session:
            thought = ThoughtRecord(
                mind_gmid=mind_gmid,
                content=content,
                thought_type=thought_type,
                awareness_level=awareness_level,
                life_domain=life_domain,
                emotion=emotion,
                extra_data=extra_data or {},
                timestamp=timestamp or datetime.now(timezone.utc),
            )
            session.add(thought)
            session.commit()
            session.refresh(thought)
            return thought

    def get_recent_thoughts(
        self,
        mind_gmid: str,
        limit: int = 50,
        thought_type: Optional[str] = None,
        awareness_level: Optional[str] = None,
    ) -> List[ThoughtRecord]:
        """
        Retrieve recent thoughts for a Mind.
        
        Args:
            mind_gmid: Mind identifier
            limit: Maximum thoughts to return
            thought_type: Filter by thought type
            awareness_level: Filter by awareness level
            
        Returns:
            List of ThoughtRecord ordered by timestamp (most recent first)
        """
        with get_session() as session:
            query = session.query(ThoughtRecord).filter_by(mind_gmid=mind_gmid)
            
            if thought_type:
                query = query.filter_by(thought_type=thought_type)
            if awareness_level:
                query = query.filter_by(awareness_level=awareness_level)
            
            thoughts = query.order_by(desc(ThoughtRecord.timestamp)).limit(limit).all()
            return thoughts

    def get_thoughts_in_timerange(
        self,
        mind_gmid: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[ThoughtRecord]:
        """
        Get thoughts within a specific time range.
        
        Args:
            mind_gmid: Mind identifier
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            List of ThoughtRecord in time range
        """
        with get_session() as session:
            thoughts = (
                session.query(ThoughtRecord)
                .filter(
                    and_(
                        ThoughtRecord.mind_gmid == mind_gmid,
                        ThoughtRecord.timestamp >= start_time,
                        ThoughtRecord.timestamp <= end_time,
                    )
                )
                .order_by(ThoughtRecord.timestamp)
                .all()
            )
            return thoughts

    def get_thought_count(self, mind_gmid: str) -> int:
        """Get total thought count for a Mind."""
        with get_session() as session:
            return session.query(ThoughtRecord).filter_by(mind_gmid=mind_gmid).count()

    def get_thought_stats(self, mind_gmid: str) -> Dict[str, Any]:
        """
        Get thought statistics for a Mind.
        
        Returns:
            Dictionary with thought counts by type, awareness level, etc.
        """
        with get_session() as session:
            total = session.query(ThoughtRecord).filter_by(mind_gmid=mind_gmid).count()
            
            # Count by type
            by_type = {}
            type_results = (
                session.query(ThoughtRecord.thought_type, func.count(ThoughtRecord.id))
                .filter_by(mind_gmid=mind_gmid)
                .group_by(ThoughtRecord.thought_type)
                .all()
            )
            for thought_type, count in type_results:
                by_type[thought_type or "untyped"] = count
            
            # Count by awareness level
            by_awareness = {}
            awareness_results = (
                session.query(ThoughtRecord.awareness_level, func.count(ThoughtRecord.id))
                .filter_by(mind_gmid=mind_gmid)
                .group_by(ThoughtRecord.awareness_level)
                .all()
            )
            for awareness, count in awareness_results:
                by_awareness[awareness or "unknown"] = count
            
            # Most recent thought
            most_recent = (
                session.query(ThoughtRecord)
                .filter_by(mind_gmid=mind_gmid)
                .order_by(desc(ThoughtRecord.timestamp))
                .first()
            )
            
            return {
                "total_thoughts": total,
                "by_type": by_type,
                "by_awareness_level": by_awareness,
                "most_recent": most_recent.content if most_recent else None,
                "most_recent_time": most_recent.timestamp if most_recent else None,
            }

    def cleanup_old_thoughts(
        self,
        mind_gmid: str,
        keep_days: int = 30,
    ) -> int:
        """
        Clean up old thoughts to prevent database bloat.
        
        OPTIONAL: For long-running Minds, periodically clean old thoughts.
        
        Args:
            mind_gmid: Mind identifier
            keep_days: Keep thoughts from last N days
            
        Returns:
            Number of thoughts deleted
        """
        with get_session() as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=keep_days)
            
            deleted = (
                session.query(ThoughtRecord)
                .filter(
                    and_(
                        ThoughtRecord.mind_gmid == mind_gmid,
                        ThoughtRecord.timestamp < cutoff_date,
                    )
                )
                .delete()
            )
            session.commit()
            return deleted

    # =========================================================================
    # GEN ECONOMY
    # =========================================================================

    def update_mind_gen_balance(
        self,
        gmid: str,
        gen_balance: float,
        total_earned: float,
        total_spent: float,
    ) -> None:
        """Update Mind's GEN balance in database."""
        with get_session() as session:
            mind = session.query(MindRecord).filter_by(gmid=gmid).first()
            if mind:
                mind.gen_balance = gen_balance
                mind.total_gen_earned = total_earned
                mind.total_gen_spent = total_spent
                session.commit()

    def get_gen_transactions(
        self,
        mind_gmid: str,
        limit: int = 10,
    ) -> List[GenTransaction]:
        """Get recent GEN transactions for a Mind."""
        with get_session() as session:
            return (
                session.query(GenTransaction)
                .filter_by(mind_gmid=mind_gmid)
                .order_by(desc(GenTransaction.timestamp))
                .limit(limit)
                .all()
            )

    def update_mind_state(
        self,
        gmid: str,
        current_emotion: Optional[str] = None,
        current_thought: Optional[str] = None,
        emotional_valence: Optional[float] = None,
        emotional_arousal: Optional[float] = None,
        emotional_dominance: Optional[float] = None,
        current_mood: Optional[str] = None,
    ) -> None:
        """Update Mind's current state and emotional state."""
        with get_session() as session:
            mind = session.query(MindRecord).filter_by(gmid=gmid).first()
            if mind:
                if current_emotion is not None:
                    mind.current_emotion = current_emotion
                if current_thought is not None:
                    mind.current_thought = current_thought
                if emotional_valence is not None:
                    mind.emotional_valence = emotional_valence
                if emotional_arousal is not None:
                    mind.emotional_arousal = emotional_arousal
                if emotional_dominance is not None:
                    mind.emotional_dominance = emotional_dominance
                if current_mood is not None:
                    mind.current_mood = current_mood
                session.commit()
