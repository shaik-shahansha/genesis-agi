"""Store user password hashes

Revision ID: 009_user_credentials
Revises: 008_governance_plane
Create Date: 2026-09-28 20:00:00.000000

Before this, `users` held a username, an email and a role but **no credential**.
Passwords lived in a module-level dict (`auth.USERS_DB`) that was process memory,
so:

  * every account created through the admin panel could not sign in after a
    restart — it still existed in this table, it just had no password anywhere;
  * a JWT issued before a restart was rejected after it, because token resolution
    read the same empty dict;
  * a Mind's creator could be recorded in `minds.creator` while the account that
    owned those Minds could no longer authenticate.

Adding the column does not recover passwords that were never stored: accounts
created by an older build will have `hashed_password IS NULL` and cannot sign in
until an administrator sets one. That is the honest outcome — the alternative
would be inventing a credential.

Nullable rather than NOT NULL, because Firebase accounts genuinely have no
password and authenticate at Google. A placeholder hash would be a credential
nobody set, which is worse than an absent one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '009_user_credentials'
down_revision: Union[str, Sequence[str], None] = '008_governance_plane'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('hashed_password', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'hashed_password')
