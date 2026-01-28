'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { getFirebaseToken } from '@/lib/firebase';

interface ConversationMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: any;
}

interface MemoryTabProps {
  mindId: string;
}

export default function MemoryTab({ mindId }: MemoryTabProps) {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [userEmail, setUserEmail] = useState<string>('');

  useEffect(() => {
    // Load user email from localStorage
    const storedEmail = localStorage.getItem('genesis_user_email');
    if (storedEmail) {
      setUserEmail(storedEmail);
    }
    loadConversations();
  }, [mindId]);

  const loadConversations = async () => {
    setLoading(true);
    try {
      const storedEmail = localStorage.getItem('genesis_user_email');
      if (!storedEmail) {
        console.log('No user email found');
        setLoading(false);
        return;
      }

      const token = await getFirebaseToken();
      if (!token) {
        console.error('No authentication token available');
        setLoading(false);
        return;
      }

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${API_URL}/api/v1/minds/${mindId}/conversations/messages?user_email=${encodeURIComponent(storedEmail)}&limit=200`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch conversations');
      }

      const data = await response.json();
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredMessages = messages.filter(m => {
    const matchesFilter = filter === 'all' || m.role === filter;
    const matchesSearch = search === '' || 
      m.content.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const filterOptions = [
    { value: 'all', label: 'All Messages' },
    { value: 'user', label: 'User Messages' },
    { value: 'assistant', label: 'Assistant Messages' }
  ];

  const userMessages = messages.filter(m => m.role === 'user');
  const assistantMessages = messages.filter(m => m.role === 'assistant');

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <input
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input flex-1"
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="input md:w-48"
          >
            {filterOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button onClick={loadConversations} className="btn-ghost">
            🔄 Refresh
          </button>
        </div>
        {userEmail && (
          <div className="mt-2 text-xs text-gray-500">
            Showing conversations for: {userEmail}
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Total Messages</div>
          <div className="text-2xl font-bold text-gray-900">{messages.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Your Messages</div>
          <div className="text-2xl font-bold text-gray-900">{userMessages.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Mind Responses</div>
          <div className="text-2xl font-bold text-gray-900">{assistantMessages.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">Filtered</div>
          <div className="text-2xl font-bold text-gray-900">{filteredMessages.length}</div>
        </div>
      </div>

      {/* Message List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-8">
            <div className="spinner mx-auto"></div>
          </div>
        ) : filteredMessages.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-600">
            {messages.length === 0 ? (
              <>
                <p className="mb-2">No conversation history yet</p>
                <p className="text-sm">Start chatting to see messages here!</p>
              </>
            ) : (
              <p>No messages match your search</p>
            )}
          </div>
        ) : (
          filteredMessages.map((message) => (
            <div 
              key={message.id} 
              className={`border rounded-lg p-4 transition-colors ${
                message.role === 'user'
                  ? 'bg-blue-50 border-blue-200 hover:border-blue-300'
                  : 'bg-purple-50 border-purple-200 hover:border-purple-300'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    message.role === 'user'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-purple-100 text-purple-700'
                  }`}>
                    {message.role === 'user' ? '👤 You' : '🤖 Mind'}
                  </span>
                </div>
                <span className="text-xs text-gray-500">
                  {new Date(message.timestamp).toLocaleString()}
                </span>
              </div>
              <p className="text-gray-900 whitespace-pre-wrap">{message.content}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
