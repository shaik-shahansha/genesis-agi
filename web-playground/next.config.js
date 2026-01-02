/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  // Disable SSL verification for external resources (fonts, etc.)
  // This fixes the UNABLE_TO_GET_ISSUER_CERT_LOCALLY error
  experimental: {
    // Disable strict SSL for development
  },
  webpack: (config) => {
    // Allow self-signed certificates in development
    if (process.env.NODE_ENV === 'development') {
      process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
    }
    return config;
  },
}

module.exports = nextConfig
