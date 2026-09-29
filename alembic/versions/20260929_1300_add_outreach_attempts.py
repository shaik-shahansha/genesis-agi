"""Record one outreach attempt per trigger, so proactivity cannot repeat itself

Revision ID: 014_outreach_attempts
Revises: 013_opt_outs
Create Date: 2026-09-29 13:00:00.000000

Proactive outreach notices facts on a loop. A commitment at risk for 24 hours is
noticed on every poll, so without a record the planner raises an approval request on
each pass — 96 of them at a 15-minute interval, all about the same obligation, all
saying the same thing. Every individual request is compliant and the aggregate is a
person being nagged. It is also exactly the noise that trains an approver to click
through without reading, which destroys the control the card exists to provide.

`uq_outreach_mind_trigger_ref` on `(mind_id, trigger, trigger_ref)` means **one
attempt per trigger instance, ever**. A new commitment has a new id and therefore a
new attempt; the same commitment never produces a second one. That is what makes the
planner safe to run on a loop.

The row is written **before** the attempt, not after, for the same reason the inbound
ledger claims before dispatch: a process that dies mid-flight leaves a record, and the
next pass does not repeat it. A missing outreach is recoverable by a human reading
`OutreachAttempts.pending()`; a repeated one is not recoverable at all.

Deliberately separate from `outbound_messages`, which is the *rate-limit* record and
counts only messages actually sent. Recording a proposal there would consume
allowance for a message nobody received.

No back-fill: outreach did not exist before this revision, so there is nothing to
reconcile.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '014_outreach_attempts'
down_revision: Union[str, Sequence[str], None] = '013_opt_outs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'outreach_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mind_id', sa.String(length=50), nullable=False),
        sa.Column('trigger', sa.String(length=40), nullable=False),
        sa.Column('trigger_ref', sa.String(length=160), nullable=False),
        sa.Column('relationship_id', sa.String(length=160), nullable=False, server_default=''),
        sa.Column('channel', sa.String(length=30), nullable=False, server_default=''),
        # `''` means the attempt was claimed and never resolved — the process died
        # mid-flight. Those are reported by `OutreachAttempts.pending()` and never
        # retried, because a retry may contact someone who was already contacted.
        sa.Column('outcome', sa.String(length=40), nullable=False, server_default=''),
        sa.Column('reason', sa.String(length=400), nullable=False, server_default=''),
        sa.Column('attempted_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'mind_id', 'trigger', 'trigger_ref', name='uq_outreach_mind_trigger_ref'
        ),
    )
    # `mind_id` is `index=True` on the column, so the index is declared exactly once.
    op.create_index(
        'ix_outreach_attempts_mind_id', 'outreach_attempts', ['mind_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_outreach_attempts_mind_id', table_name='outreach_attempts')
    op.drop_table('outreach_attempts')
