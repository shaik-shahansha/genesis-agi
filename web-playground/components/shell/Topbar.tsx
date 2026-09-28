'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef, useState } from 'react';
import { mindIdFromPath, isActivePath, mindNav, platformNav, type NavItem } from '@/lib/navigation';
import { useMindCache } from '@/lib/MindContext';
import { SearchIcon, SunIcon, MoonIcon, MenuIcon } from './icons';
import { useTheme } from './ThemeProvider';

interface TopbarProps {
  onOpenMobileNav: () => void;
  onOpenPalette: () => void;
}

/**
 * Mind switcher.
 *
 * The reported Mind is written into the shared cache so other pages can use it
 * without refetching; the switcher itself falls back to the path when the cache
 * is cold.
 */
function MindSwitcher() {
  const pathname = usePathname();
  const router = useRouter();
  const mindId = mindIdFromPath(pathname);
  const { getCachedMind } = useMindCache();
  const [open, setOpen] = useState(false);
  const [minds, setMinds] = useState<{ gmid: string; name: string; status?: string }[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || minds.length) return;
    let cancelled = false;
    (async () => {
      try {
        const token =
          (await import('@/lib/firebase').then((m) => m.getFirebaseToken())) ||
          localStorage.getItem('genesis_token');
        const response = await fetch('/api/v1/minds', {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled) setMinds(Array.isArray(data) ? data : (data.minds ?? []));
      } catch {
        /* the switcher degrades to "no other Minds" rather than erroring */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, minds.length]);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  const cached = mindId ? getCachedMind(mindId) : null;
  const currentName = cached?.name || (mindId ? mindId : 'All Minds');

  if (!mindId) {
    return (
      <Link href="/" className="text-sm font-medium text-fg-muted hover:text-fg">
        All Minds
      </Link>
    );
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="btn-ghost btn-sm"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="grid h-5 w-5 shrink-0 place-items-center rounded text-[0.625rem] font-bold"
          style={{ backgroundColor: 'rgb(var(--accent-soft))', color: 'rgb(var(--accent))' }}>
          {currentName.slice(0, 1).toUpperCase()}
        </span>
        <span className="max-w-[12rem] truncate">{currentName}</span>
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1.5 w-64 overflow-hidden rounded-lg border border-line bg-surface shadow-pop animate-fade-in">
          <p className="border-b border-line px-3 py-2 text-[0.6875rem] font-semibold uppercase tracking-wider text-fg-subtle">
            Switch Mind
          </p>
          <div className="max-h-72 overflow-y-auto py-1">
            {minds.length === 0 && (
              <p className="px-3 py-2 text-xs text-fg-muted">No other Minds available</p>
            )}
            {minds.map((mind) => (
              <button
                key={mind.gmid}
                type="button"
                onClick={() => {
                  setOpen(false);
                  router.push(`/minds/${mind.gmid}`);
                }}
                className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-surface-2 ${
                  mind.gmid === mindId ? 'text-accent' : 'text-fg'
                }`}
              >
                <span className="truncate">{mind.name || mind.gmid}</span>
                <span className="meta shrink-0">{mind.status}</span>
              </button>
            ))}
          </div>
          <Link
            href="/"
            onClick={() => setOpen(false)}
            className="block border-t border-line px-3 py-2 text-xs text-fg-muted hover:bg-surface-2"
          >
            View all Minds
          </Link>
        </div>
      )}
    </div>
  );
}

function ThemeToggle() {
  const { resolved, toggle } = useTheme();
  return (
    <button
      type="button"
      onClick={toggle}
      className="btn-ghost btn-sm !px-2"
      title={`Switch to ${resolved === 'dark' ? 'light' : 'dark'} theme`}
      aria-label="Toggle colour theme"
    >
      {resolved === 'dark' ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

export default function Topbar({ onOpenMobileNav, onOpenPalette }: TopbarProps) {
  const isMac =
    typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform || '');

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-2 border-b border-line bg-surface/85 px-3 backdrop-blur sm:px-4">
      <button
        type="button"
        onClick={onOpenMobileNav}
        className="btn-ghost btn-sm !px-2 lg:hidden"
        aria-label="Open navigation"
      >
        <MenuIcon />
      </button>

      <MindSwitcher />

      <div className="flex-1" />

      <button
        type="button"
        onClick={onOpenPalette}
        className="hidden items-center gap-2 rounded-lg border border-line bg-surface-2 px-3 py-1.5 text-xs text-fg-muted transition-colors hover:border-line-strong hover:text-fg sm:flex"
        aria-label="Open command palette"
      >
        <SearchIcon className="h-4 w-4" />
        <span>Search or jump to…</span>
        <kbd className="ml-4 rounded border border-line bg-surface px-1.5 py-0.5 font-mono text-[0.6875rem]">
          {isMac ? '⌘' : 'Ctrl'} K
        </kbd>
      </button>

      <button
        type="button"
        onClick={onOpenPalette}
        className="btn-ghost btn-sm !px-2 sm:hidden"
        aria-label="Search"
      >
        <SearchIcon />
      </button>

      <ThemeToggle />
    </header>
  );
}
