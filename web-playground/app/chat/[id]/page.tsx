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
  timestamp: string;
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

interface Environment {
  env_id: string;
  name: string;
  env_type: string;
  description?: string;
  owner_gmid: string;
  is_public: boolean;
  max_occupancy?: number;
  current_occupancy?: number;
  created_at?: string;
}

export default function ChatPage() {
  const params = useParams();
  const mindId = params.id as string;

  const [mind, setMind] = useState<Mind | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Analyzing...');
  const [userEmail, setUserEmail] = useState<string>('');
  const [showEmailPrompt, setShowEmailPrompt] = useState(true);
  const [selectedEnvironment, setSelectedEnvironment] = useState<string | null>(null);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [showEnvironmentSelect, setShowEnvironmentSelect] = useState(false);
  const [proactiveMessages, setProactiveMessages] = useState<ProactiveMessage[]>([]);
  const [allMessages, setAllMessages] = useState<Array<{type: 'chat', data: Message} | {type: 'proactive', data: ProactiveMessage}>>([]);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [feedbackSent, setFeedbackSent] = useState<Set<number>>(new Set());

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Cycling loading messages
  useEffect(() => {
    if (!loading) return;

    const loadingMessages = [
      'Analyzing your message...',
      'Thinking deeply...',
      'Preparing response...',
      'Reasoning through context...',
      'Synthesizing information...',
      'Processing your request...'
    ];

    let currentIndex = 0;
    setLoadingText(loadingMessages[0]);

    const interval = setInterval(() => {
      currentIndex = (currentIndex + 1) % loadingMessages.length;
      setLoadingText(loadingMessages[currentIndex]);
    }, 5000); // Change message every 1.5 seconds

    return () => clearInterval(interval);
  }, [loading]);

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
  }, [allMessages]);

  // WebSocket connection for proactive messages
  useEffect(() => {
    if (mindId && userEmail) {  // Only connect after email is set
      const wsUrl = `${API_URL.replace('http', 'ws')}/api/v1/minds/${mindId}/stream?user_email=${encodeURIComponent(userEmail)}`;
      
      console.log('[WebSocket] Connecting with email:', userEmail);
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('[WebSocket] Connected successfully with email:', userEmail);
        setWebsocket(ws);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          console.log('[WebSocket] Received message:', data.type, data);
          
          // Handle proactive messages sent as regular chat messages
          if (data.type === 'message' && data.metadata?.is_proactive) {
            // This is a proactive message appearing as natural chat
            const chatMsg: Message = {
              role: 'assistant',
              content: data.content,
              timestamp: data.timestamp
            };
            setMessages(prev => [...prev, chatMsg]);
            setAllMessages(prev => [...prev, { type: 'chat', data: chatMsg }]);
            
            console.log('💬 Proactive chat message received:', data.content.substring(0, 50));
            
            // Auto-scroll to show new message
            setTimeout(() => {
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }, 100);
          }
          else if (data.type === 'proactive_message') {
            // Legacy notification-style proactive message
            const proactiveMsg: ProactiveMessage = data;
            setProactiveMessages(prev => [...prev, proactiveMsg]);
            setAllMessages(prev => [...prev, { type: 'proactive', data: proactiveMsg }]);
            
            // Auto-scroll to show new message
            setTimeout(() => {
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }, 100);
          } 
          else if (data.type === 'task_progress') {
            // Task progress update - show in UI
            console.log(`[Task ${data.task_id}] Progress: ${(data.progress * 100).toFixed(0)}% - ${data.message}`);
            
            // You can add a toast/notification here or update a progress bar
            // For now, we'll add it as a proactive message
            const taskProgressMsg = {
              type: 'proactive_message' as const,
              notification_id: data.task_id,
              mind_id: data.mind_id || mindId,
              mind_name: data.mind_name || mind?.name || 'Genesis',
              title: `⏳ Task Progress: ${(data.progress * 100).toFixed(0)}%`,
              message: data.message,
              priority: 'normal',
              timestamp: data.timestamp || new Date().toISOString(),
              metadata: { task_id: data.task_id, progress: data.progress }
            };
            setProactiveMessages(prev => [...prev, taskProgressMsg]);
            setAllMessages(prev => [...prev, { type: 'proactive', data: taskProgressMsg }]);
            
            setTimeout(() => {
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }, 100);
          }
          else if (data.type === 'task_complete') {
            // Task completed - show result
            console.log(`[Task ${data.task_id}] Completed!`, data);
            
            const taskCompleteMsg = {
              type: 'proactive_message' as const,
              notification_id: data.task_id,
              mind_id: data.mind_id || mindId,
              mind_name: data.mind_name || mind?.name || 'Genesis',
              title: '[Done]Task Completed',
              message: data.message,
              priority: 'high',
              timestamp: data.timestamp || new Date().toISOString(),
              metadata: { task_id: data.task_id, result: data.result }
            };
            setProactiveMessages(prev => [...prev, taskCompleteMsg]);
            setAllMessages(prev => [...prev, { type: 'proactive', data: taskCompleteMsg }]);
            
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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    setAttachedFiles(prev => [...prev, ...selected]);
  };

  const removeFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const sendMessage = async () => {
    if ((!input.trim() && attachedFiles.length === 0) || loading) return;

    const currentInput = input;
    const currentFiles = attachedFiles;
    setInput('');
    setAttachedFiles([]);
    setLoading(true);

    try {
      let uploadedFileInfo = [];
      
      // Upload files first if any
      if (currentFiles.length > 0) {
        const uploadPromises = currentFiles.map(file => api.uploadFile(mindId, file));
        const uploadResults = await Promise.all(uploadPromises);
        uploadedFileInfo = uploadResults.map(result => `📎 ${result.filename}`);
      }

      // Build message with file references
      const messageContent = currentInput + 
        (uploadedFileInfo.length > 0 ? `\n\n${uploadedFileInfo.join('\n')}` : '');

      const userMessage: Message = {
        role: 'user',
        content: messageContent,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, userMessage]);
      setAllMessages(prev => [...prev, { type: 'chat', data: userMessage }]);

      // Send message with context about uploaded files
      const data = await api.chatWithEnvironment(
        mindId, 
        messageContent, 
        userEmail || undefined,
        selectedEnvironment || undefined
      );

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response || data.message || 'No response',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMessage]);
      setAllMessages(prev => [...prev, { type: 'chat', data: assistantMessage }]);
    } catch (error: any) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: error.message || 'Error: Could not connect to Genesis server',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
      setAllMessages(prev => [...prev, { type: 'chat', data: errorMessage }]);
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

  const handleFeedback = async (messageIndex: number, feedbackType: 'positive' | 'negative') => {
    if (feedbackSent.has(messageIndex)) {
      return; // Already sent feedback for this message
    }

    try {
      const response = await api.submitFeedback(
        mindId,
        feedbackType,
        `Feedback on response`,
        `Message index: ${messageIndex}`
      );

      // Mark feedback as sent
      setFeedbackSent(prev => new Set(prev).add(messageIndex));

      // Show notification
      if (response.success) {
        // Refresh mind data to get updated gen balance
        fetchMind();
        
        // Optional: Show toast notification
        console.log(`Feedback sent! ${response.message}`);
      }
    } catch (error) {
      console.error('Error sending feedback:', error);
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
        <div className="h-full overflow-y-auto p-6 space-y-4 messages-container">
          {allMessages.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-lg mb-2">👋 Start a conversation with {mind.name}</p>
              <p className="text-sm">I'll be proactive, thoughtful, and spontaneously engage with you</p>
            </div>
          )}

          {/* Render all messages in chronological order */}
          {allMessages.map((item, index) => {
              if (item.type === 'chat') {
                const message = item.data;
                const timestamp = new Date(message.timestamp).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                });
                
                return (
                  <div key={`chat-${index}`} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}>
                    <div className="message-group">
                      <div className={`message-bubble ${message.role === 'user' ? 'message-user' : 'message-assistant'}`}>
                        {message.role === 'assistant' ? (
                          <MarkdownRenderer content={message.content} />
                        ) : (
                          <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                        )}
                        <div className="message-timestamp">
                          <span>{timestamp}</span>
                          {message.role === 'user' && (
                            <span className="read-receipt">
                              <svg className="checkmark" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
                              </svg>
                            </span>
                          )}
                        </div>
                      </div>
                      {/* Feedback buttons for assistant messages */}
                      {message.role === 'assistant' && !feedbackSent.has(index) && (
                        <div className="flex gap-2 mt-2 ml-2">
                          <button
                            onClick={() => handleFeedback(index, 'positive')}
                            className="text-xs bg-green-600/20 hover:bg-green-600/40 text-green-300 px-3 py-1 rounded border border-green-600/30 transition-colors"
                            title="Good response (+5 gens)"
                          >
                            👍 Good
                          </button>
                          <button
                            onClick={() => handleFeedback(index, 'negative')}
                            className="text-xs bg-red-600/20 hover:bg-red-600/40 text-red-300 px-3 py-1 rounded border border-red-600/30 transition-colors"
                            title="Bad response (-5 gens)"
                          >
                            👎 Bad
                          </button>
                        </div>
                      )}
                      {message.role === 'assistant' && feedbackSent.has(index) && (
                        <div className="text-xs text-gray-500 mt-2 ml-2">
                          ✓ Feedback sent
                        </div>
                      )}
                    </div>
                  </div>
                );
              } else {
                const proactiveMsg = item.data;
                const timestamp = new Date(proactiveMsg.timestamp).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                });
                const isSpontaneous = proactiveMsg.metadata?.spontaneous || false;
                
                return (
                  <div key={`proactive-${index}`} className="flex justify-start animate-fade-in-up">
                    <div className="message-group">
                      {/* Proactive message badge */}
                      <div className="proactive-badge">
                        <div className="proactive-badge-dot"></div>
                        <span>
                          {isSpontaneous ? '💭 Thought' : proactiveMsg.title || '💚 Checking in'}
                        </span>
                        <span className="text-gray-400 ml-1">{timestamp}</span>
                      </div>
                      {/* Message bubble */}
                      <div className="message-bubble message-proactive">
                        <div className="text-sm whitespace-pre-wrap">
                          {proactiveMsg.message}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              }
            })}

          {loading && (
            <div className="flex justify-start animate-fade-in-up">
              <div className="typing-indicator">
                <div className="typing-indicator-dots">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
                <span className="text-sm text-gray-300 ml-3 animate-pulse">
                  {loadingText}
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="chat-input-container space-y-2">
        {/* File Attachments Preview */}
        {attachedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 p-2 bg-slate-800 rounded border border-slate-700">
            {attachedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-2 bg-slate-700 px-3 py-1 rounded text-sm"
              >
                <span className="text-gray-300">📎 {file.name}</span>
                <button
                  onClick={() => removeFile(index)}
                  className="text-red-400 hover:text-red-300"
                  title="Remove file"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Input Area */}
        <div className="flex gap-3 items-end">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            multiple
            className="hidden"
            accept="*/*"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-3 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-full transition flex-shrink-0"
            title="Attach files"
          >
            📎
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message..."
            className="chat-input flex-1"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={(!input.trim() && attachedFiles.length === 0) || loading}
            className="send-button flex-shrink-0"
            title="Send message"
          >
            {loading ? '⏳' : '➤'}
          </button>
        </div>
      </div>
      </div>
    </AuthRequired>
  );
}
