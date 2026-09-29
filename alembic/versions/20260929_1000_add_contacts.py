"""Add the contact store: people outside the system, and consent per channel

Revision ID: 010_contacts
Revises: 009_user_credentials
Create Date: 2026-09-29 10:00:00.000000

`genesis/channels/` could describe a channel and reach one, but it had nowhere to
store who a Mind knows: the only `ContactResolver` was `InMemoryContacts`, so a
Mind forgot everyone on restart and every sender was a stranger forever.

**Why a new table rather than `relationships`.** That table links two Minds —
`from_gmid` and `to_gmid` are foreign keys into `minds.gmid`. A human contact
cannot go there without inventing a Mind for them, and an invented Mind would then
appear in the metaverse, be counted in `MetaverseState.total_relationships`, and be
addressable as a peer. A person outside the system is a different kind of entity.

**Why consent is a column on the channel row, not on the contact.** Permission is
per way-of-reaching, not per person: someone who gave an email address has not
agreed to be telephoned. Storing one verdict about the contact would let a Mind
upgrade an email address into a phone call. `uq_contact_channels_contact_channel`
makes the question "may I call this person?" have exactly one answer.

**Why `consent_source` is `NOT NULL DEFAULT ''` rather than nullable.** Empty is
the fail-closed value and it is what `ContactRef.may_initiate()` refuses. A NULL
would have to be coalesced at every read site, and each of those is a place where
someone could accidentally coalesce it to something permissive.

Both tables are newly created, so `create_all` on a fresh database and this
migration on an existing one converge — there is no additive-column gap here, and
no back-fill to get wrong, because before this revision there was nowhere to put
contact data.

**Indexes are declared once.** `mind_id` is `index=True` on the column, which
generates `ix_contacts_mind_id`; the model therefore must not also declare an
explicit `Index` on it. Doing both is what previously made `alembic upgrade head`
abort partway on a fresh database, which made every later revision unreachable —
including the governance one. `tests/test_migrations.py` guards the chain.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_contacts'
down_revision: Union[str, Sequence[str], None] = '009_user_credentials'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mind_id', sa.String(length=50), nullable=False),
        sa.Column('relationship_id', sa.String(length=160), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False, server_default=''),
        # JSON rather than three float columns: trust is domain → score and the
        # set of domains is open-ended. A fixed schema would need a migration per
        # new domain, which is how a scoped model quietly becomes an unscoped one.
        sa.Column('trust', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('quiet_hours', sa.JSON(), nullable=True),
        sa.Column('max_outbound_per_week', sa.Integer(), nullable=True),
        sa.Column('boundaries', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('timezone_offset_hours', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'mind_id', 'relationship_id', name='uq_contacts_mind_relationship'
        ),
    )
    op.create_index('ix_contacts_mind_id', 'contacts', ['mind_id'], unique=False)

    op.create_table(
        'contact_channels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=30), nullable=False),
        sa.Column('address', sa.String(length=320), nullable=False),
        # server_default 'none', not 'reply_only': an existing row with no stated
        # permission should grant the least, and a migration is exactly the moment
        # not to guess generously.
        sa.Column('outbound', sa.String(length=20), nullable=False, server_default='none'),
        sa.Column('consent_source', sa.String(length=400), nullable=False, server_default=''),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'contact_id', 'channel', name='uq_contact_channels_contact_channel'
        ),
    )
    op.create_index(
        'ix_contact_channels_contact_id', 'contact_channels', ['contact_id'], unique=False
    )
    op.create_index(
        'ix_contact_channels_lookup',
        'contact_channels',
        ['channel', 'address'],
        unique=False,
    )


def downgrade() -> None:
    # The child first: SQLite does not enforce foreign keys by default, so dropping
    # in the other order would appear to work and leave orphaned channel rows
    # pointing at a table that no longer exists.
    op.drop_index('ix_contact_channels_lookup', table_name='contact_channels')
    op.drop_index('ix_contact_channels_contact_id', table_name='contact_channels')
    op.drop_table('contact_channels')

    op.drop_index('ix_contacts_mind_id', table_name='contacts')
    op.drop_table('contacts')
