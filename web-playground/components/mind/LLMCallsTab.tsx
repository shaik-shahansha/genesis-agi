'use client';

import { useState, useEffect } from 'react';

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
}

interface LLMCallsTabProps {
  mindId: string;
}

export default function LLMCallsTab({ mindId }: LLMCallsTabProps) {
  const [calls, setCalls] = useState<LLMCall[]>([]);
  const [loading, setLoading] = useState(false);

  // Mock data for now
  useEffect(() => {
    // TODO: Implement API call to get LLM calls
    setCalls([]);
  }, [mindId]);

  const totalCost = calls.reduce((sum, call) => sum + call.cost, 0);
  const totalTokens = calls.reduce((sum, call) => sum + call.totalTokens, 0);
  const avgLatency = calls.length > 0 
    ? calls.reduce((sum, call) => sum + call.latency, 0) / calls.length 
    : 0;

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Calls</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{calls.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Tokens</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{totalTokens.toLocaleString()}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Cost</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">${totalCost.toFixed(4)}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Avg Latency</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{avgLatency.toFixed(0)}ms</div>
        </div>
      </div>

      {/* Provider Breakdown */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Provider Usage</h2>
        <div className="space-y-3">
          {calls.length === 0 ? (
            <p className="text-gray-600 text-center py-4">No LLM calls yet</p>
          ) : (
            <div className="text-center py-4 text-gray-600">
              Waiting for LLM call data...
            </div>
          )}
        </div>
      </div>

      {/* Recent Calls */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Recent Calls</h2>
          <button className="btn-ghost">
            🔄 Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left p-3 font-medium text-gray-700">Time</th>
                <th className="text-left p-3 font-medium text-gray-700">Provider</th>
                <th className="text-left p-3 font-medium text-gray-700">Model</th>
                <th className="text-right p-3 font-medium text-gray-700">Tokens</th>
                <th className="text-right p-3 font-medium text-gray-700">Cost</th>
                <th className="text-right p-3 font-medium text-gray-700">Latency</th>
                <th className="text-center p-3 font-medium text-gray-700">Status</th>
              </tr>
            </thead>
            <tbody>
              {calls.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-gray-600">
                    No LLM calls recorded yet
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
