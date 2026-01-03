'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

interface ThinkingTabProps {
  mindId: string;
}

export default function ThinkingTab({ mindId }: ThinkingTabProps) {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [thinking, setThinking] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState<string[]>([]);

  const handleThink = async () => {
    if (!input.trim() || thinking) return;
    
    setThinking(true);
    setResponse('');
    setThinkingSteps([]);
    
    try {
      // Use the chat endpoint to get a response with thinking
      const result = await api.chat(mindId, input, {
        include_thinking: true
      });
      
      setResponse(result.response || result.message || 'No response');
      
      // Extract thinking steps if available
      if (result.thinking) {
        setThinkingSteps(Array.isArray(result.thinking) ? result.thinking : [result.thinking]);
      } else if (result.metadata?.thinking) {
        setThinkingSteps([result.metadata.thinking]);
      }
    } catch (error: any) {
      console.error('Error thinking:', error);
      setResponse(`Error: ${error.message || 'Failed to process thought'}`);
    } finally {
      setThinking(false);
    }
  };

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
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  handleThink();
                }
              }}
              placeholder="Enter a prompt to see how the mind thinks... (Ctrl+Enter to submit)"
              className="input h-24"
              disabled={thinking}
            />
          </div>

          <button
            onClick={handleThink}
            disabled={!input.trim() || thinking}
            className="btn-primary w-full"
          >
            {thinking ? '🤔 Thinking...' : '💭 Think Through This'}
          </button>

          {thinkingSteps.length > 0 && (
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-3">
              <h3 className="font-medium text-gray-900 mb-2">🧠 Thinking Process</h3>
              {thinkingSteps.map((step, idx) => (
                <div key={idx} className="bg-white border border-gray-200 rounded p-3">
                  <div className="text-xs text-gray-500 mb-1">Step {idx + 1}</div>
                  <div className="text-gray-700">{step}</div>
                </div>
              ))}
            </div>
          )}

          {response && (
            <div className="border border-blue-200 rounded-lg p-4 bg-blue-50">
              <h3 className="font-medium text-gray-900 mb-2">💡 Response</h3>
              <div className="text-gray-900 whitespace-pre-wrap">{response}</div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Thinking Patterns</h2>
        <p className="text-sm text-gray-600 mb-4">
          These metrics are derived from the Mind's interaction history and consciousness logs.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600">Reasoning Model</div>
            <div className="text-xl font-bold text-gray-900 mt-1">
              {thinking ? '...' : 'deepseek-r1'}
            </div>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600">Thinking Mode</div>
            <div className="text-xl font-bold text-gray-900 mt-1">Reflective</div>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600">Creativity</div>
            <div className="text-xl font-bold text-gray-900 mt-1">High</div>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600">Logic</div>
            <div className="text-xl font-bold text-gray-900 mt-1">High</div>
          </div>
        </div>
      </div>
    </div>
  );
}
