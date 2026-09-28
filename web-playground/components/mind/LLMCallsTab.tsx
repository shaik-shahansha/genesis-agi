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
import { RefreshIcon } from '@/components/shell/icons';

interface LLMCall {
  id: string;
  timestamp: string;
  provider: string;
  model: string;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  cost: number;
  latency: number;
  success: boolean;
  purpose?: string;
}

interface LLMCallsTabProps {
  mindId: string;
}

/**
 * Model-call history.
 *
 * The previous version swallowed every fetch error and then rendered the same
 * "No LLM calls recorded yet" panel it renders for a healthy-but-idle Mind. On
 * a 404 or an auth failure the tab said the feature was off, which is a claim
 * about the system made from no evidence. Errors are now their own state.
 */
export default function LLMCallsTab({ mindId }: LLMCallsTabProps) {
  const [calls, setCalls] = useState<LLMCall[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    totalCalls: 0,
    totalTokens: 0,
    totalCost: 0,
    avgLatency: 0,
    providers: {} as Record<string, number>,
  });

  useEffect(() => {
    loadCalls();
  }, [mindId]);

  const loadCalls = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getLLMCalls(mindId, 50);
      const rows: LLMCall[] = data?.calls || [];

      setCalls(rows);

      if (rows.length === 0) {
        setStats({ totalCalls: 0, totalTokens: 0, totalCost: 0, avgLatency: 0, providers: {} });
        return;
      }

      const providers: Record<string, number> = {};
      for (const call of rows) {
        providers[call.provider] = (providers[call.provider] || 0) + 1;
      }

      setStats({
        totalCalls: rows.length,
        totalTokens: rows.reduce((sum, call) => sum + (call.totalTokens || 0), 0),
        totalCost: rows.reduce((sum, call) => sum + (call.cost || 0), 0),
        avgLatency: rows.reduce((sum, call) => sum + (call.latency || 0), 0) / rows.length,
        providers,
      });
    } catch (err: any) {
      setCalls([]);
      setError(
        err?.message ||
          'The request failed. This is not the same as having no calls — check that the API is reachable and that you have access to this Mind.'
      );
    } finally {
      setLoading(false);
    }
  };

  if (loading && calls.length === 0 && !error) {
    return <LoadingRows rows={2} label="Loading model call history" />;
  }

  return (
    <div className="space-y-6">
      {error && <ErrorState message={error} onRetry={loadCalls} />}

      <Section title="Usage" description="Across the most recent 50 recorded calls.">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Metric label="Calls" value={stats.totalCalls} />
          <Metric label="Tokens" value={stats.totalTokens.toLocaleString()} />
          <Metric label="Cost" value={`$${stats.totalCost.toFixed(4)}`} />
          <Metric
            label="Avg latency"
            value={stats.avgLatency ? `${stats.avgLatency.toFixed(0)} ms` : '—'}
          />
        </div>
      </Section>

      <Section
        title="Recent calls"
        actions={
          <button type="button" onClick={loadCalls} disabled={loading} className="btn-ghost btn-sm">
            <RefreshIcon className="h-4 w-4" />
            Refresh
          </button>
        }
      >
        {calls.length === 0 ? (
          error ? null : (
            <EmptyState
              title="No calls recorded yet"
              description="This Mind has not made a model call that was recorded here. That changes as soon as you chat with it."
            />
          )
        ) : (
          <div className="card overflow-x-auto p-0">
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Provider</th>
                  <th>Model</th>
                  <th>Purpose</th>
                  <th className="text-right">Tokens</th>
                  <th className="text-right">Cost</th>
                  <th className="text-right">Latency</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {calls.map((call) => (
                  <tr key={call.id}>
                    <td className="whitespace-nowrap tabular-nums text-fg-muted">
                      {new Date(call.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="text-fg">{call.provider}</td>
                    <td className="font-mono text-xs text-fg-muted">{call.model}</td>
                    <td className="text-xs text-fg-muted">{call.purpose || 'chat'}</td>
                    <td className="text-right tabular-nums text-fg">
                      {call.totalTokens.toLocaleString()}
                    </td>
                    <td className="text-right tabular-nums text-fg-muted">
                      ${call.cost.toFixed(4)}
                    </td>
                    <td className="text-right tabular-nums text-fg-muted">{call.latency} ms</td>
                    <td>
                      <StatusBadge tone={call.success ? 'success' : 'danger'}>
                        {call.success ? 'OK' : 'Failed'}
                      </StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title="Provider usage">
        {Object.keys(stats.providers).length === 0 ? (
          <p className="text-sm text-fg-subtle">Nothing to break down yet.</p>
        ) : (
          <div className="space-y-2">
            {Object.entries(stats.providers).map(([provider, count]) => (
              <div
                key={provider}
                className="card-flat flex items-center justify-between"
              >
                <span className="text-sm font-medium text-fg">{provider}</span>
                <span className="text-sm tabular-nums text-fg-muted">
                  {count} {count === 1 ? 'call' : 'calls'}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="card-flat">
      <div className="text-xs text-fg-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-fg">{value}</div>
    </div>
  );
}

