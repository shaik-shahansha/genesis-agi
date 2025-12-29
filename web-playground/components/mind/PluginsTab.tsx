'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface PluginsTabProps {
  mindId: string;
}

interface Plugin {
  name: string;
  version: string;
  description: string;
  enabled: boolean;
  config?: any;
}

const availablePlugins = [
  { 
    id: 'lifecycle', 
    name: 'Lifecycle', 
    category: 'Core',
    description: 'Mortality, urgency, and limited lifespan mechanics',
    emoji: '⏳',
    requiresConfig: false,
  },
  { 
    id: 'gen', 
    name: 'GEN (Essence)', 
    category: 'Core',
    description: 'Economy system with motivation and value tracking',
    emoji: '💎',
    requiresConfig: false,
  },
  { 
    id: 'tasks', 
    name: 'Tasks', 
    category: 'Core',
    description: 'Goal-oriented task management and execution',
    emoji: '✅',
    requiresConfig: false,
  },
  { 
    id: 'workspace', 
    name: 'Workspace', 
    category: 'Core',
    description: 'File system access and management capabilities',
    emoji: '📁',
    requiresConfig: false,
  },
  { 
    id: 'relationships', 
    name: 'Relationships', 
    category: 'Core',
    description: 'Social connections and interpersonal bonds',
    emoji: '🤝',
    requiresConfig: false,
  },
  { 
    id: 'environments', 
    name: 'Environments', 
    category: 'Core',
    description: 'Metaverse and virtual environment integration',
    emoji: '🌍',
    requiresConfig: false,
  },
  { 
    id: 'roles', 
    name: 'Roles', 
    category: 'Core',
    description: 'Purpose definition and job role management',
    emoji: '🎭',
    requiresConfig: false,
  },
  { 
    id: 'events', 
    name: 'Events', 
    category: 'Core',
    description: 'Event tracking and historical timeline',
    emoji: '📅',
    requiresConfig: false,
  },
  { 
    id: 'experiences', 
    name: 'Experiences', 
    category: 'Core',
    description: 'Experience tracking and learning patterns',
    emoji: '📚',
    requiresConfig: false,
  },
  { 
    id: 'perplexity_search', 
    name: 'Perplexity Search', 
    category: 'Integration',
    description: 'Internet search capabilities via Perplexity AI',
    emoji: '🔍',
    requiresConfig: true,
    configFields: [{ name: 'api_key', label: 'API Key', type: 'password', required: true }],
  },
  { 
    id: 'mcp', 
    name: 'MCP', 
    category: 'Integration',
    description: 'Model Context Protocol server integration',
    emoji: '🔌',
    requiresConfig: false,
  },
  { 
    id: 'learning', 
    name: 'Learning', 
    category: 'Experimental',
    description: 'Knowledge accumulation (experimental)',
    emoji: '🧪',
    requiresConfig: false,
  },
  { 
    id: 'goals', 
    name: 'Goals', 
    category: 'Experimental',
    description: 'Long-term goal pursuit (work in progress)',
    emoji: '🎯',
    requiresConfig: false,
  },
  { 
    id: 'knowledge', 
    name: 'Knowledge', 
    category: 'Experimental',
    description: 'Knowledge graph system (basic)',
    emoji: '🧠',
    requiresConfig: false,
  },
];

