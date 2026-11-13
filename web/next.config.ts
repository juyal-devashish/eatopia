import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Vercel builds Next.js natively. The Docker image and the end-to-end runs ask for a self-contained server.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
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
