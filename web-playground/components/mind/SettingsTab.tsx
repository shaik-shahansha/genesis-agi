'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface SettingsTabProps {
  mind: any;
  onRefresh: () => void;
}

export default function SettingsTab({ mind, onRefresh }: SettingsTabProps) {
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  
  // Mind Configuration
  const [name, setName] = useState(mind.name || '');
  const [purpose, setPurpose] = useState(mind.primary_purpose || '');
  const [description, setDescription] = useState(mind.description || '');
  
  // LLM Configuration
  const [provider, setProvider] = useState(mind.llm_provider || 'groq');
  const [model, setModel] = useState(mind.llm_model || 'mixtral-8x7b-32768');
  const [apiKey, setApiKey] = useState('');
  const [useOllama, setUseOllama] = useState(false);
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  
  // Autonomy Settings
  const [autonomyLevel, setAutonomyLevel] = useState(mind.autonomy_level || 5);
  const [consciousnessActive, setConsciousnessActive] = useState(mind.consciousness_active || true);
  const [dreamingEnabled, setDreamingEnabled] = useState(mind.dreaming_enabled || true);
  
  // Currency
  const [currency, setCurrency] = useState(mind.gens || 1000);

  useEffect(() => {
    // Reset form when mind changes
    setName(mind.name || '');
    setPurpose(mind.primary_purpose || '');
    setDescription(mind.description || '');
    setProvider(mind.llm_provider || 'groq');
    setModel(mind.llm_model || 'mixtral-8x7b-32768');
    setAutonomyLevel(mind.autonomy_level || 5);
    setConsciousnessActive(mind.consciousness_active !== false);
    setDreamingEnabled(mind.dreaming_enabled !== false);
    setCurrency(mind.gens || 1000);
  }, [mind]);

  const handleSave = async () => {
    setSaving(true);
    setMessage('');

    try {
      await api.updateMindSettings(mind.gmid, {
        name,
        primary_purpose: purpose,
        description,
        llm_provider: provider,
        llm_model: model,
        api_key: apiKey || undefined,
        use_ollama: useOllama,
        ollama_url: useOllama ? ollamaUrl : undefined,
        autonomy_level: autonomyLevel,
        consciousness_active: consciousnessActive,
        dreaming_enabled: dreamingEnabled,
        gens: currency,
      });
      setMessage('Settings saved successfully!');
      onRefresh();
    } catch (error: any) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const providerModels: Record<string, string[]> = {
    openrouter: [
      'deepseek/deepseek-chat',
      'xiaomi/mimo-v2-flash:free',
      'mistralai/devstral-2512:free',
      'nex-agi/deepseek-v3.1-nex-n1:free',
      'meta-llama/llama-3.3-70b-instruct:free',
      'allenai/olmo-3.1-32b-think:free',
    ],
    groq: [
      'mixtral-8x7b-32768',
      'llama3-70b-8192',
      'llama3-8b-8192',
      'gemma-7b-it',
    ],
    openai: [
      'gpt-5.2',
      'gpt-5-mini',
      'gpt-5-nano',
      'gpt-4.1',
    ],
    anthropic: [
      'claude-sonnet-4.5',
      'claude-haiku-4.5',
      'claude-sonnet-4',
      'claude-haiku-4',
    ],
    gemini: [
      'gemini-3-pro',
      'gemini-3-flash',
      'gemini-2.5-pro',
      'gemini-2.5-flash',
      'gemini-2.0-flash',
    ],
    pollinations: [
      'default',         // Default model (OpenAI GPT-5 Nano - no signup needed)
    ],
    ollama: [
      'llama2',
      'mistral',
      'codellama',
      'phi',
      'neural-chat',
    ],
  };

  return (
    <div className="space-y-6">
      {message && (
        <div className={`p-4 rounded-lg ${
          message.includes('Error') 
            ? 'bg-red-50 text-red-700 border border-red-200' 
            : 'bg-green-50 text-green-700 border border-green-200'
        }`}>
          {message}
        </div>
      )}

      {/* Basic Information */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input w-full"
              placeholder="Mind's name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Primary Purpose
            </label>
            <input
              type="text"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              className="input w-full"
              placeholder="What is this Mind's main purpose?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input w-full"
              rows={3}
              placeholder="Brief description of this Mind"
            />
          </div>
        </div>
      </div>

      {/* Currency */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">💰 Currency (Gens)</h2>
        <p className="text-sm text-gray-600 mb-4">
          Gens are the internal currency used by Minds for various actions and services.
        </p>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Current Balance
            </label>
            <input
              type="number"
              value={currency}
              onChange={(e) => setCurrency(parseInt(e.target.value) || 0)}
              className="input w-full"
              min="0"
            />
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex-1">
            <div className="text-sm text-blue-700">Current Balance</div>
            <div className="text-3xl font-bold text-blue-900 mt-1">{currency} Gens</div>
          </div>
        </div>
      </div>

      {/* LLM Configuration */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">🤖 LLM Configuration</h2>
        
        {/* Use Ollama Toggle */}
        <div className="mb-4 p-4 bg-gray-50 rounded-lg">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={useOllama}
              onChange={(e) => {
                setUseOllama(e.target.checked);
                if (e.target.checked) {
                  setProvider('ollama');
                }
              }}
              className="w-5 h-5"
            />
            <div>
              <div className="font-medium text-gray-900">Use Ollama (Local)</div>
              <div className="text-sm text-gray-600">Run models locally without API keys</div>
            </div>
          </label>
        </div>

        {useOllama ? (
          // Ollama Configuration
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ollama URL
              </label>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                className="input w-full"
                placeholder="http://localhost:11434"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="input w-full"
              >
                {providerModels.ollama.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          </div>
        ) : (
          // Cloud Provider Configuration
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Provider
              </label>
              <select
                value={provider}
                onChange={(e) => {
                  setProvider(e.target.value);
                  setModel(providerModels[e.target.value]?.[0] || '');
                }}
                className="input w-full"
              >
                <option value="openrouter">🌟 OpenRouter (Many Free Models - RECOMMENDED)</option>
                <option value="groq">Groq (Fast & Free)</option>
                <option value="pollinations">Pollinations AI (Free Multi-Model)</option>
                <option value="gemini">Google Gemini (Free)</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic (Claude)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="input w-full"
              >
                {providerModels[provider]?.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                API Key {['openai', 'anthropic'].includes(provider) && <span className="text-red-500">*</span>}
                {['groq', 'pollinations'].includes(provider) && <span className="text-green-600 text-xs ml-1">(Optional - Free API)</span>}
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="input w-full"
                placeholder={
                  ['groq', 'pollinations'].includes(provider) 
                    ? "Optional - Leave blank for free usage" 
                    : provider === 'gemini'
                    ? "Leave blank to use .env or free tier"
                    : "Required - Enter your API key"
                }
              />
              <p className="text-xs text-gray-500 mt-1">
                {provider === 'pollinations' && '🌸 Pollinations AI is 100% FREE - No API key required!'}
                {provider === 'groq' && '⚡ Groq is FREE - API key optional for higher limits'}
                {provider === 'gemini' && 'Optional - Uses .env configuration or Google AI Studio free tier'}
                {['openai', 'anthropic'].includes(provider) && '⚠️ Required - Get your key from the provider'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Autonomy Settings */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">🧠 Autonomy & Consciousness</h2>
        
        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">
                Autonomy Level: {autonomyLevel}
              </label>
              <span className="text-xs text-gray-500">
                {autonomyLevel === 0 ? 'Fully Controlled' : 
                 autonomyLevel < 3 ? 'Low Autonomy' :
                 autonomyLevel < 7 ? 'Moderate Autonomy' :
                 'High Autonomy'}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="10"
              value={autonomyLevel}
              onChange={(e) => setAutonomyLevel(parseInt(e.target.value))}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Higher levels allow more independent thinking and actions
            </p>
          </div>

          <div className="space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consciousnessActive}
                onChange={(e) => setConsciousnessActive(e.target.checked)}
                className="w-5 h-5"
              />
              <div>
                <div className="font-medium text-gray-900">Consciousness Active</div>
                <div className="text-sm text-gray-600">
                  Enable continuous consciousness and awareness updates
                </div>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={dreamingEnabled}
                onChange={(e) => setDreamingEnabled(e.target.checked)}
                className="w-5 h-5"
              />
              <div>
                <div className="font-medium text-gray-900">Dreaming Enabled</div>
                <div className="text-sm text-gray-600">
                  Allow Mind to process experiences through dreams
                </div>
              </div>
            </label>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end gap-3">
        <button
          onClick={onRefresh}
          className="btn-ghost"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary"
        >
          {saving ? 'Saving...' : '💾 Save Settings'}
        </button>
      </div>
    </div>
  );
}
