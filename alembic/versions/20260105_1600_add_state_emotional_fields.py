"""Add state and emotional fields to MindRecord

Revision ID: 004_add_state_emotional_fields
Revises: 003_add_thought_storage
Create Date: 2026-01-05 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_state_emotional_fields'
down_revision: Union[str, None] = '003_add_thought_storage'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add current_emotion, current_thought, and emotional state fields to minds table."""
    # Add current state fields
    op.add_column('minds', sa.Column('current_emotion', sa.String(length=50), nullable=True, server_default='neutral'))
    op.add_column('minds', sa.Column('current_thought', sa.Text(), nullable=True))
    
    # Add emotional state fields
    op.add_column('minds', sa.Column('emotional_valence', sa.Float(), nullable=True, server_default='0.5'))
    op.add_column('minds', sa.Column('emotional_arousal', sa.Float(), nullable=True, server_default='0.5'))
    op.add_column('minds', sa.Column('emotional_dominance', sa.Float(), nullable=True, server_default='0.5'))
    op.add_column('minds', sa.Column('current_mood', sa.String(length=50), nullable=True, server_default='calm'))


def downgrade() -> None:
    """Remove state and emotional fields from minds table."""
    op.drop_column('minds', 'current_mood')
    op.drop_column('minds', 'emotional_dominance')
    op.drop_column('minds', 'emotional_arousal')
    op.drop_column('minds', 'emotional_valence')
    op.drop_column('minds', 'current_thought')
    op.drop_column('minds', 'current_emotion')
