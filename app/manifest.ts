import type { MetadataRoute } from "next";

/** Manifesto web — torna o VRmed instalável como PWA (tela inicial, standalone). */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "VRmed — Estudo de anatomia em 3D e realidade virtual",
    short_name: "VRmed",
    description:
      "Estude anatomia com modelos 3D interativos, cortes anatômicos, realidade virtual e um tutor de IA fundamentado em fontes médicas confiáveis.",
    start_url: "/",
    display: "standalone",
    background_color: "#f8f7f4",
    theme_color: "#0f4c81",
    lang: "pt-BR",
    categories: ["education", "medical", "health"],
    icons: [
      {
        src: "/icon.svg",
        type: "image/svg+xml",
        sizes: "any",
        purpose: "any",
      },
      {
        src: "/apple-icon",
        type: "image/png",
        sizes: "180x180",
        purpose: "maskable",
      },
    ],
  };
}
