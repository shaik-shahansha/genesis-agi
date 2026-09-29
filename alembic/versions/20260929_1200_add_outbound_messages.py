"""Make the outbound rate limits survive a restart

Revision ID: 012_outbound_messages
Revises: 011_inbound_events
Create Date: 2026-09-29 12:00:00.000000

The weekly cap and the minimum gap between initiated messages lived in a
process-local list (`InMemoryOutboundLedger`). For *replies* that barely mattered —
a reply is not capped. For *initiated* contact it is the whole control: a restart
cleared the counts, so a Mind that had already used its three messages this week
could start over by restarting, and "the being that contacted you four times in a
week" is precisely what the cap exists to prevent.

Only initiated messages are recorded. Replies are excluded by design: answering
someone who wrote first is not outreach, and counting it would make a Mind unable to
hold a conversation.

`relationship_id` is a plain string with no foreign key to `contacts`, for two
reasons. The cap follows the *person* rather than an address, so a cap spent on one
channel cannot be sidestepped by reaching them on another. And deleting a contact
must not delete their history — if it did, removing and re-adding a contact would
reset their allowance, which is a way to make a cap disappear by accident.

There is deliberately **no unique constraint**. Two identical sends are a real thing
(a retry after an ambiguous provider response) and both must be counted;
deduplicating here would undercount and hand back allowance that was actually spent.
The `inbound_events` table deduplicates for the opposite reason — a duplicate *reply*
is a visible harm to a person, whereas here the count is the entire point.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012_outbound_messages'
down_revision: Union[str, Sequence[str], None] = '011_inbound_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'outbound_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mind_id', sa.String(length=50), nullable=False),
        sa.Column('relationship_id', sa.String(length=160), nullable=False),
        sa.Column('channel', sa.String(length=30), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        # Why this message was sent, and which specific fact triggered it. The ref is
        # the idempotence key for proactive outreach: a commitment that is at risk for
        # a day is noticed on every poll, and without a record of "we already reminded
        # them about this one" the floors would permit three reminders about the same
        # obligation. Both default sensibly for a manual send.
        sa.Column('trigger', sa.String(length=40), nullable=False, server_default='manual'),
        sa.Column('trigger_ref', sa.String(length=160), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    # `mind_id` and `relationship_id` are `index=True` on the columns and
    # `sent_at` is not, so each index is declared exactly once — either by the
    # column or here, never both. Declaring one twice is what previously made
    # `alembic upgrade head` abort partway on a fresh database and left every later
    # revision unreachable.
    op.create_index('ix_outbound_messages_mind_id', 'outbound_messages', ['mind_id'], unique=False)
    op.create_index(
        'ix_outbound_messages_relationship_id',
        'outbound_messages',
        ['relationship_id'],
        unique=False,
    )
    op.create_index('ix_outbound_messages_sent_at', 'outbound_messages', ['sent_at'], unique=False)
    op.create_index(
        'ix_outbound_messages_window',
        'outbound_messages',
        ['mind_id', 'relationship_id', 'sent_at'],
        unique=False,
    )
    op.create_index(
        'ix_outbound_messages_trigger',
        'outbound_messages',
        ['mind_id', 'trigger', 'trigger_ref'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_outbound_messages_trigger', table_name='outbound_messages')
    op.drop_index('ix_outbound_messages_window', table_name='outbound_messages')
    op.drop_index('ix_outbound_messages_sent_at', table_name='outbound_messages')
    op.drop_index('ix_outbound_messages_relationship_id', table_name='outbound_messages')
    op.drop_index('ix_outbound_messages_mind_id', table_name='outbound_messages')
    op.drop_table('outbound_messages')
