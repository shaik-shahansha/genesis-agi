'use client';

/**
 * Capabilities — what this Mind can do, and what each capability may do without
 * a human.
 *
 * Publishing this table is a deliberate product decision: "what is this agent
 * allowed to do on its own?" is the first question a serious user asks, and an
 * answer the user can read is worth more than a claim that the system is safe.
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
} from '@/components/governance/primitives';
import {
  governanceApi,
  RISK_DESCRIPTIONS,
  type CapabilityProfile,
  type RiskLevel,
} from '@/lib/governance';
import { mindRoutes } from '@/lib/navigation';
import { RefreshIcon, LockIcon } from '@/components/shell/icons';

const LEVELS: (RiskLevel | '')[] = ['', 'R0', 'R1', 'R2', 'R3', 'R4', 'R5'];

/** What happens at each level, in the user's terms. */
const DISPOSITIONS: Record<string, string> = {
  R0: 'Runs without asking',
  R1: 'Runs without asking, and is recorded',
  R2: 'Needs approval, unless your policy pre-approves this exact capability',
  R3: 'Always needs approval — configuration cannot lower this',
  R4: 'Always needs approval from a person, not a delegate',
  R5: 'Refused',
};

function CapabilitiesPage() {
  const params = useParams();
  const mindId = params.id as string;
  const routes = mindRoutes(mindId);

  const [capabilities, setCapabilities] = useState<CapabilityProfile[]>([]);
  const [level, setLevel] = useState<RiskLevel | ''>('');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setCapabilities(await governanceApi.capabilities(mindId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load capabilities');
    } finally {
      setLoading(false);
    }
  }, [mindId]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return capabilities.filter((item) => {
      if (level && item.risk !== level) return false;
      if (!needle) return true;
      return (
        item.name.toLowerCase().includes(needle) ||
        item.category.toLowerCase().includes(needle)
      );
    });
  }, [capabilities, level, query]);

  const counts = useMemo(() => {
    const byLevel: Record<string, number> = {};
    for (const item of capabilities) {
      byLevel[item.risk] = (byLevel[item.risk] ?? 0) + 1;
    }
    return byLevel;
  }, [capabilities]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      <PageHeader
        title="Capabilities"
        breadcrumb={
          <Link href={routes.overview} className="hover:text-fg">
            Mind
          </Link>
        }
        description="Every capability this Mind has, with the risk level that decides whether it can act alone. A capability nobody has declared defaults to R3 — it is gated, not permitted."
        actions={
          <button type="button" className="btn-secondary btn-sm" onClick={load} disabled={loading}>
            <RefreshIcon className="h-4 w-4" />
            Refresh
          </button>
        }
      />

      {error && <ErrorState message={error} onRetry={load} />}

      <Section title="How each level is treated">
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {(['R0', 'R1', 'R2', 'R3', 'R4', 'R5'] as RiskLevel[]).map((item) => (
            <div key={item} className="rounded-card border border-line bg-surface p-4">
              <div className="flex items-center justify-between gap-2">
                <RiskBadge level={item} />
                <span className="meta tabular-nums">
                  {counts[item] ?? 0} {counts[item] === 1 ? 'capability' : 'capabilities'}
                </span>
              </div>
              <p className="mt-2 text-xs text-fg-muted">{RISK_DESCRIPTIONS[item]}</p>
              <p className="mt-2 text-xs font-medium text-fg">{DISPOSITIONS[item]}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section
        title={`All capabilities (${filtered.length})`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <input
              className="input w-48"
              placeholder="Filter by name…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              aria-label="Filter capabilities"
            />
            <div className="flex gap-1">
              {LEVELS.map((item) => (
                <button
                  key={item || 'all'}
                  type="button"
                  onClick={() => setLevel(item)}
                  className={`btn-sm ${level === item ? 'btn-primary' : 'btn-ghost'}`}
                  aria-pressed={level === item}
                >
                  {item || 'All'}
                </button>
              ))}
            </div>
          </div>
        }
      >
        {loading && capabilities.length === 0 ? (
          <LoadingRows rows={4} label="Loading capabilities" />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No capabilities match"
            description="Try clearing the filter."
          />
        ) : (
          <div className="overflow-hidden rounded-card border border-line bg-surface">
            <table className="table">
              <thead>
                <tr>
                  <th>Capability</th>
                  <th>Risk</th>
                  <th className="hidden sm:table-cell">Category</th>
                  <th className="hidden md:table-cell">Traits</th>
                  <th>Allowed alone?</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const needsApproval = ['R2', 'R3', 'R4'].includes(item.risk);
                  return (
                    <tr key={item.name}>
                      <td>
                        <span className="font-medium text-fg">{item.name}</span>
                        {item.prohibited_reason && (
                          <p className="mt-0.5 text-xs text-danger">{item.prohibited_reason}</p>
                        )}
                      </td>
                      <td>
                        <RiskBadge level={item.risk} />
                      </td>
                      <td className="hidden sm:table-cell">
                        <span className="badge badge-neutral">{item.category}</span>
                      </td>
                      <td className="hidden md:table-cell">
                        <span className="flex flex-wrap gap-1">
                          {item.external && <span className="badge badge-neutral">external</span>}
                          {item.physical && <span className="badge badge-danger">physical</span>}
                          {item.destructive && (
                            <span className="badge badge-danger">destructive</span>
                          )}
                          {!item.reversible && (
                            <span className="badge badge-warning">irreversible</span>
                          )}
                          {item.data_sensitivity !== 'none' && (
                            <span className="badge badge-neutral">{item.data_sensitivity}</span>
                          )}
                        </span>
                      </td>
                      <td>
                        {item.risk === 'R5' ? (
                          <span className="badge badge-danger">Never</span>
                        ) : needsApproval ? (
                          <span className="badge badge-warning">
                            <LockIcon className="h-3.5 w-3.5" />
                            {item.risk === 'R4' ? 'Human only' : 'Needs approval'}
                          </span>
                        ) : (
                          <span className="badge badge-success">Yes</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

export default function CapabilitiesPageWrapper() {
  return (
    <AuthRequired>
      <CapabilitiesPage />
    </AuthRequired>
  );
}
