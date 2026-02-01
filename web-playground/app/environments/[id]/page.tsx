'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import { EnvironmentWebSocket, EnvironmentMessage } from '@/lib/websocket';
import { isProduction } from '@/lib/env';

interface Message {
  type: string;
  from_mind_name?: string;
  content?: string;
  emotion?: string;
  timestamp: string;
  mind_name?: string;
}

export default function EnvironmentChatPage() {
  const router = useRouter();
  const params = useParams();
  const envId = params.id as string;

  const [environment, setEnvironment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [presentMinds, setPresentMinds] = useState<string[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [mindId, setMindId] = useState('');
  const [mindName, setMindName] = useState('');
  const [joined, setJoined] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [showAccessControl, setShowAccessControl] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newMindGmid, setNewMindGmid] = useState('');

  const wsRef = useRef<EnvironmentWebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Redirect if environments are disabled in production
    if (isProduction()) {
      router.push('/');
      return;
    }
    loadEnvironment();

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, [envId, router]);

  // Don't render the page if environments are disabled
  if (isProduction()) {
    return null;
  }

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadEnvironment = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getEnvironment(envId);
      setEnvironment(data);
    } catch (error: any) {
      console.error('Failed to load environment:', error);
      setError(error.message || 'Failed to load environment. Please check if the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const joinEnvironment = () => {
    if (!mindId || !mindName) {
      alert('Please enter both Mind ID and Name');
      return;
    }

    setConnecting(true);

    const ws = new EnvironmentWebSocket(envId, mindId, mindName, {
      onMessage: handleMessage,
      onConnect: () => {
        console.log('Connected to environment');
        setJoined(true);
        setConnecting(false);
      },
      onDisconnect: () => {
        console.log('Disconnected from environment');
        setJoined(false);
        setConnecting(false);
      },
      onError: (error) => {
        console.error('WebSocket error:', error);
        setConnecting(false);
      },
    });

    ws.connect();
    wsRef.current = ws;
  };

  const leaveEnvironment = () => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }
    setJoined(false);
    setMessages([]);
    setPresentMinds([]);
  };

  const handleMessage = (message: EnvironmentMessage) => {
    console.log('Received message:', message);

    if (message.type === 'welcome') {
      setMessages((prev) => [
        ...prev,
        {
          type: 'system',
          content: message.message,
          timestamp: new Date().toISOString(),
        },
      ]);
      if (message.environment?.present_minds) {
        setPresentMinds(message.environment.present_minds);
      }
    } else if (message.type === 'mind_joined') {
      setMessages((prev) => [
        ...prev,
        {
          type: 'system',
          content: `${message.mind_name} joined the environment`,
          timestamp: message.timestamp,
        },
      ]);
      setPresentMinds(message.present_minds);
    } else if (message.type === 'mind_left') {
      setMessages((prev) => [
        ...prev,
        {
          type: 'system',
          content: `${message.mind_name} left the environment`,
          timestamp: message.timestamp,
        },
      ]);
      setPresentMinds(message.present_minds);
    } else if (message.type === 'chat_message') {
      setMessages((prev) => [
        ...prev,
        {
          type: 'chat',
          from_mind_name: message.from_mind_name,
          content: message.content,
          emotion: message.emotion,
          timestamp: message.timestamp,
        },
      ]);
    }
  };

  const sendMessage = (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputMessage.trim() || !wsRef.current) return;

    wsRef.current.sendChat(inputMessage);

    // Add own message to display
    setMessages((prev) => [
      ...prev,
      {
        type: 'chat',
        from_mind_name: mindName,
        content: inputMessage,
        timestamp: new Date().toISOString(),
      },
    ]);

    setInputMessage('');
  };

  const handleAddUser = async () => {
    if (!newUserEmail) {
      alert('Please enter a user email');
      return;
    }
    try {
      await api.addUserToEnvironment(envId, newUserEmail);
      setNewUserEmail('');
      loadEnvironment();
      alert(`Added user ${newUserEmail} to environment`);
    } catch (error: any) {
      alert(`Failed to add user: ${error.message}`);
    }
  };

  const handleAddMind = async () => {
    if (!newMindGmid) {
      alert('Please enter a Mind GMID');
      return;
    }
    try {
      await api.addMindToEnvironment(envId, newMindGmid);
      setNewMindGmid('');
      loadEnvironment();
      alert(`Added Mind ${newMindGmid} to environment`);
    } catch (error: any) {
      alert(`Failed to add Mind: ${error.message}`);
    }
  };

  const handleRemoveUser = async (userEmail: string) => {
    if (!confirm(`Remove ${userEmail} from environment?`)) return;
    try {
      await api.removeUserFromEnvironment(envId, userEmail);
      loadEnvironment();
      alert(`Removed user ${userEmail}`);
    } catch (error: any) {
      alert(`Failed to remove user: ${error.message}`);
    }
  };

  const handleRemoveMind = async (mindGmid: string) => {
    if (!confirm(`Remove ${mindGmid} from environment?`)) return;
    try {
      await api.removeMindFromEnvironment(envId, mindGmid);
      loadEnvironment();
      alert(`Removed Mind ${mindGmid}`);
    } catch (error: any) {
      alert(`Failed to remove Mind: ${error.message}`);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="clean-card p-6 text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <div className="flex gap-3 justify-center">
            <button onClick={loadEnvironment} className="btn-primary">
              Retry
            </button>
            <Link href="/environments" className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition">
              Back to Environments
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!environment) {
    return null;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex-1">
          <h1 className="text-3xl font-semibold text-white">{environment.name}</h1>
          <p className="text-gray-300 mt-1">{environment.description}</p>
          
          {/* Access Info Summary */}
          <div className="flex items-center gap-4 mt-3 text-sm">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-1 rounded ${environment.is_public ? 'bg-green-500/20 text-green-300' : 'bg-orange-500/20 text-orange-300'}`}>
                {environment.is_public ? '🌍 Public' : '🔒 Private'}
              </span>
            </div>
            
            {environment.allowed_users && environment.allowed_users.length > 0 && (
              <div className="flex items-center gap-2 text-gray-300">
                <span>👤 {environment.allowed_users.length} user{environment.allowed_users.length !== 1 ? 's' : ''}</span>
              </div>
            )}
            
            {environment.allowed_minds && environment.allowed_minds.length > 0 && (
              <div className="flex items-center gap-2 text-gray-300">
                <span>🤖 {environment.allowed_minds.length} mind{environment.allowed_minds.length !== 1 ? 's' : ''}</span>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex gap-2">
          <button 
            onClick={() => setShowAccessControl(!showAccessControl)} 
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded transition"
          >
            {showAccessControl ? 'Hide' : 'Manage Access'}
          </button>
          <Link href="/environments" className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition">
            ← Back
          </Link>
        </div>
      </div>

      {/* Access Lists (Always Visible) */}
      {(!environment.is_public && (environment.allowed_users?.length > 0 || environment.allowed_minds?.length > 0)) && (
        <div className="mb-6 clean-card p-4">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Allowed Users List */}
            {environment.allowed_users && environment.allowed_users.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-2">Allowed Users ({environment.allowed_users.length})</h3>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {environment.allowed_users.map((email: string) => (
                    <div key={email} className="flex items-center gap-2 p-2 bg-slate-700/30 rounded text-sm">
                      <span className="text-blue-400">👤</span>
                      <span className="text-white">{email}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Allowed Minds List */}
            {environment.allowed_minds && environment.allowed_minds.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-2">Allowed Minds ({environment.allowed_minds.length})</h3>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {environment.allowed_minds.map((gmid: string) => (
                    <div key={gmid} className="flex items-center gap-2 p-2 bg-slate-700/30 rounded text-sm">
                      <span className="text-purple-400">🤖</span>
                      <span className="text-white font-mono">{gmid}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Access Control Panel */}
      {showAccessControl && (
        <div className="mb-6 clean-card p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Access Control</h2>
          
          <div className="grid md:grid-cols-2 gap-6">
            {/* Allowed Users */}
            <div>
              <h3 className="text-lg font-medium text-white mb-3">Allowed Users</h3>
              
              {/* Add User */}
              <div className="flex gap-2 mb-4">
                <input
                  type="email"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="input flex-1"
                />
                <button
                  onClick={handleAddUser}
                  disabled={!newUserEmail}
                  className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded transition disabled:opacity-50"
                >
                  Add
                </button>
              </div>
              
              {/* User List */}
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {environment.allowed_users && environment.allowed_users.length > 0 ? (
                  environment.allowed_users.map((email: string) => (
                    <div key={email} className="flex items-center justify-between p-2 bg-slate-700/50 rounded text-sm">
                      <span className="text-white">{email}</span>
                      <button
                        onClick={() => handleRemoveUser(email)}
                        className="text-red-400 hover:text-red-300 text-xs"
                      >
                        Remove
                      </button>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-400 text-sm italic">No users added</p>
                )}
              </div>
            </div>

            {/* Allowed Minds */}
            <div>
              <h3 className="text-lg font-medium text-white mb-3">Allowed Minds</h3>
              
              {/* Add Mind */}
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  value={newMindGmid}
                  onChange={(e) => setNewMindGmid(e.target.value)}
                  placeholder="GMD-2026-XXXX"
                  className="input flex-1"
                />
                <button
                  onClick={handleAddMind}
                  disabled={!newMindGmid}
                  className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded transition disabled:opacity-50"
                >
                  Add
                </button>
              </div>
              
              {/* Mind List */}
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {environment.allowed_minds && environment.allowed_minds.length > 0 ? (
                  environment.allowed_minds.map((gmid: string) => (
                    <div key={gmid} className="flex items-center justify-between p-2 bg-slate-700/50 rounded text-sm">
                      <span className="text-white">{gmid}</span>
                      <button
                        onClick={() => handleRemoveMind(gmid)}
                        className="text-red-400 hover:text-red-300 text-xs"
                      >
                        Remove
                      </button>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-400 text-sm italic">No minds added</p>
                )}
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded text-sm text-gray-300">
            <strong>Note:</strong> Only the environment creator can manage access. 
            If the environment is public, access control is not enforced.
          </div>
        </div>
      )}

      {!joined ? (
        /* Join Form */
        <div className="flex-1 flex items-center justify-center">
          <div className="clean-card p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold text-white mb-4">Join Environment</h2>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm text-gray-300 mb-2">Mind ID (GMID)</label>
                <input
                  type="text"
                  value={mindId}
                  onChange={(e) => setMindId(e.target.value)}
                  placeholder="GMID-12345678"
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-300 mb-2">Mind Name</label>
                <input
                  type="text"
                  value={mindName}
                  onChange={(e) => setMindName(e.target.value)}
                  placeholder="Your Mind's Name"
                  className="input w-full"
                />
              </div>
            </div>

            <button
              onClick={joinEnvironment}
              disabled={connecting || !mindId || !mindName}
              className="w-full btn-primary disabled:opacity-50"
            >
              {connecting ? 'Connecting...' : 'Join Environment'}
            </button>
          </div>
        </div>
      ) : (
        /* Chat Interface */
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 overflow-hidden">
          {/* Main Chat Area */}
          <div className="lg:col-span-3 flex flex-col clean-card overflow-hidden">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg, i) => (
                <div key={i}>
                  {msg.type === 'system' ? (
                    <div className="text-center text-gray-400 text-sm italic">
                      {msg.content}
                    </div>
                  ) : (
                    <div className={`flex ${msg.from_mind_name === mindName ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className={`max-w-xs lg:max-w-md px-3 py-2 rounded ${
                          msg.from_mind_name === mindName
                            ? 'bg-purple-600 text-white'
                            : 'bg-slate-700 text-gray-100'
                        }`}
                      >
                        <div className="font-medium text-sm mb-1">
                          {msg.from_mind_name}
                          {msg.emotion && <span className="ml-2 text-xs opacity-75">({msg.emotion})</span>}
                        </div>
                        <div className="text-sm">{msg.content}</div>
                        <div className="text-xs opacity-50 mt-1">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={sendMessage} className="p-4 border-t border-slate-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Type a message..."
                  className="input flex-1"
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim()}
                  className="btn-primary disabled:opacity-50"
                >
                  Send
                </button>
              </div>
            </form>
          </div>

          {/* Sidebar - Present Minds */}
          <div className="clean-card p-4">
            <h3 className="text-lg font-semibold text-white mb-4">
              Present ({presentMinds.length})
            </h3>

            <div className="space-y-2 mb-6">
              {presentMinds.map((mind) => (
                <div key={mind} className="flex items-center gap-2 p-2 bg-slate-700/50 rounded text-sm">
                  <span className="text-green-400">●</span>
                  <span className="text-white">{mind}</span>
                </div>
              ))}
            </div>

            <button
              onClick={leaveEnvironment}
              className="w-full px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-300 rounded transition"
            >
              Leave Environment
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
