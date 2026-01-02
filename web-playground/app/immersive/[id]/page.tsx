'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthRequired from '@/components/AuthRequired';
import { api } from '@/lib/api';
import { VoiceInput, VoiceOutput, WebcamCapture, UserContext } from '@/lib/multimodal';
import MindAvatar from '@/components/MindAvatar';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  emotion?: string;
  timestamp?: string;
  voice?: boolean;
  image_url?: string;
  user_context?: UserContext;
}

export default function ImmersiveChatPage() {
  const params = useParams();
  const mindId = params.id as string;

  const [mind, setMind] = useState<any>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Multimodal states
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [videoEnabled, setVideoEnabled] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState<any>(null);
  const [mindAvatarUrl, setMindAvatarUrl] = useState<string>('');
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const voiceInputRef = useRef<VoiceInput | null>(null);
  const voiceOutputRef = useRef<VoiceOutput | null>(null);
  const webcamRef = useRef<WebcamCapture | null>(null);
  const emotionIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchMind();
    voiceInputRef.current = new VoiceInput();
    voiceOutputRef.current = new VoiceOutput();
    webcamRef.current = new WebcamCapture();

    return () => {
      stopVideo();
      voiceOutputRef.current?.stop();
    };
  }, [mindId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (voiceEnabled && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'assistant' && !isSpeaking) {
        speakMessage(lastMessage.content);
      }
    }
  }, [messages, voiceEnabled]);

  const fetchMind = async () => {
    try {
      const data = await api.getMind(mindId);
      setMind(data);
      
      // Load persisted avatar or generate new one
      if (data.avatar_url) {
        setMindAvatarUrl(data.avatar_url);
      } else {
        await generateAvatar('neutral');
      }
    } catch (error) {
      console.error('Error fetching mind:', error);
    }
  };

  const generateAvatar = async (expression: string = 'neutral') => {
    try {
      // Call Pollinations.AI directly from frontend for instant, seamless avatar generation
      const mindNameHash = mind?.name ? Math.abs(mind.name.split('').reduce((a: number, b: string) => ((a << 5) - a) + b.charCodeAt(0), 0)) : 12345;
      const prompt = encodeURIComponent(`portrait of ${mind?.name || 'AI assistant'}, ${expression} expression, professional headshot, soft lighting, neutral background`);
      const avatarUrl = `https://image.pollinations.ai/prompt/${prompt}?width=512&height=512&seed=${mindNameHash}&model=flux&nologo=true`;
      
      setMindAvatarUrl(avatarUrl);
      
      // Save avatar URL to backend for persistence
      try {
        await api.updateMindSettings(mindId, { avatar_url: avatarUrl });
      } catch (err) {
        console.log('Could not persist avatar:', err);
      }
    } catch (error) {
      console.error('Error generating avatar:', error);
    }
  };

  const startVideo = async () => {
    if (videoRef.current && webcamRef.current) {
      const success = await webcamRef.current.start(videoRef.current);
      if (success) {
        setVideoEnabled(true);
        // Start emotion detection
        startEmotionDetection();
      }
    }
  };

  const stopVideo = () => {
    webcamRef.current?.stop();
    setVideoEnabled(false);
    if (emotionIntervalRef.current) {
      clearInterval(emotionIntervalRef.current);
      emotionIntervalRef.current = null;
    }
  };

  const startEmotionDetection = () => {
    // Capture and analyze emotion every 3 seconds
    emotionIntervalRef.current = setInterval(async () => {
      if (!webcamRef.current?.isActive()) return;

      const frame = webcamRef.current.captureFrame();
      if (frame) {
        try {
          const emotion = await api.analyzeEmotion(frame);
          setCurrentEmotion(emotion);
        } catch (error) {
          console.error('Emotion detection error:', error);
        }
      }
    }, 3000);
  };

  const startVoiceInput = () => {
    if (!voiceInputRef.current) return;

    setIsListening(true);
    voiceInputRef.current.start(
      (text) => {
        setInput(text);
        setIsListening(false);
        // Auto-send if we have text
        if (text.trim()) {
          sendMessage(text, true);
        }
      },
      (error) => {
        console.error('Voice input error:', error);
        setIsListening(false);
      }
    );
  };

  const stopVoiceInput = () => {
    voiceInputRef.current?.stop();
    setIsListening(false);
  };

  const speakMessage = (text: string) => {
    if (!voiceOutputRef.current) return;
    
    setIsSpeaking(true);
    voiceOutputRef.current.speak(text, {
      voice: 'nova', // Use nova (female) voice for "Her" movie feel
    });

    // Check if speaking ended
    const checkInterval = setInterval(() => {
      if (!voiceOutputRef.current?.isSpeaking()) {
        setIsSpeaking(false);
        clearInterval(checkInterval);
      }
    }, 100);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    setAttachedFiles(prev => [...prev, ...selected]);
  };

  const removeFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const sendMessage = async (text?: string, isVoice: boolean = false) => {
    const messageText = text || input;
    if ((!messageText.trim() && attachedFiles.length === 0) || loading) return;

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
      const messageContent = messageText + 
        (uploadedFileInfo.length > 0 ? `\n\n${uploadedFileInfo.join('\n')}` : '');

      const userMessage: Message = {
        role: 'user',
        content: messageContent,
        timestamp: new Date().toISOString(),
        voice: isVoice,
        user_context: currentEmotion ? {
          emotion: currentEmotion,
          timestamp: new Date().toISOString(),
        } : undefined,
      };

      setMessages(prev => [...prev, userMessage]);

      const context = {
        emotion: currentEmotion,
        voice_input: isVoice,
        video_context: videoEnabled ? { active: true } : undefined,
      };

      const data = await api.chatWithContext(mindId, messageContent, context);

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response || data.message,
        emotion: data.emotion,
        timestamp: new Date().toISOString(),
        image_url: data.generated_image,
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Update avatar based on response emotion
      if (data.emotion) {
        await generateAvatar(data.emotion);
      }

    } catch (error: any) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: error.message || 'Error: Could not connect to Genesis server',
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!mind) {
    return (
      <AuthRequired>
        <div className="flex items-center justify-center min-h-screen bg-black">
          <div className="spinner"></div>
        </div>
      </AuthRequired>
    );
  }

  return (
    <AuthRequired>
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900">
        {/* Header */}
        <div className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-sm border-b border-gray-800">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <Link href={`/minds/${mindId}`} className="text-gray-400 hover:text-white transition-colors">
              ← Back
            </Link>
            <h1 className="text-xl font-semibold text-white">{mind.name}</h1>
            <div className="flex items-center gap-2">
              {/* Voice Toggle */}
              <button
                onClick={() => setVoiceEnabled(!voiceEnabled)}
                className={`p-2 rounded-lg transition-colors ${
                  voiceEnabled ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
                title="Toggle voice output"
              >
                {voiceEnabled ? '🔊' : '🔇'}
              </button>

              {/* Video Toggle */}
              <button
                onClick={() => videoEnabled ? stopVideo() : startVideo()}
                className={`p-2 rounded-lg transition-colors ${
                  videoEnabled ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
                title="Toggle video mode"
              >
                {videoEnabled ? '📹' : '📷'}
              </button>
            </div>
          </div>
        </div>

        <div className="pt-16 pb-24 flex h-screen">
          <div className="flex-1 flex">
            {/* Video Feed (if enabled) */}
            {videoEnabled && (
              <div className="w-80 border-r border-gray-800 bg-black p-4">
                <div className="relative rounded-lg overflow-hidden">
                  <video
                    ref={videoRef}
                    className="w-full rounded-lg"
                    autoPlay
                    playsInline
                    muted
                  />
                  {currentEmotion && (
                    <div className="absolute bottom-2 left-2 right-2 bg-black/70 backdrop-blur-sm rounded-lg p-2 text-xs">
                      <div className="text-white font-medium">{currentEmotion.emotion}</div>
                      <div className="text-gray-400">
                        {(currentEmotion.confidence * 100).toFixed(0)}% confident
                      </div>
                    </div>
                  )}
                </div>
                <div className="mt-4 text-xs text-gray-500">
                  Your emotions are being analyzed to provide better context to {mind.name}
                </div>
              </div>
            )}

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col">
              {/* Mind Avatar */}
              <div className="flex justify-center py-8">
                <MindAvatar
                  url={mindAvatarUrl}
                  name={mind.name}
                  emotion={mind.current_emotion}
                  isSpeaking={isSpeaking}
                />
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-6 space-y-6">
                {messages.length === 0 && (
                  <div className="text-center py-12">
                    <p className="text-gray-400 text-lg">
                      Start a conversation with {mind.name}
                    </p>
                    <p className="text-gray-600 text-sm mt-2">
                      Use voice, video, or text to communicate naturally
                    </p>
                  </div>
                )}

                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[70%] ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
                      {/* User context indicator */}
                      {message.user_context?.emotion && (
                        <div className="text-xs text-gray-500 mb-1 flex items-center gap-2">
                          <span>😊 {message.user_context.emotion.emotion}</span>
                          {message.voice && <span>🎤 Voice</span>}
                        </div>
                      )}

                      <div
                        className={`rounded-2xl px-5 py-3 ${
                          message.role === 'user'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-800 text-gray-100'
                        }`}
                      >
                        <div className="text-sm whitespace-pre-wrap leading-relaxed">
                          {message.content}
                        </div>
                      </div>

                      {/* Generated image */}
                      {message.image_url && (
                        <div className="mt-2">
                          <img
                            src={message.image_url}
                            alt="Generated"
                            className="rounded-lg max-w-full"
                          />
                        </div>
                      )}

                      {message.emotion && (
                        <div className="text-xs text-gray-500 mt-1">
                          Feeling: {message.emotion}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-800 rounded-2xl px-5 py-3">
                      <div className="flex items-center gap-2">
                        <div className="spinner"></div>
                        <span className="text-gray-400 text-sm">Thinking...</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="p-6 border-t border-gray-800">
                <div className="max-w-4xl mx-auto">
                  {/* File Attachments Preview */}
                  {attachedFiles.length > 0 && (
                    <div className="flex flex-wrap gap-2 p-3 mb-3 bg-gray-800 rounded-xl border border-gray-700">
                      {attachedFiles.map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-2 bg-gray-700 px-3 py-1 rounded-lg text-sm"
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

                  <div className="flex gap-3 items-end">
                    {/* File Upload Button */}
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
                      disabled={loading}
                      className="p-3 rounded-xl transition-all bg-gray-800 text-gray-400 hover:bg-gray-700"
                      title="Attach files"
                    >
                      📎
                    </button>

                    {/* Voice Input Button */}
                    <button
                      onClick={isListening ? stopVoiceInput : startVoiceInput}
                      disabled={loading}
                      className={`p-3 rounded-xl transition-all ${
                        isListening
                          ? 'bg-red-600 text-white animate-pulse'
                          : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                      }`}
                      title={isListening ? 'Stop listening' : 'Start voice input'}
                    >
                      🎤
                    </button>

                    {/* Text Input */}
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder={isListening ? 'Listening...' : 'Type or speak your message...'}
                      className="flex-1 bg-gray-800 text-white placeholder-gray-500 rounded-xl px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-600"
                      rows={1}
                      disabled={loading || isListening}
                    />

                    {/* Send Button */}
                    <button
                      onClick={() => sendMessage()}
                      disabled={(!input.trim() && attachedFiles.length === 0) || loading}
                      className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                    >
                      {loading ? '...' : 'Send'}
                    </button>
                  </div>

                  {/* Status indicators */}
                  <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                    {voiceEnabled && <span>🔊 Voice output enabled</span>}
                    {videoEnabled && <span>📹 Video mode active</span>}
                    {currentEmotion && <span>😊 Emotion: {currentEmotion.emotion}</span>}
                    {isSpeaking && <span className="text-blue-400">🗣️ Speaking...</span>}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AuthRequired>
  );
}
