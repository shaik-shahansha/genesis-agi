"""Record which inbound messages have already been handled

Revision ID: 011_inbound_events
Revises: 010_contacts
Create Date: 2026-09-29 11:00:00.000000

A mailbox is re-read after every restart, so a poller without this table re-answers
messages by default. The person then receives duplicate replies carrying the name of
a human administrator, and nothing in the system looks broken.

`uq_inbound_events_mind_channel_message` is the entire mechanism. Claiming a message
is an `INSERT`; the conflict *is* the "already handled" signal. A `SELECT` before the
`INSERT` would be a race, and two pollers against one mailbox is the configuration
where that race produces the duplicate this table exists to prevent.

`provider_message_id` is `NOT NULL` with no empty-string exemption, because an empty
id cannot be deduplicated: storing `''` once would mark every future id-less message
as already handled and silently drop them. The ledger refuses to claim an empty id
instead, which is a lost message rather than a corrupted marker.

`outcome` defaults to `''`, and `''` means "claimed, no outcome" — the process died
mid-flight. Those rows are surfaced and deliberately not retried, because a retry may
answer a message that was already answered before the crash. There is no back-fill:
before this revision the poller did not exist, so there is nothing to reconcile.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011_inbound_events'
down_revision: Union[str, Sequence[str], None] = '010_contacts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'inbound_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mind_id', sa.String(length=50), nullable=False),
        sa.Column('channel', sa.String(length=30), nullable=False),
        sa.Column('provider_message_id', sa.String(length=255), nullable=False),
        sa.Column('claimed_at', sa.DateTime(), nullable=False),
        sa.Column('outcome', sa.String(length=40), nullable=False, server_default=''),
        sa.Column('reason', sa.String(length=400), nullable=False, server_default=''),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'mind_id',
            'channel',
            'provider_message_id',
            name='uq_inbound_events_mind_channel_message',
        ),
    )
    # `mind_id` is `index=True` on the column, so the index is declared once — here
    # only. Declaring it in both places is what previously made `alembic upgrade head`
    # abort partway on a fresh database and left every later revision unreachable.
    op.create_index('ix_inbound_events_mind_id', 'inbound_events', ['mind_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_inbound_events_mind_id', table_name='inbound_events')
    op.drop_table('inbound_events')
