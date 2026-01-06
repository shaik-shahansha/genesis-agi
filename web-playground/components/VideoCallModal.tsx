'use client';

import { useState, useEffect, useRef } from 'react';
import { VoiceInput } from '@/lib/multimodal';

export type CallType = 'audio' | 'video';
export type CallState = 'idle' | 'calling' | 'ringing' | 'connected' | 'ended';

interface VideoCallModalProps {
  isOpen: boolean;
  callType: CallType;
  recipientName: string;
  recipientAvatar?: string;
  onClose: () => void;
  onAccept?: () => void;
  initialState?: CallState;
  onVoiceInput?: (text: string) => void;
  isSpeaking?: boolean;
}

export default function VideoCallModal({
  isOpen,
  callType,
  recipientName,
  recipientAvatar,
  onClose,
  onAccept,
  initialState = 'calling',
  onVoiceInput,
  isSpeaking = false,
}: VideoCallModalProps) {
  const [callState, setCallState] = useState<CallState>(initialState);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [permissionRequested, setPermissionRequested] = useState(false);
  const [isListeningForVoice, setIsListeningForVoice] = useState(false);
  const [voiceRetryCount, setVoiceRetryCount] = useState(0);
  const MAX_VOICE_RETRIES = 3;
  
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const callStartTimeRef = useRef<number>(0);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const voiceInputRef = useRef<VoiceInput | null>(null);

  // Initialize voice input
  useEffect(() => {
    voiceInputRef.current = new VoiceInput();
    return () => {
      voiceInputRef.current?.stop();
    };
  }, []);

  // Initialize media stream when modal opens
  useEffect(() => {
    if (isOpen) {
      console.log('📱 Modal opened, initializing media immediately...');
      initializeMediaStream();
    }

    return () => {
      cleanup();
    };
  }, [isOpen, callType]); // Add callType to dependencies

  // Timer for call duration
  useEffect(() => {
    if (callState === 'connected') {
      callStartTimeRef.current = Date.now();
      timerIntervalRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - callStartTimeRef.current) / 1000);
        setCallDuration(elapsed);
      }, 1000);
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
      setCallDuration(0);
    }

    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    };
  }, [callState]);

  // Simulate call connection after 2 seconds
  useEffect(() => {
    if (callState === 'calling') {
      const timeout = setTimeout(() => {
        setCallState('connected');
        console.log('[Done]Call connected!');
      }, 2000);
      return () => clearTimeout(timeout);
    }
  }, [callState]);

  // Pause listening when AI is speaking (but don't auto-restart)
  useEffect(() => {
    if (isSpeaking && isListeningForVoice) {
      console.log('⏸️ Pausing voice input while AI speaks...');
      stopVoiceInput();
    }
  }, [isSpeaking]);

  // Reset retry count when call connects
  useEffect(() => {
    if (callState === 'connected') {
      setVoiceRetryCount(0);
    }
  }, [callState]);

  // Set video source when stream is available
  useEffect(() => {
    if (localStream && localVideoRef.current && callType === 'video') {
      console.log('📹 Setting video source in useEffect...');
      localVideoRef.current.srcObject = localStream;
      localVideoRef.current.play().then(() => {
        console.log('[Done]Video playing from effect');
      }).catch((err) => {
        console.error('❌ Video play error from effect:', err);
      });
    }
  }, [localStream, callType]);

  // Debug: Log video render conditions
  useEffect(() => {
    console.log('🔍 Video render check:', {
      callType,
      hasLocalStream: !!localStream,
      videoTracksCount: localStream?.getVideoTracks().length || 0,
      isVideoOff,
      shouldShowVideo: callType === 'video' && localStream && localStream.getVideoTracks().length > 0 && !isVideoOff
    });
  }, [callType, localStream, isVideoOff]);

  const initializeMediaStream = async () => {
    try {
      console.log('🎥 Requesting media permissions...', { callType, audio: true, video: callType === 'video' });
      setPermissionRequested(true);
      setMediaError(null);

      // Check if mediaDevices is available
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const error = 'Media devices not supported in this browser';
        console.error('❌', error);
        throw new Error(error);
      }

      console.log('[Done]MediaDevices API available');

      const constraints = {
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: callType === 'video' ? {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        } : false,
      };

      console.log('📞 Requesting getUserMedia with constraints:', constraints);
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      console.log('[Done]Media stream obtained:', {
        id: stream.id,
        active: stream.active,
        audioTracks: stream.getAudioTracks().length,
        videoTracks: stream.getVideoTracks().length,
      });

      // Log track details
      stream.getAudioTracks().forEach(track => {
        console.log('🎤 Audio track:', {
          id: track.id,
          label: track.label,
          enabled: track.enabled,
          readyState: track.readyState,
          settings: track.getSettings(),
        });
      });

      stream.getVideoTracks().forEach(track => {
        console.log('📹 Video track:', {
          id: track.id,
          label: track.label,
          enabled: track.enabled,
          readyState: track.readyState,
          settings: track.getSettings(),
        });
      });

      setLocalStream(stream);

      if (localVideoRef.current && callType === 'video') {
        console.log('📹 Setting video source...');
        localVideoRef.current.srcObject = stream;
        try {
          await localVideoRef.current.play();
          console.log('[Done]Video element playing');
        } catch (playError) {
          console.error('❌ Video play error:', playError);
        }
      }

      if (callType === 'audio') {
        console.log('[Done]Audio call ready, microphone active');
      }

      setMediaError(null);
    } catch (error: any) {
      console.error('❌ Error accessing media devices:', error);
      console.error('Error name:', error.name);
      console.error('Error message:', error.message);
      
      let errorMessage = 'Could not access camera/microphone. ';
      
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        errorMessage += 'Permission was denied. Please allow access in your browser settings.';
      } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        errorMessage += 'No camera or microphone found. Please connect a device.';
      } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        errorMessage += 'Device is already in use by another application.';
      } else if (error.name === 'OverconstrainedError') {
        errorMessage += 'No device meets the specified requirements.';
      } else {
        errorMessage += error.message;
      }
      
      setMediaError(errorMessage);
      alert(errorMessage);
    }
  };

  const cleanup = () => {
    console.log('🧹 Cleaning up call resources...');
    
    // Stop voice input
    if (isListeningForVoice) {
      stopVoiceInput();
    }
    
    // Stop media tracks
    if (localStream) {
      localStream.getTracks().forEach(track => {
        track.stop();
        console.log('🛑 Stopped track:', track.kind);
      });
      setLocalStream(null);
    }
    
    // Clear timers
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
    }
  };

  const handleEndCall = () => {
    cleanup();
    setCallState('ended');
    setTimeout(() => {
      onClose();
      setCallState('idle');
    }, 1500);
  };

  const toggleMute = () => {
    if (localStream) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsMuted(!audioTrack.enabled);
      }
    }
  };

  const toggleVideo = () => {
    if (localStream && callType === 'video') {
      const videoTrack = localStream.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoOff(!videoTrack.enabled);
      }
    }
  };

  const startVoiceInput = () => {
    if (!voiceInputRef.current || !onVoiceInput) return;
    if (callState !== 'connected') {
      console.log('⚠️ Cannot start voice input - call not connected');
      return;
    }

    console.log('🎤 Starting voice input in call...');
    setIsListeningForVoice(true);
    voiceInputRef.current.start(
      (text) => {
        console.log('🗨️ Voice input received:', text);
        setIsListeningForVoice(false);
        setVoiceRetryCount(0); // Reset retry count on success
        onVoiceInput(text);
        
        // Don't auto-restart - user must click button again or we'll restart after AI speaks
      },
      (error) => {
        console.error('❌ Voice input error:', error);
        setIsListeningForVoice(false);
        
        // Don't retry on "no-speech" - it's expected when user isn't speaking
        if (error === 'no-speech') {
          console.log('ℹ️ No speech detected. Click the voice button to try again.');
          return;
        }
        
        // Only retry on real errors, with a limit
        if (callState === 'connected' && voiceRetryCount < MAX_VOICE_RETRIES && error !== 'aborted') {
          setVoiceRetryCount(prev => prev + 1);
          console.log(`🔄 Retrying voice input (${voiceRetryCount + 1}/${MAX_VOICE_RETRIES})...`);
          setTimeout(() => {
            startVoiceInput();
          }, 2000);
        } else if (voiceRetryCount >= MAX_VOICE_RETRIES) {
          console.log('⚠️ Max voice input retries reached. Click the voice button to try again.');
        }
      }
    );
  };

  const stopVoiceInput = () => {
    voiceInputRef.current?.stop();
    setIsListeningForVoice(false);
    setVoiceRetryCount(0);
    console.log('⏹️ Voice input stopped');
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/95 backdrop-blur-sm flex items-center justify-center">
      <div className="w-full h-full flex flex-col">
        {/* Video Container */}
        <div className="flex-1 relative">
          {/* Remote Video (AI Avatar) - Full Screen */}
          <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-black to-gray-800">
            {callState === 'connected' ? (
              <div className="w-full h-full flex items-center justify-center relative">
                {recipientAvatar ? (
                  <img
                    src={recipientAvatar}
                    alt={recipientName}
                    className="w-96 h-96 rounded-full object-cover ring-4 ring-blue-500/30 shadow-2xl"
                  />
                ) : (
                  <div className="w-96 h-96 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white text-8xl font-bold shadow-2xl">
                    {recipientName[0]?.toUpperCase()}
                  </div>
                )}
                
                {/* Speaking Indicator - Pulsing Ring */}
                {isSpeaking && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="w-[400px] h-[400px] rounded-full border-4 border-green-500 animate-ping opacity-75"></div>
                    <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-16 bg-green-600 text-white px-6 py-3 rounded-full font-medium shadow-lg">
                      🗣️ AI is speaking...
                    </div>
                  </div>
                )}
                
                {/* Listening Indicator */}
                {isListeningForVoice && !isSpeaking && (
                  <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-16 bg-blue-600 text-white px-6 py-3 rounded-full font-medium shadow-lg animate-pulse">
                    🎤 Listening...
                  </div>
                )}
              </div>
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center">
                {recipientAvatar ? (
                  <img
                    src={recipientAvatar}
                    alt={recipientName}
                    className="w-48 h-48 rounded-full object-cover ring-4 ring-white/10 shadow-2xl mb-8"
                  />
                ) : (
                  <div className="w-48 h-48 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white text-6xl font-bold shadow-2xl mb-8">
                    {recipientName[0]?.toUpperCase()}
                  </div>
                )}
                <h2 className="text-3xl font-semibold text-white mb-2">{recipientName}</h2>
                <p className="text-gray-400 text-lg">
                  {callState === 'calling' && 'Calling...'}
                  {callState === 'ringing' && 'Ringing...'}
                  {callState === 'ended' && 'Call Ended'}
                </p>
                {(callState === 'calling' || callState === 'ringing') && (
                  <div className="mt-6 flex gap-3">
                    <div className="w-3 h-3 rounded-full bg-blue-500 animate-ping"></div>
                    <div className="w-3 h-3 rounded-full bg-blue-500 animate-ping" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-3 h-3 rounded-full bg-blue-500 animate-ping" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Local Video (Picture-in-Picture) - Show as soon as we have stream */}
          {callType === 'video' && localStream && localStream.getVideoTracks().length > 0 && !isVideoOff && (
            <div className="absolute top-6 right-6 w-64 h-48 rounded-2xl overflow-hidden shadow-2xl ring-2 ring-white/20 bg-gray-900">
              <video
                ref={localVideoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover mirror"
                onLoadedMetadata={(e) => {
                  console.log('\u2705 Local video metadata loaded:', {
                    videoWidth: e.currentTarget.videoWidth,
                    videoHeight: e.currentTarget.videoHeight,
                    readyState: e.currentTarget.readyState,
                  });
                }}
                onPlay={() => console.log('\u25b6\ufe0f Local video playing')}
                onError={(e) => console.error('\u274c Local video error:', e)}
              />
              {isMuted && (
                <div className="absolute top-2 left-2 bg-red-600 text-white px-2 py-1 rounded-lg text-xs font-medium flex items-center gap-1">
                  🔇 Muted
                </div>
              )}
              {!localStream && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-900/90">
                  <div className="text-center">
                    <div className="text-2xl mb-2">\ud83d\udcf9</div>
                    <div className="text-white text-sm">Initializing camera...</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Call Status Overlay */}
          <div className="absolute top-6 left-6 bg-black/70 backdrop-blur-md rounded-2xl px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white text-xl font-bold">
                {recipientName[0]?.toUpperCase()}
              </div>
              <div>
                <div className="text-white font-medium">{recipientName}</div>
                <div className="text-gray-400 text-sm flex items-center gap-2">
                  {callState === 'connected' ? (
                    <>
                      <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                      <span>{formatDuration(callDuration)}</span>
                    </>
                  ) : (
                    <span className="capitalize">{callState}...</span>
                  )}
                </div>
                {isSpeaking && callState === 'connected' && (
                  <div className="text-green-400 text-xs mt-1 flex items-center gap-1">
                    <span className="animate-pulse">\ud83d\udd0a</span> AI is speaking
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Media Error Overlay */}
          {mediaError && (
            <div className="absolute top-24 left-6 right-6 bg-red-900/90 backdrop-blur-md rounded-2xl px-6 py-4 border border-red-500/50">
              <div className="flex items-start gap-3">
                <div className="text-3xl">\u26a0\ufe0f</div>
                <div className="flex-1">
                  <div className="text-white font-medium mb-1">Media Access Error</div>
                  <div className="text-red-200 text-sm">{mediaError}</div>
                  <button
                    onClick={initializeMediaStream}
                    className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Permission Request Indicator */}
          {permissionRequested && !localStream && !mediaError && (
            <div className="absolute top-24 left-6 right-6 bg-blue-900/90 backdrop-blur-md rounded-2xl px-6 py-4 border border-blue-500/50">
              <div className="flex items-start gap-3">
                <div className="text-3xl animate-pulse">\ud83d\udd12</div>
                <div className="flex-1">
                  <div className="text-white font-medium mb-1">Permission Required</div>
                  <div className="text-blue-200 text-sm mb-3">
                    Please allow access to your {callType === 'video' ? 'camera and microphone' : 'microphone'} when prompted by your browser.
                  </div>
                  <button
                    onClick={initializeMediaStream}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Request Permissions Again
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* No Stream Warning (if waiting too long) */}
          {isOpen && !localStream && !mediaError && !permissionRequested && (
            <div className="absolute top-24 left-6 right-6 bg-yellow-900/90 backdrop-blur-md rounded-2xl px-6 py-4 border border-yellow-500/50">
              <div className="flex items-start gap-3">
                <div className="text-3xl">⚠️</div>
                <div className="flex-1">
                  <div className="text-white font-medium mb-1">Camera Not Started</div>
                  <div className="text-yellow-200 text-sm mb-3">
                    Click the button below to enable your {callType === 'video' ? 'camera and microphone' : 'microphone'}.
                  </div>
                  <button
                    onClick={initializeMediaStream}
                    className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Enable {callType === 'video' ? 'Camera & Microphone' : 'Microphone'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Call Type Badge */}
          <div className="absolute top-6 left-1/2 transform -translate-x-1/2 bg-black/70 backdrop-blur-md rounded-full px-4 py-2 flex items-center gap-2">
            <span className="text-2xl">{callType === 'video' ? '📹' : '📞'}</span>
            <span className="text-white text-sm font-medium capitalize">{callType} Call</span>
          </div>
        </div>

        {/* Control Panel */}
        <div className="flex-none bg-gradient-to-t from-black via-black/95 to-transparent px-6 py-8">
          <div className="max-w-2xl mx-auto">
            <div className="flex items-center justify-center gap-6">
              {/* Mute Button */}
              <button
                onClick={toggleMute}
                disabled={callState !== 'connected'}
                className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl transition-all transform hover:scale-110 active:scale-95 ${
                  isMuted
                    ? 'bg-red-600 text-white shadow-lg shadow-red-500/50'
                    : 'bg-gray-800/80 text-white hover:bg-gray-700/80'
                } ${callState !== 'connected' ? 'opacity-50 cursor-not-allowed' : ''}`}
                title={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted ? '🔇' : '🎤'}
              </button>

              {/* Video Toggle Button (only for video calls) */}
              {callType === 'video' && (
                <button
                  onClick={toggleVideo}
                  disabled={callState !== 'connected'}
                  className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl transition-all transform hover:scale-110 active:scale-95 ${
                    isVideoOff
                      ? 'bg-gray-600 text-white shadow-lg'
                      : 'bg-gray-800/80 text-white hover:bg-gray-700/80'
                  } ${callState !== 'connected' ? 'opacity-50 cursor-not-allowed' : ''}`}
                  title={isVideoOff ? 'Turn on camera' : 'Turn off camera'}
                >
                  {isVideoOff ? '📷' : '📹'}
                </button>
              )}

              {/* End Call Button */}
              <button
                onClick={handleEndCall}
                className="w-20 h-20 rounded-full bg-red-600 hover:bg-red-700 text-white flex items-center justify-center text-3xl shadow-2xl shadow-red-500/50 transition-all transform hover:scale-110 active:scale-95"
                title="End call"
              >
                📞
              </button>

              {/* Speaker Button */}
              <button
                disabled={callState !== 'connected'}
                className={`w-16 h-16 rounded-full bg-gray-800/80 hover:bg-gray-700/80 text-white flex items-center justify-center text-2xl transition-all transform hover:scale-110 active:scale-95 ${
                  callState !== 'connected' ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                title="Speaker"
              >
                🔊
              </button>

              {/* Voice Input Button (NEW) */}
              {onVoiceInput && (
                <button
                  onClick={isListeningForVoice ? stopVoiceInput : startVoiceInput}
                  disabled={callState !== 'connected'}
                  className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl transition-all transform hover:scale-110 active:scale-95 ${
                    isListeningForVoice
                      ? 'bg-green-600 text-white shadow-lg shadow-green-500/50 animate-pulse'
                      : 'bg-gray-800/80 text-white hover:bg-gray-700/80'
                  } ${callState !== 'connected' ? 'opacity-50 cursor-not-allowed' : ''}`}
                  title={isListeningForVoice ? 'Stop listening' : 'Voice input'}
                >
                  {isListeningForVoice ? '🎙️' : '🗣️'}
                </button>
              )}
            </div>

            {/* Voice Input Status */}
            {callState === 'connected' && !isListeningForVoice && !isSpeaking && (
              <div className="mt-4 flex items-center justify-center gap-2 text-blue-400">
                <span className="text-sm">👆 Click the voice button (🗣️) to speak</span>
              </div>
            )}
            {isListeningForVoice && (
              <div className="mt-4 flex items-center justify-center gap-2 text-green-400 animate-pulse">
                <span className="text-sm font-medium">🎙️ Listening for your voice...</span>
              </div>
            )}
            {isSpeaking && (
              <div className="mt-4 flex items-center justify-center gap-2 text-purple-400 animate-pulse">
                <span className="text-sm font-medium">🔊 AI is responding...</span>
              </div>
            )}

            {/* Additional Options */}
            {callState === 'connected' && (
              <div className="mt-6 flex items-center justify-center gap-4 text-sm text-gray-400">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  Encrypted
                </span>
                <span>•</span>
                <span>HD Quality</span>
                {localStream && (
                  <>
                    <span>•</span>
                    <span>{localStream.getAudioTracks().length} Audio</span>
                    {callType === 'video' && (
                      <>
                        <span>•</span>
                        <span>{localStream.getVideoTracks().length} Video</span>
                      </>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        .mirror {
          transform: scaleX(-1);
        }

        @keyframes pulse-ring {
          0% {
            box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
          }
          70% {
            box-shadow: 0 0 0 20px rgba(59, 130, 246, 0);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
          }
        }
      `}</style>
    </div>
  );
}
