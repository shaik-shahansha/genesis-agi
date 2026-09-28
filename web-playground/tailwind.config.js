/** @type {import('tailwindcss').Config} */
//
// One design system for the whole playground.
//
// The previous state was two contradictory themes patched together: older pages
// used dark-only utilities (`text-white`, `bg-slate-800`, `border-slate-700`)
// while newer components used light-only ones (`text-gray-900`, `bg-white`,
// `border-gray-200`). Whatever the theme, half the app was unreadable.
//
// This config defines a single semantic token set. Semantic tokens are consumed
// as `bg-surface`, `text-fg-muted`, `border-line`, etc., which resolve to CSS
// variables that change with the theme - so a component is theme-correct by
// construction. The raw Tailwind palette is left intact so existing markup keeps
// compiling; `app/globals.css` re-points the legacy dark utilities at the tokens
// so old pages inherit the theme instead of fighting it.
//
// Token values use the `rgb(var(--x) / <alpha-value>)` form so Tailwind opacity
// modifiers (`bg-surface/60`) work.

/** @param {string} variable */
const token = (variable) => `rgb(var(${variable}) / <alpha-value>)`;

module.exports = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'ui-sans-serif',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Inter',
          'Roboto',
          'Helvetica Neue',
          'sans-serif',
        ],
        mono: [
          'ui-monospace',
          'SFMono-Regular',
          'JetBrains Mono',
          'Menlo',
          'Consolas',
          'Liberation Mono',
          'monospace',
        ],
      },
      colors: {
        bg: token('--bg'),
        surface: {
          DEFAULT: token('--surface'),
          2: token('--surface-2'),
          3: token('--surface-3'),
        },
        line: {
          DEFAULT: token('--border'),
          strong: token('--border-strong'),
        },
        fg: {
          DEFAULT: token('--fg'),
          muted: token('--fg-muted'),
          subtle: token('--fg-subtle'),
        },
        accent: {
          DEFAULT: token('--accent'),
          fg: token('--accent-fg'),
          soft: token('--accent-soft'),
        },
        // Risk levels (ADR-0006). Fixed hues: R0..R5 must be distinguishable at a
        // glance, and they must not shift with the theme or a severity could be
        // misread.
        risk: {
          r0: '#64748b',
          r1: '#059669',
          r2: '#0284c7',
          r3: '#d97706',
          r4: '#ea580c',
          r5: '#dc2626',
        },
      },
      borderRadius: {
        card: '0.875rem',
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 3px 0 rgb(0 0 0 / 0.06)',
        raised: '0 4px 12px -2px rgb(0 0 0 / 0.10), 0 2px 6px -2px rgb(0 0 0 / 0.06)',
        pop: '0 12px 32px -8px rgb(0 0 0 / 0.20), 0 4px 12px -4px rgb(0 0 0 / 0.10)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 rgb(220 38 38 / 0.45)' },
          '70%': { boxShadow: '0 0 0 10px rgb(220 38 38 / 0)' },
          '100%': { boxShadow: '0 0 0 0 rgb(220 38 38 / 0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 160ms ease-out both',
        'pulse-ring': 'pulse-ring 1.8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        shimmer: 'shimmer 1.6s infinite',
      },
    },
  },
  plugins: [],
};
