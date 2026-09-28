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
import { RefreshIcon, SparkIcon } from '@/components/shell/icons';

interface ConsciousnessTabProps {
  mindId: string;
}

type Feedback = { tone: 'success' | 'danger'; message: string };

/**
 * The Mind's thought stream and recent activity.
 *
 * Changes worth naming:
 *
 *  - The activity panel was hardcoded dark (`bg-gray-900`, `text-white`) on one
 *    of the few screens that is not a terminal, so in light mode it was a black
 *    slab with near-invisible text. It uses theme tokens now.
 *  - `triggerThought` reported success only to `console.log`. Clicking "Generate
 *    Thought" produced no visible response at all — the honest reading was that
 *    the button was broken. It now says what happened, including when the model
 *    returned nothing.
 *  - The tab blocked on `loading` for every fetch, so switching auto-refresh on
 *    blanked the whole view every ten seconds. Only the first load blocks now.
 */
export default function ConsciousnessTab({ mindId }: ConsciousnessTabProps) {
  const [thoughts, setThoughts] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  useEffect(() => {
    loadData();
  }, [mindId]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => loadData({ quiet: true }), 10000);
    return () => clearInterval(interval);
  }, [mindId, autoRefresh]);

  const loadData = async ({ quiet = false }: { quiet?: boolean } = {}) => {
    if (!quiet) setLoading(true);
    setError(null);
    try {
      const [thoughtsData, logsData] = await Promise.all([
        api.getMindThoughts(mindId, 20),
        api.getMindLogs(mindId, 50),
      ]);
      setThoughts(thoughtsData?.thoughts || []);
      setLogs(logsData?.logs || []);
    } catch (err: any) {
      setError(err?.message || 'Could not load the consciousness stream.');
    } finally {
      if (!quiet) setLoading(false);
    }
  };

  const triggerThought = async () => {
    if (generating) return;

    setGenerating(true);
    setFeedback(null);
    try {
      const result = await api.generateThought(mindId);
      await loadData({ quiet: true });

      // The endpoint can return 200 with nothing in it when no provider is
      // configured. Saying "done" there would be wrong, so the message depends
      // on what actually came back.
      const produced = result?.thought || result?.content || result?.success;
      setFeedback(
        produced
          ? { tone: 'success', message: 'Thought generated. It should appear below.' }
          : {
              tone: 'danger',
              message:
                'The request succeeded but no thought came back. That usually means no model provider is configured for this Mind — check Settings, then the daemon status on the Overview tab.',
            }
      );
    } catch (err: any) {
      setFeedback({
        tone: 'danger',
        message: `Could not generate a thought: ${err?.message ?? 'unknown error'}`,
      });
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <LoadingRows rows={3} label="Loading the consciousness stream" />;
  }

  return (
    <div className="space-y-6">
      {error && <ErrorState message={error} onRetry={() => loadData()} />}

      {feedback && (
        <div
          role="status"
          className={`rounded-card border p-3 text-sm ${
            feedback.tone === 'success'
              ? 'border-success/40 bg-success/5 text-fg'
              : 'border-danger/40 bg-danger/5 text-fg'
          }`}
        >
          {feedback.message}
        </div>
      )}

      <Section
        title="Thought stream"
        description="A thought is produced by the cognition loop, which runs in the daemon — not in this page."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="consciousness-auto" className="flex cursor-pointer items-center gap-2">
              <input
                id="consciousness-auto"
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="h-4 w-4 rounded border-line accent-[rgb(var(--accent))]"
              />
              <span className="text-xs text-fg-muted">Auto-refresh (10s)</span>
            </label>
            <button
              type="button"
              onClick={triggerThought}
              disabled={generating}
              className="btn-primary btn-sm"
            >
              <SparkIcon className="h-4 w-4" />
              {generating ? 'Generating…' : 'Generate one now'}
            </button>
            <button
              type="button"
              onClick={() => loadData()}
              disabled={generating}
              className="btn-ghost btn-sm"
            >
              <RefreshIcon className="h-4 w-4" />
              Refresh
            </button>
          </div>
        }
      >
        <div className="flex items-center gap-2 text-xs text-fg-muted">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              autoRefresh ? 'animate-pulse bg-success' : 'bg-fg-subtle'
            }`}
          />
          {autoRefresh ? 'Refreshing every 10 seconds' : 'Manual refresh'}
        </div>
      </Section>

      <Section title={`Recent thoughts (${thoughts.length})`}>
        {thoughts.length === 0 ? (
          <EmptyState
            title="No thoughts yet"
            description="Start the daemon on the Overview tab and one will appear after the first cognition cycle. You can also generate a single thought above without a daemon."
          />
        ) : (
          <div className="space-y-3">
            {thoughts.map((thought, index) => (
              <div key={index} className="card-flat">
                <p className="text-xs tabular-nums text-fg-subtle">
                  {thought?.timestamp
                    ? new Date(thought.timestamp).toLocaleString()
                    : 'Time not recorded'}
                </p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-fg">
                  {typeof thought === 'string'
                    ? thought
                    : thought.content || JSON.stringify(thought)}
                </p>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section
        title={`Activity (${logs.length})`}
        description="The last 50 log entries written by this Mind, newest first."
      >
        {logs.length === 0 ? (
          <EmptyState
            title="No activity yet"
            description="The daemon writes here as the Mind works. A stopped daemon produces nothing."
          />
        ) : (
          <div className="card max-h-96 overflow-y-auto p-4 font-mono text-sm">
            {logs
              .slice()
              .reverse()
              .map((log, index) => (
                <div
                  key={index}
                  className="mb-1 rounded px-2 py-1 hover:bg-surface-2"
                >
                  <span className="text-xs tabular-nums text-fg-subtle">
                    {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}
                  </span>{' '}
                  <StatusBadge tone={logTone(log.level)}>
                    {log.level?.toUpperCase() || 'LOG'}
                  </StatusBadge>{' '}
                  <span className="text-fg">{log.message || JSON.stringify(log)}</span>
                </div>
              ))}
          </div>
        )}
      </Section>
    </div>
  );
}

function logTone(level?: string) {
  switch ((level || '').toLowerCase()) {
    case 'error':
      return 'danger';
    case 'warning':
    case 'warn':
      return 'warning';
    case 'info':
      return 'info';
    default:
      return 'neutral';
  }
}

