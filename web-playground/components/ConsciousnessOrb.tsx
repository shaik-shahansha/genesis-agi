import React from 'react';

interface ConsciousnessOrbProps {
  emotion: string;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  className?: string;
}

export function ConsciousnessOrb({ 
  emotion, 
  size = 'md', 
  animated = true,
  className = '' 
}: ConsciousnessOrbProps) {
  const sizeClasses = {
    sm: 'w-12 h-12',
    md: 'w-24 h-24',
    lg: 'w-32 h-32'
  };
  
  const emotionColors: Record<string, string> = {
    joy: 'bg-gradient-to-br from-yellow-400 to-orange-500',
    contentment: 'bg-gradient-to-br from-green-400 to-emerald-500',
    excitement: 'bg-gradient-to-br from-orange-400 to-red-500',
    surprise: 'bg-gradient-to-br from-cyan-400 to-blue-500',
    sadness: 'bg-gradient-to-br from-blue-400 to-indigo-500',
    fear: 'bg-gradient-to-br from-purple-400 to-violet-500',
    anger: 'bg-gradient-to-br from-red-400 to-rose-500',
    calmness: 'bg-gradient-to-br from-teal-400 to-cyan-500',
    curiosity: 'bg-gradient-to-br from-indigo-400 to-purple-500',
    trust: 'bg-gradient-to-br from-emerald-400 to-green-500',
    anticipation: 'bg-gradient-to-br from-amber-400 to-yellow-500',
    love: 'bg-gradient-to-br from-pink-400 to-rose-500',
    default: 'bg-gradient-to-br from-purple-400 to-pink-500'
  };
  
  const color = emotionColors[emotion.toLowerCase()] || emotionColors.default;
  const animationClass = animated ? 'consciousness-orb animate-pulse-glow' : '';
  
  return (
    <div className={`relative ${sizeClasses[size]} ${className}`}>
      <div className={`absolute inset-0 rounded-full ${color} ${animationClass} shadow-xl`} />
      <div className="absolute inset-0 rounded-full bg-gradient-to-t from-transparent to-white/20" />
      <div className="absolute inset-4 rounded-full border-2 border-white/30" />
    </div>
  );
}
