/**
 * Session handling for the built-in (non-Firebase) authentication path.
 *
 * The playground previously only knew how to authenticate through Firebase. The
 * deployment guide calls Firebase *optional*, and the API has always exposed a
 * username/password JWT login at `POST /api/v1/auth/token` plus `GET
 * /api/v1/auth/me` - but the web app never used either. The result was that a
 * single-container install without Firebase could not be signed into at all, so
 * every page redirected to a login screen whose buttons could not work.
 *
 * This module is the missing half: it stores the JWT, validates it against the
 * API, and lets `AuthRequired` treat either credential as a session.
 */

import { apiUrl } from './urls';

export const SESSION_TOKEN_KEY = 'genesis_token';
export const SESSION_EMAIL_KEY = 'genesis_user_email';

export interface SessionUser {
  username: string;
  email: string | null;
  role: string;
  disabled?: boolean;
  /** How this session was established. */
  source: 'jwt';
}

export function getSessionToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(SESSION_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setSession(token: string, email?: string | null): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(SESSION_TOKEN_KEY, token);
    // Several existing components read this key directly.
    if (email) {
      localStorage.setItem(SESSION_EMAIL_KEY, email);
      localStorage.setItem('user_email', email);
    }
  } catch {
    /* storage unavailable */
  }
}

export function clearSession(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(SESSION_TOKEN_KEY);
    localStorage.removeItem('genesis_firebase_token');
  } catch {
    /* storage unavailable */
  }
}

/**
 * Exchange a username and password for an access token.
 *
 * `POST /api/v1/auth/token` is an OAuth2 password-grant endpoint, so the body
 * must be form-encoded rather than JSON.
 */
export async function loginWithPassword(
  username: string,
  password: string
): Promise<string> {
  const body = new URLSearchParams({ username, password });
  const response = await fetch(apiUrl('/api/v1/auth/token'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  if (!response.ok) {
    let detail = 'Incorrect username or password';
    try {
      const payload = await response.json();
      if (typeof payload?.detail === 'string') detail = payload.detail;
    } catch {
      /* keep the default message */
    }
    throw new Error(detail);
  }

  const payload = await response.json();
  const token: string | undefined = payload?.access_token;
  if (!token) {
    throw new Error('The server did not return an access token');
  }
  return token;
}

/**
 * How long to wait for the API to confirm a session before giving up.
 *
 * Without a bound, an API that accepts the connection and then never answers
 * leaves every guarded page on the "Checking your session…" spinner forever —
 * no error, no retry, no way forward, and no clue that the API is the problem
 * rather than the browser. A timeout turns that into an ordinary failure.
 */
const SESSION_CHECK_TIMEOUT_MS = 8000;

/**
 * Validate the stored token and fetch the identity it belongs to.
 *
 * Returns `null` when there is no token, when the API rejects it, or when the
 * check cannot complete. A network failure also returns `null` rather than
 * throwing: the caller treats an unverifiable session as no session, which is
 * the fail-closed direction for a UI that decides whether to show protected
 * data. The cost of that choice is that a transient outage signs the user out,
 * which is the right trade only because the alternative is showing data on the
 * strength of an unverified token.
 */
export async function loadSessionUser(): Promise<SessionUser | null> {
  const token = getSessionToken();
  if (!token) return null;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), SESSION_CHECK_TIMEOUT_MS);

  try {
    const response = await fetch(apiUrl('/api/v1/auth/me'), {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    });
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) clearSession();
      return null;
    }
    const data = await response.json();
    return {
      username: data.username ?? data.sub ?? 'user',
      email: data.email ?? null,
      role: data.role ?? 'user',
      disabled: data.disabled,
      source: 'jwt',
    };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}
