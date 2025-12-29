// Genesis Playground - Clean Chat Interface
'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthRequired from '@/components/AuthRequired';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { api } from '@/lib/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Mind {
  gmid: string;
  name: string;
  model: string;
  memory_count: number;
}

interface ProactiveMessage {
  type: 'proactive_message';
  notification_id: string;
  mind_id: string;
  mind_name: string;
  title: string;
  message: string;
  priority: string;
  timestamp: string;
  metadata: any;
}

export default function ChatPage() {
  const params = useParams();
  const mindId = params.id as string;

  const [mind, setMind] = useState<Mind | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [userEmail, setUserEmail] = useState<string>('');
  const [showEmailPrompt, setShowEmailPrompt] = useState(true);
  const [selectedEnvironment, setSelectedEnvironment] = useState<string | null>(null);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [showEnvironmentSelect, setShowEnvironmentSelect] = useState(false);
  const [proactiveMessages, setProactiveMessages] = useState<ProactiveMessage[]>([]);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchMind();
    // Check if user email is stored in localStorage
    const storedEmail = localStorage.getItem('genesis_user_email');
    if (storedEmail) {
      setUserEmail(storedEmail);
      setShowEmailPrompt(false);
    }
  }, [mindId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, proactiveMessages]);

  // WebSocket connection for proactive messages
  useEffect(() => {
    if (mindId) {
      // Use userEmail if set, otherwise use default
      const wsUserEmail = userEmail || 'web_user@genesis.local';
      const wsUrl = `${API_URL.replace('http', 'ws')}/api/v1/minds/${mindId}/stream?user_email=${encodeURIComponent(wsUserEmail)}`;
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('WebSocket connected for proactive messages with email:', wsUserEmail);
        setWebsocket(ws);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'proactive_message') {
            const proactiveMsg: ProactiveMessage = data;
            setProactiveMessages(prev => [...prev, proactiveMsg]);
            
            // Auto-scroll to show new message
            setTimeout(() => {
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }, 100);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWebsocket(null);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      return () => {
        ws.close();
      };
    }
  }, [mindId, userEmail, API_URL]);

  const fetchMind = async () => {
    try {
      const data = await api.getMind(mindId);
      setMind(data);
    } catch (error) {
      console.error('Error fetching mind:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setLoading(true);

    try {
      // Pass user email and environment_id to the API
      const data = await api.chatWithEnvironment(
        mindId, 
        currentInput, 
        userEmail || undefined,
        selectedEnvironment || undefined
      );

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response || data.message || 'No response'
      }]);
    } catch (error: any) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: error.message || 'Error: Could not connect to Genesis server'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleEmailSubmit = async () => {
    if (userEmail.trim()) {
      localStorage.setItem('genesis_user_email', userEmail.trim());
      setShowEmailPrompt(false);
      // Load accessible environments after email is set
      await loadAccessibleEnvironments();
    } else {
      // Allow skipping email - use default
      const defaultEmail = 'web_user@genesis.local';
      setUserEmail(defaultEmail);
      localStorage.setItem('genesis_user_email', defaultEmail);
      setShowEmailPrompt(false);
    }
  };

  const loadAccessibleEnvironments = async () => {
    if (!userEmail || !mind) return;
    
    try {
      const data = await api.getAccessibleEnvironments(userEmail, mind.gmid);
      setEnvironments(data.environments || []);
      
      // If only one environment (likely Mind's home), auto-select it
      if (data.environments && data.environments.length === 1) {
        setSelectedEnvironment(data.environments[0].env_id);
      }
    } catch (error) {
      console.error('Error loading environments:', error);
    }
  };

  const toggleEnvironmentSelect = () => {
    if (!showEnvironmentSelect && environments.length === 0) {
      loadAccessibleEnvironments();
    }
    setShowEnvironmentSelect(!showEnvironmentSelect);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!mind) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="spinner"></div>
          <span className="ml-2 text-gray-300">Loading mind...</span>
        </div>
      </div>
    );
  }

  // Show email prompt before chat
  if (showEmailPrompt) {
    return (
      <AuthRequired>
        <div className="max-w-md mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-8">
            <h2 className="text-2xl font-semibold text-white mb-4">
              👋 Introduce Yourself
            </h2>
            <p className="text-gray-300 mb-6">
              Help <span className="font-semibold text-purple-400">{mind.name}</span> remember you better by providing your email or name.
              This allows the Mind to recall your previous conversations.
            </p>
            <div className="space-y-4">
              <input
                type="text"
                value={userEmail}
                onChange={(e) => setUserEmail(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleEmailSubmit()}
                placeholder="your.email@example.com or Your Name"
                className="input w-full"
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  onClick={handleEmailSubmit}
                  className="btn-primary flex-1"
                >
                  {userEmail.trim() ? 'Start Chatting' : 'Skip (Anonymous)'}
                </button>
              </div>
              <p className="text-xs text-gray-400">
                Your identifier is stored locally and helps the Mind maintain context across sessions.
              </p>
            </div>
          </div>
        </div>
      </AuthRequired>
    );
  }

  return (
    <AuthRequired>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6 pb-4 border-b border-slate-700">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Link href="/" className="text-gray-300 hover:text-white">
                  ← Back
                </Link>
              </div>
              <h1 className="text-2xl font-semibold text-white">{mind.name}</h1>
              <p className="text-sm text-gray-300">
                {mind.model} • {mind.memory_count} memories
                {userEmail && <span className="ml-2">• 👤 {userEmail}</span>}
              </p>
            </div>
            {userEmail && (
              <button
                onClick={() => {
                  localStorage.removeItem('genesis_user_email');
                  setUserEmail('');
                  setShowEmailPrompt(true);
                  setEnvironments([]);
                  setSelectedEnvironment(null);
                }}
                className="text-xs text-gray-400 hover:text-white"
              >
                Change Identity
              </button>
            )}
          </div>

          {/* Environment Selection */}
          {userEmail && (
            <div className="mt-3">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-400">Environment:</label>
                <button
                  onClick={toggleEnvironmentSelect}
                  className="text-sm bg-slate-700 hover:bg-slate-600 text-white px-3 py-1 rounded border border-slate-600 flex items-center gap-2"
                >
                  {selectedEnvironment 
                    ? environments.find(e => e.env_id === selectedEnvironment)?.name || 'Select Environment'
                    : 'Select Environment'}
                  <span className="text-xs">{showEnvironmentSelect ? '▲' : '▼'}</span>
                </button>
              </div>

              {showEnvironmentSelect && (
                <div className="mt-2 bg-slate-700 border border-slate-600 rounded max-h-60 overflow-y-auto">
                  {environments.length === 0 ? (
                    <div className="p-3 text-sm text-gray-400">
                      No accessible environments. The Mind's home environment will be used.
                    </div>
                  ) : (
                    <>
                      <div
                        className={`p-3 text-sm cursor-pointer hover:bg-slate-600 ${!selectedEnvironment ? 'bg-slate-600 text-white' : 'text-gray-300'}`}
                        onClick={() => {
                          setSelectedEnvironment(null);
                          setShowEnvironmentSelect(false);
                        }}
                      >
                        <div className="font-medium">No Environment</div>
                        <div className="text-xs text-gray-400">Default mind context</div>
                      </div>
                      {environments.map((env) => (
                        <div
                          key={env.env_id}
                          className={`p-3 text-sm cursor-pointer hover:bg-slate-600 border-t border-slate-600 ${selectedEnvironment === env.env_id ? 'bg-slate-600 text-white' : 'text-gray-300'}`}
                          onClick={() => {
                            setSelectedEnvironment(env.env_id);
                            setShowEnvironmentSelect(false);
                          }}
                        >
                          <div className="flex items-center justify-between">
                            <div className="font-medium">{env.name}</div>
                            <div className="text-xs">
                              {env.is_public ? '🌐 Public' : '🔒 Private'}
                            </div>
                          </div>
                          <div className="text-xs text-gray-400 mt-1">
                            {env.env_type} • {env.owner_gmid === mind?.gmid ? 'Owned' : 'Guest'}
                          </div>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}

              {selectedEnvironment && (
                <div className="mt-2 text-xs text-purple-400">
                  💬 Chatting in: {environments.find(e => e.env_id === selectedEnvironment)?.name}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Messages */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg mb-4" style={{ height: 'calc(100vh - 320px)' }}>
        <div className="h-full overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && proactiveMessages.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <p>Start a conversation with {mind.name}</p>
              <p className="text-sm mt-2">Proactive thoughts and consciousness activity will appear here</p>
            </div>
          )}

          {/* Render all messages and proactive notifications in chronological order */}
          {[...messages.map((msg, index) => ({ ...msg, index, type: 'chat' as const })),
             ...proactiveMessages.map((msg, index) => ({ ...msg, index, type: 'proactive' as const }))]
            .sort((a, b) => {
              // Sort by timestamp if available, otherwise by index
              if (a.type === 'proactive' && b.type === 'proactive') {
                return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
              } else if (a.type === 'proactive') {
                return 1; // Proactive messages after chat messages for now
              } else if (b.type === 'proactive') {
                return -1;
              }
              return (a as any).index - (b as any).index;
            })
            .map((item) => {
              if (item.type === 'chat') {
                const message = item as Message & { index: number };
                return (
                  <div key={`chat-${message.index}`} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-lg px-4 py-3 ${
                      message.role === 'user' 
                        ? 'bg-purple-600 text-white' 
                        : 'bg-slate-700 text-gray-100'
                    }`}>
                      {message.role === 'assistant' ? (
                        <MarkdownRenderer content={message.content} />
                      ) : (
                        <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                      )}
                    </div>
                  </div>
                );
              } else {
                const proactiveMsg = item as unknown as ProactiveMessage & { index: number };
                return (
                  <div key={`proactive-${proactiveMsg.index}`} className="flex justify-center">
                    <div className="max-w-[90%] bg-blue-900/50 border border-blue-700 rounded-lg px-4 py-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-blue-400 font-medium text-sm">{proactiveMsg.title}</span>
                        <span className="text-xs text-gray-400">
                          {new Date(proactiveMsg.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="text-sm text-gray-200 whitespace-pre-wrap">
                        {proactiveMsg.message}
                      </div>
                      {proactiveMsg.metadata?.type && (
                        <div className="mt-2 text-xs text-gray-400">
                          Type: {proactiveMsg.metadata.type}
                        </div>
                      )}
                    </div>
                  </div>
                );
              }
            })}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-700 rounded-lg px-4 py-3">
                <div className="spinner"></div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Send a message..."
          className="input flex-1"
          disabled={loading}
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim() || loading}
          className="btn-primary"
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
      </div>
    </AuthRequired>
  );
}
