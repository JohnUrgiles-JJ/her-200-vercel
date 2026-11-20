import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "https://her-table-eight.up.railway.app";

const nextConfig: NextConfig = {
  // The Django backend requires trailing slashes; don't let Next strip them.
  skipTrailingSlashRedirect: true,
  // Proxy API calls to the Railway backend so the browser stays same-origin (no CORS needed).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*/` }];
  },
  /* config options here */
  experimental: {
    agentFeedback: true,
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
