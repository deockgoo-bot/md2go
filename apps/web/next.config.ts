import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    NEXT_PUBLIC_API_KEY: process.env.NEXT_PUBLIC_API_KEY ?? "GVtAX-oXEPYwiJXRT44gUyDPmQfT3Olre9dYRoMweARjwVpjiWjkz8DVovRbOozp",
  },
};

export default nextConfig;
