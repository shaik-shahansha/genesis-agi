"""Add ThoughtRecord table for scalable consciousness thought storage

Revision ID: 003_add_thought_storage
Revises: 002_add_access_control
Create Date: 2026-01-04 15:00:00.000000

CRITICAL ARCHITECTURE CHANGE:
This migration moves consciousness thoughts from JSON files to SQLite database.

WHY:
- Minds running 24/7 generate thousands of thoughts
- JSON files bloat to unmanageable sizes
- SQLite provides scalable, queryable storage
- Prevents daemon performance degradation

WHAT:
- Creates 'thoughts' table for all consciousness thoughts
- Indexed by mind_gmid and timestamp for fast queries
- Supports thought types, awareness levels, emotions
- Stores metadata in JSON for flexibility

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_add_thought_storage'
down_revision: Union[str, None] = '002_add_access_control'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create thoughts table for consciousness thought storage."""
    
    op.create_table(
        'thoughts',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('mind_gmid', sa.String(50), sa.ForeignKey('minds.gmid'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('thought_type', sa.String(50), nullable=True),
        sa.Column('awareness_level', sa.String(20), nullable=True),
        sa.Column('life_domain', sa.String(50), nullable=True),
        sa.Column('emotion', sa.String(50), nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('extra_data', sa.JSON, default=dict),
    )
    
    # Create indexes for efficient queries
    op.create_index('ix_thoughts_mind_gmid', 'thoughts', ['mind_gmid'])
    op.create_index('ix_thoughts_timestamp', 'thoughts', ['timestamp'])
    op.create_index('ix_thoughts_mind_time', 'thoughts', ['mind_gmid', 'timestamp'])
    op.create_index('ix_thoughts_type', 'thoughts', ['thought_type'])
    op.create_index('ix_thoughts_awareness', 'thoughts', ['awareness_level'])
    
    print("✅ Created 'thoughts' table for scalable consciousness storage")
    print("   Consciousness thoughts will now be stored in SQLite instead of JSON")
    print("   This prevents JSON file bloat during 24/7 daemon operation")


def downgrade() -> None:
    """Remove thoughts table."""
    
    # Drop indexes first
    op.drop_index('ix_thoughts_awareness', 'thoughts')
    op.drop_index('ix_thoughts_type', 'thoughts')
    op.drop_index('ix_thoughts_mind_time', 'thoughts')
    op.drop_index('ix_thoughts_timestamp', 'thoughts')
    op.drop_index('ix_thoughts_mind_gmid', 'thoughts')
    
    # Drop table
    op.drop_table('thoughts')
    
    print("⚠️  Removed 'thoughts' table - thoughts will be stored in JSON again")
