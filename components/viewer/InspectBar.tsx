"use client";

import { MousePointerClick, X } from "lucide-react";
import { useVRMedStore } from "@/lib/store";
import { Button } from "@/components/ui/button";

/**
 * Barra de identificação: clicar numa estrutura do modelo mostra o que ela é.
 * Para os modelos de sistema (sem nomes anatômicos por malha), exibe o tecido;
 * para modelos com malhas nomeadas, exibe o nome da estrutura.
 */
export function InspectBar() {
  const hasModel = useVRMedStore((s) => s.layers.length > 0);
  const annotationMode = useVRMedStore((s) => s.annotationMode);
  const inspectedLabel = useVRMedStore((s) => s.inspectedLabel);
  const setInspectedLabel = useVRMedStore((s) => s.setInspectedLabel);

  // No modo de marcação, o clique cria anotações — não identifica.
  if (!hasModel || annotationMode) return null;

  return (
    <div
      className="pointer-events-auto absolute bottom-5 left-1/2 -translate-x-1/2"
      aria-live="polite"
    >
      {inspectedLabel ? (
        <div className="flex items-center gap-2 rounded-full border border-border bg-card py-1 pl-3 pr-1 shadow-lg">
          <MousePointerClick className="size-4 shrink-0 text-primary" />
          <span className="text-sm">
            <span className="text-muted-foreground">Estrutura: </span>
            <span className="font-medium">{inspectedLabel}</span>
          </span>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setInspectedLabel(null)}
            aria-label="Limpar identificação"
          >
            <X />
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 rounded-full border border-border bg-card/90 px-3 py-1.5 text-xs text-muted-foreground shadow-sm backdrop-blur-sm">
          <MousePointerClick className="size-3.5" />
          Clique numa estrutura para identificá-la
        </div>
      )}
    </div>
  );
}
