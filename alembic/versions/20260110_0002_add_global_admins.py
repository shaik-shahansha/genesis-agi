"""Add global_admins table

Revision ID: 005_global_admins
Revises: 004_mind_access
Create Date: 2026-01-10 00:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005_global_admins'
down_revision: Union[str, None] = '004_mind_access'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'global_admins',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('added_by', sa.String(255), nullable=True),
        sa.Column('added_at', sa.DateTime, nullable=False, server_default=sa.text("(datetime('now'))")),
    )
    op.create_index('ix_global_admins_email', 'global_admins', ['email'])


def downgrade() -> None:
    op.drop_index('ix_global_admins_email', table_name='global_admins')
    op.drop_table('global_admins')