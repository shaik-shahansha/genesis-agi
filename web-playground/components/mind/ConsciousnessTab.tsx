'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface ConsciousnessTabProps {
  mindId: string;
}

export default function ConsciousnessTab({ mindId }: ConsciousnessTabProps) {
  const [thoughts, setThoughts] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  useEffect(() => {
    loadData();
  }, [mindId]);

  // Auto-refresh every 10 seconds (disabled by default)
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      loadData();
    }, 10000);
    
    return () => clearInterval(interval);
  }, [mindId, autoRefresh]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [thoughtsData, logsData] = await Promise.all([
        api.getMindThoughts(mindId, 20),
        api.getMindLogs(mindId, 50),
      ]);
      setThoughts(thoughtsData.thoughts || []);
      setLogs(logsData.logs || []);
    } catch (error) {
      console.error('Error loading consciousness data:', error);
    } finally {
      setLoading(false);
    }
  };

  const triggerThought = async () => {
    if (generating) return;
    
    setGenerating(true);
    try {
      const result = await api.generateThought(mindId);
      console.log('Generated thought:', result);
      
      // Wait a moment for the thought to be saved
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Reload the data
      await loadData();
      
      if (result.success) {
        // Show success feedback
        console.log('Thought generated successfully');
      }
    } catch (error: any) {
      console.error('Error generating thought:', error);
      alert(`Failed to generate thought: ${error.message}`);
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="spinner mx-auto"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Consciousness Stream</h2>
          <div className="flex gap-2 items-center">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input 
                type="checkbox" 
                checked={autoRefresh} 
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              Auto-refresh (10s)
            </label>
            <button 
              onClick={triggerThought} 
              className="btn-primary"
              disabled={generating}
            >
              {generating ? '⏳ Generating...' : '💭 Generate Thought'}
            </button>
            <button 
              onClick={loadData} 
              className="btn-ghost"
              disabled={generating}
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Live Activity Logs */}
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className={autoRefresh ? "inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse" : "inline-block w-2 h-2 bg-gray-500 rounded-full"}></span>
          Live Activity Logs ({logs.length})
        </h3>
        <div className="space-y-1 font-mono text-sm max-h-96 overflow-y-auto">
          {logs.length === 0 ? (
            <p className="text-gray-400 text-center py-4">No activity logs yet</p>
          ) : (
            logs.slice().reverse().map((log, index) => (
              <div key={index} className={`p-2 rounded ${
                log.level === 'error' ? 'bg-red-900/20 text-red-300' :
                log.level === 'warning' ? 'bg-yellow-900/20 text-yellow-300' :
                log.level === 'info' ? 'bg-blue-900/20 text-blue-300' :
                'bg-gray-800 text-gray-300'
              }`}>
                <span className="text-gray-500 text-xs">
                  {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}
                </span>
                {' '}
                <span className="text-gray-400">
                  [{log.level?.toUpperCase() || 'LOG'}]
                </span>
                {' '}
                <span className="text-white">{log.message || JSON.stringify(log)}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Recent Thoughts */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Thoughts ({thoughts.length})</h3>
        <div className="space-y-3">
          {thoughts.length === 0 ? (
            <p className="text-gray-600 text-center py-4">No thoughts yet</p>
          ) : (
            thoughts.map((thought, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <span className="text-xs text-gray-500">
                    {thought.timestamp ? new Date(thought.timestamp).toLocaleString() : 'Unknown time'}
                  </span>
                </div>
                <p className="text-gray-900">{typeof thought === 'string' ? thought : thought.content || JSON.stringify(thought)}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
