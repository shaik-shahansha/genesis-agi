'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface Mind {
  gmid: string;
  name: string;
  model: string;
  status: string;
  age: string;
  current_emotion: string;
  memory_count: number;
  autonomy?: any;
  [key: string]: any;
}

interface MindContextType {
  mindCache: Record<string, { data: Mind; timestamp: number }>;
  getCachedMind: (mindId: string) => Mind | null;
  setCachedMind: (mindId: string, mind: Mind) => void;
  invalidateMind: (mindId: string) => void;
  clearCache: () => void;
}

const MindContext = createContext<MindContextType | undefined>(undefined);

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
const STORAGE_KEY = 'genesis_mind_cache';

export function MindProvider({ children }: { children: ReactNode }) {
  const [mindCache, setMindCache] = useState<Record<string, { data: Mind; timestamp: number }>>({});

  // Load cache from localStorage on mount
  useEffect(() => {
    try {
      const cached = localStorage.getItem(STORAGE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached);
        // Filter out expired entries
        const now = Date.now();
        const filtered: Record<string, { data: Mind; timestamp: number }> = {};
        Object.entries(parsed).forEach(([key, value]: [string, any]) => {
          if (now - value.timestamp < CACHE_DURATION) {
            filtered[key] = value;
          }
        });
        setMindCache(filtered);
      }
    } catch (error) {
      console.error('Error loading mind cache:', error);
    }
  }, []);

  // Save cache to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(mindCache));
    } catch (error) {
      console.error('Error saving mind cache:', error);
    }
  }, [mindCache]);

  const getCachedMind = (mindId: string): Mind | null => {
    const cached = mindCache[mindId];
    if (!cached) return null;

    const age = Date.now() - cached.timestamp;
    if (age > CACHE_DURATION) {
      // Cache expired
      return null;
    }

    console.log(`✅ Using cached mind data for ${mindId} (age: ${Math.round(age / 1000)}s)`);
    return cached.data;
  };

  const setCachedMind = (mindId: string, mind: Mind) => {
    setMindCache((prev) => ({
      ...prev,
      [mindId]: {
        data: mind,
        timestamp: Date.now(),
      },
    }));
    console.log(`💾 Cached mind data for ${mindId}`);
  };

  const invalidateMind = (mindId: string) => {
    setMindCache((prev) => {
      const newCache = { ...prev };
      delete newCache[mindId];
      return newCache;
    });
    console.log(`🗑️ Invalidated cache for mind ${mindId}`);
  };

  const clearCache = () => {
    setMindCache({});
    localStorage.removeItem(STORAGE_KEY);
    console.log('🗑️ Cleared mind cache');
  };

  return (
    <MindContext.Provider value={{ mindCache, getCachedMind, setCachedMind, invalidateMind, clearCache }}>
      {children}
    </MindContext.Provider>
  );
}

export function useMindCache() {
  const context = useContext(MindContext);
  if (context === undefined) {
    throw new Error('useMindCache must be used within a MindProvider');
  }
  return context;
}
