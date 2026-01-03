'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface LLMCall {
  id: string;
  timestamp: string;
  provider: string;
  model: string;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  cost: number;
  latency: number;
  success: boolean;
  purpose?: string;
}

interface LLMCallsTabProps {
  mindId: string;
}

export default function LLMCallsTab({ mindId }: LLMCallsTabProps) {
  const [calls, setCalls] = useState<LLMCall[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    totalCalls: 0,
    totalTokens: 0,
    totalCost: 0,
    avgLatency: 0,
    providers: {} as Record<string, number>
  });

  useEffect(() => {
    loadCalls();
  }, [mindId]);

  const loadCalls = async () => {
    setLoading(true);
    try {
      // Try to get LLM call history from the API
      const data = await api.getLLMCalls(mindId, 50);
      
      if (data.calls && data.calls.length > 0) {
        setCalls(data.calls);
        
        // Calculate stats
        const totalCalls = data.calls.length;
        const totalTokens = data.calls.reduce((sum: number, call: LLMCall) => sum + call.totalTokens, 0);
        const totalCost = data.calls.reduce((sum: number, call: LLMCall) => sum + call.cost, 0);
        const avgLatency = data.calls.reduce((sum: number, call: LLMCall) => sum + call.latency, 0) / totalCalls;
        
        const providers: Record<string, number> = {};
        data.calls.forEach((call: LLMCall) => {
          providers[call.provider] = (providers[call.provider] || 0) + 1;
        });
        
        setStats({ totalCalls, totalTokens, totalCost, avgLatency, providers });
      } else {
        // No calls yet or API not implemented - show placeholder
        setCalls([]);
        setStats({
          totalCalls: 0,
          totalTokens: 0,
          totalCost: 0,
          avgLatency: 0,
          providers: {}
        });
      }
    } catch (error) {
      console.error('Error loading LLM calls:', error);
      // API endpoint may not exist yet - that's okay
      setCalls([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Calls</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {loading ? '...' : stats.totalCalls}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Tokens</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {loading ? '...' : stats.totalTokens.toLocaleString()}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Cost</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {loading ? '...' : `$${stats.totalCost.toFixed(4)}`}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Avg Latency</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">
            {loading ? '...' : `${stats.avgLatency.toFixed(0)}ms`}
          </div>
        </div>
      </div>

      {/* Provider Breakdown */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Provider Usage</h2>
        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner"></div>
            </div>
          ) : Object.keys(stats.providers).length === 0 ? (
            <p className="text-gray-600 text-center py-4">
              No LLM calls recorded yet. Start chatting with your Mind to see usage stats.
            </p>
          ) : (
            <div className="space-y-2">
              {Object.entries(stats.providers).map(([provider, count]) => (
                <div key={provider} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                  <span className="font-medium text-gray-900">{provider}</span>
                  <span className="text-gray-600">{count} calls</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Calls */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Recent Calls</h2>
          <button onClick={loadCalls} disabled={loading} className="btn-ghost">
            🔄 Refresh
          </button>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="spinner"></div>
          </div>
        ) : calls.length === 0 ? (
          <div className="text-gray-600 text-center py-8">
            <p className="mb-2">No LLM calls recorded yet</p>
            <p className="text-sm text-gray-500">
              LLM call tracking may not be enabled. Check with your system administrator.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left p-3 font-medium text-gray-700">Time</th>
                  <th className="text-left p-3 font-medium text-gray-700">Provider</th>
                  <th className="text-left p-3 font-medium text-gray-700">Model</th>
                  <th className="text-left p-3 font-medium text-gray-700">Purpose</th>
                  <th className="text-right p-3 font-medium text-gray-700">Tokens</th>
                  <th className="text-right p-3 font-medium text-gray-700">Cost</th>
                  <th className="text-right p-3 font-medium text-gray-700">Latency</th>
                  <th className="text-center p-3 font-medium text-gray-700">Status</th>
                </tr>
              </thead>
              <tbody>
                {calls.map((call) => (
                  <tr key={call.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="p-3 text-gray-700">
                      {new Date(call.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="p-3 text-gray-700">{call.provider}</td>
                    <td className="p-3 text-gray-700 text-xs">{call.model}</td>
                    <td className="p-3 text-gray-600 text-xs">{call.purpose || 'Chat'}</td>
                    <td className="p-3 text-right text-gray-700">{call.totalTokens.toLocaleString()}</td>
                    <td className="p-3 text-right text-gray-700">${call.cost.toFixed(4)}</td>
                    <td className="p-3 text-right text-gray-700">{call.latency}ms</td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 rounded text-xs ${
                        call.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {call.success ? '✓' : '✗'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <span className="text-2xl">ℹ️</span>
          <div className="text-sm text-gray-700">
            <p className="font-medium mb-1">About LLM Call Tracking</p>
            <p className="text-gray-600">
              This feature tracks all LLM API calls made by your Mind for transparency and cost monitoring.
              If you don't see any data, LLM call tracking may need to be enabled in the backend.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

                  </td>
                </tr>
              ) : (
                calls.map((call) => (
                  <tr key={call.id} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="p-3 text-gray-900">
                      {new Date(call.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="p-3 text-gray-900">{call.provider}</td>
                    <td className="p-3 text-gray-900 font-mono text-xs">{call.model}</td>
                    <td className="p-3 text-right text-gray-900">{call.totalTokens}</td>
                    <td className="p-3 text-right text-gray-900">${call.cost.toFixed(4)}</td>
                    <td className="p-3 text-right text-gray-900">{call.latency}ms</td>
                    <td className="p-3 text-center">
                      {call.success ? (
                        <span className="text-green-600">✓</span>
                      ) : (
                        <span className="text-red-600">✗</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
