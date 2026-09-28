'use client';

/**
 * Route guard.
 *
 * Accepts **either** credential:
 *
 *  * a Firebase user (when Firebase is configured), or
 *  * a built-in JWT session created through `POST /api/v1/auth/token`.
 *
 * The second path is what makes the documented single-container deployment
 * usable without Firebase. Previously this component only checked the Firebase
 * user, so on a Firebase-less install every guarded page redirected to a login
 * screen whose only buttons were Firebase buttons - a dead end.
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { getSessionToken, loadSessionUser, type SessionUser } from '@/lib/session';

export default function AuthRequired({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [checkingSession, setCheckingSession] = useState(false);
  const [session, setSession] = useState<SessionUser | null>(null);

  useEffect(() => {
    if (loading || user) return;

    // No Firebase user: fall back to the built-in token, if one is stored.
    if (!getSessionToken()) return;

    let cancelled = false;
    setCheckingSession(true);
    loadSessionUser().then((resolved) => {
      if (cancelled) return;
      setSession(resolved);
      setCheckingSession(false);
    });
    return () => {
      cancelled = true;
    };
  }, [loading, user]);

  useEffect(() => {
    if (loading || checkingSession) return;
    if (!user && !session) router.push('/login');
  }, [user, session, loading, checkingSession, router]);

  if (loading || checkingSession) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="spinner-large" />
          <p className="text-sm text-fg-muted">Checking your session…</p>
        </div>
      </div>
    );
  }

  if (!user && !session) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center px-6">
        <div className="max-w-md text-center">
          <p className="text-sm font-medium text-fg">You need to sign in</p>
          <p className="mt-1 text-sm text-fg-muted">
            This page shows data belonging to a Mind you own or have been granted access to.
          </p>
          <button
            type="button"
            className="btn-primary btn-sm mt-4"
            onClick={() => router.push('/login')}
          >
            Go to sign in
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
