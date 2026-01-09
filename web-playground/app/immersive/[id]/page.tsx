'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthRequired from '@/components/AuthRequired';
import { api } from '@/lib/api';
import { VoiceInput, VoiceOutput, WebcamCapture, UserContext } from '@/lib/multimodal';
import { EnhancedVideoProcessor } from '@/lib/videoProcessor';
import MindAvatar from '@/components/MindAvatar';
import VideoCallModal from '@/components/VideoCallModal';

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
  
  // Call modal states
  const [isCallModalOpen, setIsCallModalOpen] = useState(false);
  const [callType, setCallType] = useState<'audio' | 'video'>('video');
  
  // Enhanced video analytics
  const [videoAnalytics, setVideoAnalytics] = useState<any>(null);
  const [engagementLevel, setEngagementLevel] = useState<string>('medium');
  const [userAttention, setUserAttention] = useState<number>(1.0);
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const voiceInputRef = useRef<VoiceInput | null>(null);
  const voiceOutputRef = useRef<VoiceOutput | null>(null);
  const webcamRef = useRef<WebcamCapture | null>(null);
  const videoProcessorRef = useRef<EnhancedVideoProcessor | null>(null);
  const emotionIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchMind();
    voiceInputRef.current = new VoiceInput();
    voiceOutputRef.current = new VoiceOutput();
    webcamRef.current = new WebcamCapture();
    videoProcessorRef.current = new EnhancedVideoProcessor();

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
      if (!mind) return;
      
      // Generate dynamic prompt based on mind's purpose/personality
      const mindPurpose = mind.purpose || mind.personality || 'AI assistant';
      const mindNameHash = mind.name ? Math.abs(mind.name.split('').reduce((a: number, b: string) => ((a << 5) - a) + b.charCodeAt(0), 0)) : 12345;
      
      // Create detailed prompt for better avatar generation (remove special chars for URL)
      const cleanExpression = expression.replace(/[^a-z0-9]/gi, '_');
      const basePrompt = `professional portrait of ${mind.name}, ${mindPurpose}, ${expression} expression, photorealistic, soft studio lighting, neutral background, high quality`;
      const prompt = encodeURIComponent(basePrompt);
      
      // Use time-based seed variation for expression changes, but consistent base
      const expressionSeed = expression === 'neutral' ? mindNameHash : mindNameHash + expression.length * 1000;
      const avatarUrl = `https://image.pollinations.ai/prompt/${prompt}?width=512&height=512&seed=${expressionSeed}&model=flux&nologo=true`;
      
      console.log('🎨 Generating avatar:', { name: mind.name, expression, purpose: mindPurpose });
      setMindAvatarUrl(avatarUrl);
      
      // Save avatar URL to backend for persistence (only if neutral)
      if (expression === 'neutral') {
        try {
          await api.updateMindSettings(mindId, { avatar_url: avatarUrl });
        } catch (err) {
          console.log('Could not persist avatar:', err);
        }
      }
    } catch (error) {
      console.error('Error generating avatar:', error);
    }
  };

  const startVideo = async () => {
    if (videoRef.current && videoProcessorRef.current) {
      // Use enhanced video processor with local analytics
      const success = await videoProcessorRef.current.start(
        videoRef.current,
        (analytics) => {
          // Update state with local video analytics
          setVideoAnalytics(analytics);
          setEngagementLevel(analytics.engagementLevel);
          setUserAttention(analytics.attentionScore);
          
          // Update emotion from local processing
          if (analytics.faceDetected && analytics.emotion.confidence > 0.6) {
            setCurrentEmotion({
              emotion: analytics.emotion.primary,
              confidence: analytics.emotion.confidence,
              valence: analytics.emotion.valence,
              arousal: analytics.emotion.arousal,
            });
          }
        }
      );
      
      if (success) {
        setVideoEnabled(true);
        console.log('[Done]Enhanced video processing started with local analytics');
      }
    }
  };

  const stopVideo = () => {
    videoProcessorRef.current?.stop();
    webcamRef.current?.stop();
    setVideoEnabled(false);
    setVideoAnalytics(null);
    if (emotionIntervalRef.current) {
      clearInterval(emotionIntervalRef.current);
      emotionIntervalRef.current = null;
    }
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

  const startAudioCall = () => {
    setCallType('audio');
    setIsCallModalOpen(true);
    if (!voiceEnabled) {
      setVoiceEnabled(true);
      console.log('🔊 Voice output enabled for call');
    }
    console.log('📞 Starting audio call...');
  };

  const startVideoCall = () => {
    setCallType('video');
    setIsCallModalOpen(true);
    if (!voiceEnabled) {
      setVoiceEnabled(true);
      console.log('🔊 Voice output enabled for call');
    }
    console.log('📹 Starting video call...');
  };

  const handleCloseCall = () => {
    setIsCallModalOpen(false);
    console.log('✖️ Call ended by user');
  };

  const handleVoiceInputFromCall = (text: string) => {
    console.log('🎤 Voice input from call:', text);
    setInput(text);
    if (text.trim()) {
      sendMessage(text, true);
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
      <div className="min-h-screen bg-black text-white overflow-hidden">
        {/* Video Call Interface */}
        <div className="h-screen flex flex-col">
          {/* Header */}
          <div className="flex-none bg-gradient-to-b from-black/80 to-transparent backdrop-blur-sm z-50 px-6 py-4">
            <div className="flex items-center justify-between">
              <Link href={`/minds/${mindId}`} className="text-gray-400 hover:text-white transition-colors flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </Link>
              
              <div className="flex items-center gap-3">
                <div className="text-center">
                  <div className="flex items-center gap-2">
                    <h1 className="text-lg font-semibold">{mind.name}</h1>
                    <span className="inline-block text-xs bg-yellow-400 text-black px-2 py-0.5 rounded">Work in progress</span>
                  </div>
                  <p className="text-xs text-gray-400">
                    {videoEnabled ? '🟢 Video Call Active' : '⚪ Voice Only'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Voice Toggle */}
                <button
                  onClick={() => setVoiceEnabled(!voiceEnabled)}
                  className={`p-3 rounded-xl transition-all ${
                    voiceEnabled 
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/50' 
                      : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50'
                  }`}
                  title="Toggle voice output"
                >
                  {voiceEnabled ? '🔊' : '🔇'}
                </button>

                {/* Audio Call Button */}
                <button
                  onClick={startAudioCall}
                  className="p-3 rounded-xl bg-gray-800/50 text-gray-400 hover:bg-green-600 hover:text-white hover:shadow-lg hover:shadow-green-500/50 transition-all"
                  title="Start audio call"
                >
                  📞
                </button>

                {/* Video Call Button */}
                <button
                  onClick={startVideoCall}
                  className="p-3 rounded-xl bg-gray-800/50 text-gray-400 hover:bg-blue-600 hover:text-white hover:shadow-lg hover:shadow-blue-500/50 transition-all"
                  title="Start video call"
                >
                  📹
                </button>

                {/* Camera Toggle (for existing video analytics) */}
                <button
                  onClick={() => videoEnabled ? stopVideo() : startVideo()}
                  className={`p-3 rounded-xl transition-all ${
                    videoEnabled 
                      ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/50' 
                      : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50'
                  }`}
                  title="Toggle camera analytics"
                >
                  {videoEnabled ? '📷' : '📷'}
                </button>
              </div>
            </div>
          </div>

          {/* Video Call Layout - Split Screen */}
          <div className="flex-1 flex overflow-hidden">
            {/* Main Video Area - AI Avatar */}
            <div className="flex-1 relative bg-gradient-to-br from-gray-900 via-black to-gray-900 flex items-center justify-center">
              {/* AI Avatar with animated background */}
              <div className="relative z-10">
                {isSpeaking && (
                  <div className="absolute inset-0 rounded-full blur-3xl opacity-30 animate-pulse">
                    <div className="w-full h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"></div>
                  </div>
                )}
                <MindAvatar
                  url={mindAvatarUrl}
                  name={mind.name}
                  emotion={mind.current_emotion}
                  isSpeaking={isSpeaking}
                  className="w-80 h-80"
                />
                
                {/* Speaking indicator */}
                {isSpeaking && (
                  <div className="absolute -bottom-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-2 rounded-full text-sm font-medium shadow-lg">
                    🗣️ Speaking...
                  </div>
                )}
              </div>

              {/* AI Status Overlay */}
              <div className="absolute top-4 left-4 bg-black/70 backdrop-blur-md rounded-xl px-4 py-3 space-y-2">
                <div className="text-xs text-gray-400">AI Status</div>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${isSpeaking ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></div>
                  <span className="text-sm">{isSpeaking ? 'Speaking' : 'Listening'}</span>
                </div>
                {mind.current_emotion && (
                  <div className="text-sm">
                    <span className="text-gray-400">Mood:</span> {mind.current_emotion}
                  </div>
                )}
              </div>

              {/* Chat Messages Overlay (Bottom) */}
              <div className="absolute bottom-0 left-0 right-0 max-h-64 overflow-y-auto scrollbar-hide">
                <div className="px-6 pb-4 space-y-2">
                  {messages.slice(-3).map((message, index) => (
                    <div
                      key={messages.length - 3 + index}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-md rounded-2xl px-4 py-2 backdrop-blur-md ${
                          message.role === 'user'
                            ? 'bg-blue-600/80 text-white'
                            : 'bg-black/70 text-gray-100'
                        }`}
                      >
                        <div className="text-sm leading-relaxed">{message.content}</div>
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div className="flex justify-start">
                      <div className="bg-black/70 backdrop-blur-md rounded-2xl px-4 py-2">
                        <div className="flex items-center gap-2">
                          <div className="spinner border-2 border-blue-500 border-t-transparent w-4 h-4"></div>
                          <span className="text-sm text-gray-300">Thinking...</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* User Video Sidebar (When video enabled) */}
            {videoEnabled && (
              <div className="w-96 bg-black/50 backdrop-blur-xl border-l border-gray-800/50 flex flex-col">
                {/* User Video Feed */}
                <div className="flex-1 relative p-4">
                  <div className="relative h-full rounded-2xl overflow-hidden shadow-2xl ring-2 ring-blue-500/30">
                    <video
                      ref={videoRef}
                      className="w-full h-full object-cover"
                      autoPlay
                      playsInline
                      muted
                    />
                    
                    {/* Video Analytics Overlay */}
                    {videoAnalytics && videoAnalytics.faceDetected && (
                      <div className="absolute inset-0 pointer-events-none">
                        {/* Attention Indicator */}
                        <div className={`absolute top-4 left-4 right-4 bg-black/70 backdrop-blur-sm rounded-lg p-3 transition-all ${
                          videoAnalytics.isLookingAtCamera ? 'ring-2 ring-green-500' : 'ring-2 ring-yellow-500'
                        }`}>
                          <div className="flex items-center justify-between text-xs">
                            <div>
                              <div className="text-white font-medium mb-1">Your Presence</div>
                              <div className="text-gray-300">
                                {videoAnalytics.isLookingAtCamera ? '[Done]Looking at camera' : '⚠️ Look away detected'}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-white font-bold text-lg">
                                {Math.round(videoAnalytics.attentionScore * 100)}%
                              </div>
                              <div className="text-gray-400">Attention</div>
                            </div>
                          </div>
                        </div>

                        {/* Emotion Display */}
                        {currentEmotion && (
                          <div className="absolute bottom-4 left-4 right-4 bg-black/70 backdrop-blur-sm rounded-lg p-3">
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="text-white font-medium text-sm mb-1">Your Emotion</div>
                                <div className="flex items-center gap-2">
                                  <span className="text-2xl">
                                    {currentEmotion.emotion === 'happy' ? '😊' :
                                     currentEmotion.emotion === 'sad' ? '😢' :
                                     currentEmotion.emotion === 'angry' ? '😠' :
                                     currentEmotion.emotion === 'surprised' ? '😲' : '😐'}
                                  </span>
                                  <span className="text-white capitalize">{currentEmotion.emotion}</span>
                                </div>
                              </div>
                              <div className="text-right text-xs text-gray-400">
                                {Math.round(currentEmotion.confidence * 100)}% confident
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Speaking Indicator */}
                        {videoAnalytics.isSpeaking && (
                          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                            <div className="bg-red-600 text-white px-6 py-3 rounded-full font-medium shadow-lg animate-pulse">
                              🎤 You're speaking
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* No Face Detected Warning */}
                    {videoAnalytics && !videoAnalytics.faceDetected && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                        <div className="text-center p-6">
                          <div className="text-4xl mb-2">🔍</div>
                          <div className="text-white font-medium">No face detected</div>
                          <div className="text-gray-400 text-sm mt-1">Position yourself in the frame</div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Video Stats */}
                  {videoAnalytics && (
                    <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                      <div className="bg-black/50 rounded-lg p-2 text-center">
                        <div className="text-gray-400">Engagement</div>
                        <div className={`font-bold mt-1 ${
                          engagementLevel === 'high' ? 'text-green-500' :
                          engagementLevel === 'medium' ? 'text-yellow-500' : 'text-red-500'
                        }`}>
                          {engagementLevel.toUpperCase()}
                        </div>
                      </div>
                      <div className="bg-black/50 rounded-lg p-2 text-center">
                        <div className="text-gray-400">FPS</div>
                        <div className="text-white font-bold mt-1">
                          {Math.round(videoAnalytics.frameRate)}
                        </div>
                      </div>
                      <div className="bg-black/50 rounded-lg p-2 text-center">
                        <div className="text-gray-400">Processing</div>
                        <div className="text-white font-bold mt-1">
                          {Math.round(videoAnalytics.processingTime)}ms
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Local Processing Notice */}
                <div className="flex-none p-4 border-t border-gray-800/50">
                  <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3 text-xs text-blue-300">
                    <div className="font-medium mb-1">🔒 Privacy First</div>
                    <div className="text-blue-400">
                      All video processing happens locally in your browser. 
                      Only emotion metadata is shared with AI.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input Controls - Bottom Bar */}
          <div className="flex-none bg-gradient-to-t from-black/90 to-transparent backdrop-blur-xl border-t border-gray-800/50 px-6 py-4">
            <div className="max-w-4xl mx-auto">{/* File Attachments Preview */}
              {attachedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 p-3 mb-3 bg-gray-900/50 rounded-xl border border-gray-700">
                  {attachedFiles.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 bg-gray-800 px-3 py-1 rounded-lg text-sm"
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
                {/* File Upload */}
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  multiple
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading}
                  className="p-4 rounded-xl bg-gray-800/50 hover:bg-gray-700/50 transition-all disabled:opacity-50"
                  title="Attach files"
                >
                  📎
                </button>

                {/* Voice Input */}
                <button
                  onClick={isListening ? stopVoiceInput : startVoiceInput}
                  disabled={loading}
                  className={`p-4 rounded-xl transition-all ${
                    isListening
                      ? 'bg-red-600 text-white shadow-lg shadow-red-500/50 animate-pulse'
                      : 'bg-gray-800/50 hover:bg-gray-700/50'
                  }`}
                  title={isListening ? 'Stop' : 'Voice input'}
                >
                  🎤
                </button>

                {/* Text Input */}
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={isListening ? 'Listening...' : 'Type your message...'}
                  className="flex-1 bg-gray-800/50 text-white placeholder-gray-500 rounded-xl px-5 py-4 resize-none focus:outline-none focus:ring-2 focus:ring-blue-600 backdrop-blur-sm"
                  rows={1}
                  disabled={loading || isListening}
                />

                {/* Send Button */}
                <button
                  onClick={() => sendMessage()}
                  disabled={(!input.trim() && attachedFiles.length === 0) || loading}
                  className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/30"
                >
                  {loading ? '...' : 'Send'}
                </button>
              </div>

              {/* Status Bar */}
              <div className="flex items-center justify-between mt-3 text-xs">
                <div className="flex items-center gap-4 text-gray-500">
                  {voiceEnabled && <span className="flex items-center gap-1">🔊 Voice enabled</span>}
                  {videoEnabled && <span className="flex items-center gap-1">📹 Video call active</span>}
                  {currentEmotion && videoAnalytics?.faceDetected && (
                    <span className="flex items-center gap-1">
                      😊 You seem {currentEmotion.emotion}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4 text-gray-500">
                  {videoAnalytics?.faceDetected && (
                    <>
                      <span>Attention: {Math.round(userAttention * 100)}%</span>
                      <span>Engagement: {engagementLevel}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        <style jsx>{`
          .spinner {
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }
          
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }

          .scrollbar-hide::-webkit-scrollbar {
            display: none;
          }

          .scrollbar-hide {
            -ms-overflow-style: none;
            scrollbar-width: none;
          }
        `}</style>
      </div>

      {/* Video Call Modal */}
      <VideoCallModal
        isOpen={isCallModalOpen}
        callType={callType}
        recipientName={mind.name}
        recipientAvatar={mindAvatarUrl}
        onClose={handleCloseCall}
        onVoiceInput={handleVoiceInputFromCall}
        isSpeaking={isSpeaking}
        initialState="calling"
      />
    </AuthRequired>
  );
}