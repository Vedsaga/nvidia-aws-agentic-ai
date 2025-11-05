import type { NextConfig } from "next";
import path from "path";
import * as dotenv from "dotenv";

// Load repository-root .env (one level above the `frontend` folder) so the
// frontend can use a single .env at the repo root as requested.
dotenv.config({ path: path.resolve(__dirname, "..", ".env") });

const nextConfig: NextConfig = {
  env: {
    // Surface the shared API gateway env to the client bundle while keeping explicit override support
    // Values can still be overridden by environment variables when running the dev server or build.
    APP_API_GATEWAY_URL: process.env.APP_API_GATEWAY_URL ?? process.env.APP_API_GATEWAY_URL ?? "",
  },
};

export default nextConfig;
