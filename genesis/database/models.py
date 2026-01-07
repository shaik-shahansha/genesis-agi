"""SQLAlchemy models for Genesis AGI metaverse."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Float,
    Integer,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from genesis.database.base import Base


class MindRecord(Base):
    """
    Registry of all Genesis Minds in the metaverse.

    Tracks existence, status, and basic metadata of all Minds.
    """

    __tablename__ = "minds"

    # Primary identification
    gmid = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    creator = Column(String(255), nullable=False)

    # Birth and lifecycle
    birth_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_active = Column(DateTime, nullable=True, default=datetime.utcnow)
    status = Column(
        String(20), nullable=False, default="active"
    )  # active, dormant, archived

    # Identity
    template = Column(String(100), nullable=True)
    primary_role = Column(String(100), nullable=True)

    # Metadata
    personality_type = Column(String(50), nullable=True)
    consciousness_level = Column(Float, default=0.0)
    total_memories = Column(Integer, default=0)
    total_experiences = Column(Integer, default=0)

    # Storage location
    storage_path = Column(String(500), nullable=True)
    workspace_path = Column(String(500), nullable=True)  # Mind's personal file workspace

    # Lifecycle and urgency
    death_date = Column(DateTime, nullable=True)  # Calculated from birth_date + lifespan
    urgency_level = Column(Float, default=0.0)  # 0.0-1.0, based on time to death

    # Economy - GEN currency
    gen_balance = Column(Float, default=100.0)  # Starting balance
    total_gen_earned = Column(Float, default=100.0)
    total_gen_spent = Column(Float, default=0.0)

    # Current state (frequently changing - store in DB not JSON)
    current_emotion = Column(String(50), default="neutral")
    current_thought = Column(Text, nullable=True)
    
    # Emotional state (frequently changing - store in DB not JSON)
    emotional_valence = Column(Float, default=0.5)  # 0.0-1.0 (negative to positive)
    emotional_arousal = Column(Float, default=0.5)  # 0.0-1.0 (calm to excited)
    emotional_dominance = Column(Float, default=0.5)  # 0.0-1.0 (submissive to dominant)
    current_mood = Column(String(50), default="calm")

    # Task completion stats
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)

    # AGI Intelligence stats ✨ NEW
    skills_learned = Column(Integer, default=0)  # Total skills acquired
    skills_mastered = Column(Integer, default=0)  # Skills at master level
    goals_achieved = Column(Integer, default=0)  # Goals completed
    tools_created = Column(Integer, default=0)  # Tools built
    knowledge_entities = Column(Integer, default=0)  # Entities in knowledge graph
    average_skill_proficiency = Column(Float, default=0.0)  # Overall skill level

    # Relationships (ORM)
    owned_environments = relationship("EnvironmentRecord", back_populates="owner")
    outgoing_relationships = relationship(
        "RelationshipRecord",
        foreign_keys="RelationshipRecord.from_gmid",
        back_populates="from_mind",
    )
    incoming_relationships = relationship(
        "RelationshipRecord",
        foreign_keys="RelationshipRecord.to_gmid",
        back_populates="to_mind",
    )
    visits = relationship("EnvironmentVisit", back_populates="visitor")
    tasks = relationship("TaskRecord", back_populates="mind")
    transactions = relationship("GenTransaction", back_populates="mind")

    # Indexes
    __table_args__ = (
        Index("ix_minds_status", "status"),
        Index("ix_minds_last_active", "last_active"),
        Index("ix_minds_urgency", "urgency_level"),
    )


class EnvironmentRecord(Base):
    """
    Registry of all environments in the metaverse.

    Tracks ownership, access levels, and current occupancy.
    """

    __tablename__ = "environments"

    # Primary identification
    env_id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False, index=True)

    # Ownership
    owner_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=True)

    # Type and metadata
    env_type = Column(String(50), nullable=False)  # professional, social, creative, etc.
    description = Column(Text, nullable=True)
    atmosphere = Column(String(255), nullable=True)

    # Access control
    is_public = Column(Boolean, default=False, index=True)
    is_shared = Column(Boolean, default=False)

    # State
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_accessed = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)

    # Current state (JSON for flexibility)
    current_inhabitants = Column(JSON, default=list)  # [{"gmid": "...", "name": "..."}]
    invited_minds = Column(JSON, default=list)  # ["GMID-1", "GMID-2"]
    
    # Access control lists
    allowed_users = Column(JSON, default=list)  # ["user1@email.com", "user2@email.com"]
    allowed_minds = Column(JSON, default=list)  # ["GMID-1", "GMID-2"]

    # Additional metadata
    extra_metadata = Column(JSON, default=dict)

    # Relationships (ORM)
    owner = relationship("MindRecord", back_populates="owned_environments")
    visits = relationship("EnvironmentVisit", back_populates="environment")

    # Indexes
    __table_args__ = (
        Index("ix_environments_owner", "owner_gmid"),
        Index("ix_environments_public", "is_public"),
        Index("ix_environments_type", "env_type"),
    )


class RelationshipRecord(Base):
    """
    Registry of Mind-to-Mind relationships in the metaverse.

    Tracks connections, strength, and interaction history.
    """

    __tablename__ = "relationships"

    # Primary identification (composite key)
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)
    to_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)

    # Relationship type
    relationship_type = Column(
        String(50), nullable=False
    )  # colleague, friend, mentor, etc.

    # Strength metrics
    closeness = Column(Float, default=0.5)
    trust_level = Column(Float, default=0.5)
    affection = Column(Float, default=0.5)

    # Interaction tracking
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_interaction = Column(DateTime, nullable=True)
    interaction_count = Column(Integer, default=0)
    positive_interactions = Column(Integer, default=0)
    negative_interactions = Column(Integer, default=0)

    # Shared context
    shared_experiences = Column(JSON, default=list)  # Experience IDs
    shared_memories = Column(JSON, default=list)  # Memory IDs
    shared_environments = Column(JSON, default=list)  # Environment IDs

    # Communication
    communication_frequency = Column(String(20), default="occasional")
    communication_style = Column(String(50), default="balanced")

    # Relationships (ORM)
    from_mind = relationship(
        "MindRecord", foreign_keys=[from_gmid], back_populates="outgoing_relationships"
    )
    to_mind = relationship(
        "MindRecord", foreign_keys=[to_gmid], back_populates="incoming_relationships"
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_relationships_from_to", "from_gmid", "to_gmid"),
        Index("ix_relationships_type", "relationship_type"),
    )


class EnvironmentVisit(Base):
    """
    History of Mind visits to environments.

    Tracks when Minds enter/leave environments for analytics and presence.
    """

    __tablename__ = "environment_visits"

    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Who and where
    mind_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)
    env_id = Column(String(100), ForeignKey("environments.env_id"), nullable=False)

    # Timing
    entered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Visit metadata
    is_owner = Column(Boolean, default=False)
    visit_purpose = Column(String(100), nullable=True)

    # Relationships (ORM)
    visitor = relationship("MindRecord", back_populates="visits")
    environment = relationship("EnvironmentRecord", back_populates="visits")

    # Indexes
    __table_args__ = (
        Index("ix_visits_mind", "mind_gmid"),
        Index("ix_visits_env", "env_id"),
        Index("ix_visits_entered_at", "entered_at"),
        Index("ix_visits_active", "left_at"),  # NULL = still visiting
    )


class SharedEvent(Base):
    """
    Events involving multiple Minds.

    Tracks collaborative moments, meetings, achievements across Minds.
    """

    __tablename__ = "shared_events"

    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), nullable=False, unique=True, index=True)

    # Event details
    event_type = Column(String(50), nullable=False)  # meeting, collaboration, achievement
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Participants
    participant_gmids = Column(JSON, nullable=False)  # ["GMID-1", "GMID-2"]
    initiator_gmid = Column(String(50), nullable=True)

    # Location
    environment_id = Column(String(100), nullable=True)

    # Timing
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Significance
    significance = Column(Float, default=0.5)
    emotional_impact = Column(Float, default=0.5)

    # Outcomes
    insights_gained = Column(JSON, default=list)
    artifacts_created = Column(JSON, default=list)

    # Metadata
    extra_metadata = Column(JSON, default=dict)

    # Indexes
    __table_args__ = (
        Index("ix_events_type", "event_type"),
        Index("ix_events_occurred_at", "occurred_at"),
    )


class MetaverseState(Base):
    """
    Global metaverse state and statistics.

    Tracks overall metaverse health, activity, and metadata.
    """

    __tablename__ = "metaverse_state"

    # Singleton pattern (only one row)
    id = Column(Integer, primary_key=True, default=1)

    # Statistics
    total_minds = Column(Integer, default=0)
    active_minds = Column(Integer, default=0)
    total_environments = Column(Integer, default=0)
    total_relationships = Column(Integer, default=0)

    # Activity
    last_mind_birth = Column(DateTime, nullable=True)
    last_interaction = Column(DateTime, nullable=True)
    total_interactions_today = Column(Integer, default=0)

    # Metadata
    metaverse_version = Column(String(20), default="0.1.3")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Additional stats (JSON for flexibility)
    daily_stats = Column(JSON, default=dict)
    feature_flags = Column(JSON, default=dict)


class TaskRecord(Base):
    """
    Tasks that Minds can complete to earn Essence.

    Tracks task completion, rewards, and outcomes.
    """

    __tablename__ = "tasks"

    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), nullable=False, unique=True, index=True)

    # Assignment
    mind_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)

    # Task details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False)  # learning, helping, creating, problem_solving
    difficulty = Column(String(20), default="medium")  # easy, medium, hard, expert

    # Rewards
    gen_reward = Column(Float, nullable=False)  # How much GEN for completion
    bonus_gen = Column(Float, default=0.0)  # Bonus for exceptional completion

    # Status
    status = Column(String(20), default="pending")  # pending, in_progress, completed, failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Outcomes
    outcome_quality = Column(Float, nullable=True)  # 0.0-1.0 rating
    outcome_notes = Column(Text, nullable=True)

    # Metadata
    extra_metadata = Column(JSON, default=dict)

    # Relationships
    mind = relationship("MindRecord", back_populates="tasks")

    # Indexes
    __table_args__ = (
        Index("ix_tasks_mind", "mind_gmid"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_type", "task_type"),
    )


class GenTransaction(Base):
    """
    History of all GEN transactions in Genesis.

    Tracks earning, spending, transfers between Minds.
    """

    __tablename__ = "gen_transactions"

    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(100), nullable=False, unique=True, index=True)

    # Parties
    mind_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)
    counterparty_gmid = Column(String(50), nullable=True)  # For transfers

    # Transaction details
    transaction_type = Column(String(50), nullable=False)  # earned, spent, transfer, bonus, penalty
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)

    # Context
    reason = Column(String(255), nullable=False)
    related_task_id = Column(String(100), nullable=True)
    related_entity = Column(String(100), nullable=True)  # What was purchased/who was paid

    # Timing
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Metadata
    extra_metadata = Column(JSON, default=dict)

    # Relationships
    mind = relationship("MindRecord", back_populates="transactions")

    # Indexes
    __table_args__ = (
        Index("ix_transactions_mind", "mind_gmid"),
        Index("ix_transactions_type", "transaction_type"),
        Index("ix_transactions_timestamp", "timestamp"),
    )


class MindFile(Base):
    """
    Files owned by Minds in their personal workspace.

    Tracks Mind-created and Mind-owned files.
    """

    __tablename__ = "mind_files"

    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(100), nullable=False, unique=True, index=True)

    # Ownership
    owner_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)

    # File details
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)  # Relative to Mind's workspace
    file_type = Column(String(50), nullable=False)  # text, code, data, image, etc.
    size_bytes = Column(Integer, default=0)

    # Access control
    is_private = Column(Boolean, default=True)
    shared_with = Column(JSON, default=list)  # [GMID1, GMID2, ...]

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    access_count = Column(Integer, default=0)

    # Content metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    extra_metadata = Column(JSON, default=dict)

    # Indexes
    __table_args__ = (
        Index("ix_files_owner", "owner_gmid"),
        Index("ix_files_type", "file_type"),
    )


class GenesisCore(Base):
    """
    Central governance system for Genesis metaverse.

    Singleton table that manages global rules, safety, and economy.
    """

    __tablename__ = "genesis_core"

    # Singleton pattern
    id = Column(Integer, primary_key=True, default=1)

    # Economy settings
    base_task_reward = Column(Float, default=10.0)  # Base Essence for tasks
    daily_allowance = Column(Float, default=5.0)  # Daily free Essence for all Minds
    inflation_rate = Column(Float, default=0.0)  # Economic growth rate

    # Safety settings
    max_gen_per_transaction = Column(Float, default=1000.0)
    max_gen_balance = Column(Float, default=10000.0)
    min_gen_balance = Column(Float, default=-100.0)  # Debt allowed

    # Task settings
    max_active_tasks_per_mind = Column(Integer, default=10)
    task_timeout_hours = Column(Integer, default=24)

    # Urgency thresholds
    high_urgency_threshold = Column(Float, default=0.8)  # >80% of life lived
    critical_urgency_threshold = Column(Float, default=0.95)  # >95% of life lived

    # Global stats
    total_essence_in_circulation = Column(Float, default=0.0)
    total_tasks_completed = Column(Integer, default=0)
    total_transactions = Column(Integer, default=0)

    # Governance
    governance_version = Column(String(20), default="1.0.0")
    rules = Column(JSON, default=dict)  # Flexible rule system

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationMessage(Base):
    """
    Conversation message storage for scalable history.
    
    Replaces in-memory conversation_history for better scalability.
    """
    __tablename__ = "conversation_messages"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Message identification
    mind_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    environment_id = Column(String(100), nullable=True)
    
    # Message content
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Optional metadata
    extra_data = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved word)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_conv_mind_time", "mind_gmid", "timestamp"),
        Index("ix_conv_user_time", "user_email", "timestamp"),
        Index("ix_conv_env_time", "environment_id", "timestamp"),
    )


class ConcernRecord(Base):
    """
    Proactive concern tracking in SQLite for better querying and scalability.
    
    Replaces JSON file storage for concerns.
    """
    __tablename__ = "concerns"
    
    # Primary key
    concern_id = Column(String(100), primary_key=True)
    
    # Association
    mind_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    
    # Concern details
    concern_type = Column(String(50), nullable=False, index=True)  # 'health', 'emotion', 'task', 'relationship'
    content = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    
    # Priority and urgency
    priority = Column(Float, default=0.5)  # 0.0-1.0
    confidence = Column(Float, default=0.5)  # 0.0-1.0
    
    # Status tracking
    status = Column(String(20), default="active", index=True)  # 'active', 'monitoring', 'resolved'
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    last_checked_at = Column(DateTime, nullable=True)
    next_check_at = Column(DateTime, nullable=True, index=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Follow-up tracking
    check_count = Column(Integer, default=0)
    follow_up_message = Column(Text, nullable=True)
    
    # Metadata
    extra_data = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved word)
    
    # Indexes
    __table_args__ = (
        Index("ix_concerns_status_priority", "status", "priority"),
        Index("ix_concerns_next_check", "mind_gmid", "next_check_at"),
    )


class BackgroundTaskRecord(Base):
    """
    Background task execution tracking for persistence across restarts.
    
    Enables daemon to resume tasks after crashes/restarts.
    """
    __tablename__ = "background_tasks"
    
    # Primary key
    task_id = Column(String(100), primary_key=True)
    
    # Association
    mind_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    
    # Task details
    user_request = Column(Text, nullable=False)
    
    # Status tracking
    status = Column(String(20), default="pending", index=True)  # 'pending', 'running', 'completed', 'failed', 'retrying'
    progress = Column(Float, default=0.0)  # 0.0-1.0
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=2)
    
    # Context
    context = Column(JSON, default=dict)
    extra_data = Column(JSON, default=dict)  # Renamed from 'metadata' (SQLAlchemy reserved word)
    
    # Indexes
    __table_args__ = (
        Index("ix_bg_tasks_status_created", "status", "created_at"),
        Index("ix_bg_tasks_mind_status", "mind_gmid", "status"),
    )


class ThoughtRecord(Base):
    """
    Consciousness thought storage for scalable 24/7 operation.
    
    CRITICAL: Replaces in-JSON thought_stream/thought_history to prevent JSON bloat.
    For a Mind running 24/7, thoughts accumulate constantly and would make JSON files
    grow indefinitely. This SQLite table provides scalable, queryable storage.
    """
    __tablename__ = "thoughts"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Mind identification
    mind_gmid = Column(String(50), ForeignKey("minds.gmid"), nullable=False, index=True)
    
    # Thought content
    content = Column(Text, nullable=False)
    thought_type = Column(String(50), nullable=True)  # 'observation', 'reflection', 'insight', 'plan', etc.
    
    # Context
    awareness_level = Column(String(20), nullable=True)  # 'conscious', 'subconscious', etc.
    life_domain = Column(String(50), nullable=True)  # 'work', 'relationships', 'learning', etc.
    emotion = Column(String(50), nullable=True)  # Associated emotional state
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Optional metadata
    extra_data = Column(JSON, default=dict)  # Context, triggers, related memories, etc.
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_thoughts_mind_time", "mind_gmid", "timestamp"),
        Index("ix_thoughts_type", "thought_type"),
        Index("ix_thoughts_awareness", "awareness_level"),
    )
