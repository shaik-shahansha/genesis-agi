/**
 * Origin resolution for the Genesis web app.
 *
 * Deployment default is SAME-ORIGIN: NEXT_PUBLIC_API_URL is empty, so the
 * browser talks to the API through the same host/port that served the page
 * (nginx proxies /api/ to the FastAPI service inside the single-container image).
 *
 * Set NEXT_PUBLIC_API_URL to an absolute URL only when the API is served from a
 * different origin than the web app.
 *
 * NOTE: NEXT_PUBLIC_* values are inlined at BUILD time, so changing this
 * requires rebuilding the image.
 */

const configuredApiUrl = (process.env.NEXT_PUBLIC_API_URL ?? '').trim();

/**
 * Base URL prepended to API paths.
 * Empty string => relative, same-origin requests (API paths already include
 * the /api/v1 prefix).
 */
export const API_BASE_URL = configuredApiUrl.replace(/\/+$/, '');

/** Absolute HTTP origin for the API, resolved from the browser if needed. */
export function resolveApiOrigin(): string {
  if (/^https?:\/\//i.test(API_BASE_URL)) {
    return API_BASE_URL;
  }
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }
  return '';
}

/** Join the API base with a path, for fetch calls. */
export function apiUrl(path: string): string {
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${suffix}`;
}

/**
 * Build an absolute WebSocket URL for an API path.
 *
 * `new WebSocket()` requires an absolute ws:// or wss:// URL, so a relative API
 * base must be upgraded using window.location. This is what makes the
 * single-container (same-origin) deployment work — including behind a TLS
 * terminator, where the page is https and therefore wss is required.
 */
export function buildWebSocketUrl(path: string): string {
  const suffix = path.startsWith('/') ? path : `/${path}`;

  if (/^https?:\/\//i.test(API_BASE_URL)) {
    return `${API_BASE_URL.replace(/^http/i, 'ws')}${suffix}`;
  }

  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}${suffix}`;
  }

  // Server-side rendering: no socket is opened, return the relative path.
  return suffix;
}
