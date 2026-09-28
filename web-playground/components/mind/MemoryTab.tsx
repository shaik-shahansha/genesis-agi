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

interface ConversationMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: any;
}

interface MemoryTabProps {
  mindId: string;
}

/**
 * Conversation history between you and this Mind.
 *
 * The tab is labelled "Memory" in the Mind nav, but the endpoint it reads is the
 * conversation log — long-term memory lives behind `/memories` and is a
 * different thing. The heading says what this actually is rather than inheriting
 * the nav label, because "Memory" implies you are looking at what the Mind has
 * retained, and you are not.
 *
 * The previous implementation read `genesis_user_email` out of `localStorage`
 * and fetched with a Firebase token directly. That key is only written by the
 * Firebase sign-in flow, so on an install using the built-in JWT login the tab
 * silently showed "no conversation history" — forever, with no error. The email
 * is not needed at all: the server takes it from the verified token, which also
 * means a client cannot ask for someone else's transcript.
 */
export default function MemoryTab({ mindId }: MemoryTabProps) {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadConversations();
  }, [mindId]);

  const loadConversations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getConversationMessages(mindId, 200);
      setMessages(data?.messages || []);
    } catch (err: any) {
      setMessages([]);
      setError(err?.message || 'Could not load the conversation history.');
    } finally {
      setLoading(false);
    }
  };

  const filteredMessages = messages.filter((m) => {
    const matchesFilter = filter === 'all' || m.role === filter;
    const matchesSearch =
      search === '' || m.content.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const filterOptions = [
    { value: 'all', label: 'All messages' },
    { value: 'user', label: 'Your messages' },
    { value: 'assistant', label: 'Mind replies' },
  ];

  const userMessages = messages.filter((m) => m.role === 'user');
  const assistantMessages = messages.filter((m) => m.role === 'assistant');

  if (loading) {
    return <LoadingRows rows={3} label="Loading conversation history" />;
  }

  return (
    <div className="space-y-6">
      {error && <ErrorState message={error} onRetry={loadConversations} />}

      <Section
        title="Conversation history"
        description="Messages exchanged with this Mind. This is the transcript, not the long-term memory store."
        actions={
          <button
            type="button"
            onClick={loadConversations}
            disabled={loading}
            className="btn-ghost btn-sm"
          >
            <RefreshIcon className="h-4 w-4" />
            Refresh
          </button>
        }
      >
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="search"
            placeholder="Search the transcript…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input flex-1"
            aria-label="Search conversation history"
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input sm:w-48"
            aria-label="Filter by speaker"
          >
            {filterOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Metric label="Messages" value={messages.length} />
          <Metric label="From you" value={userMessages.length} />
          <Metric label="From the Mind" value={assistantMessages.length} />
          <Metric label="Matching" value={filteredMessages.length} />
        </div>
      </Section>

      {filteredMessages.length === 0 ? (
        messages.length === 0 ? (
          <EmptyState
            title="No conversation yet"
            description="Messages appear here once you have talked to this Mind. The transcript is per-user: you only ever see your own."
          />
        ) : (
          <EmptyState
            title="Nothing matches"
            description="No messages match the current search and filter."
          />
        )
      ) : (
        <div className="space-y-3">
          {filteredMessages.map((message) => {
            const fromUser = message.role === 'user';
            return (
              <div key={message.id} className="card-flat">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <StatusBadge tone={fromUser ? 'info' : 'violet'}>
                    {fromUser ? 'You' : 'Mind'}
                  </StatusBadge>
                  <span className="text-xs text-fg-subtle">
                    {new Date(message.timestamp).toLocaleString()}
                  </span>
                </div>
                <p className="whitespace-pre-wrap text-sm text-fg">{message.content}</p>
              </div>
            );
          })}
        </div>
      )}
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

