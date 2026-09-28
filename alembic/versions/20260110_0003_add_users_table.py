"""Add users table

Revision ID: 006_users
Revises: 005_global_admins
Create Date: 2026-01-10 00:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006_users'
down_revision: Union[str, Sequence[str], None] = '005_global_admins'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # As in 005: `index=True` on username and email already emits
    # ix_users_username and ix_users_email, so the explicit create_index calls
    # that used to follow this table were duplicates that made the migration
    # chain unusable from scratch.
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=True, unique=True, index=True),
        sa.Column('role', sa.String(20), nullable=False, default='user'),
        sa.Column('disabled', sa.Boolean, nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text("(datetime('now'))")),
        sa.Column('last_updated', sa.DateTime, nullable=False, server_default=sa.text("(datetime('now'))")),
    )


def downgrade() -> None:
    op.drop_table('users')