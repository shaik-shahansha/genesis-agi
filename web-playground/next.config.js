/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV === 'development';

const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,

  // Emit a self-contained server bundle (.next/standalone) so the web app can be
  // shipped inside the same container as the Genesis API. See Dockerfile.
  output: 'standalone',

  env: {
    // Production default is EMPTY => same-origin: the browser calls /api/v1/...
    // on the host that served the page. This is what makes the single-container,
    // single-port deployment work (no CORS, no baked hostname, no TLS bypass).
    // Development keeps an explicit localhost fallback for `next dev`.
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ?? (isDev ? 'http://localhost:8000' : ''),
  },

  // SECURITY: the previous `webpack` hook here disabled TLS certificate
  // verification (NODE_TLS_REJECT_UNAUTHORIZED=0). It has been removed; it
  // weakened integrity for every outbound HTTPS request made by the dev/build
  // process. See docs/v3/SECURITY_BASELINE.md (SEC-18).
}

module.exports = nextConfig
