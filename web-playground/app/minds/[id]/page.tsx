'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthRequired from '@/components/AuthRequired';
import { api } from '@/lib/api';
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

type TabType = 'overview' | 'identity' | 'memory' | 'consciousness' | 'thinking' | 'autonomy' | 'workspace' | 'plugins' | 'llm' | 'logs' | 'settings';

export default function MindDetailPage() {
  const params = useParams();
  const mindId = params.id as string;
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [mind, setMind] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMind();
  }, [mindId]);

  const loadMind = async () => {
    try {
      const data = await api.getMind(mindId);
      setMind(data);
    } catch (error) {
      console.error('Error loading mind:', error);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'identity', label: 'Identity', icon: '🆔' },
    { id: 'memory', label: 'Memory', icon: '🧠' },
    { id: 'consciousness', label: 'Consciousness', icon: '✨' },
    { id: 'thinking', label: 'Thinking', icon: '💭' },
    { id: 'autonomy', label: 'Autonomy', icon: '🤖' },
    { id: 'workspace', label: 'Workspace', icon: '📁' },
    { id: 'plugins', label: 'Plugins', icon: '🔌' },
    { id: 'llm', label: 'LLM Calls', icon: '📡' },
    { id: 'logs', label: 'Logs', icon: '📝' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  if (loading) {
    return (
      <AuthRequired>
        <div className="flex items-center justify-center min-h-screen">
          <div className="spinner"></div>
        </div>
      </AuthRequired>
    );
  }

  if (!mind) {
    return (
      <AuthRequired>
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-white mb-4">Mind Not Found</h1>
            <Link href="/" className="btn-primary">
              Back to Dashboard
            </Link>
          </div>
        </div>
      </AuthRequired>
    );
  }

  return (
    <AuthRequired>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link href="/" className="text-sm text-gray-300 hover:text-white mb-2 inline-block">
            ← Back to Dashboard
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">{mind.name}</h1>
              <p className="text-gray-300 mt-1">GMID: {mind.gmid}</p>
            </div>
            <div className="flex gap-2">
              <Link href={`/chat/${mind.gmid}`} className="btn-ghost">
                💬 Chat
              </Link>
              <Link href={`/immersive/${mind.gmid}`} className="btn-primary">
                🎭 Immersive Mode
              </Link>
            </div>
          </div>
        </div>

        {/* Status Bar */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <span className="text-sm text-gray-400">Status</span>
                <p className="font-semibold text-white">{mind.status}</p>
              </div>
              <div>
                <span className="text-sm text-gray-400">Age</span>
                <p className="font-semibold text-white">{mind.age}</p>
              </div>
              <div>
                <span className="text-sm text-gray-400">Emotion</span>
                <p className="font-semibold text-white">{mind.current_emotion}</p>
              </div>
              <div>
                <span className="text-sm text-gray-400">Memories</span>
                <p className="font-semibold text-white">{mind.memory_count}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-700 mb-6">
          <div className="flex gap-2 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? 'border-b-2 border-purple-500 text-purple-400'
                    : 'text-gray-300 hover:text-white'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="min-h-[500px]">
          {activeTab === 'overview' && <OverviewTab mind={mind} onRefresh={loadMind} />}
          {activeTab === 'identity' && <IdentityTab mind={mind} />}
          {activeTab === 'memory' && <MemoryTab mindId={mindId} />}
          {activeTab === 'consciousness' && <ConsciousnessTab mindId={mindId} />}
          {activeTab === 'thinking' && <ThinkingTab mindId={mindId} />}
          {activeTab === 'autonomy' && <AutonomyTab mindId={mindId} />}
          {activeTab === 'workspace' && <WorkspaceTab mindId={mindId} />}
          {activeTab === 'plugins' && <PluginsTab mindId={mindId} />}
          {activeTab === 'llm' && <LLMCallsTab mindId={mindId} />}
          {activeTab === 'logs' && <LogsTab mindId={mindId} />}
          {activeTab === 'settings' && <SettingsTab mind={mind} onRefresh={loadMind} />}
        </div>
      </div>
    </AuthRequired>
  );
}
