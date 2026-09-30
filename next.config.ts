import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Contêiner na CX33; o build da Vercel mantém seu formato original.
  ...(process.env.VRMED_STANDALONE === "1" ? { output: "standalone" as const } : {}),
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
