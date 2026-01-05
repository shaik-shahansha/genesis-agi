'use client';

import { useState, useEffect, useRef } from 'react';

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
}

export default function VideoCallModal({
  isOpen,
  callType,
  recipientName,
  recipientAvatar,
  onClose,
  onAccept,
  initialState = 'calling',
}: VideoCallModalProps) {
  const [callState, setCallState] = useState<CallState>(initialState);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const callStartTimeRef = useRef<number>(0);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize media stream when call starts
  useEffect(() => {
    if (isOpen && (callState === 'calling' || callState === 'ringing')) {
      initializeMediaStream();
    }

    return () => {
      cleanup();
    };
  }, [isOpen, callState]);

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
      }, 2000);
      return () => clearTimeout(timeout);
    }
  }, [callState]);

  const initializeMediaStream = async () => {
    try {
      const constraints = {
        audio: true,
        video: callType === 'video' ? {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        } : false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      setLocalStream(stream);

      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }
    } catch (error) {
      console.error('Error accessing media devices:', error);
      alert('Could not access camera/microphone. Please check permissions.');
    }
  };

  const cleanup = () => {
    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
      setLocalStream(null);
    }
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
              <div className="w-full h-full flex items-center justify-center">
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

          {/* Local Video (Picture-in-Picture) */}
          {callType === 'video' && callState === 'connected' && !isVideoOff && (
            <div className="absolute top-6 right-6 w-64 h-48 rounded-2xl overflow-hidden shadow-2xl ring-2 ring-white/20 bg-gray-900">
              <video
                ref={localVideoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover mirror"
              />
              {isMuted && (
                <div className="absolute top-2 left-2 bg-red-600 text-white px-2 py-1 rounded-lg text-xs font-medium flex items-center gap-1">
                  🔇 Muted
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
              </div>
            </div>
          </div>

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

              {/* Add Person Button (placeholder) */}
              <button
                disabled={callState !== 'connected'}
                className={`w-16 h-16 rounded-full bg-gray-800/80 hover:bg-gray-700/80 text-white flex items-center justify-center text-2xl transition-all transform hover:scale-110 active:scale-95 ${
                  callState !== 'connected' ? 'opacity-50 cursor-not-allowed' : ''
                }`}
                title="Add person"
              >
                👤➕
              </button>
            </div>

            {/* Additional Options */}
            {callState === 'connected' && (
              <div className="mt-6 flex items-center justify-center gap-4 text-sm text-gray-400">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  Encrypted
                </span>
                <span>•</span>
                <span>HD Quality</span>
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
