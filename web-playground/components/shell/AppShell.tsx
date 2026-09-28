'use client';

import { useCallback, useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import CommandPalette from './CommandPalette';
import { CloseIcon } from './icons';
import { useTheme } from './ThemeProvider';

/**
 * Application shell.
 *
 * Everything except `/login` renders inside this: a persistent sidebar for
 * navigation, a topbar for context and search, and a scrollable content region.
 * The previous layout put navigation in a top bar and left pages to invent their
 * own headers, which produced the inconsistency the revamp is fixing.
 *
 * The shell also owns the global Ctrl/Cmd+K shortcut.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  // Mounting the theme hook here guarantees the provider is above the shell and
  // that the document class is applied before the first paint of content.
  useTheme();

  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const isLoginPage = pathname === '/login' || pathname?.startsWith('/login/');

  const openPalette = useCallback(() => setPaletteOpen(true), []);
  const closePalette = useCallback(() => setPaletteOpen(false), []);

  // Global shortcut.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen((value) => !value);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Close the mobile drawer when the route changes.
  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  // A login page renders standalone: the shell's navigation would be dead weight.
  if (isLoginPage) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen bg-bg">
      {/* Desktop sidebar */}
      <div className="sticky top-0 hidden h-screen shrink-0 lg:block">
        <Sidebar />
      </div>

      {/* Mobile drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileNavOpen(false)}
            aria-hidden="true"
          />
          <div className="relative h-full w-64 bg-surface shadow-pop animate-fade-in">
            <button
              type="button"
              onClick={() => setMobileNavOpen(false)}
              className="absolute right-2 top-3 z-10 btn-ghost btn-sm !px-2"
              aria-label="Close navigation"
            >
              <CloseIcon />
            </button>
            <Sidebar onNavigate={() => setMobileNavOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onOpenMobileNav={() => setMobileNavOpen(true)}
          onOpenPalette={openPalette}
        />
        <main className="min-w-0 flex-1">{children}</main>
      </div>

      <CommandPalette open={paletteOpen} onClose={closePalette} />
    </div>
  );
}
