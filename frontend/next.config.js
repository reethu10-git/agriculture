const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.resolve(__dirname),
  async rewrites() {
    // When API_BACKEND_URL is explicitly configured (e.g. separate backend host)
    if (process.env.API_BACKEND_URL) {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.API_BACKEND_URL}/api/:path*`,
        },
      ];
    }
    // In local development without API_BACKEND_URL, proxy to local FastAPI on 8000
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: 'http://127.0.0.1:8000/api/:path*',
        },
      ];
    }
    // In production Vercel deployment (same origin), return empty rewrites
    // so Vercel edge routes /api/* directly to the Python serverless function.
    return [];
  },
};

module.exports = nextConfig;

