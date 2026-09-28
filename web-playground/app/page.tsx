'use client';

/**
 * Dashboard — "what needs me?"
 *
 * The old dashboard listed Minds and nothing else, so a user had to open each
 * one to find out whether it was waiting on them or in trouble. Now the primary
 * content is the set of things that need a decision, and each Mind row carries
 * its real governance state (pending approvals, stop state, recent refusals).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import AuthRequired from '@/components/AuthRequired';
import PageHeader from '@/components/shell/PageHeader';
import { EmptyState, ErrorState, LoadingRows, Section } from '@/components/governance/primitives';
import { governanceApi, formatRelative, type GovernanceSummary } from '@/lib/governance';
import { mindRoutes } from '@/lib/navigation';
import { isCreationDisabled } from '@/lib/env';
import { AlertIcon, PlusIcon, RefreshIcon, StopIcon, ShieldIcon } from '@/components/shell/icons';

interface Mind {
  gmid: string;
  name: string;
  model?: string;
  status?: string;
  memory_count?: number;
  daemon_running?: boolean;
  age?: string;
  current_emotion?: string;
}

/** How many Minds to fetch governance state for. Keeps the dashboard one round. */
const SUMMARY_LIMIT = 12;

function Dashboard() {
  const router = useRouter();
  const [minds, setMinds] = useState<Mind[]>([]);
  const [summaries, setSummaries] = useState<Record<string, GovernanceSummary>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await api.getMinds();
      const list: Mind[] = Array.isArray(data) ? data : (data?.minds ?? []);
      setMinds(list);

      // Governance state is fetched in parallel and is allowed to fail
      // independently: a Mind whose governance call errors should not blank the
      // whole dashboard.
      const results = await Promise.allSettled(
        list.slice(0, SUMMARY_LIMIT).map((mind) => governanceApi.summary(mind.gmid))
      );
      const next: Record<string, GovernanceSummary> = {};
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') next[list[index].gmid] = result.value;
      });
      setSummaries(next);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : 'Could not load your Minds';
      if (message.includes('401')) {
        router.push('/login');
        return;
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    load();
    const onFocus = () => load();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [load]);

  const totals = useMemo(() => {
    const values = Object.values(summaries);
    return {
      pending: values.reduce((sum, item) => sum + (item.pending_approvals ?? 0), 0),
      halted: values.filter((item) => item.emergency_stop?.engaged).length,
      refused24h: values.reduce((sum, item) => sum + (item.last_24h?.blocked ?? 0), 0),
      brokenJournals: values.filter((item) => item.journal && !item.journal.ok).length,
    };
  }, [summaries]);

  const needsAttention = useMemo(
    () =>
      minds.filter((mind) => {
        const summary = summaries[mind.gmid];
        if (!summary) return false;
        return (
          summary.pending_approvals > 0 ||
          summary.emergency_stop?.engaged ||
          (summary.journal && !summary.journal.ok)
        );
      }),
    [minds, summaries]
  );

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 space-y-8">
      <PageHeader
        title="Minds"
        description={`${minds.length} ${minds.length === 1 ? 'Mind' : 'Minds'} you can access. Consequential actions wait for your decision, and every attempt is recorded.`}
        actions={
          <>
            <button type="button" className="btn-secondary btn-sm" onClick={load} disabled={loading}>
              <RefreshIcon className="h-4 w-4" />
              Refresh
            </button>
            {!isCreationDisabled() && (
              <Link href="/create" className="btn-primary btn-sm">
                <PlusIcon className="h-4 w-4" />
                New Mind
              </Link>
            )}
          </>
        }
      />

      {error && <ErrorState message={error} onRetry={load} />}

      {loading && minds.length === 0 ? (
        <LoadingRows rows={3} label="Loading Minds" />
      ) : minds.length === 0 ? (
        <EmptyState
          title="No Minds yet"
          description="A Mind owns a workspace, keeps memory across restarts, and acts on a schedule. You decide what it may do without you."
          action={
            !isCreationDisabled() ? (
              <Link href="/create" className="btn-primary btn-sm">
                <PlusIcon className="h-4 w-4" />
                Create your first Mind
              </Link>
            ) : undefined
          }
        />
      ) : (
        <>
          {(totals.pending > 0 ||
            totals.halted > 0 ||
            totals.refused24h > 0 ||
            totals.brokenJournals > 0) && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Metric
                label="Awaiting your decision"
                value={totals.pending}
                tone={totals.pending > 0 ? 'accent' : 'neutral'}
                hint={totals.pending > 0 ? 'Open a Mind’s Governance page' : undefined}
              />
              <Metric
                label="Minds halted"
                value={totals.halted}
                tone={totals.halted > 0 ? 'danger' : 'neutral'}
              />
              <Metric
                label="Actions refused (24h)"
                value={totals.refused24h}
                tone="neutral"
                hint="Blocked by policy before they ran"
              />
              <Metric
                label="Journal integrity"
                value={totals.brokenJournals}
                tone={totals.brokenJournals > 0 ? 'danger' : 'neutral'}
                hint={totals.brokenJournals > 0 ? 'A hash chain did not verify' : 'All chains verified'}
              />
            </div>
          )}

          {needsAttention.length > 0 && (
            <Section
              title="Needs you"
              description="These Minds are waiting on a decision, halted, or have a journal that failed verification."
            >
              <div className="space-y-2.5">
                {needsAttention.map((mind) => (
                  <AttentionRow key={mind.gmid} mind={mind} summary={summaries[mind.gmid]} />
                ))}
              </div>
            </Section>
          )}

          <Section title="All Minds">
            <div className="grid gap-2.5">
              {minds.map((mind) => (
                <MindRow key={mind.gmid} mind={mind} summary={summaries[mind.gmid]} />
              ))}
            </div>
          </Section>
        </>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  tone = 'neutral',
  hint,
}: {
  label: string;
  value: number;
  tone?: 'neutral' | 'accent' | 'danger';
  hint?: string;
}) {
  const colour =
    tone === 'danger' && value > 0
      ? 'text-danger'
      : tone === 'accent' && value > 0
        ? 'text-accent'
        : 'text-fg';
  return (
    <div
      className={`rounded-card border bg-surface p-4 ${
        tone === 'danger' && value > 0
          ? 'border-danger/40'
          : tone === 'accent' && value > 0
            ? 'border-accent/40'
            : 'border-line'
      }`}
    >
      <p className="text-xs text-fg-muted">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${colour}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-fg-subtle">{hint}</p>}
    </div>
  );
}

