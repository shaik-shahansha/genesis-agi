'use client';

import { useState } from 'react';
import { formatRelative, shortId, type ApprovalCard } from '@/lib/governance';
import { RiskBadge } from './primitives';
import { CheckIcon, LockIcon, XMarkIcon } from '@/components/shell/icons';

/**
 * One approval, as a card a non-engineer can decide on.
 *
 * Design rules, in order of importance:
 *
 * 1. **What, why, and what it costs** are above the fold. Everything else is
 *    secondary. The card content comes from the server, which derives it from
 *    the capability, risk level, and material parameters - never from the
 *    model's own prose.
 * 2. **What can be reversed** is stated explicitly, including the rollback plan,
 *    because "not reversible" is the fact that should change a decision.
 * 3. Approve is a deliberate two-step action and the note is recorded. Reject
 *    is equally easy - a system where refusing is harder than permitting will
 *    drift towards permitting.
 * 4. `requires_human` blocks approval from a Mind actor server-side; the UI
 *    says so instead of letting the user discover it via an error.
 */
export default function ApprovalCardView({
  approval,
  onApprove,
  onReject,
  busy = false,
}: {
  approval: ApprovalCard;
  onApprove: (options: { note?: string; ttlSeconds?: number }) => Promise<void> | void;
  onReject: (note?: string) => Promise<void> | void;
  busy?: boolean;
}) {
  const [mode, setMode] = useState<'idle' | 'approving' | 'rejecting'>('idle');
  const [note, setNote] = useState('');
  const [ttlMinutes, setTtlMinutes] = useState(15);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setMode('idle');
    setNote('');
    setError(null);
  };

  const run = async (action: 'approve' | 'reject') => {
    setError(null);
    try {
      if (action === 'approve') {
        await onApprove({ note: note || undefined, ttlSeconds: ttlMinutes * 60 });
      } else {
        await onReject(note || undefined);
      }
      reset();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The decision could not be recorded');
    }
  };

  const irreversible = approval.reversibility !== 'reversible';

  return (
    <article className="rounded-card border border-line bg-surface p-5 shadow-card">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-base font-semibold capitalize text-fg">{approval.action}</h3>
          <p className="mt-0.5 text-xs text-fg-subtle">
            Requested by {approval.requested_by || 'the Mind'} · {formatRelative(approval.requested_at)}
            {approval.expires_at && <> · expires {formatRelative(approval.expires_at)}</>}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <RiskBadge level={approval.risk_level} showDescription />
          {approval.requires_human && (
            <span className="badge badge-danger" title="A responsible human owner must decide this">
              <LockIcon className="h-3.5 w-3.5" />
              Human required
            </span>
          )}
        </div>
      </header>

      <dl className="mt-4 space-y-2.5 text-sm">
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-fg-subtle">Why</dt>
          <dd className="mt-0.5 text-fg">{approval.why}</dd>
        </div>

        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-fg-subtle">Impact</dt>
          <dd className="mt-0.5 text-fg">{approval.expected_impact}</dd>
        </div>

        <div className="grid gap-2.5 sm:grid-cols-3">
          <div className="rounded-lg bg-surface-2 p-3">
            <dt className="text-xs text-fg-subtle">Reversible?</dt>
            <dd className={`mt-0.5 text-sm font-medium ${irreversible ? 'text-danger' : 'text-fg'}`}>
              {approval.reversibility}
            </dd>
          </div>
          <div className="rounded-lg bg-surface-2 p-3">
            <dt className="text-xs text-fg-subtle">Cost</dt>
            <dd className="mt-0.5 text-sm font-medium tabular-nums text-fg">
              {approval.cost_essence ? `${approval.cost_essence} GEN` : 'None'}
            </dd>
          </div>
          <div className="rounded-lg bg-surface-2 p-3">
            <dt className="text-xs text-fg-subtle">Scope</dt>
            <dd className="mt-0.5 text-sm font-medium text-fg">{approval.duration}</dd>
          </div>
        </div>

        {approval.recipient && (
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-fg-subtle">Recipient</dt>
            <dd className="mt-0.5 break-all font-mono text-sm text-fg">{approval.recipient}</dd>
          </div>
        )}

        {approval.data_accessed.length > 0 && (
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-fg-subtle">
              Data touched
            </dt>
            <dd className="mt-0.5 flex flex-wrap gap-1.5">
              {approval.data_accessed.map((item) => (
                <span key={item} className="badge badge-neutral font-mono">
                  {item}
                </span>
              ))}
            </dd>
          </div>
        )}

        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-fg-subtle">
            If it goes wrong
          </dt>
          <dd className="mt-0.5 text-fg-muted">{approval.rollback}</dd>
        </div>

        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-fg-subtle">Scope bound</dt>
          <dd className="mt-0.5 font-mono text-xs text-fg-muted">{approval.scope}</dd>
        </div>
      </dl>

      <p className="mt-4 rounded-lg border border-line bg-surface-2 px-3 py-2 text-xs text-fg-muted">
        Approving issues a grant bound to{' '}
        <strong className="font-medium">these exact parameters</strong>. If anything material
        changes, the grant is invalidated and the action returns here. It is single-use and
        expires.
      </p>

      {error && (
        <p className="mt-3 rounded-lg border border-danger/40 bg-danger/5 px-3 py-2 text-xs text-danger">
          {error}
        </p>
      )}

      <footer className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4">
        {mode === 'idle' && (
          <>
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={busy}
              onClick={() => setMode('approving')}
            >
              <CheckIcon className="h-4 w-4" />
              Approve
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={busy}
              onClick={() => setMode('rejecting')}
            >
              <XMarkIcon className="h-4 w-4" />
              Reject
            </button>
            <span className="meta ml-auto font-mono">{shortId(approval.approval_id, 14)}</span>
          </>
        )}

        {mode === 'approving' && (
          <div className="flex w-full flex-wrap items-end gap-2">
            <div className="min-w-[12rem] flex-1">
              <label className="label" htmlFor={`note-${approval.approval_id}`}>
                Note (recorded in the audit trail)
              </label>
              <input
                id={`note-${approval.approval_id}`}
                className="input"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="e.g. approved for this week's class"
                autoFocus
              />
            </div>
            <div className="w-32">
              <label className="label" htmlFor={`ttl-${approval.approval_id}`}>
                Valid for (min)
              </label>
              <input
                id={`ttl-${approval.approval_id}`}
                className="input tabular-nums"
                type="number"
                min={1}
                max={1440}
                value={ttlMinutes}
                onChange={(event) => setTtlMinutes(Number(event.target.value) || 15)}
              />
            </div>
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={busy}
              onClick={() => run('approve')}
            >
              Confirm approval
            </button>
            <button type="button" className="btn-ghost btn-sm" onClick={reset}>
              Cancel
            </button>
          </div>
        )}

        {mode === 'rejecting' && (
          <div className="flex w-full flex-wrap items-end gap-2">
            <div className="min-w-[12rem] flex-1">
              <label className="label" htmlFor={`reject-${approval.approval_id}`}>
                Why not? (recorded, and shown to the Mind)
              </label>
              <input
                id={`reject-${approval.approval_id}`}
                className="input"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="e.g. use the internal channel instead"
                autoFocus
              />
            </div>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={busy}
              onClick={() => run('reject')}
            >
              Confirm rejection
            </button>
            <button type="button" className="btn-ghost btn-sm" onClick={reset}>
              Cancel
            </button>
          </div>
        )}
      </footer>
    </article>
  );
}
