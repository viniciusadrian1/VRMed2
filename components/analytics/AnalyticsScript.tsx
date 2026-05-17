"use client";

import Script from "next/script";
import { useVRMedStore } from "@/lib/store";

/**
 * Injeta o script de analytics (Umami) apenas após consentimento explícito.
 * Sem consentimento ou sem configuração, nada é carregado — nenhuma requisição
 * de terceiros é feita, em conformidade com a LGPD.
 */
export function AnalyticsScript() {
  const consent = useVRMedStore((s) => s.analyticsConsent);

  const url = process.env.NEXT_PUBLIC_ANALYTICS_URL;
  const websiteId = process.env.NEXT_PUBLIC_ANALYTICS_ID;

  if (consent !== "granted" || !url || !websiteId) return null;

  return (
    <Script
      defer
      strategy="afterInteractive"
      src={`${url.replace(/\/$/, "")}/script.js`}
      data-website-id={websiteId}
    />
  );
}
