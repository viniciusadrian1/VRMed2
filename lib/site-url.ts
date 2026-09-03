/** URL base pública do site (canonical, Open Graph, sitemap, robots).
 *  Ordem: NEXT_PUBLIC_SITE_URL (explícita) → RENDER_EXTERNAL_URL (injetada pelo Render) → localhost. */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ??
  process.env.RENDER_EXTERNAL_URL ??
  "http://localhost:3000"
).replace(/\/$/, "");
