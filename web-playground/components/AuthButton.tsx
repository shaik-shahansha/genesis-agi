'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { useState, useRef, useEffect } from 'react';

export default function AuthButton() {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await signOut();
      router.push('/login');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  if (pathname === '/login' || loading) {
    return null;
  }

  if (!user) {
    return (
      <button
        onClick={() => router.push('/login')}
        className="btn-primary"
      >
        Login
      </button>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* User Icon Button */}
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        className="flex items-center justify-center w-9 h-9 rounded-full bg-purple-600 hover:bg-purple-700 transition text-white font-semibold text-sm"
        title={user.email || 'User menu'}
      >
        {(user.email || 'U')[0].toUpperCase()}
      </button>

      {/* Dropdown Menu */}
      {dropdownOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-2 z-50">
          {/* User Info */}
          <div className="px-4 py-3 border-b border-slate-700">
            <div className="text-xs text-gray-400">Signed in as</div>
            <div className="text-sm text-white font-medium truncate mt-1">{user.email || 'User'}</div>
          </div>
          
          {/* Menu Items */}
          <button
            onClick={handleLogout}
            className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-slate-700 hover:text-white transition flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
