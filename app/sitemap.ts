import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site-url";

/** Mapa do site com as rotas públicas (exclui as páginas administrativas). */
export default function sitemap(): MetadataRoute.Sitemap {
  const routes = [
    "",
    "/viewer",
    "/compare",
    "/quiz",
    "/sala",
    "/duelo",
    "/clinica",
    "/arena",
    "/history",
    "/privacidade",
  ];
  return routes.map((path) => ({
    url: `${SITE_URL}${path}`,
    changeFrequency: "monthly",
    priority: path === "" ? 1 : 0.8,
  }));
}
