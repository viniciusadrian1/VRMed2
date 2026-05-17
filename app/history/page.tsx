"use client";

import Link from "next/link";
import { History } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { SessionList } from "@/components/history/SessionList";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useVRMedStore } from "@/lib/store";

/** Estado exibido quando ainda não há sessões salvas. */
function EmptyHistory() {
  return (
    <div className="grid place-items-center py-16">
      <div className="flex max-w-sm flex-col items-center gap-4 text-center">
        <span className="grid size-14 place-items-center rounded-2xl bg-accent text-accent-foreground">
          <History className="size-7" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-medium">
            Nenhuma sessão salva
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Estude um órgão no visualizador e salve a sessão para retomá-la
            depois ou exportá-la em PDF.
          </p>
        </div>
        <Button asChild>
          <Link href="/viewer">Abrir o visualizador</Link>
        </Button>
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const hasHydrated = useVRMedStore((s) => s.hasHydrated);
  const sessions = useVRMedStore((s) => s.sessions);

  return (
    <AppShell
      title="Histórico de estudo"
      description="Sessões salvas neste navegador"
    >
      {!hasHydrated ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} className="h-64 rounded-xl" />
          ))}
        </div>
      ) : sessions.length === 0 ? (
        <EmptyHistory />
      ) : (
        <SessionList sessions={sessions} />
      )}
    </AppShell>
  );
}
