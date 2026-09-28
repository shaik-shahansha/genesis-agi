import React from 'react';
import { CheckIcon } from '@/components/shell/icons';

interface CodeBlockProps {
  code: string;
  language?: string;
}

/**
 * A code block with a copy control.
 *
 * Two fixes over the previous version:
 *
 *  - The copy button only appeared on `group-hover`, so it was unreachable by
 *    keyboard and invisible on touch devices — where there is no hover state at
 *    all, and copying is the entire reason to reach for the button. It is always
 *    rendered now and reveals on hover purely as emphasis.
 *  - `navigator.clipboard` is undefined on an insecure origin (plain HTTP, which
 *    is how a self-hosted install is often first reached) and rejects when the
 *    document is not focused. That call was unhandled, so the button reported
 *    "Copied!" after a failure that never happened.
 */
export function CodeBlock({ code, language = 'javascript' }: CodeBlockProps) {
  const [state, setState] = React.useState<'idle' | 'copied' | 'failed'>('idle');

  const copyToClipboard = async () => {
    try {
      if (!navigator.clipboard) {
        throw new Error('clipboard API unavailable');
      }
      await navigator.clipboard.writeText(code);
      setState('copied');
    } catch {
      setState('failed');
    }
    setTimeout(() => setState('idle'), 2000);
  };

  return (
    <div className="group relative">
      <div className="absolute right-2 top-2 opacity-60 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
        <button
          type="button"
          onClick={copyToClipboard}
          className="btn-secondary btn-sm"
          aria-label={`Copy the ${language} code block`}
        >
          {state === 'copied' && <CheckIcon className="h-3.5 w-3.5 text-success" />}
          {state === 'copied' ? 'Copied' : state === 'failed' ? 'Copy failed' : 'Copy'}
        </button>
      </div>
      <div className="overflow-x-auto rounded-card border border-line bg-surface-2">
        <div className="border-b border-line px-3 py-1.5 font-mono text-xs text-fg-subtle">
          {language}
        </div>
        <pre className="p-3 font-mono text-xs text-fg">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}

