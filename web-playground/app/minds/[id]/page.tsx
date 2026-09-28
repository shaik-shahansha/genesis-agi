'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthRequired from '@/components/AuthRequired';
import { api } from '@/lib/api';
import { useMindCache } from '@/lib/MindContext';
import PageHeader from '@/components/shell/PageHeader';
import { LoadingRows, StatusBadge } from '@/components/governance/primitives';
import OverviewTab from '@/components/mind/OverviewTab';
import IdentityTab from '@/components/mind/IdentityTab';
import MemoryTab from '@/components/mind/MemoryTab';
import ConsciousnessTab from '@/components/mind/ConsciousnessTab';
import ThinkingTab from '@/components/mind/ThinkingTab';
import AutonomyTab from '@/components/mind/AutonomyTab';
import WorkspaceTab from '@/components/mind/WorkspaceTab';
import PluginsTab from '@/components/mind/PluginsTab';
import LLMCallsTab from '@/components/mind/LLMCallsTab';
import LogsTab from '@/components/mind/LogsTab';
import SettingsTab from '@/components/mind/SettingsTab';

type TabType =
  | 'overview'
  | 'identity'
  | 'memory'
  | 'consciousness'
  | 'thinking'
  | 'autonomy'
  | 'workspace'
  | 'plugins'
  | 'llm'
  | 'logs'
  | 'settings';

/**
 * The Mind detail surface.
 *
 * This page previously drew its own header, back-link, status bar and tab strip,
 * duplicating the app shell around it. `PageHeader` owns that now, and the shell
 * owns the frame, so the tabs only have to be tabs.
 *
 * The tab list is data rather than markup so a new tab cannot forget to render
 * its own active state.
 */
export default function MindDetailPage() {
  const params = useParams();
  const mindId = params.id as string;
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [mind, setMind] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { getCachedMind, setCachedMind, invalidateMind } = useMindCache();

  useEffect(() => {
    loadMind();
  }, [mindId]);

  const loadMind = async () => {
    try {
      const cached = getCachedMind(mindId);
      if (cached) {
        setMind(cached);
        setLoading(false);
        // Still refresh in the background; the cache is for first paint only.
        api
          .getMind(mindId)
          .then((data) => {
            setMind(data);
            setCachedMind(mindId, data);
          })
          .catch(console.error);
        return;
      }

      const data = await api.getMind(mindId);
      setMind(data);
      setCachedMind(mindId, data);
    } catch (error) {
      console.error('Error loading mind:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    invalidateMind(mindId);
    await loadMind();
  };

  const tabs: { id: TabType; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'identity', label: 'Identity' },
    { id: 'memory', label: 'Conversation' },
    { id: 'consciousness', label: 'Consciousness' },
    { id: 'thinking', label: 'Thinking' },
    { id: 'autonomy', label: 'Autonomy' },
    { id: 'workspace', label: 'Workspace' },
    { id: 'plugins', label: 'Plugins' },
    { id: 'llm', label: 'LLM Calls' },
    { id: 'logs', label: 'Logs' },
    { id: 'settings', label: 'Settings' },
  ];

  if (loading) {
    return (
      <AuthRequired>
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="skeleton h-8 w-56" />
          <div className="skeleton mt-3 h-4 w-80" />
          <div className="mt-8">
            <LoadingRows rows={3} label="Loading this Mind" />
          </div>
        </div>
      </AuthRequired>
    );
  }

  if (!mind) {
    return (
      <AuthRequired>
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="page-title">Mind not found</h1>
          <p className="mt-2 text-sm text-fg-muted">
            No Mind with the identifier <span className="font-mono text-xs">{mindId}</span> exists
            on this installation, or you do not have access to it.
          </p>
          <Link href="/" className="btn-primary mt-6">
            Back to dashboard
          </Link>
        </div>
      </AuthRequired>
    );
  }

  const statusTone =
    mind.status === 'active' ? 'success' : mind.status === 'sleeping' ? 'warning' : 'neutral';

  return (
    <AuthRequired>
      <PageHeader
        breadcrumb={
          <Link href="/" className="hover:text-fg">
            ← All Minds
          </Link>
        }
        title={mind.name}
        description={
          <span className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="font-mono text-xs">{mind.gmid}</span>
            <StatusBadge tone={statusTone}>{mind.status || 'unknown'}</StatusBadge>
            <span>
              {mind.age || '—'} · {mind.memory_count ?? 0} memories ·{' '}
              <span className="capitalize">{mind.current_emotion || 'neutral'}</span>
            </span>
          </span>
        }
        actions={
          <>
            <Link href={`/chat/${mind.gmid}`} className="btn-primary">
              Chat
            </Link>
            <Link href={`/immersive/${mind.gmid}`} className="btn-secondary">
              Immersive
            </Link>
          </>
        }
      />

      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <nav className="scroll-strip mb-6 -mx-1 flex gap-1 overflow-x-auto border-b border-line pb-px">
          {tabs.map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                aria-current={active ? 'page' : undefined}
                className={`whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? 'border-accent text-fg'
                    : 'border-transparent text-fg-muted hover:border-line-strong hover:text-fg'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        <div className="min-h-[400px]">
          {activeTab === 'overview' && <OverviewTab mind={mind} onRefresh={handleRefresh} />}
          {activeTab === 'identity' && <IdentityTab mind={mind} />}
          {activeTab === 'memory' && <MemoryTab mindId={mindId} />}
          {activeTab === 'consciousness' && <ConsciousnessTab mindId={mindId} />}
          {activeTab === 'thinking' && <ThinkingTab mindId={mindId} mind={mind} />}
          {activeTab === 'autonomy' && <AutonomyTab mindId={mindId} mind={mind} />}
          {activeTab === 'workspace' && <WorkspaceTab mindId={mindId} />}
          {activeTab === 'plugins' && <PluginsTab mindId={mindId} />}
          {activeTab === 'llm' && <LLMCallsTab mindId={mindId} />}
          {activeTab === 'logs' && <LogsTab mindId={mindId} />}
          {activeTab === 'settings' && <SettingsTab mind={mind} onRefresh={handleRefresh} />}
        </div>
      </div>
    </AuthRequired>
  );
}

