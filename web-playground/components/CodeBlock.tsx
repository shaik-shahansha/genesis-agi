import React from 'react';

interface CodeBlockProps {
  code: string;
  language?: string;
}

export function CodeBlock({ code, language = 'javascript' }: CodeBlockProps) {
  const [copied, setCopied] = React.useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={copyToClipboard}
          className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-white text-xs rounded-md transition"
        >
          {copied ? '✓ Copied!' : '📋 Copy'}
        </button>
      </div>
      <div className="bg-slate-900 rounded-lg p-4 overflow-x-auto">
        <div className="text-xs text-gray-400 mb-2">{language}</div>
        <pre className="text-sm text-gray-100 font-mono">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}
