'use client';

/**
 * Timeline — the event journal for one Mind.
 *
 * This answers "why did the Mind do that?" from recorded facts rather than from
 * the Mind's own recollection. Events are correlated: a single objective shares
 * a `correlation_id`, and each event can point at its `causation_id`, so a chain
 * of decisions is followable rather than a flat log.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthRequired from '@/components/AuthRequired';
import PageHeader from '@/components/shell/PageHeader';
import { EmptyState, ErrorState, LoadingRows, Section } from '@/components/governance/primitives';
import {
  governanceApi,
  formatRelative,
  shortId,
  type AuditEvent,
  type JournalVerification,
} from '@/lib/governance';
import { mindRoutes } from '@/lib/navigation';
import { RefreshIcon, CheckIcon, AlertIcon } from '@/components/shell/icons';

const WINDOWS = [
  { hours: 1, label: '1h' },
  { hours: 24, label: '24h' },
  { hours: 24 * 7, label: '7d' },
  { hours: 24 * 30, label: '30d' },
];

/** Event families, and how loud each should look. */
const FAMILIES = [
  { prefix: '', label: 'All' },
  { prefix: 'action.', label: 'Actions' },
  { prefix: 'grant.', label: 'Approvals' },
  { prefix: 'memory.', label: 'Memory' },
  { prefix: 'journal.', label: 'Integrity' },
];

function toneFor(eventType: string): string {
  if (eventType.includes('blocked') || eventType.includes('emergency_stop')) return 'danger';
  if (eventType.includes('tampered')) return 'danger';
  if (eventType.includes('approval_requested') || eventType.includes('expired')) return 'warning';
  if (eventType.includes('executed') || eventType.includes('approved')) return 'success';
  if (eventType.includes('failed') || eventType.includes('rejected')) return 'warning';
  return 'neutral';
}

function TimelinePage() {
  const params = useParams();
  const mindId = params.id as string;
  const routes = mindRoutes(mindId);

  const [hours, setHours] = useState(24);
  const [family, setFamily] = useState('');
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [journal, setJournal] = useState<JournalVerification | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [rows, verification] = await Promise.all([
        governanceApi.timeline(mindId, {
          hours,
          eventType: family || undefined,
          limit: 300,
        }),
        governanceApi.verifyJournal(mindId),
      ]);
      // Newest first: a timeline you have to scroll to the bottom of is a log.
      setEvents([...rows].reverse());
      setJournal(verification);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load the timeline');
    } finally {
      setLoading(false);
    }
  }, [mindId, hours, family]);

  useEffect(() => {
    load();
  }, [load]);

  const grouped = useMemo(() => {
    const buckets = new Map<string, AuditEvent[]>();
    for (const event of events) {
      const day = new Date(event.timestamp).toLocaleDateString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      });
      const list = buckets.get(day) ?? [];
      list.push(event);
      buckets.set(day, list);
    }
    return Array.from(buckets.entries());
  }, [events]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      <PageHeader
        title="Timeline"
        breadcrumb={
          <Link href={routes.overview} className="hover:text-fg">
            Mind
          </Link>
        }
        description="What happened, in order, from the append-only journal. Each entry is hash-chained to the one before it, so a deletion or edit is detectable rather than invisible."
        actions={
          <button type="button" className="btn-secondary btn-sm" onClick={load} disabled={loading}>
            <RefreshIcon className="h-4 w-4" />
            Refresh
          </button>
        }
      />

      {journal && (
        <div
          className={`flex flex-wrap items-center gap-3 rounded-card border p-4 ${
            journal.ok ? 'border-line bg-surface' : 'border-danger/50 bg-danger/5'
          }`}
        >
          <span className={journal.ok ? 'text-accent' : 'text-danger'}>
            {journal.ok ? <CheckIcon /> : <AlertIcon />}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-fg">
              {journal.ok ? 'Journal integrity verified' : 'Journal integrity FAILED'}
            </p>
            <p className="mt-0.5 text-xs text-fg-muted">
              {journal.ok
                ? `${journal.checked} events re-hashed and matched.`
                : `${journal.reason} at ${journal.broken_at}. This is an incident: the record has been altered.`}
            </p>
          </div>
        </div>
      )}

      {error && <ErrorState message={error} onRetry={load} />}

      <Section title="Filters">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex flex-wrap gap-1.5">
            {WINDOWS.map((window) => (
              <button
                key={window.hours}
                type="button"
                onClick={() => setHours(window.hours)}
                className={`btn-sm ${hours === window.hours ? 'btn-primary' : 'btn-secondary'}`}
                aria-pressed={hours === window.hours}
              >
                Last {window.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {FAMILIES.map((item) => (
              <button
                key={item.prefix || 'all'}
                type="button"
                onClick={() => setFamily(item.prefix)}
                className={`btn-sm ${family === item.prefix ? 'btn-primary' : 'btn-ghost'}`}
                aria-pressed={family === item.prefix}
              >
                {item.label}
              </button>
            ))}
          </div>
          <p className="meta ml-auto">{events.length} events</p>
        </div>
      </Section>

      {loading && events.length === 0 ? (
        <LoadingRows rows={5} label="Loading timeline" />
      ) : events.length === 0 ? (
        <EmptyState
          title="Nothing in this window"
          description="Try a longer time range, or a different event family."
        />
      ) : (
        <div className="space-y-6">
          {grouped.map(([day, dayEvents]) => (
            <div key={day}>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-fg-subtle">
                {day}
              </p>
              <ol className="space-y-1.5">
                {dayEvents.map((event) => (
                  <li
                    key={event.event_id}
                    className="rounded-lg border border-line bg-surface px-4 py-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`badge badge-${toneFor(event.type)} font-mono`}>
                        {event.type}
                      </span>
                      <time className="meta" dateTime={event.timestamp}>
                        {formatRelative(event.timestamp)}
                      </time>
                      <span className="meta ml-auto font-mono" title="Event id">
                        {shortId(event.event_id, 10)}
                      </span>
                    </div>

                    {Object.keys(event.payload).length > 0 && (
                      <pre className="mono mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all rounded-md bg-surface-2 p-2.5 text-xs text-fg-muted">
                        {JSON.stringify(event.payload, null, 2)}
                      </pre>
                    )}

                    <p className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-[0.6875rem] text-fg-subtle">
                      <span>
                        actor: {event.actor_type}
                        {event.actor_id ? ` (${shortId(event.actor_id, 16)})` : ''}
                      </span>
                      {event.correlation_id && (
                        <span title="All events from the same objective share this id">
                          correlation: {shortId(event.correlation_id, 12)}
                        </span>
                      )}
                      <span>seq {event.sequence}</span>
                    </p>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function TimelinePageWrapper() {
  return (
    <AuthRequired>
      <TimelinePage />
    </AuthRequired>
  );
}
