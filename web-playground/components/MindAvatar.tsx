'use client';

import { useEffect, useState } from 'react';

interface MindAvatarProps {
  url: string;
  name: string;
  emotion?: string;
  isSpeaking?: boolean;
  className?: string;
  showWaveform?: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function MindAvatar({ url, name, emotion, isSpeaking, className, showWaveform = true }: MindAvatarProps) {
  const [placeholder, setPlaceholder] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [waveformBars, setWaveformBars] = useState<number[]>([]);

  useEffect(() => {
    // Generate a placeholder color based on name
    const hash = name.split('').reduce((acc, char) => char.charCodeAt(0) + acc, 0);
    const hue = hash % 360;
    setPlaceholder(`hsl(${hue}, 70%, 60%)`);
  }, [name]);

  useEffect(() => {
    // Convert relative URL to absolute API URL
    if (url) {
      if (url.startsWith('http')) {
        setImageUrl(url);
      } else {
        setImageUrl(`${API_URL}${url}`);
      }
    }
  }, [url]);

  // Animated waveform when speaking
  useEffect(() => {
    if (isSpeaking && showWaveform) {
      const interval = setInterval(() => {
        setWaveformBars(Array.from({ length: 5 }, () => Math.random() * 100 + 20));
      }, 100);
      return () => clearInterval(interval);
    } else {
      setWaveformBars([]);
    }
  }, [isSpeaking, showWaveform]);

  // Emotion-based color mapping
  const getEmotionColor = (emotion?: string) => {
    switch (emotion?.toLowerCase()) {
      case 'happy':
      case 'joy':
        return 'border-yellow-400 shadow-yellow-400/50';
      case 'excited':
        return 'border-orange-400 shadow-orange-400/50';
      case 'calm':
      case 'peaceful':
        return 'border-blue-400 shadow-blue-400/50';
      case 'sad':
        return 'border-blue-600 shadow-blue-600/50';
      case 'angry':
        return 'border-red-500 shadow-red-500/50';
      case 'curious':
        return 'border-purple-400 shadow-purple-400/50';
      default:
        return 'border-gray-700 shadow-gray-700/50';
    }
  };

  const avatarSize = className || 'w-48 h-48';

  return (
    <div className="relative inline-block">
      {/* Multiple glow layers for depth */}
      {isSpeaking && (
        <>
          <div className={`absolute inset-0 ${avatarSize} rounded-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 opacity-20 blur-3xl animate-pulse`}></div>
          <div className={`absolute inset-0 ${avatarSize} rounded-full bg-blue-500 opacity-10 blur-2xl animate-ping`}></div>
        </>
      )}

      {/* Avatar Container */}
      <div className="relative">
        {/* Avatar Image or Placeholder */}
        <div
          className={`${avatarSize} rounded-full overflow-hidden border-4 transition-all duration-500 ${
            isSpeaking
              ? 'border-blue-500 shadow-2xl shadow-blue-500/70 scale-105 ring-4 ring-blue-500/30 ring-offset-2 ring-offset-black'
              : getEmotionColor(emotion) + ' shadow-xl'
          }`}
          style={{
            backgroundColor: imageUrl ? 'transparent' : placeholder,
            transform: isSpeaking ? 'scale(1.05)' : 'scale(1)',
          }}
        >
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={name}
              className={`w-full h-full object-cover transition-all duration-300 ${
                isSpeaking ? 'brightness-110' : 'brightness-100'
              }`}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-white text-6xl font-bold">
              {name[0].toUpperCase()}
            </div>
          )}

          {/* Gradient overlay for depth */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent pointer-events-none"></div>
        </div>

        {/* Animated speaking ring */}
        {isSpeaking && (
          <>
            <div className="absolute inset-0 rounded-full border-2 border-blue-500/50 animate-ping"></div>
            <div className="absolute inset-0 rounded-full border-2 border-purple-500/30 animate-pulse" style={{ animationDelay: '0.2s' }}></div>
          </>
        )}

        {/* Waveform visualization when speaking */}
        {isSpeaking && showWaveform && waveformBars.length > 0 && (
          <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 flex items-end gap-1 h-6">
            {waveformBars.map((height, index) => (
              <div
                key={index}
                className="w-1.5 bg-gradient-to-t from-blue-500 to-purple-500 rounded-full transition-all duration-100"
                style={{ height: `${height}%` }}
              ></div>
            ))}
          </div>
        )}

        {/* Emotion Badge */}
        {emotion && !isSpeaking && (
          <div className="absolute -bottom-4 left-1/2 transform -translate-x-1/2">
            <div className="bg-gradient-to-r from-gray-900 to-gray-800 text-white px-4 py-1.5 rounded-full text-xs font-medium border border-gray-700 shadow-lg backdrop-blur-sm">
              <span className="mr-1">
                {emotion === 'happy' ? '😊' :
                 emotion === 'sad' ? '😢' :
                 emotion === 'excited' ? '🤩' :
                 emotion === 'calm' ? '😌' :
                 emotion === 'curious' ? '🤔' :
                 emotion === 'angry' ? '😠' : '😐'}
              </span>
              {emotion}
            </div>
          </div>
        )}

        {/* Speaking indicator text */}
        {isSpeaking && (
          <div className="absolute -bottom-4 left-1/2 transform -translate-x-1/2">
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-1.5 rounded-full text-xs font-medium shadow-lg shadow-blue-500/50 animate-pulse">
              <span className="mr-1">🗣️</span>
              Speaking...
            </div>
          </div>
        )}
      </div>

      {/* Name Label */}
      <div className="text-center mt-8">
        <h2 className="text-2xl font-semibold text-white drop-shadow-lg">{name}</h2>
        {emotion && (
          <p className="text-sm text-gray-400 mt-1 capitalize">Feeling {emotion}</p>
        )}
      </div>

      {/* CSS for additional animations */}
      <style jsx>{`
        @keyframes pulse-ring {
          0%, 100% {
            transform: scale(1);
            opacity: 1;
          }
          50% {
            transform: scale(1.1);
            opacity: 0.5;
          }
        }
      `}</style>
    </div>
  );
}