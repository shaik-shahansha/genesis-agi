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

/**
 * Whether we know, yet, that this visitor is signed in.
 *
 * This is a three-state value rather than two booleans, and that is the whole
 * point. The previous version kept `checkingSession` and `session` separately,
 * started the check in one effect and redirected in a second effect. Both
 * effects run in the same commit, so the redirect effect read
 * `checkingSession === false` from the render *before* the check had begun and
 * pushed to `/login` immediately - racing the fetch, which was then aborted.
 * The visible symptom was a signed-in user being unable to open any guarded
 * page: the redirect fired every time, and because the request was cancelled
 * there was not even a failed request to look at.
 *
 * Starting at `checking` and only ever leaving it inside the effect removes the
 * race by construction: there is no render in which "not authenticated" is
 * concluded before the question has actually been asked.
 */
type Status = 'checking' | 'authenticated' | 'anonymous';

export default function AuthRequired({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [session, setSession] = useState<SessionUser | null>(null);
  const [status, setStatus] = useState<Status>('checking');

  useEffect(() => {
    // Still resolving Firebase; we know nothing yet and must keep waiting.
    if (loading) return;

    // A Firebase user is sufficient on its own.
    if (user) {
      setStatus('authenticated');
      return;
    }

    if (!getSessionToken()) {
      setStatus('anonymous');
      return;
    }

    let cancelled = false;
    setStatus('checking');
    loadSessionUser().then((resolved) => {
      if (cancelled) return;
      setSession(resolved);
      setStatus(resolved ? 'authenticated' : 'anonymous');
    });

    return () => {
      cancelled = true;
    };
  }, [loading, user]);

  useEffect(() => {
    if (status === 'anonymous') router.push('/login');
  }, [status, router]);

  if (status === 'checking') {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="spinner-large" />
          <p className="text-sm text-fg-muted">Checking your session…</p>
        </div>
      </div>
    );
  }

  if (status === 'anonymous') {
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
