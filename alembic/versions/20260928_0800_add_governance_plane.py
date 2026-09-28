"""Add governance control plane (policy, approvals, receipts, event journal)

Revision ID: 008_governance_plane
Revises: 007_purpose_role_guidance
Create Date: 2026-09-28 08:00:00.000000

Implements ADR-0006 (deterministic policy engine), ADR-0007 (approval state
machine), ADR-0008 (append-only event journal + immutable receipts).

Four additive tables. No existing table is modified, so this migration is safe
to apply to a live single-node install:

* ``governance_events``  - append-only, hash-chained journal.
* ``action_receipts``    - immutable record of every action attempt.
* ``approval_requests``  - the approval state machine.
* ``permission_grants``  - single-use, parameter-bound authorizations.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '008_governance_plane'
down_revision: Union[str, Sequence[str], None] = '007_purpose_role_guidance'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Append-only event journal (ADR-0008)
    # ------------------------------------------------------------------ #
    op.create_table(
        'governance_events',
        sa.Column('event_id', sa.String(64), primary_key=True),
        sa.Column('stream_key', sa.String(200), nullable=False),
        sa.Column('sequence', sa.Integer, nullable=False),
        sa.Column('type', sa.String(64), nullable=False),
        sa.Column('schema_version', sa.Integer, nullable=False, server_default=sa.text('1')),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('mind_id', sa.String(50), nullable=True),
        sa.Column('actor_type', sa.String(32), nullable=False, server_default='system'),
        sa.Column('actor_id', sa.String(200), nullable=False, server_default=''),
        sa.Column('correlation_id', sa.String(64), nullable=False, server_default=''),
        sa.Column('causation_id', sa.String(64), nullable=True),
        sa.Column('payload', sa.JSON, nullable=False),
        sa.Column('payload_hash', sa.String(64), nullable=False, server_default=''),
        sa.Column('prev_hash', sa.String(64), nullable=False, server_default=''),
        sa.Column('integrity_hash', sa.String(64), nullable=False, server_default=''),
    )
    op.create_index('ix_governance_events_stream_key', 'governance_events', ['stream_key'])
    op.create_index('ix_governance_events_type', 'governance_events', ['type'])
    op.create_index('ix_governance_events_timestamp', 'governance_events', ['timestamp'])
    op.create_index('ix_governance_events_tenant_id', 'governance_events', ['tenant_id'])
    op.create_index('ix_governance_events_mind_id', 'governance_events', ['mind_id'])
    op.create_index('ix_governance_events_correlation_id', 'governance_events', ['correlation_id'])
    op.create_index(
        'ix_gov_events_stream_seq', 'governance_events', ['stream_key', 'sequence'], unique=True
    )
    op.create_index('ix_gov_events_mind_ts', 'governance_events', ['mind_id', 'timestamp'])

    # ------------------------------------------------------------------ #
    # Action receipts (ADR-0008 §2)
    # ------------------------------------------------------------------ #
    op.create_table(
        'action_receipts',
        sa.Column('receipt_id', sa.String(64), primary_key=True),
        sa.Column('action_id', sa.String(64), nullable=False),
        sa.Column('action_name', sa.String(120), nullable=False),
        sa.Column('mind_id', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('objective_id', sa.String(64), nullable=True),
        sa.Column('outcome', sa.String(32), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('requested_by', sa.String(200), nullable=False, server_default=''),
        sa.Column('actor_type', sa.String(32), nullable=False, server_default='mind'),
        sa.Column('intent', sa.Text, nullable=False, server_default=''),
        sa.Column('selected_skill', sa.String(120), nullable=True),
        sa.Column('arguments', sa.JSON, nullable=False),
        sa.Column('arguments_hash', sa.String(64), nullable=False, server_default=''),
        sa.Column('risk_level', sa.String(4), nullable=False, server_default=''),
        sa.Column('policy_decision', sa.JSON, nullable=False),
        sa.Column('matched_rules', sa.JSON, nullable=False),
        sa.Column('approval_id', sa.String(64), nullable=True),
        sa.Column('approver_id', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('duration_ms', sa.Float, nullable=True),
        sa.Column('affected_resources', sa.JSON, nullable=False),
        sa.Column('artifacts', sa.JSON, nullable=False),
        sa.Column('evidence', sa.JSON, nullable=False),
        sa.Column('model_invocations', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('cost_essence', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('error_class', sa.String(120), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('rollback', sa.JSON, nullable=True),
        sa.Column('correlation_id', sa.String(64), nullable=False, server_default=''),
        sa.Column('payload_hash', sa.String(64), nullable=False, server_default=''),
        sa.Column('prev_hash', sa.String(64), nullable=False, server_default=''),
        sa.Column('integrity_hash', sa.String(64), nullable=False, server_default=''),
        sa.Column('sequence', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('schema_version', sa.Integer, nullable=False, server_default=sa.text('1')),
    )
    op.create_index('ix_action_receipts_action_id', 'action_receipts', ['action_id'])
    op.create_index('ix_action_receipts_action_name', 'action_receipts', ['action_name'])
    op.create_index('ix_action_receipts_mind_id', 'action_receipts', ['mind_id'])
    op.create_index('ix_action_receipts_tenant_id', 'action_receipts', ['tenant_id'])
    op.create_index('ix_action_receipts_objective_id', 'action_receipts', ['objective_id'])
    op.create_index('ix_action_receipts_outcome', 'action_receipts', ['outcome'])
    op.create_index('ix_action_receipts_created_at', 'action_receipts', ['created_at'])
    op.create_index('ix_action_receipts_approval_id', 'action_receipts', ['approval_id'])
    op.create_index('ix_action_receipts_correlation_id', 'action_receipts', ['correlation_id'])
    op.create_index('ix_receipts_mind_created', 'action_receipts', ['mind_id', 'created_at'])

    # ------------------------------------------------------------------ #
    # Approval requests (ADR-0007)
    # ------------------------------------------------------------------ #
    op.create_table(
        'approval_requests',
        sa.Column('approval_id', sa.String(64), primary_key=True),
        sa.Column('action_id', sa.String(64), nullable=False),
        sa.Column('action_name', sa.String(120), nullable=False),
        sa.Column('mind_id', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('objective_id', sa.String(64), nullable=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('risk_level', sa.String(4), nullable=False, server_default='R3'),
        sa.Column('requested_at', sa.DateTime, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('parameters', sa.JSON, nullable=False),
        sa.Column('parameters_hash', sa.String(64), nullable=False, server_default=''),
        sa.Column('summary', sa.Text, nullable=False, server_default=''),
        sa.Column('reason', sa.Text, nullable=False, server_default=''),
        sa.Column('expected_impact', sa.Text, nullable=False, server_default=''),
        sa.Column('data_accessed', sa.JSON, nullable=False),
        sa.Column('recipient', sa.String(300), nullable=True),
        sa.Column('financial_cost_essence', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('reversibility', sa.String(32), nullable=False, server_default='unknown'),
        sa.Column('requested_duration', sa.String(64), nullable=False, server_default='one-off'),
        sa.Column('scope', sa.Text, nullable=False, server_default=''),
        sa.Column('proposed_rollback', sa.Text, nullable=False, server_default=''),
        sa.Column('evidence', sa.JSON, nullable=False),
        sa.Column('policy_decision', sa.JSON, nullable=False),
        sa.Column('matched_rules', sa.JSON, nullable=False),
        sa.Column('policy_version', sa.String(64), nullable=False, server_default=''),
        sa.Column('requires_human', sa.Boolean, nullable=False, server_default=sa.text('0')),
        sa.Column('approver_role', sa.String(64), nullable=True),
        sa.Column('requested_by', sa.String(200), nullable=False, server_default=''),
        sa.Column('actor_type', sa.String(32), nullable=False, server_default='mind'),
        sa.Column('approver_id', sa.String(200), nullable=True),
        sa.Column('resolution_note', sa.Text, nullable=True),
        sa.Column('correlation_id', sa.String(64), nullable=False, server_default=''),
        sa.Column('transition_log', sa.JSON, nullable=False),
    )
    op.create_index('ix_approval_requests_action_id', 'approval_requests', ['action_id'])
    op.create_index('ix_approval_requests_action_name', 'approval_requests', ['action_name'])
    op.create_index('ix_approval_requests_mind_id', 'approval_requests', ['mind_id'])
    op.create_index('ix_approval_requests_tenant_id', 'approval_requests', ['tenant_id'])
    op.create_index('ix_approval_requests_objective_id', 'approval_requests', ['objective_id'])
    op.create_index('ix_approval_requests_status', 'approval_requests', ['status'])
    op.create_index('ix_approval_requests_requested_at', 'approval_requests', ['requested_at'])
    op.create_index('ix_approval_requests_expires_at', 'approval_requests', ['expires_at'])
    op.create_index('ix_approval_requests_correlation_id', 'approval_requests', ['correlation_id'])

    # ------------------------------------------------------------------ #
    # Permission grants (ADR-0007 binding rules)
    # ------------------------------------------------------------------ #
    op.create_table(
        'permission_grants',
        sa.Column('grant_id', sa.String(64), primary_key=True),
        sa.Column('approval_id', sa.String(64), nullable=False),
        sa.Column('mind_id', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('objective_id', sa.String(64), nullable=True),
        sa.Column('action_name', sa.String(120), nullable=False),
        sa.Column('parameters_hash', sa.String(64), nullable=False),
        sa.Column('scope', sa.Text, nullable=False, server_default=''),
        sa.Column('issued_by', sa.String(200), nullable=False, server_default=''),
        sa.Column('issued_at', sa.DateTime, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('single_use', sa.Boolean, nullable=False, server_default=sa.text('1')),
        sa.Column('max_uses', sa.Integer, nullable=False, server_default=sa.text('1')),
        sa.Column('consumed_at', sa.DateTime, nullable=True),
        sa.Column('revoked_at', sa.DateTime, nullable=True),
        sa.Column('revoked_by', sa.String(200), nullable=True),
    )
    op.create_index('ix_permission_grants_approval_id', 'permission_grants', ['approval_id'])
    op.create_index('ix_permission_grants_mind_id', 'permission_grants', ['mind_id'])
    op.create_index('ix_permission_grants_tenant_id', 'permission_grants', ['tenant_id'])
    op.create_index('ix_permission_grants_action_name', 'permission_grants', ['action_name'])
    op.create_index('ix_permission_grants_parameters_hash', 'permission_grants', ['parameters_hash'])
    op.create_index('ix_permission_grants_expires_at', 'permission_grants', ['expires_at'])
    op.create_index('ix_grants_mind_action', 'permission_grants', ['mind_id', 'action_name'])


def downgrade() -> None:
    op.drop_index('ix_grants_mind_action', table_name='permission_grants')
    op.drop_index('ix_permission_grants_expires_at', table_name='permission_grants')
    op.drop_index('ix_permission_grants_parameters_hash', table_name='permission_grants')
    op.drop_index('ix_permission_grants_action_name', table_name='permission_grants')
    op.drop_index('ix_permission_grants_tenant_id', table_name='permission_grants')
    op.drop_index('ix_permission_grants_mind_id', table_name='permission_grants')
    op.drop_index('ix_permission_grants_approval_id', table_name='permission_grants')
    op.drop_table('permission_grants')

    op.drop_index('ix_approval_requests_correlation_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_expires_at', table_name='approval_requests')
    op.drop_index('ix_approval_requests_requested_at', table_name='approval_requests')
    op.drop_index('ix_approval_requests_status', table_name='approval_requests')
    op.drop_index('ix_approval_requests_objective_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_tenant_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_mind_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_action_name', table_name='approval_requests')
    op.drop_index('ix_approval_requests_action_id', table_name='approval_requests')
    op.drop_table('approval_requests')

    op.drop_index('ix_receipts_mind_created', table_name='action_receipts')
    op.drop_index('ix_action_receipts_correlation_id', table_name='action_receipts')
    op.drop_index('ix_action_receipts_approval_id', table_name='action_receipts')
    op.drop_index('ix_action_receipts_created_at', table_name='action_receipts')
    op.drop_index('ix_action_receipts_outcome', table_name='action_receipts')
    op.drop_index('ix_action_receipts_objective_id', table_name='action_receipts')
    op.drop_index('ix_action_receipts_tenant_id', table_name='action_receipts')
    op.drop_index('ix_action_receipts_mind_id', table_name='action_receipts')
    op.drop_index('ix_action_receipts_action_name', table_name='action_receipts')
    op.drop_index('ix_action_receipts_action_id', table_name='action_receipts')
    op.drop_table('action_receipts')

    op.drop_index('ix_gov_events_mind_ts', table_name='governance_events')
    op.drop_index('ix_gov_events_stream_seq', table_name='governance_events')
    op.drop_index('ix_governance_events_correlation_id', table_name='governance_events')
    op.drop_index('ix_governance_events_mind_id', table_name='governance_events')
    op.drop_index('ix_governance_events_tenant_id', table_name='governance_events')
    op.drop_index('ix_governance_events_timestamp', table_name='governance_events')
    op.drop_index('ix_governance_events_type', table_name='governance_events')
    op.drop_index('ix_governance_events_stream_key', table_name='governance_events')
    op.drop_table('governance_events')
