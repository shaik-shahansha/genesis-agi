'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import {
  EmptyState,
  ErrorState,
  LoadingRows,
  Section,
  StatusBadge,
} from '@/components/governance/primitives';
import { AlertIcon, RefreshIcon, TrashIcon } from '@/components/shell/icons';

interface LogEntry {
  timestamp: string;
  mind_id: string;
  mind_name: string;
  level: string;
  message: string;
  emotion: string | null;
  metadata: Record<string, any>;
}

interface LogsTabProps {
  mindId: string;
}

/** Log levels the API emits, with the tone each should read as. */
const LEVELS: { value: string; label: string; tone: string }[] = [
  { value: 'all', label: 'All levels', tone: 'neutral' },
  { value: 'info', label: 'Info', tone: 'neutral' },
  { value: 'thought', label: 'Thoughts', tone: 'violet' },
  { value: 'dream', label: 'Dreams', tone: 'info' },
  { value: 'memory', label: 'Memory', tone: 'success' },
  { value: 'llm_call', label: 'Model calls', tone: 'warning' },
  { value: 'emotion', label: 'Emotions', tone: 'violet' },
  { value: 'action', label: 'Actions', tone: 'info' },
  { value: 'search', label: 'Searches', tone: 'info' },
  { value: 'relationship', label: 'Relationships', tone: 'success' },
  { value: 'error', label: 'Errors', tone: 'danger' },
];

const LEVEL_TONE: Record<string, string> = {
  error: 'text-danger',
  thought: 'text-violet',
  dream: 'text-info',
  memory: 'text-success',
  llm_call: 'text-warning',
  emotion: 'text-violet',
  action: 'text-info',
  search: 'text-info',
  relationship: 'text-success',
};

/**
 * The Mind's activity log.
 *
 * The previous version carried a "CLI Commands" panel: a text input labelled
 * `genesis command...` and an **Execute** button with no handler, plus four
 * quick-command buttons that did nothing either. Typing a command and pressing
 * Execute silently did nothing at all, which is the worst version of this
 * feature — it looks like a working console.
 *
 * It has not been wired up, and that is deliberate. A web endpoint that runs
 * arbitrary shell commands is remote code execution, and the whole governance
 * plane exists to make the opposite guarantee: every consequential action is
 * classified, approval-gated above R2, and written to a hash-chained journal.
 * A free-text command box is none of those things. The commands are listed
 * instead, as text, to be run on the host by whoever operates the install.
 */
