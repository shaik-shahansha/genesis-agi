'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { api } from '@/lib/api';

export default function AuthButton() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    checkAuth();
  }, [pathname]);

  const checkAuth = async () => {
    if (api.isAuthenticated()) {
      try {
        const user = await api.getCurrentUser();
        setIsAuthenticated(true);
        setUsername(user.username);
      } catch {
        setIsAuthenticated(false);
        setUsername(null);
      }
    } else {
      setIsAuthenticated(false);
      setUsername(null);
    }
  };

  const handleLogout = () => {
    api.logout();
    setIsAuthenticated(false);
    setUsername(null);
    router.push('/login');
  };

  if (pathname === '/login') {
    return null;
  }

  if (!isAuthenticated) {
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
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-200 font-medium">{username}</span>
      <button
        onClick={handleLogout}
        className="btn-ghost text-sm"
      >
        Logout
      </button>
    </div>
  );
}
