'use client';

import './globals.css';
import '../styles/chat-enhancements.css';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import AuthButton from '@/components/AuthButton';
import NotificationBell from '@/components/NotificationBell';
import { AuthProvider } from '@/lib/auth-context';
import { MindProvider } from '@/lib/MindContext';
import dynamic from 'next/dynamic';
import { isCreationDisabled, isProduction } from '@/lib/env';

// Dynamically import AdminLink to avoid using hooks directly in layout's top-level
const AdminLink = dynamic(() => import('@/components/AdminLink').then(mod => mod.AdminLink), { ssr: false });

// Use system fonts instead of Google Fonts to avoid SSL certificate issues
const fontClassName = 'font-sans';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login' || pathname?.startsWith('/login/');
  const creationDisabled = isCreationDisabled();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <html lang="en">
      <body className={fontClassName}>
        <AuthProvider>
          <MindProvider>
            <div className="min-h-screen bg-slate-900">
            {/* Navigation - Hidden on login page */}
            {!isLoginPage && (
              <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-slate-700/50 shadow-lg">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <div className="flex items-center justify-between h-16">
                    <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity" onClick={() => setMobileMenuOpen(false)}>
                      <span className="text-2xl" style={{ color: 'var(--genesis-primary)' }}>◉</span>
                      <span className="text-base sm:text-lg md:text-xl font-bold gradient-text tracking-wide">GENESIS AGI FRAMEWORK</span>
                    </Link>
                    
                    {/* Desktop Menu */}
                    <div className="hidden md:flex items-center gap-1">
                      <Link href="/" className="btn-ghost">
                        Dashboard
                      </Link>
                      {!creationDisabled && (
                        <Link href="/create" className="btn-ghost">
                          New Mind
                        </Link>
                      )}
                      {!isProduction() && (
                        <Link href="/environments" className="btn-ghost">
                          Environments
                        </Link>
                      )}
                      {!isProduction() && (
                        <Link href="/settings" className="btn-ghost">
                          Settings
                        </Link>
                      )}
                      {/* Admin link shown only to global admins */}
                      <AdminLink />
                      <a 
                        href="https://github.com/shaik-shahansha/genesis-agi" 
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-ghost"
                      >
                        GitHub
                      </a>
                      <NotificationBell />
                      <AuthButton />
                    </div>

                    {/* Mobile Menu Button & Auth */}
                    <div className="md:hidden flex items-center gap-2">
                      <NotificationBell />
                      <AuthButton />
                      <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="p-2 text-gray-300 hover:text-white hover:bg-slate-700 rounded-lg transition"
                        aria-label="Toggle menu"
                      >
                        {mobileMenuOpen ? (
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        ) : (
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Mobile Menu Dropdown */}
                  {mobileMenuOpen && (
                    <div className="md:hidden border-t border-slate-700 py-2">
                      <div className="flex flex-col space-y-1">
                        <Link 
                          href="/" 
                          className="px-3 py-2 text-gray-300 hover:text-white hover:bg-slate-700 rounded-lg transition"
                          onClick={() => setMobileMenuOpen(false)}
                        >
                          🏠 Dashboard
                        </Link>
                        {!creationDisabled && (
                          <Link 
                            href="/create" 
                            className="px-3 py-2 text-gray-300 hover:text-white hover:bg-slate-700 rounded-lg transition"
                            onClick={() => setMobileMenuOpen(false)}
                          >
                            ➕ New Mind
                          </Link>
                        )}
                        {!isProduction() && (
                          <Link 
                            href="/environments" 
                            className="px-3 py-2 text-gray-300 hover:text-white hover:bg-slate-700 rounded-lg transition"
                            onClick={() => setMobileMenuOpen(false)}
                          >
                            🌐 Environments
                          </Link>
                        )}
                        {!isProduction() && (
                          <Link 
                            href="/settings" 
                            className="px-3 py-2 text-gray-300 hover:text-white hover:bg-slate-700 rounded-lg transition"
                            onClick={() => setMobileMenuOpen(false)}
                          >
                            ⚙️ Settings
                          </Link>
                        )}
                        <a 
                          href="https://github.com/shaik-shahansha/genesis-agi" 
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3 py-2 text-gray-300 hover:text-white hover:bg-slate-700 rounded-lg transition"
                          onClick={() => setMobileMenuOpen(false)}
                        >
                          📦 GitHub
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              </nav>
            )}

          {/* Main Content */}
          <main className={isLoginPage ? '' : 'pt-16'}>
            {children}
          </main>

          {/* Footer - Hidden on login page */}
          {!isLoginPage && (
            <footer className="border-t border-slate-700 py-8 bg-slate-800">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-gray-300 text-sm">
                <p>Genesis AGI Framework v0.1.5</p>
              </div>
            </footer>
          )}
        </div>
        </MindProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