export default function LogsTab({ mindId }: LogsTabProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState('all');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadLogs();
  }, [mindId]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => loadLogs({ quiet: true }), 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, mindId]);

  /**
   * `quiet` keeps the auto-refresh from flipping the page into a loading state
   * every five seconds, which made the buttons flicker and the list blank.
   */
  const loadLogs = async ({ quiet = false }: { quiet?: boolean } = {}) => {
    if (!quiet) setLoading(true);
    setError(null);
    try {
      const data = await api.getMindLogs(mindId);
      setLogs(data?.logs || []);
    } catch (err: any) {
      setLogs([]);
      setError(err?.message || 'Could not load the log.');
    } finally {
      if (!quiet) setLoading(false);
    }
  };

  const clearLogs = async () => {
    if (!confirm('Clear all logs for this Mind? This cannot be undone.')) return;
    try {
      await api.clearMindLogs(mindId);
      setLogs([]);
    } catch (err: any) {
      setError(`Failed to clear logs: ${err?.message ?? 'unknown error'}`);
    }
  };

  const downloadLogs = () => {
    const content = logs
      .map(
        (log) =>
          `[${log.timestamp}] [${log.level.toUpperCase()}] ${log.message}` +
          (log.emotion ? ` (${log.emotion})` : '')
      )
      .join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mind-${mindId}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredLogs =
    filter === 'all'
      ? logs
      : logs.filter((log) => log.level?.toLowerCase() === filter.toLowerCase());

  const errorCount = logs.filter((l) => l.level === 'error').length;
  const thoughtCount = logs.filter((l) => l.level === 'thought').length;

  if (loading) {
    return <LoadingRows rows={3} label="Loading the activity log" />;
  }

  return (
    <div className="space-y-6">
      {error && <ErrorState message={error} onRetry={() => loadLogs()} />}

      <Section
        title="Activity log"
        description="What this Mind has been doing, newest first."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" onClick={() => loadLogs()} className="btn-ghost btn-sm">
              <RefreshIcon className="h-4 w-4" />
              Refresh
            </button>
            <button type="button" onClick={downloadLogs} className="btn-ghost btn-sm">
              Download
            </button>
            <button
              type="button"
              onClick={clearLogs}
              className="btn-ghost btn-sm text-danger"
              disabled={logs.length === 0}
            >
              <TrashIcon className="h-4 w-4" />
              Clear
            </button>
          </div>
        }
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <label htmlFor="auto-refresh" className="flex cursor-pointer items-center gap-2">
            <input
              id="auto-refresh"
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="h-4 w-4 rounded border-line accent-[rgb(var(--accent))]"
            />
            <span className="text-sm text-fg-muted">Refresh every 5 seconds</span>
          </label>

          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input sm:w-48"
            aria-label="Filter by log level"
          >
            {LEVELS.map((level) => (
              <option key={level.value} value={level.value}>
                {level.label}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Metric label="Entries" value={logs.length} />
          <Metric label="Shown" value={filteredLogs.length} />
          <Metric label="Errors" value={errorCount} tone={errorCount > 0 ? 'danger' : undefined} />
          <Metric label="Thoughts" value={thoughtCount} />
        </div>
      </Section>

      <Section title="Entries">
        {filteredLogs.length === 0 ? (
          <EmptyState
            title={logs.length === 0 ? 'Nothing logged yet' : 'Nothing matches'}
            description={
              logs.length === 0
                ? 'The daemon writes here as the Mind thinks. If you expect entries and see none, check the Overview tab — a stopped daemon produces no log.'
                : 'No entries at this level. Switch the filter to see the rest.'
            }
          />
        ) : (
          <div className="card overflow-hidden p-0">
            <div className="max-h-[600px] overflow-auto p-4 font-mono text-sm">
              {filteredLogs.map((log, index) => {
                const hasMetadata =
                  log.metadata && Object.keys(log.metadata).length > 0;
                return (
                  <div
                    key={`${log.timestamp}-${index}`}
                    className="mb-2 rounded px-2 py-1 hover:bg-surface-2"
                  >
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className="text-xs tabular-nums text-fg-subtle">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                      <span className={LEVEL_TONE[log.level] ?? 'text-fg-muted'}>
                        [{log.level?.toUpperCase() ?? 'INFO'}]
                      </span>
                      {log.emotion && <span className="text-violet">({log.emotion})</span>}
                    </div>
                    <div className={`pl-0 sm:pl-6 ${LEVEL_TONE[log.level] ?? 'text-fg'}`}>
                      {log.message}
                    </div>
                    {hasMetadata && (
                      <pre className="mt-1 pl-0 text-xs text-fg-subtle sm:pl-6">
                        {JSON.stringify(log.metadata, null, 2)}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Section>

      <Section title="Operator commands">
        <div className="card">
          <p className="text-sm text-fg-muted">
            These run on the host, not in this page. There is deliberately no button for them: a web
            endpoint that executes arbitrary commands is remote code execution, and it would sit
            entirely outside the governance plane — no risk classification, no approval, no receipt.
            If you need one of these as an auditable action, register it as a capability instead
            (see §6.1 of the developer guide) so it is classified and journalled like everything else.
          </p>
          <div className="mt-4 space-y-2">
            {[
              ['genesis list', 'Every Mind on this install'],
              [`genesis inspect ${mindId}`, 'This Mind\u2019s stored state'],
              ['genesis status', 'Daemon and provider health'],
              [`genesis daemon start ${mindId}`, 'Start the daemon for this Mind'],
            ].map(([command, purpose]) => (
              <div
                key={command}
                className="flex flex-wrap items-baseline justify-between gap-3 rounded-lg border border-line bg-surface-2 px-3 py-2"
              >
                <code className="font-mono text-xs text-fg">{command}</code>
                <span className="text-xs text-fg-subtle">{purpose}</span>
              </div>
            ))}
          </div>
          <p className="mt-3 flex items-start gap-2 text-xs text-fg-subtle">
            <span className="mt-0.5 text-warning">
              <AlertIcon className="h-4 w-4" />
            </span>
            <span>
              The daemon lifecycle commands go through <code>GENESIS_SUPERVISOR</code>. With the
              default supervisor the API refuses to start a daemon rather than forking one, and
              tells you the command to run.
            </span>
          </p>
        </div>
      </Section>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  tone?: string;
}) {
  return (
    <div className="card-flat">
      <div className="text-xs text-fg-muted">{label}</div>
      <div
        className={`mt-1 text-2xl font-semibold tabular-nums ${
          tone === 'danger' ? 'text-danger' : 'text-fg'
        }`}
      >
        {value}
      </div>
    </div>
  );
}

