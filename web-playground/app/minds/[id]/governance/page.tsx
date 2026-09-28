'use client';

/**
 * Governance — the approval inbox.
 *
 * This is the surface that makes "accountable autonomy" real for a user: the
 * actions a Mind cannot take without a decision, in plain language, with the
 * cost, the reversibility, and the rollback plan next to each one.
 *
 * It is also where the emergency stop lives, because both are "things a human
 * must do about what the Mind is doing" and separating them made neither easy to
 * find.
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthRequired from '@/components/AuthRequired';
import PageHeader from '@/components/shell/PageHeader';
import EmergencyStopBanner from '@/components/governance/EmergencyStopBanner';
import ApprovalCardView from '@/components/governance/ApprovalCard';
import {
  EmptyState,
  ErrorState,
  LoadingRows,
  Section,
} from '@/components/governance/primitives';
import {
  governanceApi,
  shortId,
  type ApprovalCard,
  type EmergencyStopState,
  type GovernanceSummary,
  type JournalVerification,
} from '@/lib/governance';
import { mindRoutes } from '@/lib/navigation';
import { RefreshIcon } from '@/components/shell/icons';

function GovernancePage() {
  const params = useParams();
  const mindId = params.id as string;
  const routes = mindRoutes(mindId);

  const [approvals, setApprovals] = useState<ApprovalCard[]>([]);
  const [summary, setSummary] = useState<GovernanceSummary | null>(null);
  const [stopState, setStopState] = useState<EmergencyStopState | null>(null);
  const [journal, setJournal] = useState<JournalVerification | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [cards, summaryData, stop, verification] = await Promise.all([
        governanceApi.approvals(mindId),
        governanceApi.summary(mindId),
        governanceApi.emergencyStopState(mindId),
        governanceApi.verifyJournal(mindId),
      ]);
      setApprovals(cards);
      setSummary(summaryData);
      setStopState(stop);
      setJournal(verification);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load governance data');
    } finally {
      setLoading(false);
    }
  }, [mindId]);

  useEffect(() => {
    load();
  }, [load]);

  const decide = async (
    approvalId: string,
    action: 'approve' | 'reject',
    options: { note?: string; ttlSeconds?: number }
  ) => {
    setBusy(true);
    try {
      if (action === 'approve') {
        await governanceApi.approve(mindId, approvalId, options);
      } else {
        await governanceApi.reject(mindId, approvalId, options.note);
      }
      // Drop it locally immediately, then reconcile with the server.
      setApprovals((current) => current.filter((item) => item.approval_id !== approvalId));
      await load();
    } finally {
      setBusy(false);
    }
  };

  const toggleStop = async (engage: boolean, reason: string) => {
    setBusy(true);
    try {
      const result = await governanceApi.setEmergencyStop(mindId, engage, reason);
      setStopState(result.state);
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      <PageHeader
        title="Governance"
        breadcrumb={
          <Link href={routes.overview} className="hover:text-fg">
            Mind
          </Link>
        }
        description="Every action this Mind wants to take that carries real consequence stops here for your decision. Nothing consequential runs without one."
        actions={
          <>
            <button type="button" className="btn-secondary btn-sm" onClick={load} disabled={loading}>
              <RefreshIcon className="h-4 w-4" />
              Refresh
            </button>
            <Link href={routes.receipts} className="btn-ghost btn-sm">
              See receipts
            </Link>
          </>
        }
      />

      {error && <ErrorState message={error} onRetry={load} />}

      {loading && !summary ? (
        <LoadingRows rows={3} label="Loading approvals" />
      ) : (
        <>
          <EmergencyStopBanner
            state={stopState}
            onToggle={toggleStop}
            busy={busy}
          />

          {summary && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Stat
                label="Awaiting your decision"
                value={String(summary.pending_approvals)}
                emphasis={summary.pending_approvals > 0}
              />
              <Stat
                label="Refused in the last 24h"
                value={String(summary.last_24h.blocked)}
                hint="Actions the policy engine blocked"
              />
              <Stat
                label="Executed in the last 24h"
                value={String(summary.last_24h.executed)}
                hint={`${summary.last_24h.failed} failed`}
              />
              <Stat
                label="Journal integrity"
                value={journal?.ok ? 'Verified' : 'Broken'}
                hint={
                  journal?.ok
                    ? `${journal.checked} events hash-chained`
                    : `First break at ${shortId(journal?.broken_at ?? '', 14)}`
                }
                danger={!journal?.ok}
              />
            </div>
          )}

          <Section
            title={`Waiting for you (${approvals.length})`}
            description="Approve or reject. Approving binds permission to these exact parameters, once, until it expires."
          >
            {approvals.length === 0 ? (
              <EmptyState
                title="Nothing is waiting on you"
                description="When this Mind wants to do something consequential — email someone, deploy, spend, or touch regulated data — it will appear here instead of doing it."
              />
            ) : (
              <div className="space-y-4">
                {approvals.map((approval) => (
                  <ApprovalCardView
                    key={approval.approval_id}
                    approval={approval}
                    busy={busy}
                    onApprove={(options) => decide(approval.approval_id, 'approve', options)}
                    onReject={(note) => decide(approval.approval_id, 'reject', { note })}
                  />
                ))}
              </div>
            )}
          </Section>

          {summary && (
            <Section
              title="How decisions are made"
              description="Deterministic rules, not a language model's judgement. A model may raise the required control, never lower it."
            >
              <div className="rounded-card border border-line bg-surface p-5">
                <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
                  <Info label="Policy version" value={summary.policy_version} mono />
                  <Info label="Charter version" value={summary.charter_version} mono />
                  <Info
                    label="Policy evaluations (24h)"
                    value={String(summary.last_24h.policy_evaluations)}
                  />
                  <Info
                    label="Emergency stops (24h)"
                    value={String(summary.last_24h.emergency_stops)}
                  />
                </dl>
                <p className="mt-4 text-xs leading-relaxed text-fg-muted">
                  Risk levels run R0 (read-only) to R5 (prohibited). R3 and above always need a
                  human, and that ceiling cannot be lowered by configuration. R4 additionally
                  requires a person rather than a delegate.{' '}
                  <Link href={routes.capabilities} className="text-accent hover:underline">
                    See what each capability is allowed to do.
                  </Link>
                </p>
              </div>
            </Section>
          )}
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  emphasis = false,
  danger = false,
}: {
  label: string;
  value: string;
  hint?: string;
  emphasis?: boolean;
  danger?: boolean;
}) {
  return (
    <div
      className={`rounded-card border bg-surface p-4 ${
        danger ? 'border-danger/40' : emphasis ? 'border-accent/40' : 'border-line'
      }`}
    >
      <p className="text-xs text-fg-muted">{label}</p>
      <p
        className={`mt-1 text-2xl font-semibold tabular-nums ${
          danger ? 'text-danger' : emphasis ? 'text-accent' : 'text-fg'
        }`}
      >
        {value}
      </p>
      {hint && <p className="mt-0.5 text-xs text-fg-subtle">{hint}</p>}
    </div>
  );
}

function Info({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line pb-2">
      <dt className="text-sm text-fg-muted">{label}</dt>
      <dd className={`text-sm text-fg ${mono ? 'font-mono text-xs' : 'tabular-nums'}`}>{value}</dd>
    </div>
  );
}

export default function GovernancePageWrapper() {
  return (
    <AuthRequired>
      <GovernancePage />
    </AuthRequired>
  );
}
