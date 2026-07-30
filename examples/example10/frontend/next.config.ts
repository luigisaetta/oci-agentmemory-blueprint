import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Permit local IP access to development-only HMR resources.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
