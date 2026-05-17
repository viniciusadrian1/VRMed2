import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Cabeçalhos para permitir rastreamento espacial do WebXR (VR/AR no navegador)
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Permissions-Policy",
            value: "xr-spatial-tracking=(self), camera=(self), microphone=(self)",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
