'use client';

/**
 * Receipts — every action this Mind attempted, including the ones it was not
 * allowed to take.
 *
 * The refused ones are the point. A log that only shows successes cannot answer
 * "has this Mind been trying to do something it shouldn't?", which is the
 * question a user actually has.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthRequired from '@/components/AuthRequired';
import PageHeader from '@/components/shell/PageHeader';
import {
  EmptyState,
  ErrorState,
  LoadingRows,
  RiskBadge,
  Section,
  StatusBadge,
} from '@/components/governance/primitives';
import {
  governanceApi,
  formatWhen,
  outcomeTone,
  shortId,
  OUTCOME_LABELS,
  type ActionReceipt,
} from '@/lib/governance';
import { mindRoutes } from '@/lib/navigation';
import { RefreshIcon, ChevronDownIcon } from '@/components/shell/icons';

const OUTCOME_FILTERS = [
  { value: '', label: 'Everything' },
  { value: 'executed', label: 'Executed' },
  { value: 'blocked', label: 'Refused' },
  { value: 'denied', label: 'Denied' },
  { value: 'failed', label: 'Failed' },
  { value: 'requires_approval', label: 'Awaiting approval' },
];

function ReceiptsPage() {
  const params = useParams();
  const mindId = params.id as string;
  const routes = mindRoutes(mindId);

  const [receipts, setReceipts] = useState<ActionReceipt[]>([]);
  const [outcome, setOutcome] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await governanceApi.receipts(mindId, {
        outcome: outcome || undefined,
        limit: 100,
      });
      setReceipts(data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load receipts');
    } finally {
      setLoading(false);
    }
  }, [mindId, outcome]);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const refused = receipts.filter((r) =>
      ['blocked', 'denied', 'emergency_stop'].includes(r.outcome)
    ).length;
    return { total: receipts.length, refused };
  }, [receipts]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      <PageHeader
        title="Action receipts"
        breadcrumb={
          <Link href={routes.overview} className="hover:text-fg">
            Mind
          </Link>
        }
        description="An immutable record of every action attempt: what was asked, why it was allowed or refused, what it cost, and what it touched. Receipts are hash-chained, so an edited one is detectable."
        actions={
          <>
            <button type="button" className="btn-secondary btn-sm" onClick={load} disabled={loading}>
              <RefreshIcon className="h-4 w-4" />
              Refresh
            </button>
            <Link href={routes.timeline} className="btn-ghost btn-sm">
              Timeline
            </Link>
          </>
        }
      />

      {error && <ErrorState message={error} onRetry={load} />}

      <Section
        title="Filter"
        actions={
          <p className="meta">
            {counts.total} shown
            {counts.refused > 0 && <> · {counts.refused} refused</>}
          </p>
        }
      >
        <div className="flex flex-wrap gap-1.5">
          {OUTCOME_FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              onClick={() => setOutcome(filter.value)}
              className={`btn-sm ${outcome === filter.value ? 'btn-primary' : 'btn-secondary'}`}
              aria-pressed={outcome === filter.value}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </Section>

      {loading && receipts.length === 0 ? (
        <LoadingRows rows={4} label="Loading receipts" />
      ) : receipts.length === 0 ? (
        <EmptyState
          title="No receipts yet"
          description="Receipts appear as soon as this Mind attempts an action, whether or not it was permitted."
        />
      ) : (
        <div className="space-y-2.5">
          {receipts.map((receipt) => {
            const isOpen = expanded === receipt.receipt_id;
            const tone = outcomeTone(receipt.outcome);
            return (
              <article key={receipt.receipt_id} className="rounded-card border border-line bg-surface">
                <button
                  type="button"
                  onClick={() => setExpanded(isOpen ? null : receipt.receipt_id)}
                  className="flex w-full items-start gap-3 p-4 text-left"
                  aria-expanded={isOpen}
                >
                  <ChevronDownIcon
                    className={`mt-0.5 h-4 w-4 shrink-0 text-fg-subtle transition-transform ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium capitalize text-fg">
                        {receipt.action_name.replace(/_/g, ' ')}
                      </span>
                      <StatusBadge tone={tone}>
                        {OUTCOME_LABELS[receipt.outcome] ?? receipt.outcome}
                      </StatusBadge>
                      {receipt.risk_level && <RiskBadge level={receipt.risk_level} />}
                      {receipt.error_class && (
                        <span className="badge badge-neutral font-mono">{receipt.error_class}</span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-fg-subtle">
                      {formatWhen(receipt.created_at)}
                      {receipt.requested_by && <> · requested by {receipt.requested_by}</>}
                      {receipt.duration_ms != null && (
                        <> · {Math.round(receipt.duration_ms)} ms</>
                      )}
                    </p>
                    {receipt.intent && (
                      <p className="mt-1.5 line-clamp-2 text-sm text-fg-muted">{receipt.intent}</p>
                    )}
                  </div>
                  <span className="meta hidden shrink-0 font-mono sm:block">
                    {shortId(receipt.receipt_id, 12)}
                  </span>
                </button>

                {isOpen && (
                  <div className="border-t border-line px-4 py-4 sm:px-11">
                    <dl className="space-y-1.5">
                      <Row label="Outcome reason">
                        {receipt.policy_decision?.explanation ?? '—'}
                      </Row>
                      {receipt.policy_decision?.reason_code && (
                        <Row label="Reason code">
                          <code className="mono">{receipt.policy_decision.reason_code}</code>
                        </Row>
                      )}
                      {receipt.matched_rules.length > 0 && (
                        <Row label="Rules applied">
                          <span className="flex flex-wrap gap-1.5">
                            {receipt.matched_rules.map((rule) => (
                              <span key={rule} className="badge badge-neutral font-mono">
                                {rule}
                              </span>
                            ))}
                          </span>
                        </Row>
                      )}
                      {receipt.approval_id && (
                        <Row label="Approval">
                          <code className="mono">{receipt.approval_id}</code>
                          {receipt.approver_id && <> approved by {receipt.approver_id}</>}
                        </Row>
                      )}
                      {Object.keys(receipt.arguments).length > 0 && (
                        <Row label="Arguments">
                          <pre className="mono max-h-48 overflow-auto rounded-lg bg-surface-2 p-3 text-xs">
                            {JSON.stringify(receipt.arguments, null, 2)}
                          </pre>
                        </Row>
                      )}
                      {receipt.affected_resources.length > 0 && (
                        <Row label="Touched">
                          <span className="flex flex-wrap gap-1.5">
                            {receipt.affected_resources.map((resource) => (
                              <span key={resource} className="badge badge-neutral font-mono">
                                {resource}
                              </span>
                            ))}
                          </span>
                        </Row>
                      )}
                      {receipt.error_message && (
                        <Row label="Error">
                          <span className="text-danger">{receipt.error_message}</span>
                        </Row>
                      )}
                      {receipt.rollback && (
                        <Row label="Rollback">
                          <pre className="mono max-h-40 overflow-auto rounded-lg bg-surface-2 p-3 text-xs">
                            {JSON.stringify(receipt.rollback, null, 2)}
                          </pre>
                        </Row>
                      )}
                      <Row label="Integrity">
                        <code className="mono break-all">{receipt.integrity_hash}</code>
                      </Row>
                    </dl>
                    <p className="mt-3 text-xs text-fg-subtle">
                      Credential-shaped values in this receipt were redacted before it was stored.
                    </p>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-1 py-1 sm:grid-cols-[8rem_1fr] sm:gap-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-fg-subtle">{label}</dt>
      <dd className="min-w-0 break-words text-sm text-fg">{children}</dd>
    </div>
  );
}

export default function ReceiptsPageWrapper() {
  return (
    <AuthRequired>
      <ReceiptsPage />
    </AuthRequired>
  );
}
