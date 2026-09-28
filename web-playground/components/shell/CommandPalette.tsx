'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { mindIdFromPath, mindNav, platformNav, type NavItem } from '@/lib/navigation';
import { SearchIcon } from './icons';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Keyboard-driven navigation (Ctrl/Cmd+K).
 *
 * With the revamp the app has considerably more surface area, so a palette is a
 * usability requirement rather than a flourish: it is the only way to reach a
 * Mind's governance pages without first navigating to the Mind.
 */
export default function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const items = useMemo<NavItem[]>(() => {
    const mindId = mindIdFromPath(pathname);
    return [...(mindId ? mindNav(mindId) : []), ...platformNav()];
  }, [pathname]);

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((item) => {
      const haystack = [item.label, item.description ?? '', ...(item.keywords ?? [])]
        .join(' ')
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [items, query]);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setCursor(0);
    const id = window.setTimeout(() => inputRef.current?.focus(), 10);
    return () => window.clearTimeout(id);
  }, [open]);

  useEffect(() => {
    setCursor(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        setCursor((value) => Math.min(value + 1, Math.max(results.length - 1, 0)));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setCursor((value) => Math.max(value - 1, 0));
      } else if (event.key === 'Enter') {
        const target = results[cursor];
        if (target) {
          event.preventDefault();
          router.push(target.href);
          onClose();
        }
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, results, cursor, router, onClose]);

  // Keep the highlighted row in view while arrowing through a long list.
  useEffect(() => {
    const node = listRef.current?.querySelector('[data-active="true"]');
    node?.scrollIntoView({ block: 'nearest' });
  }, [cursor]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center p-4 pt-[12vh]"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="relative w-full max-w-xl overflow-hidden rounded-xl border border-line bg-surface shadow-pop animate-fade-in">
        <div className="flex items-center gap-2.5 border-b border-line px-4">
          <SearchIcon className="h-4 w-4 text-fg-subtle" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search pages, approvals, receipts…"
            className="h-12 flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-fg-subtle"
            aria-label="Search"
          />
          <kbd className="rounded border border-line bg-surface-2 px-1.5 py-0.5 font-mono text-[0.6875rem] text-fg-muted">
            Esc
          </kbd>
        </div>

        <div ref={listRef} className="max-h-80 overflow-y-auto py-1.5">
          {results.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-fg-muted">
              Nothing matches “{query}”.
            </p>
          )}
          {results.map((item, index) => (
            <button
              key={item.href}
              type="button"
              data-active={index === cursor}
              onMouseEnter={() => setCursor(index)}
              onClick={() => {
                router.push(item.href);
                onClose();
              }}
              className={`flex w-full items-start gap-3 px-4 py-2.5 text-left ${
                index === cursor ? 'bg-surface-2' : ''
              }`}
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-fg">{item.label}</p>
                {item.description && (
                  <p className="mt-0.5 truncate text-xs text-fg-muted">{item.description}</p>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
