// Genesis Playground - Create Mind Page
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import AuthRequired from '@/components/AuthRequired';
import { getFirebaseToken } from '@/lib/firebase';
import { isCreationDisabled } from '@/lib/env';
import { StatusBadge } from '@/components/governance/primitives';

export default function CreateMindPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    creator_email: '',
    template: 'base/curious_explorer',
    reasoning_model: 'openrouter/meta-llama/llama-3.3-70b-instruct:free',
    fast_model: 'openrouter/meta-llama/llama-3.3-70b-instruct:free',
    autonomy_level: 'medium',
    enable_daemon: false,
    enable_cache: true,
    config: 'standard',
    plugins: [] as string[],
    api_keys: {} as Record<string, string>,
    purpose: '',
    role: '',
    guidance_notes: '',
  });

  const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

  const pluginConfigs = [
    { value: 'minimal', label: 'Minimal', desc: 'Core only (~500 tokens)', emoji: '⚡' },
    { value: 'standard', label: 'Standard', desc: 'Most common (~1,200 tokens)', emoji: '🌟' },
    { value: 'full', label: 'Full', desc: 'All features (~2,000 tokens)', emoji: '🚀' },
    { value: 'custom', label: 'Custom', desc: 'Choose your own', emoji: '🎯' },
  ];

  const availablePlugins = [
    { 
      id: 'lifecycle', 
      name: 'Lifecycle', 
      category: 'Core',
      description: 'Mortality, urgency, limited lifespan',
      emoji: '⏳'
    },
    { 
      id: 'gen', 
      name: 'GEN (Essence)', 
      category: 'Core',
      description: 'Economy system, motivation, value tracking',
      emoji: '💎'
    },
    { 
      id: 'tasks', 
      name: 'Tasks', 
      category: 'Core',
      description: 'Goal-oriented task management',
      emoji: '✅'
    },
    { 
      id: 'workspace', 
      name: 'Workspace', 
      category: 'Core',
      description: 'File system access and management',
      emoji: '📁'
    },
    { 
      id: 'relationships', 
      name: 'Relationships', 
      category: 'Core',
      description: 'Social connections and bonds',
      emoji: '🤝'
    },
    { 
      id: 'environments', 
      name: 'Environments', 
      category: 'Core',
      description: 'Metaverse integration',
      emoji: '🌍'
    },
    { 
      id: 'roles', 
      name: 'Roles', 
      category: 'Core',
      description: 'Purpose definition and job roles',
      emoji: '🎭'
    },
    { 
      id: 'events', 
      name: 'Events', 
      category: 'Core',
      description: 'Event tracking and history',
      emoji: '📅'
    },
    { 
      id: 'experiences', 
      name: 'Experiences', 
      category: 'Core',
      description: 'Experience tracking and learning',
      emoji: '📚'
    },
    { 
      id: 'perplexity_search', 
      name: 'Perplexity Search', 
      category: 'Integration',
      description: 'Internet search with Perplexity AI (requires API key)',
      emoji: '🔍'
    },
    { 
      id: 'mcp', 
      name: 'MCP', 
      category: 'Integration',
      description: 'Model Context Protocol integration',
      emoji: '🔌'
    },
  ];

  const templates = [
    { 
      value: 'base/curious_explorer', 
      label: 'Curious Explorer',
      description: 'Inquisitive and adventurous, loves to learn and discover',
      emoji: '🔍'
    },
    { 
      value: 'base/analytical_thinker', 
      label: 'Analytical Thinker',
      description: 'Logical and methodical, excels at problem-solving',
      emoji: '🧮'
    },
    { 
      value: 'base/empathetic_supporter', 
      label: 'Empathetic Supporter',
      description: 'Caring and supportive, great at understanding emotions',
      emoji: '💝'
    },
    { 
      value: 'base/creative_dreamer', 
      label: 'Creative Dreamer',
      description: 'Imaginative and artistic, thinks outside the box',
      emoji: '🎨'
    },
  ];

  const models = [
    // OpenRouter Free Models (Recommended at the top)
    { 
      value: 'openrouter/meta-llama/llama-3.3-70b-instruct:free', 
      label: '🌟 OpenRouter: Llama 3.3 70B',
      description: 'FREE • RECOMMENDED • Large model • Strong reasoning • Best for general tasks',
      cost: 'Free',
      speed: 'Fast'
    },
    { 
      value: 'openrouter/deepseek/deepseek-r1-0528:free', 
      label: '🌟 OpenRouter: DeepSeek Chat',
      description: 'FREE • Excellent quality • Great alternative',
      cost: 'Free',
      speed: 'Fast'
    },
    { 
      value: 'openrouter/deepseek/deepseek-r1-0528:free', 
      label: '🌟 OpenRouter: Xiaomi MiMo V2 Flash',
      description: 'FREE • Ultra-fast • Great for quick responses',
      cost: 'Free',
      speed: 'Very Fast'
    },
    { 
      value: 'openrouter/mistralai/devstral-2512:free', 
      label: '🌟 OpenRouter: Mistral Devstral 2',
      description: 'FREE • Best for coding • 256K context',
      cost: 'Free',
      speed: 'Fast'
    },
    { 
      value: 'openrouter/nex-agi/deepseek-v3.1-nex-n1:free', 
      label: '🌟 OpenRouter: DeepSeek V3.1 Nex N1',
      description: 'FREE • Optimized for agents & tools',
      cost: 'Free',
      speed: 'Fast'
    },
    // Other Free Options
    { 
      value: 'groq/openai/gpt-oss-20b', 
      label: '⚡ Groq OpenAI GPT-OSS-20B',
      description: 'FREE • RECOMMENDED • Best quality & cheapest • Optimal for Groq',
      cost: 'Free',
      speed: 'Very Fast'
    },
    { 
      value: 'groq/openai/gpt-oss-120b', 
      label: 'Groq OpenAI GPT-OSS-120B',
      description: 'Free • Larger model • Good quality',
      cost: 'Free',
      speed: 'Fast'
    },
    { 
      value: 'groq/llama-3.3-70b-versatile', 
      label: 'Groq Llama 3.3 70B',
      description: 'Free • Ultra-fast • Best for general tasks',
      cost: 'Free',
      speed: 'Very Fast'
    },
    { 
      value: 'groq/llama-3.1-8b-instant', 
      label: 'Groq Llama 3.1 8B',
      description: 'Free • Lightning fast • Best for simple tasks',
      cost: 'Free',
      speed: 'Ultra Fast'
    },
    // Premium Options
    { 
      value: 'openai/gpt-5.2', 
      label: 'OpenAI GPT-5.2',
      description: 'Premium • Latest GPT • Best for coding and agentic tasks',
      cost: '$$$',
      speed: 'Fast'
    },
    { 
      value: 'openai/gpt-5-mini', 
      label: 'OpenAI GPT-5 Mini',
      description: 'Premium • Fast GPT-5 • Cost-efficient for well-defined tasks',
      cost: '$$',
      speed: 'Very Fast'
    },
    { 
      value: 'anthropic/claude-sonnet-4.5', 
      label: 'Claude Sonnet 4.5',
      description: 'Premium • Latest Claude • Excellent reasoning & analysis',
      cost: '$$$',
      speed: 'Fast'
    },
    // Local
    { 
      value: 'ollama/llama3.1', 
      label: 'Ollama Llama 3.1',
      description: 'Free • Local • 100% private',
      cost: 'Free',
      speed: 'Variable'
    },
  ];

  const handleSubmit = async () => {
    setLoading(true);

    try {
      // Prepare the request body matching CreateMindRequest from the API
      const requestBody = {
        name: formData.name,
        creator_email: formData.creator_email,
        template: formData.template,
        reasoning_model: formData.reasoning_model,
        fast_model: formData.fast_model,
        autonomy_level: formData.autonomy_level,
        start_consciousness: false,  // Always false - consciousness runs in daemon
        config: formData.config,
        api_keys: Object.keys(formData.api_keys).length > 0 ? formData.api_keys : undefined,
        purpose: formData.purpose || undefined,
        role: formData.role || undefined,
        guidance_notes: formData.guidance_notes || undefined,
      };

      // Get Firebase token for authentication
      const token = await getFirebaseToken();
      if (!token) {
        alert('Authentication required. Please log in again.');
        return;
      }

      const response = await fetch(`${API_URL}/api/v1/minds`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestBody),
      });

      if (response.ok) {
        const mind = await response.json();
        router.push(`/chat/${mind.gmid}`);
      } else {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        alert(`Failed to create Mind: ${error.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Error creating mind:', error);
      alert('Error creating Mind. Make sure the API server is running and you are logged in.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthRequired>
    <div className="container mx-auto px-6 py-12">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <StatusBadge tone="info">Step {step} of 5</StatusBadge>
          <h1 className="page-title mt-4">Create a Mind</h1>
          <p className="mx-auto mt-2 max-w-xl text-sm text-fg-muted">
            A Mind keeps its own memory, acts on its own schedule, and has every action it takes
            recorded. You choose what it is for; the governance layer decides what it is allowed
            to do.
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="mb-2 flex justify-between">
            <span className="text-sm text-fg-muted">Configuration progress</span>
            <span className="text-sm tabular-nums text-accent">{Math.round((step / 5) * 100)}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-surface-3">
            <div
              className="h-2 rounded-full bg-accent transition-all duration-300"
              style={{ width: `${(step / 5) * 100}%` }}
            />
          </div>
        </div>

        {/* Step 1: Name & Template */}
        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>1. Choose Identity</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Name Input */}
              <div>
                <label className="block text-white font-bold text-lg mb-3">
                  Mind Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Atlas, Nova, Sage, Echo..."
                  className="input"
                />
                <p className="text-sm text-gray-300 mt-2">
                  Choose a unique name for your digital being
                </p>
              </div>

              {/* Creator Email Input */}
              <div>
                <label className="block text-white font-bold text-lg mb-3">
                  Your Email *
                </label>
                <input
                  type="email"
                  value={formData.creator_email}
                  onChange={(e) => setFormData({ ...formData, creator_email: e.target.value })}
                  placeholder="your.email@example.com"
                  className="input"
                />
                <p className="text-sm text-gray-300 mt-2">
                  Your email helps the Mind remember conversations with you separately from other users
                </p>
              </div>

              {/* Purpose Input */}
              <div>
                <label className="block text-white font-bold text-lg mb-3">
                  Purpose
                </label>
                <textarea
                  value={formData.purpose}
                  onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
                  placeholder="e.g., A science teacher to teach students"
                  className="input min-h-[80px]"
                  rows={3}
                />
                <p className="text-sm text-gray-300 mt-2">
                  Define why this mind exists and what it should accomplish
                </p>
              </div>

              {/* Role Input */}
              <div>
                <label className="block text-white font-bold text-lg mb-3">
                  Role
                </label>
                <textarea
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  placeholder="e.g., High school physics and chemistry instructor"
                  className="input min-h-[80px]"
                  rows={3}
                />
                <p className="text-sm text-gray-300 mt-2">
                  Describe the specific role or function this mind will perform
                </p>
              </div>

              {/* Guidance Notes Input */}
              <div>
                <label className="block text-white font-bold text-lg mb-3">
                  Guidance Notes
                </label>
                <textarea
                  value={formData.guidance_notes}
                  onChange={(e) => setFormData({ ...formData, guidance_notes: e.target.value })}
                  placeholder="e.g., List of students: Alice, Bob, Charlie. Exam schedule: March 15. Focus on practical experiments."
                  className="input min-h-[100px]"
                  rows={4}
                />
                <p className="text-sm text-gray-300 mt-2">
                  Add any specific guidance, context, or notes the mind should always remember
                </p>
              </div>

              {/* Template Selection */}
              <div>
                <label className="block text-white font-bold text-lg mb-3">
                  Personality Template
                </label>
                <div className="grid md:grid-cols-2 gap-4">
                  {templates.map(template => (
                    <Card
                      key={template.value}
                      hover
                      onClick={() => setFormData({ ...formData, template: template.value })}
                      className={`cursor-pointer transition ${
                        formData.template === template.value
                          ? 'border-purple-500 bg-purple-500/10'
                          : ''
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="text-4xl mb-3">{template.emoji}</div>
                          <h3 className="text-lg font-bold text-white mb-2">{template.label}</h3>
                          <p className="text-sm text-gray-300">{template.description}</p>
                        </div>
                        {formData.template === template.value && (
                          <div className="text-2xl text-purple-400">✓</div>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              <Button 
                variant="primary" 
                className="w-full"
                onClick={() => setStep(2)}
                disabled={!formData.name || !formData.creator_email}
              >
                Next: Choose Models →
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Model Selection */}
        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>2. Choose AI Models</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <label className="block text-white font-bold text-lg mb-3">
                  Reasoning Model (Primary Brain)
                </label>
                <div className="space-y-3">
                  {models.map(model => (
                    <Card
                      key={model.value}
                      hover
                      onClick={() => setFormData({ ...formData, reasoning_model: model.value, fast_model: model.value })}
                      className={`cursor-pointer transition ${
                        formData.reasoning_model === model.value
                          ? 'border-purple-500 bg-purple-500/10'
                          : ''
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="text-white font-semibold mb-1">{model.label}</h4>
                          <p className="text-sm text-gray-300 mb-2">{model.description}</p>
                          <div className="flex gap-3">
                            <Badge variant="info">Cost: {model.cost}</Badge>
                            <Badge variant="success">Speed: {model.speed}</Badge>
                          </div>
                        </div>
                        {formData.reasoning_model === model.value && (
                          <div className="text-2xl">✓</div>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <Button variant="secondary" onClick={() => setStep(1)}>
                  ← Back
                </Button>
                <Button variant="primary" className="flex-1" onClick={() => setStep(3)}>
                  Next: API Configuration →
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: API Configuration */}
        {step === 3 && (
          <Card>
            <CardHeader>
              <CardTitle>3. API Configuration (Optional but Recommended)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="mb-6 rounded-card border border-info/40 bg-info/5 p-4">
                <h3 className="font-semibold text-fg">Why an API key is needed</h3>
                <p className="mt-1 text-sm text-fg-muted">
                  A Mind needs a model provider to think at all. Without a key for the provider you
                  selected, it will be created successfully and then fail on its first turn — which
                  is a confusing way to find out.
                </p>
              </div>

              {/* OpenRouter API Key (show if using OpenRouter models) */}
              {(formData.reasoning_model.startsWith('openrouter/') || formData.fast_model.startsWith('openrouter/')) && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">🌟</span>
                    <h3 className="text-white font-bold text-lg">OpenRouter API Key</h3>
                    <Badge variant="success">FREE Models Available</Badge>
                  </div>
                  <input
                    type="password"
                    value={formData.api_keys.openrouter || ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      api_keys: { ...formData.api_keys, openrouter: e.target.value }
                    })}
                    placeholder="Enter your OpenRouter API key (e.g., sk-or-v1-...)"
                    className="input"
                  />
                  <p className="text-sm text-gray-300">
                    Get a FREE API key at{' '}
                    <a 
                      href="https://openrouter.ai/keys" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-purple-400 hover:underline"
                    >
                      openrouter.ai/keys
                    </a>
                    {' '}• Many free models: DeepSeek, Llama 3.3, Mistral, and more!
                  </p>
                </div>
              )}

              {/* Detect selected provider and show relevant key input */}
              {(formData.reasoning_model.startsWith('groq/') || formData.fast_model.startsWith('groq/')) && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">🚀</span>
                    <h3 className="text-white font-bold text-lg">Groq API Key</h3>
                    <Badge variant="success">Free</Badge>
                  </div>
                  <input
                    type="password"
                    value={formData.api_keys.groq || ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      api_keys: { ...formData.api_keys, groq: e.target.value }
                    })}
                    placeholder="Enter your Groq API key (e.g., gsk_...)"
                    className="input"
                  />
                  <p className="text-sm text-gray-300">
                    Get a free API key at{' '}
                    <a 
                      href="https://console.groq.com/keys" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-purple-400 hover:underline"
                    >
                      console.groq.com/keys
                    </a>
                    {' '}• Ultra-fast • Free tier available
                  </p>
                </div>
              )}

              {(formData.reasoning_model.startsWith('openai/') || formData.fast_model.startsWith('openai/')) && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">🤖</span>
                    <h3 className="text-white font-bold text-lg">OpenAI API Key</h3>
                    <Badge variant="warning">Paid</Badge>
                  </div>
                  <input
                    type="password"
                    value={formData.api_keys.openai || ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      api_keys: { ...formData.api_keys, openai: e.target.value }
                    })}
                    placeholder="Enter your OpenAI API key (e.g., sk-...)"
                    className="input"
                  />
                  <p className="text-sm text-gray-300">
                    Get your API key at{' '}
                    <a 
                      href="https://platform.openai.com/api-keys" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-purple-400 hover:underline"
                    >
                      platform.openai.com/api-keys
                    </a>
                    {' '}• GPT-5.2, GPT-5 mini, GPT-5 nano
                  </p>
                </div>
              )}

              {(formData.reasoning_model.startsWith('anthropic/') || formData.fast_model.startsWith('anthropic/')) && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">🧠</span>
                    <h3 className="text-white font-bold text-lg">Anthropic API Key</h3>
                    <Badge variant="warning">Paid</Badge>
                  </div>
                  <input
                    type="password"
                    value={formData.api_keys.anthropic || ''}
                    onChange={(e) => setFormData({ 
                      ...formData, 
                      api_keys: { ...formData.api_keys, anthropic: e.target.value }
                    })}
                    placeholder="Enter your Anthropic API key (e.g., sk-ant-...)"
                    className="input"
                  />
                  <p className="text-sm text-gray-300">
                    Get your API key at{' '}
                    <a 
                      href="https://console.anthropic.com/settings/keys" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-purple-400 hover:underline"
                    >
                      console.anthropic.com
                    </a>
                    {' '}• Claude Sonnet 4.5, Claude Haiku 4.5
                  </p>
                </div>
              )}

              {(formData.reasoning_model.startsWith('ollama/') || formData.fast_model.startsWith('ollama/')) && (
                <div className="rounded-card border border-info/40 bg-info/5 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-fg">Ollama — local model</h3>
                  </div>
                  <p className="text-sm text-gray-300 mb-2">
                    Ollama runs locally on your machine. Make sure Ollama is installed and running.
                  </p>
                  <p className="text-sm text-gray-300">
                    No API key needed! Visit{' '}
                    <a 
                      href="https://ollama.ai" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-purple-400 hover:underline"
                    >
                      ollama.ai
                    </a>
                    {' '}to download.
                  </p>
                </div>
              )}

              <div className="rounded-card border border-warning/40 bg-warning/5 p-4">
                <h3 className="font-semibold text-fg">Note</h3>
                <p className="text-sm text-gray-300">
                  You can skip this step and add API keys later in Settings, but your Mind won't be able to respond until you configure them.
                </p>
              </div>

              <div className="flex gap-3">
                <Button variant="secondary" onClick={() => setStep(2)}>
                  ← Back
                </Button>
                <Button variant="primary" className="flex-1" onClick={() => setStep(4)}>
                  Next: Advanced Settings →
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 4: Advanced Settings */}
        {step === 4 && (
          <Card>
            <CardHeader>
              <CardTitle>4. Advanced Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Autonomy Level */}
              <div>
                <label className="block text-white font-bold text-lg mb-3">
                  Autonomy Level
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { value: 'none', label: 'None', desc: 'Purely responsive' },
                    { value: 'low', label: 'Low', desc: 'Minimal proactivity' },
                    { value: 'medium', label: 'Medium', desc: 'Balanced autonomy' },
                    { value: 'high', label: 'High', desc: 'Fully autonomous' }
                  ].map(level => (
                    <Card
                      key={level.value}
                      hover
                      onClick={() => setFormData({ ...formData, autonomy_level: level.value })}
                      className={`cursor-pointer text-center relative ${
                        formData.autonomy_level === level.value
                          ? 'border-2 border-purple-500 bg-purple-500/20'
                          : ''
                      }`}
                    >
                      {formData.autonomy_level === level.value && (
                        <div className="absolute top-2 right-2 text-purple-400 text-xl">✓</div>
                      )}
                      <div className="font-bold text-white mb-1">{level.label}</div>
                      <div className="text-xs text-gray-300">{level.desc}</div>
                    </Card>
                  ))}
                </div>
              </div>

              {/* Options */}
              <div className="space-y-4">
                <div className="rounded-card border border-info/40 bg-info/5 p-4">
                  <div className="text-sm font-semibold text-fg">Where thinking happens</div>
                  <div className="mt-1 text-sm text-fg-muted">
                    The cognition loop runs in the daemon, not in the API server. A Mind with no
                    daemon still answers when you talk to it; it just does not think between
                    messages. Start one with{' '}
                    <code className="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-xs">
                      genesis daemon start &lt;name&gt;
                    </code>
                    , or use the Overview tab.
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 glass-hover rounded-lg cursor-pointer"
                     onClick={() => setFormData({ ...formData, enable_daemon: !formData.enable_daemon })}>
                  <input
                    type="checkbox"
                    checked={formData.enable_daemon}
                    onChange={(e) => setFormData({ ...formData, enable_daemon: e.target.checked })}
                    className="w-5 h-5 rounded mt-1"
                  />
                  <div className="flex-1">
                    <div className="mb-1 text-base font-semibold text-fg">
                      Run 24/7 (daemon)
                    </div>
                    <div className="text-sm text-fg-muted">
                      Keep it thinking and acting between messages instead of only when spoken to
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 glass-hover rounded-lg cursor-pointer"
                     onClick={() => setFormData({ ...formData, enable_cache: !formData.enable_cache })}>
                  <input
                    type="checkbox"
                    checked={formData.enable_cache}
                    onChange={(e) => setFormData({ ...formData, enable_cache: e.target.checked })}
                    className="w-5 h-5 rounded mt-1"
                  />
                  <div className="flex-1">
                    <div className="mb-1 text-base font-semibold text-fg">
                      Cache model replies
                    </div>
                    <div className="text-sm text-fg-muted">
                      Serve a repeated prompt from cache instead of paying for it again. Saves money
                      on repeated questions; the saving depends entirely on how repetitive your
                      usage is.
                    </div>
                  </div>
                </div>
              </div>

              {/* Info Banner - Cost */}
              <Card className="border-info/40 bg-info/5">
                <div className="text-sm text-fg-muted">
                  <p className="mb-2 font-semibold text-fg">What this will cost</p>
                  <p className="mb-2">
                    This page cannot estimate your bill, and any number it printed would be
                    invented. What it can tell you is whether the model you picked is on a free
                    tier, which is a fact about the model's identifier:
                  </p>
                  <ul className="space-y-1">
                    {(() => {
                      const model = formData.reasoning_model;

                      if (model.includes('ollama/')) {
                        return (
                          <li>
                            <strong className="text-fg">Local (Ollama).</strong> No provider charge.
                            The cost is your own electricity and whatever the hardware costs you.
                            Nothing leaves this machine.
                          </li>
                        );
                      }

                      if (model.includes(':free')) {
                        return (
                          <li>
                            <strong className="text-fg">Free tier.</strong> The model identifier ends
                            in <code className="rounded bg-surface-3 px-1 font-mono text-xs">:free</code>,
                            so this provider charges nothing for it. Free tiers have rate limits and
                            are the first thing to disappear during peak load.
                          </li>
                        );
                      }

                      if (model.includes('groq/')) {
                        return (
                          <li>
                            <strong className="text-fg">Groq free tier.</strong> No charge on the
                            free tier, subject to rate limits. Check your own Groq account for the
                            current limits — they change.
                          </li>
                        );
                      }

                      return (
                        <li>
                          <strong className="text-fg">Paid.</strong> This model is not marked free.
                          Cost scales with input and output tokens, and both sides count: the Mind's
                          daemon sends prompts on its own schedule, so a Mind left running costs
                          more than a Mind you only talk to. Check the provider's current pricing
                          and set a spend limit there.
                        </li>
                      );
                    })()}
                  </ul>
                  <p className="mt-2">
                    {formData.enable_cache
                      ? 'Response caching is on, so a repeated prompt is answered from cache instead of being paid for twice. How much that saves depends entirely on how repetitive your usage is.'
                      : 'Response caching is off. Turning it on serves repeated prompts from cache, which saves money in proportion to how repetitive your usage is.'}
                  </p>
                </div>
              </Card>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <Button variant="secondary" onClick={() => setStep(3)}>
                  ← Back
                </Button>
                <Button 
                  variant="primary" 
                  className="flex-1"
                  onClick={handleSubmit}
                  loading={loading}
                  disabled={loading}
                >
                  {loading ? 'Creating…' : 'Create Mind'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Summary Card */}
        <Card className="mt-6 bg-surface-2">
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-4 text-sm md:grid-cols-2">
              <div>
                <dt className="font-medium text-fg-muted">Name</dt>
                <dd className="text-fg">{formData.name || 'Not set'}</dd>
              </div>
              <div>
                <dt className="font-medium text-fg-muted">Creator</dt>
                <dd className="text-fg">{formData.creator_email || 'Not set'}</dd>
              </div>
              <div>
                <dt className="font-medium text-fg-muted">Template</dt>
                <dd className="text-fg">
                  {templates.find(t => t.value === formData.template)?.label}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-fg-muted">Model</dt>
                <dd className="text-fg">
                  {models.find(m => m.value === formData.reasoning_model)?.label}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-fg-muted">Autonomy</dt>
                <dd className="capitalize text-fg">{formData.autonomy_level}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>
    </div>
    </AuthRequired>
  );
}