export default function PluginsTab({ mindId }: PluginsTabProps) {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedPlugin, setSelectedPlugin] = useState<any>(null);
  const [pluginConfig, setPluginConfig] = useState<any>({});

  useEffect(() => {
    loadPlugins();
  }, [mindId]);

  const loadPlugins = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/minds/${mindId}/plugins`);
      if (response.ok) {
        const data = await response.json();
        setPlugins(data.plugins || []);
      } else if (response.status === 404) {
        // Mind doesn't exist or no plugins
        setPlugins([]);
      } else {
        console.error('Error loading plugins:', response.statusText);
      }
    } catch (error) {
      console.error('Error loading plugins:', error);
      // Continue with empty plugins instead of crashing
      setPlugins([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPlugin = async (pluginId: string) => {
    setActionLoading(pluginId);
    try {
      const payload: any = { plugin_name: pluginId };
      
      // Add config if required
      if (pluginConfig[pluginId]) {
        payload.config = pluginConfig[pluginId];
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/minds/${mindId}/plugins`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }
      );

      if (response.ok) {
        await loadPlugins();
        setShowAddModal(false);
        setSelectedPlugin(null);
        setPluginConfig({});
      } else {
        const error = await response.json();
        alert(`Failed to add plugin: ${error.detail || 'Unknown error'}`);
      }
    } catch (error: any) {
      alert(`Error adding plugin: ${error.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRemovePlugin = async (pluginName: string) => {
    if (!confirm(`Are you sure you want to remove the ${pluginName} plugin?`)) {
      return;
    }

    setActionLoading(pluginName);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/minds/${mindId}/plugins/${pluginName}`,
        { method: 'DELETE' }
      );

      if (response.ok) {
        await loadPlugins();
      } else {
        const error = await response.json();
        alert(`Failed to remove plugin: ${error.detail || 'Unknown error'}`);
      }
    } catch (error: any) {
      alert(`Error removing plugin: ${error.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleTogglePlugin = async (pluginName: string, currentlyEnabled: boolean) => {
    setActionLoading(pluginName);
    try {
      const action = currentlyEnabled ? 'disable' : 'enable';
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/minds/${mindId}/plugins/${pluginName}/${action}`,
        { method: 'POST' }
      );

      if (response.ok) {
        await loadPlugins();
      } else {
        const error = await response.json();
        alert(`Failed to ${action} plugin: ${error.detail || 'Unknown error'}`);
      }
    } catch (error: any) {
      alert(`Error toggling plugin: ${error.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const categories = ['all', 'Core', 'Integration', 'Experimental'];
  const installedPluginNames = plugins.map(p => p.name.toLowerCase().replace(/\s+/g, '_'));
  
  const filteredAvailablePlugins = availablePlugins.filter(p => {
    if (selectedCategory !== 'all' && p.category !== selectedCategory) return false;
    return !installedPluginNames.includes(p.id);
  });

  const filteredInstalledPlugins = plugins.filter(p => {
    if (selectedCategory === 'all') return true;
    const plugin = availablePlugins.find(ap => ap.id === p.name.toLowerCase().replace(/\s+/g, '_'));
    return plugin?.category === selectedCategory;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Plugin Management</h2>
            <p className="text-sm text-gray-600 mt-1">
              Extend your Mind's capabilities with plugins. Add, remove, or configure features.
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn-primary"
          >
            ➕ Add Plugin
          </button>
        </div>

        {/* Category Filter */}
        <div className="flex gap-2">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedCategory === cat
                  ? 'bg-blue-100 text-blue-700 border border-blue-300'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300'
              }`}
            >
              {cat === 'all' ? 'All Plugins' : cat}
            </button>
          ))}
        </div>
      </div>

      {/* Installed Plugins */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-md font-semibold text-gray-900 mb-4">
          Installed Plugins ({filteredInstalledPlugins.length})
        </h3>
        
        {filteredInstalledPlugins.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No plugins installed in this category.
          </div>
        ) : (
          <div className="space-y-3">
            {filteredInstalledPlugins.map((plugin) => {
              const pluginInfo = availablePlugins.find(p => p.id === plugin.name.toLowerCase().replace(/\s+/g, '_'));
              return (
                <div
                  key={plugin.name}
                  className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                      <div className="text-3xl">{pluginInfo?.emoji || '🔌'}</div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-gray-900">{plugin.name}</h4>
                          <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                            v{plugin.version}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            plugin.enabled 
                              ? 'bg-green-100 text-green-700' 
                              : 'bg-gray-100 text-gray-600'
                          }`}>
                            {plugin.enabled ? '✓ Enabled' : '○ Disabled'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{plugin.description}</p>
                      </div>
                    </div>
                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => handleTogglePlugin(plugin.name, plugin.enabled)}
                        disabled={actionLoading === plugin.name}
                        className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {actionLoading === plugin.name ? '...' : plugin.enabled ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        onClick={() => handleRemovePlugin(plugin.name)}
                        disabled={actionLoading === plugin.name}
                        className="px-3 py-1.5 text-sm bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition-colors disabled:opacity-50"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Plugin Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Add Plugin</h3>
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setSelectedPlugin(null);
                    setPluginConfig({});
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="p-6">
              {!selectedPlugin ? (
                <div className="space-y-3">
                  {filteredAvailablePlugins.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      All available plugins in this category are already installed.
                    </div>
                  ) : (
                    filteredAvailablePlugins.map((plugin) => (
                      <div
                        key={plugin.id}
                        className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors cursor-pointer"
                        onClick={() => setSelectedPlugin(plugin)}
                      >
                        <div className="flex items-start gap-3">
                          <div className="text-3xl">{plugin.emoji}</div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <h4 className="font-semibold text-gray-900">{plugin.name}</h4>
                              <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                                {plugin.category}
                              </span>
                              {plugin.requiresConfig && (
                                <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded">
                                  Requires Config
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-gray-600 mt-1">{plugin.description}</p>
                          </div>
                          <div className="text-gray-400">→</div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              ) : (
                <div>
                  <button
                    onClick={() => setSelectedPlugin(null)}
                    className="text-sm text-gray-600 hover:text-gray-900 mb-4"
                  >
                    ← Back to plugin list
                  </button>

                  <div className="border border-gray-200 rounded-lg p-4 mb-6">
                    <div className="flex items-start gap-3">
                      <div className="text-4xl">{selectedPlugin.emoji}</div>
                      <div>
                        <h4 className="text-lg font-semibold text-gray-900">{selectedPlugin.name}</h4>
                        <p className="text-sm text-gray-600 mt-1">{selectedPlugin.description}</p>
                        <div className="flex gap-2 mt-2">
                          <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                            {selectedPlugin.category}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {selectedPlugin.requiresConfig && selectedPlugin.configFields && (
                    <div className="space-y-4 mb-6">
                      <h5 className="font-semibold text-gray-900">Configuration</h5>
                      {selectedPlugin.configFields.map((field: any) => (
                        <div key={field.name}>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            {field.label}
                            {field.required && <span className="text-red-500 ml-1">*</span>}
                          </label>
                          <input
                            type={field.type || 'text'}
                            value={pluginConfig[selectedPlugin.id]?.[field.name] || ''}
                            onChange={(e) => setPluginConfig({
                              ...pluginConfig,
                              [selectedPlugin.id]: {
                                ...pluginConfig[selectedPlugin.id],
                                [field.name]: e.target.value,
                              }
                            })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            placeholder={field.placeholder}
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex gap-3">
                    <button
                      onClick={() => setSelectedPlugin(null)}
                      className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleAddPlugin(selectedPlugin.id)}
                      disabled={actionLoading === selectedPlugin.id}
                      className="flex-1 btn-primary disabled:opacity-50"
                    >
                      {actionLoading === selectedPlugin.id ? 'Installing...' : 'Install Plugin'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
