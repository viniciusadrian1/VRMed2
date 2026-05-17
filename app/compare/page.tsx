"use client";

import { useEffect, useRef, useState } from "react";
import { Link2, Link2Off, SplitSquareHorizontal } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { SplitView } from "@/components/compare/SplitView";
import type { CameraSyncState } from "@/components/compare/SyncedCameras";
import { Button } from "@/components/ui/button";
import { track } from "@/lib/analytics";
import { COMPARISON_NOTES, getComparableOrgans } from "@/lib/organs";
import type { OrganDefinition } from "@/types";

/** Painel inferior com a legenda das diferenças anatômicas. */
function ComparisonLegend({ organ }: { organ: OrganDefinition }) {
  const notes = COMPARISON_NOTES[organ.id] ?? [];
  return (
    <div className="shrink-0 border-t border-border bg-card px-4 py-3">
      <div className="mx-auto flex max-w-4xl flex-col gap-2">
        <div className="flex items-center gap-2">
          <SplitSquareHorizontal className="size-4 text-primary" />
          <h2 className="text-sm font-semibold">
            {organ.name}: saudável vs. {organ.pathologyName}
          </h2>
        </div>
        <ul className="grid gap-1.5 sm:grid-cols-2">
          {notes.map((note) => (
            <li
              key={note}
              className="flex gap-2 text-xs text-muted-foreground"
            >
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" />
              {note}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function ComparePage() {
  const comparable = getComparableOrgans();
  const [organId, setOrganId] = useState<string | null>(
    comparable[0]?.id ?? null,
  );
  const [synced, setSynced] = useState(true);
  const syncRef = useRef<CameraSyncState>({
    pos: [3, 2, 4],
    target: [0, 0, 0],
    epoch: 0,
  });

  const organ = comparable.find((item) => item.id === organId);

  // Telemetria + reinício do estado de câmera ao trocar de par.
  useEffect(() => {
    if (!organId) return;
    syncRef.current = { pos: [3, 2, 4], target: [0, 0, 0], epoch: 0 };
    track("compare_mode_used", { pair: organId });
  }, [organId]);

  return (
    <AppShell
      title="Comparação anatômica"
      description="Anatomia saudável vs. patológica"
      fullBleed
      actions={
        <Button
          variant={synced ? "default" : "outline"}
          size="sm"
          onClick={() => setSynced((value) => !value)}
        >
          {synced ? <Link2 /> : <Link2Off />}
          {synced ? "Câmeras sincronizadas" : "Câmeras independentes"}
        </Button>
      }
    >
      <div className="flex h-full flex-col">
        <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-border bg-card px-4 py-2">
          <span className="text-xs font-medium text-muted-foreground">
            Comparar:
          </span>
          {comparable.map((item) => (
            <Button
              key={item.id}
              variant={item.id === organId ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setOrganId(item.id)}
            >
              {item.name}
            </Button>
          ))}
        </div>

        {organ ? (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="min-h-0 flex-1">
              <SplitView
                key={organ.id}
                organ={organ}
                synced={synced}
                syncRef={syncRef}
              />
            </div>
            <ComparisonLegend organ={organ} />
          </div>
        ) : (
          <div className="grid flex-1 place-items-center text-sm text-muted-foreground">
            Nenhum par de modelos disponível para comparação.
          </div>
        )}
      </div>
    </AppShell>
  );
}
