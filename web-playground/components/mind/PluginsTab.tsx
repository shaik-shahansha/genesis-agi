'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import {
  EmptyState,
  LoadingRows,
  Section,
  StatusBadge,
} from '@/components/governance/primitives';
import { ChevronRightIcon, PlugIcon, PlusIcon, XMarkIcon } from '@/components/shell/icons';

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
    id: 'browser_use', 
    name: 'Browser Automation', 
    category: 'Integration',
    description: 'Web scraping, form filling, and browser automation',
    emoji: '🌐',
    requiresConfig: false,
    capabilities: ['web_scraping', 'form_filling', 'automation'],
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
      const data = await api.getPlugins(mindId);
      setPlugins(data.plugins || []);
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
      const config = pluginConfig[pluginId] || undefined;
      await api.addPlugin(mindId, pluginId, config);
      await loadPlugins();
      setShowAddModal(false);
      setSelectedPlugin(null);
      setPluginConfig({});
    } catch (error: any) {
      alert(`Failed to add plugin: ${error.message}`);
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
      await api.removePlugin(mindId, pluginName);
      await loadPlugins();
    } catch (error: any) {
      alert(`Failed to remove plugin: ${error.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleTogglePlugin = async (pluginName: string, currentlyEnabled: boolean) => {
    setActionLoading(pluginName);
    try {
      if (currentlyEnabled) {
        await api.disablePlugin(mindId, pluginName);
      } else {
        await api.enablePlugin(mindId, pluginName);
      }
      await loadPlugins();
    } catch (error: any) {
      alert(`Failed to toggle plugin: ${error.message}`);
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
    return <LoadingRows rows={3} label="Loading plugins" />;
  }

  return (
    <div className="space-y-6">
      <Section
        title="Plugins"
        description="Capabilities this Mind has. Installing one widens what it can do, so every plugin's actions still pass through the governance gate."
        actions={
          <button type="button" onClick={() => setShowAddModal(true)} className="btn-primary">
            <PlusIcon className="h-4 w-4" />
            Add plugin
          </button>
        }
      >
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setSelectedCategory(cat)}
              aria-pressed={selectedCategory === cat}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                selectedCategory === cat
                  ? 'border-accent bg-accent-soft text-accent'
                  : 'border-line bg-surface text-fg-muted hover:border-line-strong hover:text-fg'
              }`}
            >
              {cat === 'all' ? 'All' : cat}
            </button>
          ))}
        </div>
      </Section>

      <Section title={`Installed (${filteredInstalledPlugins.length})`}>
        {filteredInstalledPlugins.length === 0 ? (
          <EmptyState
            title="No plugins in this category"
            description="Switch the filter, or install one from the catalogue."
          />
        ) : (
          <div className="space-y-3">
            {filteredInstalledPlugins.map((plugin) => {
              const pluginInfo = availablePlugins.find(
                (p) => p.id === plugin.name.toLowerCase().replace(/\s+/g, '_')
              );
              const busy = actionLoading === plugin.name;
              return (
                <div key={plugin.name} className="card-flat">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex min-w-0 flex-1 items-start gap-3">
                      <PluginGlyph emoji={pluginInfo?.emoji} />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-medium text-fg">{plugin.name}</h3>
                          <span className="font-mono text-xs text-fg-subtle">v{plugin.version}</span>
                          <StatusBadge tone={plugin.enabled ? 'success' : 'neutral'}>
                            {plugin.enabled ? 'Enabled' : 'Disabled'}
                          </StatusBadge>
                        </div>
                        <p className="mt-1 text-sm text-fg-muted">{plugin.description}</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => handleTogglePlugin(plugin.name, plugin.enabled)}
                        disabled={busy}
                        className="btn-secondary btn-sm"
                      >
                        {busy ? '…' : plugin.enabled ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRemovePlugin(plugin.name)}
                        disabled={busy}
                        className="btn-ghost btn-sm text-danger"
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
      </Section>

      {showAddModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-plugin-title"
        >
          <div className="card max-h-[80vh] w-full max-w-2xl overflow-y-auto">
            <div className="mb-4 flex items-center justify-between border-b border-line pb-4">
              <h3 id="add-plugin-title" className="text-base font-semibold text-fg">
                {selectedPlugin ? 'Configure and install' : 'Add a plugin'}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setShowAddModal(false);
                  setSelectedPlugin(null);
                  setPluginConfig({});
                }}
                className="btn-ghost btn-sm"
                aria-label="Close"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>

            {!selectedPlugin ? (
              <div className="space-y-3">
                {filteredAvailablePlugins.length === 0 ? (
                  <EmptyState
                    title="Nothing left to install"
                    description="Every plugin in this category is already on this Mind."
                  />
                ) : (
                  filteredAvailablePlugins.map((plugin) => (
                    <button
                      key={plugin.id}
                      type="button"
                      onClick={() => setSelectedPlugin(plugin)}
                      className="card-interactive w-full text-left"
                    >
                      <div className="flex items-start gap-3">
                        <PluginGlyph emoji={plugin.emoji} />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h4 className="font-medium text-fg">{plugin.name}</h4>
                            <StatusBadge tone="info">{plugin.category}</StatusBadge>
                            {plugin.requiresConfig && (
                              <StatusBadge tone="warning">Needs configuration</StatusBadge>
                            )}
                          </div>
                          <p className="mt-1 text-sm text-fg-muted">{plugin.description}</p>
                        </div>
                        <ChevronRightIcon className="mt-1 h-4 w-4 flex-shrink-0 text-fg-subtle" />
                      </div>
                    </button>
                  ))
                )}
              </div>
            ) : (
              <div>
                <button
                  type="button"
                  onClick={() => setSelectedPlugin(null)}
                  className="btn-ghost btn-sm mb-4"
                >
                  ← Back to the list
                </button>

                <div className="card-flat mb-6">
                  <div className="flex items-start gap-3">
                    <PluginGlyph emoji={selectedPlugin.emoji} />
                    <div>
                      <h4 className="font-medium text-fg">{selectedPlugin.name}</h4>
                      <p className="mt-1 text-sm text-fg-muted">{selectedPlugin.description}</p>
                      <div className="mt-2">
                        <StatusBadge tone="info">{selectedPlugin.category}</StatusBadge>
                      </div>
                    </div>
                  </div>
                </div>

                {selectedPlugin.requiresConfig && selectedPlugin.configFields && (
                  <div className="mb-6 space-y-4">
                    <h5 className="section-title">Configuration</h5>
                    {selectedPlugin.configFields.map((field: any) => (
                      <div key={field.name}>
                        <label
                          htmlFor={`plugin-${selectedPlugin.id}-${field.name}`}
                          className="label mb-1.5 block"
                        >
                          {field.label}
                          {field.required && <span className="ml-1 text-danger">*</span>}
                        </label>
                        <input
                          id={`plugin-${selectedPlugin.id}-${field.name}`}
                          type={field.type || 'text'}
                          value={pluginConfig[selectedPlugin.id]?.[field.name] || ''}
                          onChange={(e) =>
                            setPluginConfig({
                              ...pluginConfig,
                              [selectedPlugin.id]: {
                                ...pluginConfig[selectedPlugin.id],
                                [field.name]: e.target.value,
                              },
                            })
                          }
                          className="input"
                          placeholder={field.placeholder}
                          autoComplete={field.type === 'password' ? 'new-password' : 'off'}
                        />
                      </div>
                    ))}
                    <p className="text-xs text-fg-subtle">
                      Values are sent to this installation only. Secret-shaped fields are redacted in
                      the audit journal — the journal records that a credential was configured, never
                      its value.
                    </p>
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setSelectedPlugin(null)}
                    className="btn-secondary flex-1 justify-center"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => handleAddPlugin(selectedPlugin.id)}
                    disabled={actionLoading === selectedPlugin.id}
                    className="btn-primary flex-1 justify-center"
                  >
                    {actionLoading === selectedPlugin.id ? 'Installing…' : 'Install plugin'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * The catalogue's glyph for a plugin.
 *
 * `availablePlugins` carries emoji for this, but one entry was changed to the
 * literal text `[Done]` — a placeholder that leaked into the UI and rendered as
 * grey brackets next to every installed plugin. Rather than trust the data, this
 * falls back to an icon whenever the value is not a single grapheme.
 */
function PluginGlyph({ emoji }: { emoji?: string }) {
  const usable = typeof emoji === 'string' && emoji.length > 0 && emoji.length <= 4 && !emoji.startsWith('[');
  return (
    <div className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-card bg-surface-3 text-lg">
      {usable ? emoji : <PlugIcon className="h-4 w-4 text-fg-subtle" />}
    </div>
  );
}

