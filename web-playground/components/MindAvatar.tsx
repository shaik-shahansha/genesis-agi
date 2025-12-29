'use client';

import { useEffect, useState } from 'react';

interface MindAvatarProps {
  url: string;
  name: string;
  emotion?: string;
  isSpeaking?: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function MindAvatar({ url, name, emotion, isSpeaking }: MindAvatarProps) {
  const [placeholder, setPlaceholder] = useState('');
  const [imageUrl, setImageUrl] = useState('');

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

  return (
    <div className="relative">
      {/* Avatar Image or Placeholder */}
      <div
        className={`w-48 h-48 rounded-full overflow-hidden border-4 transition-all duration-300 ${
          isSpeaking
            ? 'border-blue-500 shadow-lg shadow-blue-500/50 scale-105'
            : 'border-gray-700 shadow-xl'
        }`}
        style={{
          backgroundColor: imageUrl ? 'transparent' : placeholder,
        }}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-white text-6xl font-bold">
            {name[0].toUpperCase()}
          </div>
        )}
      </div>

      {/* Emotion Indicator */}
      {emotion && (
        <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-3">
          <div className="bg-gray-800 text-white px-4 py-1 rounded-full text-sm font-medium border border-gray-700">
            {emotion}
          </div>
        </div>
      )}

      {/* Speaking Animation */}
      {isSpeaking && (
        <div className="absolute inset-0 rounded-full">
          <div className="absolute inset-0 rounded-full bg-blue-500/20 animate-ping"></div>
          <div className="absolute inset-0 rounded-full bg-blue-500/10 animate-pulse"></div>
        </div>
      )}

      {/* Name */}
      <div className="text-center mt-6">
        <h2 className="text-2xl font-semibold text-white">{name}</h2>
      </div>
    </div>
  );
}
