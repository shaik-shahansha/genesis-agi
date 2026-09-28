'use client';

/**
 * Theme handling.
 *
 * The previous playground had no theme system at all: pages hardcoded either
 * dark (`text-white`, `bg-slate-800`) or light (`text-gray-900`, `bg-white`)
 * palette values, so whichever theme the user got, roughly half the app was
 * unreadable.
 *
 * This provider owns a single `light` | `dark` | `system` preference, applies it
 * as `.dark` on `<html>` (which is what the tokens in `globals.css` switch on),
 * and persists it. An inline script in `app/layout.tsx` applies it before paint
 * so there is no flash of the wrong theme.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';

export const THEME_STORAGE_KEY = 'genesis_theme';

interface ThemeContextValue {
  /** What the user chose. */
  preference: ThemePreference;
  /** What is actually applied right now. */
  resolved: 'light' | 'dark';
  setPreference: (next: ThemePreference) => void;
  /** Flip between light and dark, leaving `system` behind. */
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function systemPrefersDark(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

export function resolveTheme(preference: ThemePreference): 'light' | 'dark' {
  if (preference === 'system') return systemPrefersDark() ? 'dark' : 'light';
  return preference;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  // Default to light: the app is a workspace, and the light theme is the one
  // that reads best for dense tables, receipts and audit trails. Users who
  // prefer dark get it in one click (or automatically under `system`).
  const [preference, setPreferenceState] = useState<ThemePreference>('light');
  const [resolved, setResolved] = useState<'light' | 'dark'>('light');

  // Restore the stored preference on mount.
  useEffect(() => {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY) as ThemePreference | null;
      if (stored === 'light' || stored === 'dark' || stored === 'system') {
        setPreferenceState(stored);
      }
    } catch {
      /* localStorage unavailable (private mode) - keep the default */
    }
  }, []);

  // Apply the preference, and keep following the OS while on `system`.
  useEffect(() => {
    const applied = resolveTheme(preference);
    setResolved(applied);

    const root = document.documentElement;
    root.classList.toggle('dark', applied === 'dark');
    root.style.colorScheme = applied;

    if (preference !== 'system' || !window.matchMedia) return;

    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => {
      const next = query.matches ? 'dark' : 'light';
      setResolved(next);
      root.classList.toggle('dark', next === 'dark');
      root.style.colorScheme = next;
    };
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, [preference]);

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const toggle = useCallback(() => {
    setPreference(resolveTheme(preference) === 'dark' ? 'light' : 'dark');
  }, [preference, setPreference]);

  const value = useMemo(
    () => ({ preference, resolved, setPreference, toggle }),
    [preference, resolved, setPreference, toggle]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
