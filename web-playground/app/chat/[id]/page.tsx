// Genesis Playground - Clean Chat Interface
'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthRequired from '@/components/AuthRequired';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { api } from '@/lib/api';
import { getFirebaseToken } from '@/lib/firebase';

interface Message {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: any;  // For artifacts and other metadata
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

interface ConversationThread {
  user_email: string;
  environment_id: string | null;
  environment_name: string;
  environment_type: string;
  last_message_time: string;
  message_count: number;
  last_message_preview: string;
  last_message_role: string;
}

// Helper function to detect if user wants to generate an image
const detectImageGenerationRequest = (message: string): string | null => {
  const lowerMessage = message.toLowerCase();
  const imageKeywords = [
    'generate image',
    'create image',
    'generate picture',
    'create picture',
    'generate a picture',
    'create a picture',
    'generate an image',
    'create an image',
    'make an image',
    'make a picture',
    'draw an image',
    'draw a picture',
    'show me an image',
    'show me a picture'
  ];
  
  for (const keyword of imageKeywords) {
    if (lowerMessage.includes(keyword)) {
      // Extract the prompt after the keyword
      const parts = message.split(new RegExp(keyword, 'i'));
      if (parts.length > 1) {
        const prompt = parts[1].trim().replace(/^(of |for |:)/i, '').trim();
        return prompt || null;
      }
    }
  }
  
  return null;
};

// Generate Pollinations AI image URL
const generatePollinationsImageUrl = (prompt: string): string => {
  const encodedPrompt = encodeURIComponent(prompt);
  return `https://image.pollinations.ai/prompt/${encodedPrompt}?nologo=true`;
};

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
  const [conversationThreads, setConversationThreads] = useState<ConversationThread[]>([]);
  const [showEnvironmentSelect, setShowEnvironmentSelect] = useState(false);
  const [proactiveMessages, setProactiveMessages] = useState<ProactiveMessage[]>([]);
  const [allMessages, setAllMessages] = useState<Array<{type: 'chat', data: Message} | {type: 'proactive', data: ProactiveMessage}>>([]);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [feedbackSent, setFeedbackSent] = useState<Set<number>>(new Set());
  const [frontendHandledImage, setFrontendHandledImage] = useState(false);

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
    console.log('🔄 Initial page load effect triggered for mind:', mindId);
    fetchMind();
    // Check if user email is stored in localStorage
    const storedEmail = localStorage.getItem('genesis_user_email');
    console.log('📧 Stored email from localStorage:', storedEmail);
    if (storedEmail) {
      setUserEmail(storedEmail);
      setShowEmailPrompt(false);
      // Load conversation immediately when email is available from localStorage
      // This ensures conversations load on direct URL access or page refresh
      console.log('🚀 Initiating conversation load...');
      loadConversationMessages(null, storedEmail);
      fetchConversationThreads(storedEmail);
    } else {
      console.log('⚠️ No stored email found, showing email prompt');
    }
  }, [mindId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    // Use setTimeout to ensure DOM is fully updated (including images/markdown)
    const timer = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, 200);
    return () => clearTimeout(timer);
  }, [allMessages]);

  // WebSocket connection for proactive messages
  useEffect(() => {
    if (mindId && userEmail) {  // Only connect after email is set
      const wsUrl = `${API_URL.replace('http', 'ws')}/api/v1/minds/${mindId}/stream?user_email=${encodeURIComponent(userEmail)}`;
      
      console.log('[WebSocket] Connecting with email:', userEmail);
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('[WebSocket] ✅ Connected successfully');
        console.log('[WebSocket] User:', userEmail);
        console.log('[WebSocket] Mind:', mindId);
        console.log('[WebSocket] URL:', wsUrl);
        setWebsocket(ws);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          console.log('[WebSocket] Received message:', data.type, data);
          
          // Handle proactive messages sent as regular chat messages
          if (data.type === 'message' && data.metadata?.is_proactive) {
            // Skip if this looks like an image generation task response (frontend already handled it)
            const lowerContent = data.content.toLowerCase();
            const isImageTask = lowerContent.includes('image') && 
                               (lowerContent.includes('pollinations') || 
                                lowerContent.includes('create') || 
                                lowerContent.includes('generate'));
            
            if (isImageTask) {
              console.log('🚫 Suppressing backend image generation response (frontend handled)');
              return;
            }
            
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
            // Skip if this is an image generation task (frontend handles those)
            const lowerMessage = data.message?.toLowerCase() || '';
            const isImageTask = lowerMessage.includes('image') && 
                               (lowerMessage.includes('generate') || 
                                lowerMessage.includes('create') || 
                                lowerMessage.includes('pollinations'));
            
            if (isImageTask) {
              console.log('🚫 Suppressing image generation task progress');
              return;
            }
            
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
            // Skip if this is an image generation task (frontend handles those)
            const lowerMessage = data.message?.toLowerCase() || '';
            const isImageTask = lowerMessage.includes('image') && 
                               (lowerMessage.includes('generate') || 
                                lowerMessage.includes('create') || 
                                lowerMessage.includes('pollinations'));
            
            if (isImageTask) {
              console.log('🚫 Suppressing image generation task completion');
              return;
            }
            
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
              metadata: { 
                task_id: data.task_id, 
                result: data.result,
                artifacts: data.artifacts || []
              }
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
        console.error('[WebSocket] ❌ Connection error:', error);
        console.error('[WebSocket] URL:', wsUrl);
        console.error('[WebSocket] This may be due to CORS, auth, or network issues');
        console.error('[WebSocket] Check if backend WebSocket endpoint is accessible');
      };
      
      return () => {
        ws.close();
      };
    }
  }, [mindId, userEmail, API_URL]);

  const fetchMind = async () => {
    try {
      // Wait for auth token to be available
      const token = await getFirebaseToken();
      if (!token) {
        console.warn('No auth token available yet, retrying...');
        // Retry after a short delay
        setTimeout(fetchMind, 500);
        return;
      }
      const data = await api.getMind(mindId);
      setMind(data);
    } catch (error) {
      console.error('Error fetching mind:', error);
    }
  };

  const fetchConversationThreads = async (emailOverride?: string) => {
    const email = emailOverride || userEmail;
    if (!email) return;
    
    try {
      const token = await getFirebaseToken();
      if (!token) {
        console.warn('No auth token available yet for fetching threads, retrying...');
        // Retry after a short delay
        setTimeout(() => fetchConversationThreads(emailOverride), 500);
        return;
      }
      
      console.log('🔄 Fetching conversation threads for:', email);
      
      const response = await fetch(
        `${API_URL}/api/v1/minds/${mindId}/conversations?user_email=${encodeURIComponent(email)}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        setConversationThreads(data.threads || []);
        console.log('✅ Loaded conversation threads:', data.threads?.length || 0);
      } else {
        console.error('Failed to load threads:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Error fetching conversation threads:', error);
    }
  };

  const loadConversationMessages = async (envId: string | null, emailOverride?: string) => {
    const email = emailOverride || userEmail;
    if (!email) return;
    setLoading(true);
    setLoadingMore(false);

    try {
      const params = new URLSearchParams({
        user_email: email,
        limit: '50'
      });

      if (envId) {
        params.append('environment_id', envId);
      }

      const token = await getFirebaseToken();
      if (!token) {
        console.warn('No auth token available yet for loading messages, retrying...');
        setLoading(false);
        // Retry after a short delay
        setTimeout(() => loadConversationMessages(envId, emailOverride), 500);
        return;
      }

      console.log('🔄 Loading conversation messages for:', email, 'env:', envId);
      
      const response = await fetch(
        `${API_URL}/api/v1/minds/${mindId}/conversations/messages?${params}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();

        console.log('📥 Loaded messages from API:', data.messages?.length || 0);
        console.log('📥 Message roles:', data.messages?.map((m: any) => m.role));

        // Convert messages to the format we need (keep id, metadata for pagination and artifacts)
        const chatMessages: Message[] = data.messages
          .filter((msg: any) => msg.role !== 'system')
          .map((msg: any) => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            metadata: msg.metadata  // Include metadata for artifacts and other data
          }));

        console.log('✅ Filtered chat messages:', chatMessages.length);
        console.log('✅ Filtered roles:', chatMessages.map(m => m.role));
        console.log('📦 Messages with artifacts:', chatMessages.filter(m => m.metadata?.artifacts?.length > 0).length);

        setMessages(chatMessages);

        // Convert to allMessages format
        const formattedMessages = chatMessages.map((msg: Message) => ({
          type: 'chat' as const,
          data: msg
        }));

        setAllMessages(formattedMessages);

        // Pagination metadata
        setHasMore(Boolean(data.has_more));

        // Scroll to bottom after messages load
        setTimeout(() => {
          messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 3000);
      } else {
        console.error('Failed to load messages:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Error loading conversation messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadEarlierMessages = async () => {
    if (!userEmail || loadingMore || !hasMore) return;
    if (!messages || messages.length === 0) return;

    setLoadingMore(true);

    try {
      const earliest = messages[0];
      if (!earliest.id) {
        setLoadingMore(false);
        return;
      }

      const oldScrollTop = messagesContainerRef.current?.scrollTop ?? 0;
      const oldScrollHeight = messagesContainerRef.current?.scrollHeight ?? 0;

      const params = new URLSearchParams({
        user_email: userEmail,
        limit: '50',
        before_id: String(earliest.id)
      });

      if (selectedEnvironment) {
        params.append('environment_id', selectedEnvironment);
      }

      const token = await getFirebaseToken();
      if (!token) {
        console.error('No authentication token available');
        setLoadingMore(false);
        return;
      }

      const response = await fetch(
        `${API_URL}/api/v1/minds/${mindId}/conversations/messages?${params}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        const olderMsgs: Message[] = data.messages
          .filter((msg: any) => msg.role !== 'system')
          .map((msg: any) => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            metadata: msg.metadata  // Include metadata for artifacts
          }));

        if (olderMsgs.length > 0) {
          setMessages(prev => [...olderMsgs, ...prev]);
          setAllMessages(prev => [...olderMsgs.map(m => ({ type: 'chat' as const, data: m })), ...prev]);

          // Adjust scroll to keep view stable
          setTimeout(() => {
            const newScrollHeight = messagesContainerRef.current?.scrollHeight ?? 0;
            const delta = newScrollHeight - oldScrollHeight;
            messagesContainerRef.current && (messagesContainerRef.current.scrollTop = oldScrollTop + delta + 10);
          }, 50);
        }

        setHasMore(Boolean(data.has_more));
      }
    } catch (error) {
      console.error('Error loading earlier messages:', error);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleThreadSelect = (thread: ConversationThread) => {
    setSelectedEnvironment(thread.environment_id);
    loadConversationMessages(thread.environment_id);
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
      // Build user message with file attachments immediately
      let messageContent = currentInput;
      if (currentFiles.length > 0) {
        const fileList = currentFiles.map(f => `📎 ${f.name}`).join('\n');
        messageContent = messageContent ? `${messageContent}\n\n${fileList}` : fileList;
      }

      // Show user message immediately in chat
      const userMessage: Message = {
        role: 'user',
        content: messageContent,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, userMessage]);
      setAllMessages(prev => [...prev, { type: 'chat', data: userMessage }]);

      let uploadedFileInfo = [];
      
      // Upload files first if any
      if (currentFiles.length > 0) {
        const uploadPromises = currentFiles.map(file => api.uploadFile(mindId, file, userEmail));
        const uploadResults = await Promise.all(uploadPromises);
        uploadedFileInfo = uploadResults.map(result => {
          // Include file summary if available
          if (result.summary) {
            return `\n📎 File: ${result.filename}\nSummary: ${result.summary}`;
          }
          return `\n📎 File uploaded: ${result.filename}`;
        });
      }

      // Build final message content for backend (includes file upload info)
      const backendMessageContent = currentInput + 
        (uploadedFileInfo.length > 0 ? `\n\n${uploadedFileInfo.join('\n')}` : '');

      // Check if this is an image generation request
      const imagePrompt = detectImageGenerationRequest(currentInput);
      
      if (imagePrompt) {
        // For image generation, handle it entirely on frontend (no backend call needed)
        const imageUrl = generatePollinationsImageUrl(imagePrompt);
        
        const assistantMessage: Message = {
          role: 'assistant',
          content: `I've generated an image for: "${imagePrompt}"`,
          timestamp: new Date().toISOString(),
          metadata: {
            image_url: imageUrl,
            image_prompt: imagePrompt,
            is_generated_image: true
          }
        };
        
        setMessages(prev => [...prev, assistantMessage]);
        setAllMessages(prev => [...prev, { type: 'chat', data: assistantMessage }]);
      } else {
        // Send message with context about uploaded files to backend
        const data = await api.chatWithEnvironment(
          mindId, 
          backendMessageContent,  // Use message content with file info
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
      }
      
      // Refresh conversation threads after sending message
      fetchConversationThreads();
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
      <div className="flex h-screen bg-slate-900" style={{height: '75vh'}}>
        {/* Sidebar */}
        <div className="w-80 bg-slate-800 border-r border-slate-700 flex flex-col">
          {/* Sidebar Header */}
          <div className="p-4 border-b border-slate-700 flex-shrink-0">
            <div className="flex items-center justify-between mb-2">
              <Link href="/" className="text-gray-400 hover:text-white text-sm">
                ← Back
              </Link>
              <button
                onClick={() => {
                  localStorage.removeItem('genesis_user_email');
                  setUserEmail('');
                  setShowEmailPrompt(true);
                }}
                className="text-xs text-gray-400 hover:text-white"
                title="Change Identity"
              >
                🔄
              </button>
            </div>
            <h2 className="text-lg font-semibold text-white">{mind.name}</h2>
            <p className="text-xs text-gray-400">{userEmail}</p>
          </div>

          {/* Conversation Threads */}
          <div className="flex-1 overflow-y-auto min-h-0">
            <div className="p-2">
              <div className="text-xs text-gray-500 px-2 py-2 font-medium">
                CONVERSATIONS
              </div>
              
              {conversationThreads.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-500 text-sm">
                  <p>No conversations yet</p>
                  <p className="text-xs mt-1">Start chatting to create threads</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {conversationThreads.map((thread, idx) => {
                    const isSelected = thread.environment_id === selectedEnvironment;
                    const timeAgo = new Date(thread.last_message_time).toLocaleString();
                    
                    // Environment icon
                    let envIcon = '💬';
                    if (thread.environment_type === 'direct') envIcon = '💬';
                    else if (thread.environment_type === 'workspace') envIcon = '💼';
                    else if (thread.environment_type === 'social') envIcon = '🌐';
                    else if (thread.environment_type === 'metaverse') envIcon = '🎮';
                    
                    return (
                      <button
                        key={idx}
                        onClick={() => handleThreadSelect(thread)}
                        className={`w-full text-left px-3 py-3 rounded-lg transition-all ${
                          isSelected
                            ? 'bg-blue-600/20 border border-blue-500/50'
                            : 'hover:bg-slate-700/50'
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <span className="text-xl flex-shrink-0">{envIcon}</span>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-white text-sm truncate">
                              {thread.environment_name}
                            </div>
                            <div className="text-xs text-gray-400 truncate mt-0.5">
                              {thread.last_message_preview}
                            </div>
                            <div className="flex items-center justify-between mt-1">
                              <span className="text-xs text-gray-500">
                                {new Date(thread.last_message_time).toLocaleDateString()}
                              </span>
                              <span className="text-xs text-gray-600">
                                {thread.message_count} msgs
                              </span>
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* New Conversation Button */}
          <div className="p-4 border-t border-slate-700 flex-shrink-0">
            <button
              onClick={() => {
                setSelectedEnvironment(null);
                setMessages([]);
                setAllMessages([]);
              }}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition"
            >
              ➕ New Conversation
            </button>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Chat Header */}
          <div className="px-6 py-4 border-b border-slate-700 bg-slate-800 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-semibold text-white">
                  {selectedEnvironment
                    ? conversationThreads.find(t => t.environment_id === selectedEnvironment)?.environment_name || 'Chat'
                    : 'New Conversation'}
                </h1>
                <p className="text-sm text-gray-400 mt-0.5">
                  {mind.model} • {mind.memory_count} total memories stored
                </p>
              </div>
            </div>
          </div>

          {/* Messages Area - this container handles infinite scroll upwards */}
          <div
            ref={messagesContainerRef}
            onScroll={(e) => {
              const target = e.currentTarget as HTMLDivElement;
              if (target.scrollTop < 120 && hasMore && !loadingMore && !loading) {
                loadEarlierMessages();
              }
            }}
            className="flex-1 overflow-y-auto p-6 space-y-4 messages-container bg-slate-900"
          >
            {loadingMore && (
              <div className="text-center py-2 text-sm text-gray-400">Loading earlier messages...</div>
            )}

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
                        
                        {/* Display generated image with download button */}
                        {message.role === 'assistant' && message.metadata?.is_generated_image && message.metadata?.image_url && (
                          <div className="mt-4 pt-4 border-t border-slate-700/50">
                            <div className="text-xs text-gray-400 mb-3">🎨 Generated Image:</div>
                            <div className="space-y-3">
                              <img 
                                src={message.metadata.image_url} 
                                alt={message.metadata.image_prompt || 'Generated image'}
                                className="rounded-lg w-full max-w-md border border-slate-600"
                                loading="lazy"
                              />
                              <a
                                href={message.metadata.image_url}
                                download={`generated-${message.metadata.image_prompt?.substring(0, 30).replace(/[^a-z0-9]/gi, '-') || 'image'}.png`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                              >
                                <span>⬇️</span>
                                <span>Download Image</span>
                              </a>
                            </div>
                          </div>
                        )}
                        
                        {/* Download buttons for artifacts (from task completion) */}
                        {message.role === 'assistant' && message.metadata?.artifacts && message.metadata.artifacts.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-slate-700/50">
                            <div className="text-xs text-gray-400 mb-2">📎 Attachments:</div>
                            <div className="flex flex-col gap-2">
                              {message.metadata.artifacts.map((artifact: any, idx: number) => {
                                const artifactName = artifact.filename || artifact.name || `artifact-${idx}`;
                                const artifactType = artifact.type || 'file';
                                const downloadUrl = `${API_URL}/api/v1/minds/${mindId}/artifacts/download?filename=${encodeURIComponent(artifactName)}`;
                                
                                return (
                                  <a
                                    key={idx}
                                    href={downloadUrl}
                                    download={artifactName}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 rounded-lg text-sm text-blue-300 transition-colors"
                                  >
                                    <span>📥</span>
                                    <span className="font-medium">{artifactName}</span>
                                    <span className="text-xs text-gray-400">({artifactType})</span>
                                  </a>
                                );
                              })}
                            </div>
                          </div>
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
                const artifacts = proactiveMsg.metadata?.artifacts || [];
                
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
                        
                        {/* Download buttons for artifacts */}
                        {artifacts.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-gray-700">
                            <div className="text-xs text-gray-400 mb-2">📥 Download Files:</div>
                            <div className="space-y-2">
                              {artifacts.map((artifact: any, idx: number) => {
                                const artifactName = artifact.name || artifact.filename || 'file';
                                const ext = artifactName.split('.').pop()?.toLowerCase() || '';
                                
                                // Determine icon based on extension
                                let icon = '📄';
                                if (['pptx', 'ppt'].includes(ext)) icon = '📊';
                                else if (['docx', 'doc'].includes(ext)) icon = '📝';
                                else if (['xlsx', 'xls', 'csv'].includes(ext)) icon = '📈';
                                else if (ext === 'pdf') icon = '📕';
                                else if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) icon = '🖼️';
                                else if (['py', 'js', 'ts', 'java', 'cpp', 'c', 'html', 'css'].includes(ext)) icon = '💻';
                                
                                // Use environment variable API URL (works with VPS + Vercel)
                                const apiUrl = process.env.NEXT_PUBLIC_API_URL || API_URL;
                                const downloadUrl = `${apiUrl}/api/v1/minds/${mindId}/artifacts/download?filename=${encodeURIComponent(artifactName)}`;
                                
                                return (
                                  <a
                                    key={idx}
                                    href={downloadUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    download={artifactName}
                                    className="flex items-center justify-between p-2 bg-slate-700/50 hover:bg-slate-700 rounded border border-slate-600 hover:border-blue-500 transition-all group"
                                  >
                                    <div className="flex items-center gap-2">
                                      <span className="text-xl">{icon}</span>
                                      <span className="text-sm text-gray-300 group-hover:text-white">
                                        {artifactName}
                                      </span>
                                    </div>
                                    <button className="text-blue-400 hover:text-blue-300 text-sm px-2 py-1 rounded hover:bg-blue-500/10 transition">
                                      ⬇️ Download
                                    </button>
                                  </a>
                                );
                              })}
                            </div>
                          </div>
                        )}
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

          {/* Input Area */}
          <div className="p-4 border-t border-slate-700 bg-slate-800 flex-shrink-0">
            {/* File Attachments Preview */}
            {attachedFiles.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
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

            {/* Input Controls */}
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
      </div>
    </AuthRequired>
  );
}
