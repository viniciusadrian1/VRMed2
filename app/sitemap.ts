import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://vrmed.vercel.app";

/** Mapa do site com as rotas públicas (exclui as páginas administrativas). */
export default function sitemap(): MetadataRoute.Sitemap {
  const routes = ["", "/viewer", "/compare", "/quiz", "/history", "/privacidade"];
  return routes.map((path) => ({
    url: `${SITE_URL}${path}`,
    changeFrequency: "monthly",
    priority: path === "" ? 1 : 0.8,
  }));
}