function AttentionRow({ mind, summary }: { mind: Mind; summary?: GovernanceSummary }) {
  const routes = mindRoutes(mind.gmid);
  const halted = summary?.emergency_stop?.engaged;
  const broken = summary?.journal && !summary.journal.ok;

  return (
    <div
      className={`flex flex-wrap items-center gap-3 rounded-card border p-4 ${
        broken || halted ? 'border-danger/40 bg-danger/5' : 'border-warning/40 bg-warning/5'
      }`}
    >
      <span className={broken || halted ? 'text-danger' : 'text-warning'}>
        {halted ? <StopIcon /> : <AlertIcon />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-fg">{mind.name || mind.gmid}</p>
        <p className="mt-0.5 text-xs text-fg-muted">
          {broken
            ? `Journal integrity failed: ${summary?.journal.reason}`
            : halted
              ? `Halted: ${summary?.emergency_stop.reason || 'no reason recorded'}`
              : `${summary?.pending_approvals ?? 0} action${summary?.pending_approvals === 1 ? '' : 's'} waiting for your decision`}
        </p>
      </div>
      <Link
        href={broken || halted ? routes.timeline : routes.governance}
        className="btn-secondary btn-sm"
      >
        {broken || halted ? 'Investigate' : 'Review'}
      </Link>
    </div>
  );
}

function MindRow({ mind, summary }: { mind: Mind; summary?: GovernanceSummary }) {
  const routes = mindRoutes(mind.gmid);
  const pending = summary?.pending_approvals ?? 0;
  const halted = summary?.emergency_stop?.engaged;

  return (
    <div className="rounded-card border border-line bg-surface p-4 transition-colors hover:border-line-strong">
      <div className="flex flex-wrap items-start gap-3">
        <Link href={routes.overview} className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-base font-semibold text-fg">{mind.name || mind.gmid}</span>
            {halted && (
              <span className="badge badge-danger">
                <StopIcon className="h-3.5 w-3.5" />
                Halted
              </span>
            )}
            {pending > 0 && (
              <span className="badge badge-warning">
                {pending} awaiting you
              </span>
            )}
            {mind.daemon_running && <span className="badge badge-success">Running</span>}
            {mind.status && !mind.daemon_running && (
              <span className="badge badge-neutral">{mind.status}</span>
            )}
          </div>
          <p className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-fg-muted">
            {mind.memory_count != null && <span>{mind.memory_count} memories</span>}
            {mind.age && <span>{mind.age}</span>}
            {mind.current_emotion && <span>{mind.current_emotion}</span>}
            {summary && (
              <span>
                {summary.last_24h.executed} executed · {summary.last_24h.blocked} refused (24h)
              </span>
            )}
          </p>
        </Link>

        <div className="flex flex-wrap items-center gap-1.5">
          {summary && (
            <span
              className="meta hidden font-mono sm:block"
              title={`Last event: ${formatRelative(summary.journal?.broken_at ?? undefined)}`}
            >
              {summary.policy_version.replace('genesis-policy-', 'policy ')}
            </span>
          )}
          <Link href={routes.conversation} className="btn-secondary btn-sm">
            Talk
          </Link>
          <Link href={routes.governance} className="btn-ghost btn-sm">
            <ShieldIcon className="h-4 w-4" />
            Governance
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function DashboardWrapper() {
  return (
    <AuthRequired>
      <Dashboard />
    </AuthRequired>
  );
}
