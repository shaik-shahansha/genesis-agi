'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface Memory {
  id: string;
  type: string;
  content: string;
  timestamp: string;
  emotion?: string;
  importance: number;
  tags: string[];
}

interface MemoryTabProps {
  mindId: string;
}

export default function MemoryTab({ mindId }: MemoryTabProps) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadMemories();
  }, [mindId, filter]);

  const loadMemories = async () => {
    setLoading(true);
    try {
      const data = await api.getMindMemories(mindId, 100);
      setMemories(data);
    } catch (error) {
      console.error('Error loading memories:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredMemories = memories.filter(m => {
    const matchesFilter = filter === 'all' || m.type === filter;
    const matchesSearch = search === '' || 
      m.content.toLowerCase().includes(search.toLowerCase()) ||
      m.tags.some(tag => tag.toLowerCase().includes(search.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  const memoryTypes = ['all', 'conversation', 'experience', 'reflection', 'learning', 'emotional'];

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <input
            type="text"
            placeholder="Search memories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input flex-1"
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input md:w-48"
          >
            {memoryTypes.map(type => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
          <button onClick={loadMemories} className="btn-ghost">
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total</div>
          <div className="text-2xl font-bold text-gray-900">{memories.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Filtered</div>
          <div className="text-2xl font-bold text-gray-900">{filteredMemories.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Avg Importance</div>
          <div className="text-2xl font-bold text-gray-900">
            {memories.length ? (memories.reduce((sum, m) => sum + m.importance, 0) / memories.length).toFixed(2) : '0'}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Types</div>
          <div className="text-2xl font-bold text-gray-900">
            {new Set(memories.map(m => m.type)).size}
          </div>
        </div>
      </div>

      {/* Memory List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-8">
            <div className="spinner mx-auto"></div>
          </div>
        ) : filteredMemories.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-600">
            No memories found
          </div>
        ) : (
          filteredMemories.map((memory) => (
            <div key={memory.id} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium">
                    {memory.type}
                  </span>
                  {memory.emotion && (
                    <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs">
                      {memory.emotion}
                    </span>
                  )}
                  <span className="text-xs text-gray-500">
                    Importance: {memory.importance.toFixed(2)}
                  </span>
                </div>
                <span className="text-xs text-gray-500">
                  {new Date(memory.timestamp).toLocaleString()}
                </span>
              </div>
              <p className="text-gray-900 mb-2">{memory.content}</p>
              {memory.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {memory.tags.map((tag, i) => (
                    <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
