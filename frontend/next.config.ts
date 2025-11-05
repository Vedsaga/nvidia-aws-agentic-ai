import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    // Surface the shared API gateway env to the client bundle while keeping explicit override support
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? process.env.APP_API_GATEWAY_URL ?? "",
  },
};

export default nextConfig;
