"use client";

import { useCallback, useRef, useState, type RefObject } from "react";
import { Clock, Sparkles } from "lucide-react";
import { clamp } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import type { OrganDefinition } from "@/types";
import { CompareCanvas } from "./CompareCanvas";
import type { CameraSyncState } from "./SyncedCameras";

interface SplitViewProps {
  organ: OrganDefinition;
  synced: boolean;
  syncRef: RefObject<CameraSyncState>;
}

/** Divisão em tela com os dois canvas e um divisor arrastável. */
export function SplitView({ organ, synced, syncRef }: SplitViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);
  const [ratio, setRatio] = useState(0.5);
  // Sinaliza quando o lado patológico caiu no modelo de demonstração
  // (o .glb real ainda não existe), para exibir o aviso honesto.
  const [placeholder, setPlaceholder] = useState(false);
  const handleResolved = useCallback(
    (kind: "real" | "placeholder") => setPlaceholder(kind === "placeholder"),
    [],
  );

  return (
    <div
      ref={containerRef}
      className="relative flex h-full w-full select-none overflow-hidden"
    >
      {/* Lado saudável */}
      <div
        className="vrmed-radial relative h-full"
        style={{ width: `${ratio * 100}%` }}
      >
        <CompareCanvas
          path={organ.modelPath}
          variant="healthy"
          synced={synced}
          syncRef={syncRef}
        />
        <span className="absolute left-3 top-3 rounded-md bg-card/90 px-2.5 py-1 text-xs font-semibold shadow-sm backdrop-blur-sm">
          Saudável
        </span>
      </div>

      {/* Divisor arrastável */}
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Arraste para redimensionar"
        className="z-10 w-1.5 shrink-0 cursor-col-resize bg-border transition-colors hover:bg-primary"
        onPointerDown={(event) => {
          dragging.current = true;
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!dragging.current || !containerRef.current) return;
          const rect = containerRef.current.getBoundingClientRect();
          setRatio(clamp((event.clientX - rect.left) / rect.width, 0.22, 0.78));
        }}
        onPointerUp={(event) => {
          dragging.current = false;
          event.currentTarget.releasePointerCapture(event.pointerId);
        }}
      />

      {/* Lado patológico */}
      <div
        className="vrmed-radial relative h-full"
        style={{ width: `${(1 - ratio) * 100}%` }}
      >
        {organ.pathologicalPath ? (
          <>
            <CompareCanvas
              path={organ.pathologicalPath}
              variant="pathological"
              synced={synced}
              syncRef={syncRef}
              onResolved={handleResolved}
            />
            <div className="absolute right-3 top-3 flex flex-col items-end gap-1">
              <span className="rounded-md bg-card/90 px-2.5 py-1 text-xs font-semibold shadow-sm backdrop-blur-sm">
                {organ.pathologyName ?? "Patológico"}
              </span>
              {placeholder && (
                <>
                  <Badge
                    variant="outline"
                    className="bg-card/90 shadow-sm backdrop-blur-sm"
                  >
                    <Sparkles className="size-3" />
                    Modelo de demonstração
                  </Badge>
                  <span className="text-[11px] text-muted-foreground">
                    Modelo patológico real em preparação
                  </span>
                </>
              )}
            </div>
          </>
        ) : (
          <div className="grid size-full place-items-center p-6 text-center">
            <div className="flex max-w-xs flex-col items-center gap-3 text-muted-foreground">
              <span className="grid size-12 place-items-center rounded-xl bg-muted">
                <Clock className="size-6" />
              </span>
              <p className="text-sm">
                O modelo patológico deste órgão estará disponível em breve.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
