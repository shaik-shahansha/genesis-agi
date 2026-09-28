'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { loginWithPassword, setSession, getSessionToken, loadSessionUser } from '@/lib/session';
import { isFirebaseConfigured } from '@/lib/firebase';
import { AlertIcon } from '@/components/shell/icons';

/**
 * Sign-in page.
 *
 * Firebase is optional in this product, and this page used to render the Google
 * and Firebase-email controls unconditionally. On an install without Firebase
 * those controls were all there was, in the primary position, and every one of
 * them failed — which is the dead end the deployment guide's "Firebase is
 * optional" claim was silently contradicting.
 *
 * When Firebase is not configured the form shown is the one that works, and the
 * page says why the others are absent rather than hiding them without comment.
 */
export default function LoginPage() {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { user, signInWithGoogle, signInWithEmail, signUpWithEmail } = useAuth();
  const router = useRouter();

  // Built-in (non-Firebase) credentials. The panel is open by default when
  // Firebase is absent, because then it is the only path and collapsing it would
  // recreate the dead end.
  const [directOpen, setDirectOpen] = useState(!isFirebaseConfigured);
  const [username, setUsername] = useState('');
  const [directPassword, setDirectPassword] = useState('');

  // Redirect if already logged in (Firebase user, or a still-valid API session).
  useEffect(() => {
    if (user) {
      router.push('/');
      return;
    }
    if (getSessionToken()) {
      loadSessionUser().then((session) => {
        if (session) router.push('/');
      });
    }
  }, [user, router]);

  const handleDirectSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const token = await loginWithPassword(username, directPassword);
      setSession(token, username.includes('@') ? username : null);
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Sign in failed');
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError('');
    setLoading(true);

    try {
      await signInWithGoogle();
      // The auth context will handle the redirect
    } catch (err: any) {
      setError(err.message || 'Failed to sign in with Google');
      setLoading(false);
    }
  };

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'signup') {
        await signUpWithEmail(email, password);
      } else {
        await signInWithEmail(email, password);
      }
      // The auth context will handle the redirect
    } catch (err: any) {
      setError(err.message || `Failed to ${mode === 'signup' ? 'sign up' : 'sign in'}`);
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="page-title">Genesis</h1>
          <p className="mt-2 text-sm text-fg-muted">
            Sign in to reach the Minds on this installation.
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-card border border-danger/40 bg-danger/5 p-3 text-sm text-fg"
          >
            <span className="mt-0.5 text-danger">
              <AlertIcon className="h-4 w-4" />
            </span>
            <span className="min-w-0 break-words">{error}</span>
          </div>
        )}

        <div className="card space-y-4">
          {isFirebaseConfigured ? (
            <>
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={loading}
                className="btn-secondary w-full justify-center"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                {loading ? 'Signing in…' : 'Continue with Google'}
              </button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-line" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-surface px-2 text-xs text-fg-subtle">or</span>
                </div>
              </div>

              <form onSubmit={handleEmailAuth} className="space-y-4">
                <div>
                  <label htmlFor="firebase-email" className="label mb-1.5 block">
                    Email address
                  </label>
                  <input
                    id="firebase-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="input w-full"
                    autoComplete="email"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="firebase-password" className="label mb-1.5 block">
                    Password
                  </label>
                  <input
                    id="firebase-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="input w-full"
                    autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                    required
                  />
                </div>
                <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
                  {loading ? 'Working…' : mode === 'signup' ? 'Create account' : 'Sign in'}
                </button>
              </form>

              <p className="text-center text-sm text-fg-muted">
                {mode === 'signup' ? 'Already have an account?' : 'Need an account?'}{' '}
                <button
                  type="button"
                  onClick={() => setMode(mode === 'signup' ? 'signin' : 'signup')}
                  className="text-accent underline underline-offset-2"
                >
                  {mode === 'signup' ? 'Sign in' : 'Sign up'}
                </button>
              </p>
            </>
          ) : (
            <p className="text-sm text-fg-muted">
              This installation is not configured with Firebase, so there is no Google or
              account-based sign-in to offer. Use the administrator credentials below — they are
              the ones set when this instance was deployed.
            </p>
          )}

          {isFirebaseConfigured && !directOpen && (
            <button
              type="button"
              onClick={() => setDirectOpen(true)}
              className="btn-ghost w-full justify-center text-xs"
            >
              Sign in with a username and password instead
            </button>
          )}

          {directOpen && (
            <div className={isFirebaseConfigured ? 'space-y-3 border-t border-line pt-4' : 'space-y-3'}>
              {isFirebaseConfigured && (
                <div>
                  <p className="text-sm font-medium text-fg">Framework account</p>
                  <p className="text-xs text-fg-muted">
                    Signs in against the API directly, without Firebase.
                  </p>
                </div>
              )}

              <form onSubmit={handleDirectSignIn} className="space-y-3">
                <div>
                  <label htmlFor="direct-username" className="label mb-1.5 block">
                    Username or email
                  </label>
                  <input
                    id="direct-username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    className="input w-full"
                    autoComplete="username"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="direct-password" className="label mb-1.5 block">
                    Password
                  </label>
                  <input
                    id="direct-password"
                    type="password"
                    value={directPassword}
                    onChange={(e) => setDirectPassword(e.target.value)}
                    placeholder="••••••••"
                    className="input w-full"
                    autoComplete="current-password"
                    required
                  />
                </div>
                <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
                  {loading ? 'Signing in…' : 'Sign in'}
                </button>
              </form>
            </div>
          )}
        </div>

        <p className="text-center text-xs text-fg-subtle">
          By signing in you agree to the Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}
