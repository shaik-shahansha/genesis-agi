"""Add allowed_users and allowed_minds columns to environments

Revision ID: 002_add_access_control
Revises: 001_initial
Create Date: 2025-12-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_access_control'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add allowed_users and allowed_minds columns to environments table."""
    
    # Add allowed_users column
    op.add_column('environments', 
        sa.Column('allowed_users', sa.JSON, nullable=True, default=list)
    )
    
    # Add allowed_minds column
    op.add_column('environments', 
        sa.Column('allowed_minds', sa.JSON, nullable=True, default=list)
    )
    
    # Update existing rows to have empty lists
    op.execute("UPDATE environments SET allowed_users = '[]' WHERE allowed_users IS NULL")
    op.execute("UPDATE environments SET allowed_minds = '[]' WHERE allowed_minds IS NULL")


def downgrade() -> None:
    """Remove allowed_users and allowed_minds columns."""
    
    op.drop_column('environments', 'allowed_minds')
    op.drop_column('environments', 'allowed_users')
