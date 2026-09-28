'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { isCreationDisabled, isProduction } from '@/lib/env';
import { useAuth } from '@/lib/auth-context';
import { Section, DetailRow, StatusBadge } from '@/components/governance/primitives';
import {
  AlertIcon,
  CoinsIcon,
  PlayIcon,
  RefreshIcon,
  StopSquareIcon,
  TrashIcon,
} from '@/components/shell/icons';

interface OverviewTabProps {
  mind: any;
  onRefresh: () => void;
}

type DaemonState = 'running' | 'stopped' | 'unknown';

/**
 * The Mind's landing tab.
 *
 * The order is deliberate: what the being is *doing* first, then the numbers,
 * then identity, and the irreversible action last. The danger zone stays
 * reachable because hiding the button does not remove the endpoint — a user who
 * cannot find the control assumes deleting is impossible, and the API says
 * otherwise.
 */
export default function OverviewTab({ mind, onRefresh }: OverviewTabProps) {
  const [daemonStatus, setDaemonStatus] = useState<DaemonState>('unknown');
  const [loading, setLoading] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const { user, genesisUser } = useAuth();
  const deletionDisabled = isCreationDisabled();
  const daemonControlDisabled = isProduction();

  const canDeleteMind = () => {
    if (!user) return false;

    if (genesisUser?.is_global_admin) return true;

    const userEmail = user.email?.toLowerCase();
    const creatorEmail = (mind.creator_email || mind.creator || '').toLowerCase();

    return userEmail === creatorEmail;
  };


  useEffect(() => {
    checkDaemonStatus();
  }, [mind.gmid]);

  const checkDaemonStatus = async () => {
    try {
      const status = await api.getDaemonStatus(mind.gmid);
      setDaemonStatus(status.running ? 'running' : 'stopped');
    } catch (error) {
      setDaemonStatus('unknown');
    }
  };

  const handleStartDaemon = async () => {
    setLoading(true);
    try {
      await api.startDaemon(mind.gmid);
      setDaemonStatus('running');
      onRefresh();
    } catch (error: any) {
      alert(`Failed to start daemon: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStopDaemon = async () => {
    setLoading(true);
    try {
      await api.stopDaemon(mind.gmid);
      setDaemonStatus('stopped');
      onRefresh();
    } catch (error: any) {
      alert(`Failed to stop daemon: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      // A running daemon holds the mind's files open, so stop it first.
      if (daemonStatus === 'running') {
        await api.stopDaemon(mind.gmid);
      }

      await api.deleteMind(mind.gmid);

      // Full navigation rather than a client route change: the deleted Mind's
      // data is cached in several providers that have no invalidation hook.
      window.location.href = '/';
    } catch (error: any) {
      alert(`Failed to delete mind: ${error.message}`);
      setDeleting(false);
      setShowDeleteModal(false);
    }
  };

  const daemonLabel =
    daemonStatus === 'running' ? 'Running' : daemonStatus === 'stopped' ? 'Stopped' : 'Unknown';
  const daemonTone =
    daemonStatus === 'running' ? 'success' : daemonStatus === 'stopped' ? 'neutral' : 'warning';

  return (
    <div className="space-y-6">
      <Section
        title="Autonomy"
        description={
          daemonControlDisabled
            ? 'Continuous operation is enforced in production.'
            : 'The daemon is what makes this being act between your messages.'
        }
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge tone={daemonTone}>{daemonLabel}</StatusBadge>
            <button type="button" onClick={checkDaemonStatus} className="btn-ghost btn-sm">
              <RefreshIcon className="h-4 w-4" />
              Refresh
            </button>
          </div>
        }
      >
        <div className="card">
          {daemonControlDisabled ? (
            <p className="max-w-prose text-sm text-fg-muted">
              Start and stop are disabled here. In production the daemon runs continuously so the
              Mind keeps thinking, dreaming and updating its state between your messages. Stop it
              from the host instead — see the deployment guide — because from this screen a Mind
              whose daemon has died looks exactly like one that is simply idle.
            </p>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="max-w-prose text-sm text-fg-muted">
                Autonomous thinking, dreaming and consciousness updates all run inside the daemon.
                Stopping it pauses that work; it deletes nothing.
              </p>
              <div className="flex gap-2">
                {daemonStatus === 'running' ? (
                  <button
                    type="button"
                    onClick={handleStopDaemon}
                    disabled={loading}
                    className="btn-secondary"
                  >
                    <StopSquareIcon className="h-4 w-4" />
                    {loading ? 'Stopping…' : 'Stop daemon'}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleStartDaemon}
                    disabled={loading}
                    className="btn-primary"
                  >
                    <PlayIcon className="h-4 w-4" />
                    {loading ? 'Starting…' : 'Start daemon'}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </Section>

      <Section title="Vitals">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <Stat
            label="Gens"
            value={mind.gens !== undefined && mind.gens !== null ? mind.gens : 100}
            icon={<CoinsIcon className="h-4 w-4" />}
            tone="warning"
            hint="Compute budget this Mind is allowed to spend"
          />
          <Stat label="Memories" value={mind.memory_count || 0} />
          <Stat label="Dreams" value={mind.dream_count || 0} />
          <Stat label="Emotion" value={mind.current_emotion || '—'} tone="violet" compact />
          <Stat label="Status" value={mind.status || '—'} tone="info" compact />
        </div>
      </Section>

      <Section title="Current state">
        <div className="card">
          {mind.current_thought ? (
            <div className="mb-4">
              <p className="label mb-1">Most recent thought</p>
              <p className="whitespace-pre-wrap text-sm text-fg">{mind.current_thought}</p>
            </div>
          ) : (
            <p className="mb-4 text-sm text-fg-subtle">
              No thought recorded yet. One appears once the daemon has completed a cognition cycle.
            </p>
          )}
          <dl className="border-t border-line pt-3">
            <DetailRow label="Age">{mind.age || '—'}</DetailRow>
            <DetailRow label="GMID">
              <span className="font-mono text-xs">{mind.gmid}</span>
            </DetailRow>
            <DetailRow label="Creator">{mind.creator_email || mind.creator || '—'}</DetailRow>
          </dl>
        </div>
      </Section>

      {!deletionDisabled && canDeleteMind() && (
        <Section title="Danger zone">
          <div className="rounded-card border border-danger/40 bg-danger/5 p-5">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 text-danger">
                <AlertIcon />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-fg">Delete this Mind permanently</p>
                <p className="mt-1 max-w-prose text-sm text-fg-muted">
                  Every memory, dream and episode of state this Mind has accumulated is destroyed.
                  There is no export, no archive and no undo.
                </p>
                <button
                  type="button"
                  onClick={() => setShowDeleteModal(true)}
                  className="btn-danger mt-4"
                >
                  <TrashIcon className="h-4 w-4" />
                  Delete Mind…
                </button>
              </div>
            </div>
          </div>
        </Section>
      )}

      {showDeleteModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-mind-title"
        >
          <div className="card w-full max-w-md shadow-xl">
            <h3 id="delete-mind-title" className="text-base font-semibold text-fg">
              Delete this Mind permanently?
            </h3>

            <dl className="mt-4 rounded-card border border-line bg-surface-2 p-4">
              <DetailRow label="Name">{mind.name}</DetailRow>
              <DetailRow label="GMID">
                <span className="font-mono text-xs">{mind.gmid}</span>
              </DetailRow>
              <DetailRow label="Age">{mind.age}</DetailRow>
              <DetailRow label="Memories">{mind.memory_count}</DetailRow>
              <DetailRow label="Dreams">{mind.dream_count}</DetailRow>
            </dl>

            <p className="mt-4 text-sm text-fg-muted">
              This cannot be undone. If the daemon is running it is stopped first.
            </p>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
                className="btn-secondary flex-1 justify-center"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="btn-danger flex-1 justify-center"
              >
                {deleting ? 'Deleting…' : 'Delete forever'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * One number from the vitals row.
 *
 * `compact` exists because two of these hold words rather than counts: an
 * emotion name is not a number and must not be typeset like one, or the row
 * reads as five quantities of the same kind when it is not.
 */
function Stat({
  label,
  value,
  icon,
  tone = 'neutral',
  hint,
  compact = false,
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  tone?: string;
  hint?: string;
  compact?: boolean;
}) {
  const accent: Record<string, string> = {
    neutral: 'text-fg-subtle',
    warning: 'text-warning',
    violet: 'text-violet-500',
    info: 'text-info',
  };

  return (
    <div className="card-flat" title={hint}>
      <div className={`flex items-center gap-1.5 text-xs text-fg-muted ${accent[tone] || ''}`}>
        {icon}
        <span>{label}</span>
      </div>
      <div
        className={`mt-1 truncate font-semibold text-fg ${
          compact ? 'text-base' : 'text-2xl tabular-nums'
        }`}
      >
        {value}
      </div>
    </div>
  );
}

