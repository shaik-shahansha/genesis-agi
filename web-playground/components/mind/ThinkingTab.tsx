'use client';

import { useState } from 'react';

interface ThinkingTabProps {
  mindId: string;
}

export default function ThinkingTab({ mindId }: ThinkingTabProps) {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [thinking, setThinking] = useState(false);

  return (
    <div className="space-y-6">
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Interactive Thinking</h2>
        <p className="text-gray-600 mb-4">
          Observe the mind's thinking process in real-time. This view shows how the mind reasons through problems.
        </p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Prompt or Question
            </label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Enter a prompt to see how the mind thinks..."
              className="input h-24"
              disabled={thinking}
            />
          </div>

          <button
            onClick={() => {/* TODO: Implement thinking API */}}
            disabled={!input.trim() || thinking}
            className="btn-primary w-full"
          >
            {thinking ? '🤔 Thinking...' : '💭 Think Through This'}
          </button>

          {response && (
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <h3 className="font-medium text-gray-900 mb-2">Thinking Process</h3>
              <div className="text-gray-900 whitespace-pre-wrap">{response}</div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Thinking Patterns</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600">Average Response Time</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">2.3s</div>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600">Reasoning Depth</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">Medium</div>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600">Creativity Score</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">0.75</div>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600">Logic Score</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">0.85</div>
          </div>
        </div>
      </div>
    </div>
  );
}
