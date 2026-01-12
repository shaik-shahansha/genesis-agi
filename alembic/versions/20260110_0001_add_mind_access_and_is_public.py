"""Add mind_access table and is_public column to minds

Revision ID: 004_mind_access
Revises: 003_add_state_emotional_fields
Create Date: 2026-01-10 00:01:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_mind_access'
down_revision: Union[str, None] = '004_add_state_emotional_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_public column to minds
    op.add_column('minds', sa.Column('is_public', sa.Boolean, nullable=False, server_default=sa.text('0')))
    op.create_index('ix_minds_is_public', 'minds', ['is_public'])

    # Create mind_access table
    op.create_table(
        'mind_access',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('mind_gmid', sa.String(50), sa.ForeignKey('minds.gmid'), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('added_by', sa.String(255), nullable=True),
        sa.Column('added_at', sa.DateTime, nullable=False, server_default=sa.text("(datetime('now'))")),
    )
    op.create_index('ix_mind_access_mind_gmid', 'mind_access', ['mind_gmid'])


def downgrade() -> None:
    op.drop_index('ix_mind_access_mind_gmid', table_name='mind_access')
    op.drop_table('mind_access')
    op.drop_index('ix_minds_is_public', table_name='minds')
    op.drop_column('minds', 'is_public')