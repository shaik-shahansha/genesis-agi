"""Initial metaverse schema

Revision ID: 001_initial
Revises:
Create Date: 2025-12-07 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial metaverse database schema."""

    # Create minds table
    op.create_table(
        'minds',
        sa.Column('gmid', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('creator', sa.String(255), nullable=False),
        sa.Column('birth_date', sa.DateTime, nullable=False),
        sa.Column('last_active', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('template', sa.String(100), nullable=True),
        sa.Column('primary_role', sa.String(100), nullable=True),
        sa.Column('personality_type', sa.String(50), nullable=True),
        sa.Column('consciousness_level', sa.Float, default=0.0),
        sa.Column('total_memories', sa.Integer, default=0),
        sa.Column('total_experiences', sa.Integer, default=0),
        sa.Column('storage_path', sa.String(500), nullable=True),
    )

    op.create_index('ix_minds_status', 'minds', ['status'])
    op.create_index('ix_minds_last_active', 'minds', ['last_active'])

    # Create environments table
    op.create_table(
        'environments',
        sa.Column('env_id', sa.String(100), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('owner_gmid', sa.String(50), sa.ForeignKey('minds.gmid'), nullable=True),
        sa.Column('env_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('atmosphere', sa.String(255), nullable=True),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('is_shared', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('last_accessed', sa.DateTime, nullable=True),
        sa.Column('access_count', sa.Integer, default=0),
        sa.Column('current_inhabitants', sa.JSON, default=[]),
        sa.Column('invited_minds', sa.JSON, default=[]),
        sa.Column('extra_metadata', sa.JSON, default={}),
    )

    op.create_index('ix_environments_owner', 'environments', ['owner_gmid'])
    op.create_index('ix_environments_public', 'environments', ['is_public'])
    op.create_index('ix_environments_type', 'environments', ['env_type'])

    # Create relationships table
    op.create_table(
        'relationships',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('from_gmid', sa.String(50), sa.ForeignKey('minds.gmid'), nullable=False),
        sa.Column('to_gmid', sa.String(50), sa.ForeignKey('minds.gmid'), nullable=False),
        sa.Column('relationship_type', sa.String(50), nullable=False),
        sa.Column('closeness', sa.Float, default=0.5),
        sa.Column('trust_level', sa.Float, default=0.5),
        sa.Column('affection', sa.Float, default=0.5),
        sa.Column('started_at', sa.DateTime, nullable=False),
        sa.Column('last_interaction', sa.DateTime, nullable=True),
        sa.Column('interaction_count', sa.Integer, default=0),
        sa.Column('positive_interactions', sa.Integer, default=0),
        sa.Column('negative_interactions', sa.Integer, default=0),
        sa.Column('shared_experiences', sa.JSON, default=[]),
        sa.Column('shared_memories', sa.JSON, default=[]),
        sa.Column('shared_environments', sa.JSON, default=[]),
        sa.Column('communication_frequency', sa.String(20), default='occasional'),
        sa.Column('communication_style', sa.String(50), default='balanced'),
    )

    op.create_index('ix_relationships_from_to', 'relationships', ['from_gmid', 'to_gmid'])
    op.create_index('ix_relationships_type', 'relationships', ['relationship_type'])

    # Create environment_visits table
    op.create_table(
        'environment_visits',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('mind_gmid', sa.String(50), sa.ForeignKey('minds.gmid'), nullable=False),
        sa.Column('env_id', sa.String(100), sa.ForeignKey('environments.env_id'), nullable=False),
        sa.Column('entered_at', sa.DateTime, nullable=False),
        sa.Column('left_at', sa.DateTime, nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('is_owner', sa.Boolean, default=False),
        sa.Column('visit_purpose', sa.String(100), nullable=True),
    )

    op.create_index('ix_visits_mind', 'environment_visits', ['mind_gmid'])
    op.create_index('ix_visits_env', 'environment_visits', ['env_id'])
    op.create_index('ix_visits_entered_at', 'environment_visits', ['entered_at'])
    op.create_index('ix_visits_active', 'environment_visits', ['left_at'])

    # Create shared_events table
    op.create_table(
        'shared_events',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(100), nullable=False, unique=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('participant_gmids', sa.JSON, nullable=False),
        sa.Column('initiator_gmid', sa.String(50), nullable=True),
        sa.Column('environment_id', sa.String(100), nullable=True),
        sa.Column('occurred_at', sa.DateTime, nullable=False),
        sa.Column('significance', sa.Float, default=0.5),
        sa.Column('emotional_impact', sa.Float, default=0.5),
        sa.Column('insights_gained', sa.JSON, default=[]),
        sa.Column('artifacts_created', sa.JSON, default=[]),
        sa.Column('extra_metadata', sa.JSON, default={}),
    )

    op.create_index('ix_events_type', 'shared_events', ['event_type'])
    op.create_index('ix_events_occurred_at', 'shared_events', ['occurred_at'])

    # Create metaverse_state table
    op.create_table(
        'metaverse_state',
        sa.Column('id', sa.Integer, primary_key=True, default=1),
        sa.Column('total_minds', sa.Integer, default=0),
        sa.Column('active_minds', sa.Integer, default=0),
        sa.Column('total_environments', sa.Integer, default=0),
        sa.Column('total_relationships', sa.Integer, default=0),
        sa.Column('last_mind_birth', sa.DateTime, nullable=True),
        sa.Column('last_interaction', sa.DateTime, nullable=True),
        sa.Column('total_interactions_today', sa.Integer, default=0),
        sa.Column('metaverse_version', sa.String(20), default='0.1.0'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('daily_stats', sa.JSON, default={}),
        sa.Column('feature_flags', sa.JSON, default={}),
    )

    # Insert initial metaverse state
    op.execute("""
        INSERT INTO metaverse_state (id, created_at, updated_at)
        VALUES (1, datetime('now'), datetime('now'))
    """)


def downgrade() -> None:
    """Drop all metaverse tables."""
    op.drop_table('metaverse_state')
    op.drop_table('shared_events')
    op.drop_table('environment_visits')
    op.drop_table('relationships')
    op.drop_table('environments')
    op.drop_table('minds')
