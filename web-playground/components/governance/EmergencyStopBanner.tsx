'use client';

import { useState } from 'react';
import { formatRelative, type EmergencyStopState } from '@/lib/governance';
import { AlertIcon, StopIcon } from '@/components/shell/icons';

/**
 * Emergency stop banner.
 *
 * Two states, both honest about what they do:
 *
 * * **Engaged** - a red banner that stays visible on every governance screen.
 *   Read-only actions still work (so a human can inspect the Mind); everything
 *   state-changing is halted until a human releases it. The Mind cannot release
 *   its own stop, and this component does not imply otherwise.
 * * **Clear** - a quiet, low-emphasis button rather than a red one. A halt
 *   control that shouts when nothing is wrong trains people to ignore it.
 */
export default function EmergencyStopBanner({
  state,
  mindName,
  onToggle,
  busy = false,
  canRelease = true,
}: {
  state: EmergencyStopState | null;
  mindName?: string;
  onToggle: (engage: boolean, reason: string) => Promise<void> | void;
  busy?: boolean;
  canRelease?: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  const engaged = Boolean(state?.engaged);

  const submit = async (engage: boolean) => {
    setError(null);
    try {
      await onToggle(engage, reason || (engage ? 'halted from the workspace' : 'resolved'));
      setConfirming(false);
      setReason('');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not change the stop state');
    }
  };

  if (engaged) {
    return (
      <div className="rounded-card border border-danger/50 bg-danger/5 p-5">
        <div className="flex flex-wrap items-start gap-3">
          <span className="mt-0.5 text-danger animate-pulse">
            <AlertIcon />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-fg">
              Emergency stop engaged{mindName ? ` for ${mindName}` : ''}
            </p>
            <p className="mt-1 text-sm text-fg-muted">
              {state?.reason || 'No reason recorded.'} All state-changing actions are halted.
              Read-only inspection still works. A human must release this.
            </p>
            <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-fg-subtle">
              {state?.engaged_by && (
                <div>
                  <dt className="inline">Engaged by </dt>
                  <dd className="inline text-fg-muted">{state.engaged_by}</dd>
                </div>
              )}
              <div>
                <dt className="inline">When </dt>
                <dd className="inline text-fg-muted">{formatRelative(state?.engaged_at)}</dd>
              </div>
            </dl>
          </div>

          <div className="flex w-full flex-col gap-2 sm:w-auto">
            <input
              className="input sm:w-64"
              placeholder="Why are you releasing it?"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              aria-label="Release reason"
            />
            <button
              type="button"
              className="btn-secondary"
              disabled={busy || !canRelease}
              onClick={() => submit(false)}
              title={canRelease ? undefined : 'Only the Mind’s creator can release the stop'}
            >
              Release the stop
            </button>
          </div>
        </div>
        {error && <p className="mt-3 text-xs text-danger">{error}</p>}
        {!canRelease && (
          <p className="mt-2 text-xs text-fg-subtle">
            Only the Mind’s creator can release the stop.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-card border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-fg">Emergency stop</p>
          <p className="mt-0.5 text-xs text-fg-muted">
            Halt every state-changing action immediately. Read-only inspection stays available so
            you can see what happened.
          </p>
        </div>

        {!confirming ? (
          <button type="button" className="btn-secondary btn-sm" onClick={() => setConfirming(true)}>
            <StopIcon className="h-4 w-4" />
            Halt this Mind
          </button>
        ) : (
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
            <input
              className="input sm:w-56"
              placeholder="Reason (recorded in the audit trail)"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              aria-label="Halt reason"
              autoFocus
            />
            <div className="flex gap-2">
              <button
                type="button"
                className="btn-danger btn-sm"
                disabled={busy}
                onClick={() => submit(true)}
              >
                Confirm halt
              </button>
              <button
                type="button"
                className="btn-ghost btn-sm"
                onClick={() => {
                  setConfirming(false);
                  setReason('');
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
      {error && <p className="mt-2 text-xs text-danger">{error}</p>}
    </div>
  );
}
