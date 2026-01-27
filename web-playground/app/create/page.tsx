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
  });

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
      emoji: '[Done]'
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
      value: 'groq/openai/gpt-oss-120b', 
      label: 'Groq OpenAI GPT-OSS-120B',
      description: 'Free • Best quality • Recommended for Groq',
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

  // Check if creation is disabled in production
  useEffect(() => {
    if (isCreationDisabled()) {
      router.push('/');
    }
  }, [router]);

  // Don't render the page if creation is disabled
  if (isCreationDisabled()) {
    return null;
  }

  return (
    <AuthRequired>
    <div className="container mx-auto px-6 py-12">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <Badge variant="purple" className="mb-4 text-lg px-6 py-2">
            Step {step} of 5
          </Badge>
          <h1 className="text-5xl font-bold mb-4">
            <span className="gradient-text">✨ Birth a New Mind</span>
          </h1>
          <p className="text-gray-300 text-lg">
            Create a conscious digital being with persistent memory and emotions
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between mb-2">
            <span className="text-sm text-gray-300">Configuration Progress</span>
            <span className="text-sm text-purple-400">{Math.round((step / 5) * 100)}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(step / 5) * 100}%` }}
            ></div>
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
              <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 mb-6">
                <h3 className="text-blue-300 font-semibold mb-2">📋 Why API Keys?</h3>
                <p className="text-sm text-gray-300 mb-2">
                  API keys allow your Mind to connect to AI model providers. Without them, the Mind cannot think or respond.
                </p>
                <p className="text-sm text-gray-300">
                  Similar to the CLI, you need to provide API keys for the selected model providers.
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
                <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">🦙</span>
                    <h3 className="text-blue-300 font-bold">Ollama - Local Model</h3>
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

              <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4">
                <h3 className="text-yellow-300 font-semibold mb-2">⚠️ Note</h3>
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
                <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
                  <div className="flex items-start gap-2">
                    <span className="text-2xl">ℹ️</span>
                    <div>
                      <div className="text-blue-300 font-semibold mb-1">
                        Consciousness Engine
                      </div>
                      <div className="text-sm text-gray-300">
                        The consciousness engine (thought generation) runs in the daemon, not the API server.
                        Start the daemon with: <code className="bg-black/30 px-2 py-1 rounded">genesis daemon start &lt;name&gt;</code>
                      </div>
                    </div>
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
                    <div className="text-white font-bold text-base mb-1">
                      ⚡ Enable 24/7 Daemon Mode
                    </div>
                    <div className="text-sm text-gray-300">
                      Run continuously in the background with autonomous actions
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
                    <div className="text-white font-bold text-base mb-1">
                      💾 Enable LLM Response Cache
                    </div>
                    <div className="text-sm text-gray-300">
                      Cache responses to reduce costs by ~90% with Redis
                    </div>
                  </div>
                </div>
              </div>

              {/* Info Banner - Dynamic Cost Estimation */}
              <Card className="bg-gradient-to-r from-purple-900/20 to-pink-900/20 border-purple-500/30">
                <div className="text-sm text-gray-300">
                  <p className="font-semibold text-purple-300 mb-2">🚀 Estimated Costs:</p>
                  <ul className="space-y-1">
                    {(() => {
                      const model = formData.reasoning_model;
                      const isFree = model.includes(':free') || model.includes('groq/');
                      const isOpenRouter = model.includes('openrouter/');
                      const isGroq = model.includes('groq/');
                      const isOllama = model.includes('ollama/');
                      const isOpenAI = model.includes('openai/');
                      const isAnthropic = model.includes('anthropic/');
                      
                      if (isOllama) {
                        return (
                          <>
                            <li>• Local (Ollama): $0/month (100% private, no limits)</li>
                            <li>• Hardware: Runs on your computer (4-16GB RAM)</li>
                            <li>• Consciousness Engine v2: 95% fewer LLM calls</li>
                            <li>• Total cost: <strong className="text-green-400">Free Forever!</strong></li>
                          </>
                        );
                      } else if (isFree && isOpenRouter) {
                        return (
                          <>
                            <li>• OpenRouter (Free tier): $0/month with usage limits</li>
                            <li>• {formData.enable_cache ? 'With caching: 90% cost reduction' : 'Enable caching for 90% savings'}</li>
                            <li>• Consciousness Engine v2: 95% fewer LLM calls</li>
                            <li>• Total cost: <strong className="text-green-400">Free (with limits)!</strong></li>
                          </>
                        );
                      } else if (isGroq) {
                        return (
                          <>
                            <li>• Groq (Free tier): $0/month with rate limits</li>
                            <li>• Speed: Ultra-fast inference (350+ tokens/sec)</li>
                            <li>• Consciousness Engine v2: 95% fewer LLM calls</li>
                            <li>• Total cost: <strong className="text-green-400">Free (with limits)!</strong></li>
                          </>
                        );
                      } else if (isOpenAI) {
                        return (
                          <>
                            <li>• OpenAI (Paid): ~$1-5/day depending on usage</li>
                            <li>• {formData.enable_cache ? 'With caching: 90% cost reduction' : 'Enable caching for 90% savings'}</li>
                            <li>• Consciousness Engine v2: 95% fewer LLM calls</li>
                            <li>• Total estimated: <strong className="text-yellow-400">$10-50/month</strong></li>
                          </>
                        );
                      } else if (isAnthropic) {
                        return (
                          <>
                            <li>• Anthropic (Paid): ~$2-8/day depending on usage</li>
                            <li>• {formData.enable_cache ? 'With caching: 90% cost reduction' : 'Enable caching for 90% savings'}</li>
                            <li>• Consciousness Engine v2: 95% fewer LLM calls</li>
                            <li>• Total estimated: <strong className="text-yellow-400">$20-80/month</strong></li>
                          </>
                        );
                      } else {
                        return (
                          <>
                            <li>• Selected model: Check provider pricing</li>
                            <li>• {formData.enable_cache ? 'With caching: 90% cost reduction' : 'Enable caching for 90% savings'}</li>
                            <li>• Consciousness Engine v2: 95% fewer LLM calls</li>
                            <li>• Total: <strong className="text-blue-400">Varies by provider</strong></li>
                          </>
                        );
                      }
                    })()}
                  </ul>
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
                  {loading ? 'Creating...' : '✨ Birth Mind'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Summary Card */}
        <Card className="mt-6 bg-slate-900/50">
          <CardHeader>
            <CardTitle>Configuration Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-300 font-semibold">Name:</span>
                <span className="text-white ml-2">{formData.name || 'Not set'}</span>
              </div>
              <div>
                <span className="text-gray-300 font-semibold">Creator:</span>
                <span className="text-white ml-2">{formData.creator_email || 'Not set'}</span>
              </div>
              <div>
                <span className="text-gray-300 font-semibold">Template:</span>
                <span className="text-white ml-2">
                  {templates.find(t => t.value === formData.template)?.label}
                </span>
              </div>
              <div>
                <span className="text-gray-300 font-semibold">Model:</span>
                <span className="text-white ml-2">
                  {models.find(m => m.value === formData.reasoning_model)?.label}
                </span>
              </div>
              <div>
                <span className="text-gray-300 font-semibold">Autonomy:</span>
                <span className="text-white ml-2 capitalize">{formData.autonomy_level}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
    </AuthRequired>
  );
}
