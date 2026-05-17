import { useVRMedStore } from "@/lib/store";
import type { AnalyticsEvent } from "@/types";

declare global {
  interface Window {
    umami?: {
      track: (event: string, data?: Record<string, unknown>) => void;
    };
  }
}

/** Indica se as variáveis de analytics foram configuradas no ambiente. */
export function isAnalyticsConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_ANALYTICS_URL && process.env.NEXT_PUBLIC_ANALYTICS_ID,
  );
}

/**
 * Registra um evento de telemetria anônimo.
 *
 * Wrapper exigido pela camada de pesquisa: só envia dados quando o usuário
 * concedeu consentimento explícito (LGPD) e quando o analytics está configurado.
 * Qualquer falha é silenciada — telemetria nunca deve interromper o estudo.
 */
export function track(
  event: AnalyticsEvent,
  properties?: Record<string, unknown>,
): void {
  if (typeof window === "undefined") return;
  if (useVRMedStore.getState().analyticsConsent !== "granted") return;
  if (!isAnalyticsConfigured()) return;

  try {
    window.umami?.track(event, properties);
  } catch {
    /* telemetria é best-effort: ignora erros de rede ou de script ausente */
  }
}
