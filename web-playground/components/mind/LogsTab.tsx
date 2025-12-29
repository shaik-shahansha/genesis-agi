'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface LogEntry {
  timestamp: string;
  mind_id: string;
  mind_name: string;
  level: string;
  message: string;
  emotion: string | null;
  metadata: Record<string, any>;
}

interface LogsTabProps {
  mindId: string;
}

export default function LogsTab({ mindId }: LogsTabProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState('all');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadLogs();
  }, [mindId]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(loadLogs, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, mindId]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getMindLogs(mindId);
      setLogs(data.logs || []);
    } catch (error) {
      console.error('Error loading logs:', error);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const clearLogs = async () => {
    if (!confirm('Clear all logs?')) return;

    try {
      await api.clearMindLogs(mindId);
      setLogs([]);
    } catch (error: any) {
      alert(`Failed to clear logs: ${error.message}`);
    }
  };

  const downloadLogs = () => {
    const content = logs.map(log => 
      `[${log.timestamp}] [${log.level.toUpperCase()}] ${log.message}${log.emotion ? ` (${log.emotion})` : ''}`
    ).join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mind-${mindId}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredLogs = logs.filter(log => {
    if (filter === 'all') return true;
    return log.level.toLowerCase() === filter.toLowerCase();
  });

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={loadLogs}
              disabled={loading}
              className="btn-ghost"
            >
              🔄 Refresh
            </button>
            <button onClick={downloadLogs} className="btn-ghost">
              📥 Download
            </button>
            <button onClick={clearLogs} className="btn-ghost text-red-600">
              🗑️ Clear
            </button>
            <label className="flex items-center gap-2 px-3 py-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm text-gray-700">Auto-refresh</span>
            </label>
          </div>

          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input md:w-48"
          >
            <option value="all">All Logs</option>
            <option value="info">ℹ️ Info</option>
            <option value="thought">💭 Thoughts</option>
            <option value="dream">💤 Dreams</option>
            <option value="memory">🧠 Memory</option>
            <option value="llm_call">🤖 LLM Calls</option>
            <option value="emotion">😊 Emotions</option>
            <option value="action">⚡ Actions</option>
            <option value="search">🔍 Searches</option>
            <option value="relationship">👥 Relationships</option>
            <option value="error">❌ Errors</option>
          </select>
        </div>
      </div>

      {/* Log Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total</div>
          <div className="text-2xl font-bold text-gray-900">{logs.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Filtered</div>
          <div className="text-2xl font-bold text-gray-900">{filteredLogs.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Errors</div>
          <div className="text-2xl font-bold text-red-600">
            {logs.filter(l => l.level === 'error').length}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Thoughts</div>
          <div className="text-2xl font-bold text-purple-600">
            {logs.filter(l => l.level === 'thought').length}
          </div>
        </div>
      </div>

      {/* Log Viewer */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-900 text-gray-100 p-4 font-mono text-sm overflow-auto" style={{ maxHeight: '600px' }}>
          {filteredLogs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              {logs.length === 0 ? 'No logs available' : 'No logs match the filter'}
            </div>
          ) : (
            filteredLogs.map((log, index) => {
              const isError = log.level === 'error';
              const isThought = log.level === 'thought';
              const isDream = log.level === 'dream';
              const isMemory = log.level === 'memory';
              const isLLM = log.level === 'llm_call';
              
              const color = isError ? 'text-red-400' : 
                           isThought ? 'text-purple-400' : 
                           isDream ? 'text-blue-400' :
                           isMemory ? 'text-green-400' :
                           isLLM ? 'text-yellow-400' :
                           'text-gray-300';
              
              const emoji = isError ? '❌' :
                           isThought ? '💭' :
                           isDream ? '💤' :
                           isMemory ? '🧠' :
                           isLLM ? '🤖' :
                           '📝';
              
              return (
                <div key={index} className={`${color} mb-2 hover:bg-gray-800 px-2 py-1 rounded`}>
                  <div className="flex gap-2">
                    <span className="opacity-60 text-xs">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    <span>{emoji}</span>
                    <span className="font-semibold">[{log.level.toUpperCase()}]</span>
                    {log.emotion && <span className="text-pink-400">({log.emotion})</span>}
                  </div>
                  <div className="ml-20">{log.message}</div>
                  {Object.keys(log.metadata).length > 0 && (
                    <div className="ml-20 mt-1 text-xs opacity-70">
                      {JSON.stringify(log.metadata, null, 2)}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* CLI Commands */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">CLI Commands</h2>
        <div className="space-y-2">
          <p className="text-sm text-gray-600 mb-3">
            Execute Genesis CLI commands directly from the interface
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="genesis command..."
              className="input flex-1 font-mono text-sm"
            />
            <button className="btn-primary">
              ▶️ Execute
            </button>
          </div>
          <div className="mt-4 space-y-2">
            <p className="text-xs text-gray-600 font-medium">Quick Commands:</p>
            <div className="flex flex-wrap gap-2">
              <button className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded">
                genesis list
              </button>
              <button className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded">
                genesis inspect {mindId}
              </button>
              <button className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded">
                genesis status
              </button>
              <button className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded">
                genesis think {mindId}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
