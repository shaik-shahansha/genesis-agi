"""Make opt-out survive a restart, and apply on every channel

Revision ID: 013_opt_outs
Revises: 012_outbound_messages
Create Date: 2026-09-29 12:30:00.000000

The opt-out list lived in a process-local set, which made it the most dangerous
non-durable control in the codebase. Someone says "stop", the daemon restarts, and
the Mind writes to them again — not a limit being slightly generous, but the exact
behaviour they explicitly asked to end, repeated, with nothing in the logs to
explain it. It also failed silently, because nothing about a restart looks like a
policy change.

**Two subject kinds in one table.** A person may say "stop" against the
*relationship* (the Mind knows who they are) or against a bare *handle* (they wrote
from an address with no contact record). Both must work, and both must apply on every
channel — otherwise the Mind simply moves to another address the person also has,
which is the behaviour the mechanism exists to prevent.

One table with a `subject_kind` discriminator rather than two tables, because every
read is "is this person opted out, by either key" and that is one query here instead
of two that could drift apart.

`uq_opt_outs_mind_subject` makes asking twice one opt-out rather than two. Without
it a person repeating themselves would grow the table and change nothing.

No back-fill: before this revision there was nowhere to put an opt-out, so an
existing install has none recorded. That is a real gap on upgrade — anyone who opted
out before this revision must be re-recorded — and it is stated rather than papered
over, because inventing opt-outs from historical message data would mean guessing
which past message was a "stop".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013_opt_outs'
down_revision: Union[str, Sequence[str], None] = '012_outbound_messages'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'communication_opt_outs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mind_id', sa.String(length=50), nullable=False),
        sa.Column('subject_kind', sa.String(length=20), nullable=False),
        sa.Column('subject', sa.String(length=320), nullable=False),
        sa.Column('reason', sa.String(length=400), nullable=False, server_default=''),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'mind_id', 'subject_kind', 'subject', name='uq_opt_outs_mind_subject'
        ),
    )
    # `mind_id` is `index=True` on the column, so the index is declared exactly once
    # — here. Declaring it in both places is what previously made
    # `alembic upgrade head` abort partway on a fresh database.
    op.create_index(
        'ix_communication_opt_outs_mind_id',
        'communication_opt_outs',
        ['mind_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_communication_opt_outs_mind_id', table_name='communication_opt_outs'
    )
    op.drop_table('communication_opt_outs')
