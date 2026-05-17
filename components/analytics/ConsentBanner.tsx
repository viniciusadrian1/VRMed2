"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { BarChart3 } from "lucide-react";
import { isAnalyticsConfigured } from "@/lib/analytics";
import { useVRMedStore } from "@/lib/store";
import { Button } from "@/components/ui/button";

/**
 * Banner discreto de consentimento de telemetria (LGPD).
 * Só aparece quando o analytics está configurado e o usuário ainda não decidiu.
 */
export function ConsentBanner() {
  const consent = useVRMedStore((s) => s.analyticsConsent);
  const hasHydrated = useVRMedStore((s) => s.hasHydrated);
  const setConsent = useVRMedStore((s) => s.setConsent);

  const visible = hasHydrated && consent === null && isAnalyticsConfigured();

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          role="dialog"
          aria-label="Consentimento de coleta de dados"
          initial={{ y: 90, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 90, opacity: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 28 }}
          className="fixed inset-x-4 bottom-4 z-[90] mx-auto max-w-2xl rounded-xl border border-border bg-card p-4 shadow-xl md:bottom-6"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
                <BarChart3 className="size-4.5" />
              </span>
              <p className="text-sm text-muted-foreground">
                O VRmed é um projeto de Iniciação Científica e coleta{" "}
                <strong className="font-medium text-foreground">
                  dados de uso anônimos
                </strong>{" "}
                para fins de pesquisa. Nenhuma informação pessoal é registrada.{" "}
                <Link
                  href="/privacidade"
                  className="font-medium text-primary underline underline-offset-2"
                >
                  Saiba mais
                </Link>
                .
              </p>
            </div>
            <div className="flex shrink-0 gap-2 sm:ml-auto">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConsent("denied")}
              >
                Recusar
              </Button>
              <Button size="sm" onClick={() => setConsent("granted")}>
                Aceitar
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
