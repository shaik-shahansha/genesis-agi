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
  const [purpose, setPurpose] = useState(mind.purpose || '');
  const [role, setRole] = useState(mind.role || '');
  const [guidanceNotes, setGuidanceNotes] = useState(mind.guidance_notes || '');
  
  // LLM Configuration
  const [provider, setProvider] = useState(mind.llm_provider || 'groq');
  const [model, setModel] = useState(mind.llm_model || 'mixtral-8x7b-32768');
  const [apiKey, setApiKey] = useState('');
  const [useOllama, setUseOllama] = useState(false);
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [maxTokens, setMaxTokens] = useState(mind.max_tokens || 8000);
  
  // Autonomy Settings
  const [autonomyLevel, setAutonomyLevel] = useState(mind.autonomy_level || 5);
  const [consciousnessActive, setConsciousnessActive] = useState(mind.consciousness_active || true);
  const [dreamingEnabled, setDreamingEnabled] = useState(mind.dreaming_enabled || true);
  
  // Currency
  const [currency, setCurrency] = useState(mind.gens || 100);

  // Access
  const [allowedUsers, setAllowedUsers] = useState<string[]>([]);
  const [isPublic, setIsPublic] = useState<boolean>(mind.is_public || false);

  useEffect(() => {
    // Reset form when mind changes
    setName(mind.name || '');
    setPurpose(mind.purpose || '');
    setRole(mind.role || '');
    setGuidanceNotes(mind.guidance_notes || '');
    setProvider(mind.llm_provider || 'groq');
    setModel(mind.llm_model || 'mixtral-8x7b-32768');
    setMaxTokens(mind.max_tokens || 8000);
    setAutonomyLevel(mind.autonomy_level || 5);
    setConsciousnessActive(mind.consciousness_active !== false);
    setDreamingEnabled(mind.dreaming_enabled !== false);
    setCurrency(mind.gens || 100);

    // Fetch access info
    (async () => {
      try {
        const res = await api.getMindAccess(mind.gmid);
        setAllowedUsers(res.allowed_users || []);
        setIsPublic(!!res.is_public);
      } catch (e) {
        setAllowedUsers([]);
      }
    })();
  }, [mind]);

  const handleSave = async () => {
    setSaving(true);
    setMessage('');

    try {
      await api.updateMindSettings(mind.gmid, {
        name,
        purpose,
        role,
        guidance_notes: guidanceNotes,
        llm_provider: provider,
        llm_model: model,
        api_key: apiKey || undefined,
        use_ollama: useOllama,
        ollama_url: useOllama ? ollamaUrl : undefined,
        max_tokens: maxTokens,
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
      'meta-llama/llama-3.3-70b-instruct:free',
      'deepseek/deepseek-r1-0528:free',
      'mistralai/devstral-2512:free',
      'nex-agi/deepseek-v3.1-nex-n1:free',
    ],
    groq: [
      'openai/gpt-oss-20b',
      'openai/gpt-oss-120b',
      'llama-3.3-70b-versatile',
      'llama-3.1-8b-instant',
    ],
    openai: [
      'gpt-5.2',
      'gpt-5-mini',
    ],
    anthropic: [
      'claude-sonnet-4.5',
    ],
    ollama: [
      'llama3.1',
      'llama2',
      'mistral',
      'codellama',
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
              Purpose <span className="text-gray-500 font-normal">(Why does this Mind exist?)</span>
            </label>
            <textarea
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              className="input w-full"
              rows={2}
              placeholder="e.g., To teach science to Grade 10 students"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Role <span className="text-gray-500 font-normal">(What is this Mind's specific role?)</span>
            </label>
            <textarea
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="input w-full"
              rows={2}
              placeholder="e.g., Science Teacher for Grade 10, Section A"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Guidance Notes <span className="text-gray-500 font-normal">(Additional context and information)</span>
            </label>
            <textarea
              value={guidanceNotes}
              onChange={(e) => setGuidanceNotes(e.target.value)}
              className="input w-full"
              rows={5}
              placeholder="e.g., Student list: Alice, Bob, Charlie&#10;Next exam: Physics Chapter 5 on Feb 15&#10;Focus areas: Thermodynamics, Kinematics"
            />
            <p className="text-xs text-gray-500 mt-1">
              This information will be included in every prompt to help the Mind maintain context.
            </p>
          </div>
        </div>
      </div>

      {/* Access Control */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">🔒 Access</h2>
        <p className="text-sm text-gray-600 mb-4">Control who can view and chat with this Mind. Only the creator can add users or make the Mind public.</p>

        <div className="flex items-center gap-4 mb-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={async (e) => {
                const val = e.target.checked;
                setIsPublic(val);
                try {
                  setSaving(true);
                  await api.setMindPublic(mind.gmid, val);
                  onRefresh();
                } catch (err: any) {
                  setMessage(`Error: ${err.message}`);
                } finally {
                  setSaving(false);
                }
              }}
              className="w-5 h-5"
            />
            <div>
              <div className="font-medium text-gray-900">Public</div>
              <div className="text-sm text-gray-600">If public, any authenticated user may see this Mind</div>
            </div>
          </label>
        </div>

        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700 mb-2">Invite User by Email</label>
          <div className="flex gap-2">
            <input
              type="email"
              placeholder="user@example.com"
              className="input flex-1"
              onKeyDown={async (e) => {
                if (e.key === 'Enter') {
                  const val = (e.target as HTMLInputElement).value.trim();
                  if (!val) return;
                  setSaving(true);
                  try {
                    await api.addMindUser(mind.gmid, val);
                    setMessage('User added');
                    onRefresh();
                    (e.target as HTMLInputElement).value = '';
                  } catch (err: any) {
                    setMessage(`Error: ${err.message}`);
                  } finally {
                    setSaving(false);
                  }
                }
              }}
            />
            <button
              className="btn"
              onClick={async () => {
                const input = (document.querySelector('input[type="email"]') as HTMLInputElement);
                const val = input?.value?.trim();
                if (!val) return;
                setSaving(true);
                try {
                  await api.addMindUser(mind.gmid, val);
                  setMessage('User added');
                  onRefresh();
                  input.value = '';
                } catch (err: any) {
                  setMessage(`Error: ${err.message}`);
                } finally {
                  setSaving(false);
                }
              }}
            >Add</button>
          </div>
        </div>

        {/* Allowed users list fetched from /access */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Allowed Users</label>
          <div className="bg-gray-50 border border-gray-100 rounded p-3">
            {(allowedUsers && allowedUsers.length > 0) ? (
              allowedUsers.map((u: string) => (
                <div key={u} className="flex items-center justify-between py-1">
                  <div className="text-sm">{u}</div>
                  <button
                    className="text-sm text-red-600"
                    onClick={async () => {
                      setSaving(true);
                      try {
                        await api.removeMindUser(mind.gmid, u);
                        setMessage('User removed');
                        onRefresh();
                      } catch (err: any) {
                        setMessage(`Error: ${err.message}`);
                      } finally {
                        setSaving(false);
                      }
                    }}
                  >Remove</button>
                </div>
              ))
            ) : (
              <div className="text-sm text-gray-500">No invited users</div>
            )}
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
                {['groq', 'openrouter'].includes(provider) && <span className="text-green-600 text-xs ml-1">(Optional - Free tier available)</span>}
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="input w-full"
                placeholder={
                  ['groq', 'openrouter'].includes(provider) 
                    ? "Optional - Leave blank for free usage" 
                    : "Required - Enter your API key"
                }
              />
              <p className="text-xs text-gray-500 mt-1">
                {provider === 'openrouter' && '🌟 OpenRouter has many FREE models available!'}
                {provider === 'groq' && '⚡ Groq is FREE - API key optional for higher limits'}
                {['openai', 'anthropic'].includes(provider) && '⚠️ Required - Get your key from the provider'}
              </p>
            </div>
          </div>
        )}

        {/* Max Tokens Configuration */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Max Tokens
          </label>
          <input
            type="number"
            min="100"
            max="100000"
            step="100"
            value={maxTokens}
            onChange={(e) => setMaxTokens(parseInt(e.target.value) || 8000)}
            className="input w-full"
            placeholder="8000"
          />
          <p className="text-xs text-gray-500 mt-1">
            Maximum number of tokens for AI response generation (default: 8000)
          </p>
        </div>
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
