'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

interface Environment {
  id: string;
  name: string;
  env_type: string;
  description: string;
  creator_gmid: string;
  is_public: boolean;
  max_occupancy: number;
  current_occupancy: number;
  created_at: string;
}

export default function EnvironmentsPage() {
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [active, setActive] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newEnv, setNewEnv] = useState({
    name: '',
    template: '',
    description: '',
    is_public: true,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Load all data in parallel with error handling
      const results = await Promise.allSettled([
        api.getEnvironments({ limit: 50 }),
        api.getEnvironmentTemplates(),
        api.getActiveEnvironments()
      ]);

      if (results[0].status === 'fulfilled') {
        setEnvironments(results[0].value.environments || []);
      }
      if (results[1].status === 'fulfilled') {
        setTemplates(results[1].value.templates || []);
      }
      if (results[2].status === 'fulfilled') {
        setActive(results[2].value.active_environments || []);
      }

      // If all failed, show error
      if (results.every(r => r.status === 'rejected')) {
        setError('Failed to load environments. Please check if the backend server is running.');
      }
    } catch (error) {
      console.error('Failed to load data:', error);
      setError('Failed to load environments. Please check if the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEnvironment = async () => {
    try {
      await api.createEnvironment(newEnv);
      setShowCreateModal(false);
      setNewEnv({ name: '', template: '', description: '', is_public: true });
      loadData();
    } catch (error: any) {
      alert(`Failed to create environment: ${error.message}`);
    }
  };

  const getTypeIcon = (type: string) => {
    const icons: { [key: string]: string } = {
      educational: '📚',
      professional: '💼',
      wellness: '🧘',
      creative: '🎨',
      social: '👥',
      academic: '🔬',
      entertainment: '🎮'
    };
    return icons[type] || '🌍';
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="clean-card p-6 text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button onClick={loadData} className="btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-white">Environments</h1>
          <p className="text-gray-300 mt-1">{environments.length} total</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="btn-primary">
          New Environment
        </button>
      </div>

      {/* Active Environments */}
      {active.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">Active Now</h2>
          <div className="clean-card p-4">
            <div className="space-y-2">
              {active.map((env) => (
                <Link
                  key={env.environment_id}
                  href={`/environments/${env.environment_id}`}
                  className="flex items-center justify-between p-3 bg-slate-700/50 hover:bg-slate-700 rounded transition"
                >
                  <div>
                    <h3 className="font-medium text-white">{env.name}</h3>
                    <p className="text-sm text-gray-400">{env.occupancy} Minds present</p>
                  </div>
                  <span className="text-green-400 text-sm">● Live</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* All Environments */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-white mb-4">All Environments</h2>
        {environments.length === 0 ? (
          <div className="clean-card p-6 text-center">
            <p className="text-gray-300 mb-4">No environments yet</p>
            <button onClick={() => setShowCreateModal(true)} className="btn-primary">
              Create First Environment
            </button>
          </div>
        ) : (
          <div className="grid gap-4">
            {environments.map((env) => (
              <Link
                key={env.id}
                href={`/environments/${env.id}`}
                className="clean-card p-6 flex items-center justify-between hover:border-purple-500 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <span className="text-3xl">{getTypeIcon(env.env_type)}</span>
                  <div>
                    <h3 className="text-lg font-semibold text-white">{env.name}</h3>
                    <div className="flex items-center gap-3 mt-1 text-sm text-gray-300">
                      <span className="capitalize">{env.env_type}</span>
                      <span>·</span>
                      <span>{env.current_occupancy}/{env.max_occupancy} occupancy</span>
                      {env.is_public && (
                        <>
                          <span>·</span>
                          <span className="text-green-400">Public</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-purple-400">→</div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Templates */}
      {templates.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">Templates</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((template) => (
              <div
                key={template.name}
                className="clean-card p-4 cursor-pointer hover:border-purple-500 transition"
                onClick={() => {
                  setNewEnv({ ...newEnv, template: template.name });
                  setShowCreateModal(true);
                }}
              >
                <h3 className="font-semibold text-white mb-2">{template.name}</h3>
                <p className="text-sm text-gray-400">{template.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setShowCreateModal(false)}>
          <div className="clean-card p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-xl font-semibold text-white mb-4">Create Environment</h2>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm text-gray-300 mb-2">Name</label>
                <input
                  type="text"
                  value={newEnv.name}
                  onChange={(e) => setNewEnv({ ...newEnv, name: e.target.value })}
                  placeholder="My Environment"
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-300 mb-2">Template</label>
                <select
                  value={newEnv.template}
                  onChange={(e) => setNewEnv({ ...newEnv, template: e.target.value })}
                  className="input w-full"
                >
                  <option value="">No template</option>
                  {templates.map((t) => (
                    <option key={t.name} value={t.name}>{t.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-300 mb-2">Description</label>
                <textarea
                  value={newEnv.description}
                  onChange={(e) => setNewEnv({ ...newEnv, description: e.target.value })}
                  placeholder="Describe your environment..."
                  rows={3}
                  className="input w-full"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_public"
                  checked={newEnv.is_public}
                  onChange={(e) => setNewEnv({ ...newEnv, is_public: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="is_public" className="text-sm text-gray-300">
                  Public (anyone can join)
                </label>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateEnvironment}
                disabled={!newEnv.name}
                className="flex-1 btn-primary disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
