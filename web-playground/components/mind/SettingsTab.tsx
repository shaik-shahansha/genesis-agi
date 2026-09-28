'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Section, StatusBadge } from '@/components/governance/primitives';
import { AlertIcon, CheckIcon } from '@/components/shell/icons';

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
        <div
          role="status"
          className={`flex items-start gap-2 rounded-card border p-3 text-sm ${
            message.toLowerCase().includes('error')
              ? 'border-danger/40 bg-danger/5 text-fg'
              : 'border-success/40 bg-success/5 text-fg'
          }`}
        >
          <span className={message.toLowerCase().includes('error') ? 'text-danger' : 'text-success'}>
            {message.toLowerCase().includes('error') ? (
              <AlertIcon className="h-4 w-4" />
            ) : (
              <CheckIcon className="h-4 w-4" />
            )}
          </span>
          <span>{message}</span>
        </div>
      )}

      {/* Basic Information */}
      <Section title="Identity fields" description="These are compiled into every prompt, so they shape how the Mind interprets what you say.">
        <div className="card space-y-4">
          <div>
            <label htmlFor="mind-name" className="label mb-1.5 block">
              Name
            </label>
            <input
              id="mind-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input w-full"
              placeholder="Mind's name"
            />
          </div>

          <div>
            <label htmlFor="mind-purpose" className="label mb-1.5 block">
              Purpose <span className="font-normal text-fg-subtle">— why does this Mind exist?</span>
            </label>
            <textarea
              id="mind-purpose"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              className="input w-full resize-y"
              rows={2}
              placeholder="e.g., To teach science to Grade 10 students"
            />
          </div>

          <div>
            <label htmlFor="mind-role" className="label mb-1.5 block">
              Role <span className="font-normal text-fg-subtle">— what is its specific remit?</span>
            </label>
            <textarea
              id="mind-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="input w-full resize-y"
              rows={2}
              placeholder="e.g., Science Teacher for Grade 10, Section A"
            />
          </div>

          <div>
            <label htmlFor="mind-guidance" className="label mb-1.5 block">
              Guidance notes <span className="font-normal text-fg-subtle">— standing context</span>
            </label>
            <textarea
              id="mind-guidance"
              value={guidanceNotes}
              onChange={(e) => setGuidanceNotes(e.target.value)}
              className="input w-full resize-y font-mono text-xs"
              rows={5}
              placeholder={'e.g., Student list: Alice, Bob, Charlie\nNext exam: Physics Chapter 5 on Feb 15'}
            />
            <p className="mt-1.5 text-xs text-fg-subtle">
              Included in every prompt. Nothing secret belongs here — it is sent to the model
              provider with each turn, and it is visible to anyone who can read this Mind.
            </p>
          </div>
        </div>
      </Section>

      {/* Access Control */}
      <Section
        title="Access"
        description="Who can see and talk to this Mind. Only the creator can change this."
      >
        <div className="card space-y-5">
          <label htmlFor="mind-public" className="flex cursor-pointer items-start gap-3">
            <input
              id="mind-public"
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
                  // Revert, or the checkbox keeps claiming a change that did not happen.
                  setIsPublic(!val);
                  setMessage(`Error: ${err.message}`);
                } finally {
                  setSaving(false);
                }
              }}
              className="mt-0.5 h-4 w-4 rounded border-line accent-[rgb(var(--accent))]"
            />
            <span>
              <span className="block text-sm font-medium text-fg">Public</span>
              <span className="block text-sm text-fg-muted">
                Any authenticated user on this installation can read this Mind and see its
                conversation. It does not let them spend its budget or act on its behalf.
              </span>
            </span>
          </label>

          <div>
            <label htmlFor="mind-invite" className="label mb-1.5 block">
              Invite by email
            </label>
            <div className="flex gap-2">
              <input
                id="mind-invite"
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
                type="button"
                className="btn-secondary"
                onClick={async () => {
                  const input = document.getElementById('mind-invite') as HTMLInputElement | null;
                  const val = input?.value?.trim();
                  if (!val) return;
                  setSaving(true);
                  try {
                    await api.addMindUser(mind.gmid, val);
                    setMessage('User added');
                    onRefresh();
                    if (input) input.value = '';
                  } catch (err: any) {
                    setMessage(`Error: ${err.message}`);
                  } finally {
                    setSaving(false);
                  }
                }}
              >
                Add
              </button>
            </div>
          </div>

          <div>
            <p className="label mb-2">Allowed users</p>
            {allowedUsers && allowedUsers.length > 0 ? (
              <div className="divide-y divide-[rgb(var(--border))] rounded-card border border-line">
                {allowedUsers.map((u: string) => (
                  <div key={u} className="flex items-center justify-between gap-3 px-3 py-2">
                    <span className="min-w-0 truncate text-sm text-fg">{u}</span>
                    <button
                      type="button"
                      className="btn-ghost btn-sm text-danger"
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
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-fg-subtle">
                No users invited. This Mind is visible only to you
                {isPublic ? ' — except that it is marked public, which overrides this list.' : '.'}
              </p>
            )}
          </div>
        </div>
      </Section>

      {/* Currency */}
      <Section
        title="Gens"
        description="The compute budget this Mind may spend on model calls and paid tool calls."
      >
        <div className="card">
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex-1">
              <label htmlFor="mind-gens" className="label mb-1.5 block">
                Balance
              </label>
              <input
                id="mind-gens"
                type="number"
                value={currency}
                onChange={(e) => setCurrency(parseInt(e.target.value) || 0)}
                className="input w-full"
                min="0"
              />
            </div>
            <div className="card-flat flex-1">
              <div className="text-xs text-fg-muted">Current balance</div>
              <div className="mt-1 text-2xl font-semibold tabular-nums text-fg">
                {currency.toLocaleString()} Gens
              </div>
            </div>
          </div>
          <p className="mt-4 text-xs text-fg-subtle">
            Gens are an internal accounting unit, not a token and not transferable between
            installations. Raising the number here grants real spending headroom — it is capped by
            the policy engine's budget rules, not by this field.
          </p>
        </div>
      </Section>


      {/* LLM Configuration */}
      <Section
        title="Model"
        description="Which provider and model this Mind thinks with."
      >
        <div className="card space-y-4">
          <label htmlFor="use-ollama" className="flex cursor-pointer items-start gap-3 rounded-card border border-line bg-surface-2 p-3">
            <input
              id="use-ollama"
              type="checkbox"
              checked={useOllama}
              onChange={(e) => {
                setUseOllama(e.target.checked);
                if (e.target.checked) {
                  setProvider('ollama');
                }
              }}
              className="mt-0.5 h-4 w-4 rounded border-line accent-[rgb(var(--accent))]"
            />
            <span>
              <span className="block text-sm font-medium text-fg">Use Ollama (local)</span>
              <span className="block text-sm text-fg-muted">
                Runs the model on this machine. No API key, and no prompt text leaves the host.
              </span>
            </span>
          </label>

          {useOllama ? (
            <div className="space-y-4">
              <div>
                <label htmlFor="ollama-url" className="label mb-1.5 block">
                  Ollama URL
                </label>
                <input
                  id="ollama-url"
                  type="text"
                  value={ollamaUrl}
                  onChange={(e) => setOllamaUrl(e.target.value)}
                  className="input w-full"
                  placeholder="http://localhost:11434"
                />
              </div>
              <div>
                <label htmlFor="ollama-model" className="label mb-1.5 block">
                  Model
                </label>
                <select
                  id="ollama-model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="input w-full"
                >
                  {providerModels.ollama.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label htmlFor="llm-provider" className="label mb-1.5 block">
                  Provider
                </label>
                <select
                  id="llm-provider"
                  value={provider}
                  onChange={(e) => {
                    setProvider(e.target.value);
                    setModel(providerModels[e.target.value]?.[0] || '');
                  }}
                  className="input w-full"
                >
                  <option value="openrouter">OpenRouter — many free models</option>
                  <option value="groq">Groq — fast, free tier</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </div>

              <div>
                <label htmlFor="llm-model" className="label mb-1.5 block">
                  Model
                </label>
                <select
                  id="llm-model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="input w-full"
                >
                  {providerModels[provider]?.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="llm-api-key" className="label mb-1.5 block">
                  API key
                </label>
                <input
                  id="llm-api-key"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="input w-full"
                  placeholder="Leave blank to keep the stored key"
                  autoComplete="new-password"
                />
                <p className="mt-1.5 text-xs text-fg-subtle">
                  Leave blank unless you are replacing it — this field is empty even when a key is
                  already stored, because the key is never sent back to the browser. Where to get
                  one:{' '}
                  {{
                    openrouter: 'openrouter.ai',
                    groq: 'console.groq.com',
                    openai: 'platform.openai.com',
                    anthropic: 'console.anthropic.com',
                  }[provider] || 'your provider’s console'}
                  .
                </p>
              </div>
            </div>
          )}

          <div>
            <label htmlFor="max-tokens" className="label mb-1.5 block">
              Max tokens per reply
            </label>
            <input
              id="max-tokens"
              type="number"
              min={100}
              max={100000}
              step={100}
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value) || 8000)}
              className="input w-full"
              placeholder="8000"
            />
            <p className="mt-1.5 text-xs text-fg-subtle">
              Caps the length of a single model reply, not the length of the conversation. Default
              8000.
            </p>
          </div>
        </div>
      </Section>

      {/* Save Button */}
      <div className="flex justify-end gap-3">
        <button type="button" onClick={onRefresh} className="btn-secondary">
          Discard changes
        </button>
        <button type="button" onClick={handleSave} disabled={saving} className="btn-primary">
          {saving ? 'Saving…' : 'Save settings'}
        </button>
      </div>
    </div>
  );
}

