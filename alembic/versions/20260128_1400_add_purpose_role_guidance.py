"""Add purpose, role, and guidance_notes to minds table

Revision ID: 008_purpose_role_guidance
Revises: 007_add_users_table
Create Date: 2026-01-28 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_purpose_role_guidance'
down_revision: Union[str, None] = '006_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add purpose, role, and guidance_notes fields to minds table."""
    # Add new fields for creator-defined purpose and guidance
    op.add_column('minds', sa.Column('purpose', sa.Text(), nullable=True))
    op.add_column('minds', sa.Column('role', sa.Text(), nullable=True))
    op.add_column('minds', sa.Column('guidance_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove purpose, role, and guidance_notes fields from minds table."""
    op.drop_column('minds', 'guidance_notes')
    op.drop_column('minds', 'role')
    op.drop_column('minds', 'purpose')
