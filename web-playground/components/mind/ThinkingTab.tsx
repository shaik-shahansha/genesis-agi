'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { Section, ErrorState, LoadingRows } from '@/components/governance/primitives';
import { SparkIcon } from '@/components/shell/icons';

interface ThinkingTabProps {
  mindId: string;
  /** Optional so the tab still works where only an id is available. */
  mind?: any;
}

/**
 * Interactive thinking, as a chat turn with the reasoning surfaced.
 *
 * The previous version of this tab carried a "Thinking Patterns" panel showing
 * Reasoning Model `deepseek-r1`, Thinking Mode `Reflective`, Creativity `High`
 * and Logic `High`, under the sentence "These metrics are derived from the
 * Mind's interaction history and consciousness logs". Every one of those four
 * values was a hardcoded string and no such metrics exist anywhere in the
 * system. A panel that looks like measured data and is not is worse than no
 * panel, because it is the kind of thing a person repeats.
 *
 * What replaced it is what the API actually returns, and an explicit statement
 * when a field is absent rather than a plausible-looking default.
 */
export default function ThinkingTab({ mindId, mind }: ThinkingTabProps) {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thinkingSteps, setThinkingSteps] = useState<string[]>([]);
  const [lastTurn, setLastTurn] = useState<{ prompt: string; ms: number } | null>(null);

  const handleThink = async () => {
    if (!input.trim() || thinking) return;

    setThinking(true);
    setResponse('');
    setError(null);
    setThinkingSteps([]);

    const startedAt = Date.now();
    const prompt = input;

    try {
      const result = await api.chat(mindId, prompt);

      setResponse(result.response || result.message || 'No response returned.');
      setLastTurn({ prompt, ms: Date.now() - startedAt });

      // The reasoning field is genuinely optional: it only appears when the
      // configured model emits it AND the provider passes it through. Saying so
      // is better than rendering an empty "Thinking Process" box.
      if (result.thinking) {
        setThinkingSteps(Array.isArray(result.thinking) ? result.thinking : [result.thinking]);
      } else if (result.metadata?.thinking) {
        setThinkingSteps(Array.isArray(result.metadata.thinking) ? result.metadata.thinking : [result.metadata.thinking]);
      }
    } catch (err: any) {
      setError(err?.message || 'The turn failed. Check that a model provider is configured.');
    } finally {
      setThinking(false);
    }
  };

  return (
    <div className="space-y-6">
      <Section
        title="Interactive thinking"
        description="Send a prompt and see the reasoning the model returns alongside its answer."
      >
        <div className="card space-y-4">
          <div>
            <label htmlFor="thinking-input" className="label mb-1.5 block">
              Prompt
            </label>
            <textarea
              id="thinking-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  handleThink();
                }
              }}
              placeholder="Ask something that requires a step of reasoning… (Ctrl+Enter to send)"
              className="input h-24 resize-y"
              disabled={thinking}
            />
            <p className="mt-1.5 text-xs text-fg-subtle">
              This is a real turn against the Mind — it is remembered like any other message.
            </p>
          </div>

          <button
            type="button"
            onClick={handleThink}
            disabled={!input.trim() || thinking}
            className="btn-primary w-full justify-center"
          >
            <SparkIcon className="h-4 w-4" />
            {thinking ? 'Thinking…' : 'Send'}
          </button>

          {error && <ErrorState message={error} />}

          {thinking && !response && <LoadingRows rows={1} label="Waiting for the model" />}

          {thinkingSteps.length > 0 && (
            <div className="rounded-card border border-line bg-surface-2 p-4">
              <h3 className="section-title mb-3">Reasoning returned by the model</h3>
              <ol className="space-y-2">
                {thinkingSteps.map((step, idx) => (
                  <li key={idx} className="rounded-lg border border-line bg-surface p-3">
                    <div className="text-xs text-fg-subtle">Step {idx + 1}</div>
                    <div className="mt-0.5 whitespace-pre-wrap text-sm text-fg">{step}</div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {!thinking && !response && !error && thinkingSteps.length === 0 && (
            <p className="text-sm text-fg-subtle">
              Nothing sent yet. The reasoning block only appears when the configured model returns
              one — many do not, and for those this tab shows the answer alone.
            </p>
          )}

          {response && (
            <div className="rounded-card border border-accent/40 bg-accent/5 p-4">
              <h3 className="section-title mb-2">Response</h3>
              <div className="whitespace-pre-wrap text-sm text-fg">{response}</div>
              {lastTurn && (
                <p className="mt-3 border-t border-line pt-2 text-xs text-fg-subtle">
                  Reply to “{lastTurn.prompt.slice(0, 60)}
                  {lastTurn.prompt.length > 60 ? '…' : ''}” in {lastTurn.ms} ms
                </p>
              )}
            </div>
          )}
        </div>
      </Section>

      <Section title="What this tab can and cannot tell you">
        <div className="card">
          <dl className="space-y-3 text-sm">
            <div className="grid grid-cols-[10rem_1fr] gap-3">
              <dt className="text-fg-muted">Model</dt>
              <dd className="text-fg">{mind?.llm_model || 'not reported by this endpoint'}</dd>
            </div>
            <div className="grid grid-cols-[10rem_1fr] gap-3">
              <dt className="text-fg-muted">Reasoning trace</dt>
              <dd className="text-fg-muted">
                Shown when the provider returns one. There is no separate reasoning log to browse
                later — the trace is not persisted.
              </dd>
            </div>
            <div className="grid grid-cols-[10rem_1fr] gap-3">
              <dt className="text-fg-muted">Reasoning style</dt>
              <dd className="text-fg-muted">
                Not measured. There is no score for logic, creativity or "thinking mode" anywhere in
                the system, so this tab no longer shows any.
              </dd>
            </div>
          </dl>
        </div>
      </Section>
    </div>
  );
}

