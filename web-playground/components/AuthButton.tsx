'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';

export default function AuthButton() {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

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
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-200 font-medium">{user.email || 'User'}</span>
      <button
        onClick={handleLogout}
        className="btn-ghost text-sm"
      >
        Logout
      </button>
    </div>
  );
}
