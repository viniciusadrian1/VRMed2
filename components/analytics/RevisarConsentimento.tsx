"use client";

import { isAnalyticsConfigured } from "@/lib/analytics";
import { useVRMedStore } from "@/lib/store";

/**
 * Reabre a escolha de telemetria na /privacidade. A política promete que dá
 * para recusar a qualquer momento, mas o banner some depois da primeira
 * decisão; limpar os dados do site apagaria também sessões e anotações.
 */
export function RevisarConsentimento() {
  const consent = useVRMedStore((s) => s.analyticsConsent);
  const hasHydrated = useVRMedStore((s) => s.hasHydrated);

  if (!hasHydrated || consent === null || !isAnalyticsConfigured()) return null;

  return (
    <button
      type="button"
      className="mt-3 text-sm font-medium text-primary underline underline-offset-2"
      onClick={() => {
        // O persist grava na hora no localStorage. O reload é necessário porque
        // o script do Umami já carregado segue contando pageviews mesmo depois
        // que o <Script> desmonta; ao voltar, o banner reaparece.
        useVRMedStore.getState().setConsent(null);
        window.location.reload();
      }}
    >
      {consent === "granted" ? "Revogar consentimento" : "Rever minha escolha"}
    </button>
  );
}
