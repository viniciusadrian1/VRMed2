"use client";

import { Crosshair, MapPin, Plus, Trash2 } from "lucide-react";
import { Html } from "@react-three/drei";
import { track } from "@/lib/analytics";
import { useVRMedStore } from "@/lib/store";
import { viewerBridge } from "@/lib/viewer-bridge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";

/* -------------------------------------------------------------------------- */
/* Hotspots renderizados dentro do Canvas                                      */
/* -------------------------------------------------------------------------- */

/** Pontos clicáveis sobre o modelo, com rótulo flutuante e oclusão. */
export function AnnotationHotspots() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  const byOrgan = useVRMedStore((s) => s.annotationsByOrgan);
  const annotations = organId ? (byOrgan[organId] ?? []) : [];

  if (!organId || annotations.length === 0) return null;

  return (
    <>
      {annotations.map((annotation, index) => (
        <Html
          key={annotation.id}
          position={annotation.position}
          center
          occlude
          zIndexRange={[24, 0]}
        >
          <button
            type="button"
            onClick={() => {
              viewerBridge.frameTo(annotation.position);
              track("annotation_clicked", { organ: organId });
            }}
            className="flex items-center gap-1.5"
            aria-label={`Anotação ${index + 1}: ${annotation.text || "sem descrição"}`}
          >
            <span
              className="grid size-6 shrink-0 place-items-center rounded-full text-xs font-semibold text-white shadow-md ring-2 ring-white/75"
              style={{ backgroundColor: annotation.color }}
            >
              {index + 1}
            </span>
            {!annotation.hideLabel && annotation.text && (
              <span className="max-w-44 truncate rounded-md bg-card px-2 py-1 text-xs font-medium text-card-foreground shadow-md">
                {annotation.text}
              </span>
            )}
          </button>
        </Html>
      ))}
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* Painel de gerenciamento de anotações                                        */
/* -------------------------------------------------------------------------- */

/** Painel lateral para criar, editar e remover anotações. */
export function AnnotationPanel() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  const byOrgan = useVRMedStore((s) => s.annotationsByOrgan);
  const annotationMode = useVRMedStore((s) => s.annotationMode);
  const setAnnotationMode = useVRMedStore((s) => s.setAnnotationMode);
  const updateAnnotation = useVRMedStore((s) => s.updateAnnotation);
  const removeAnnotation = useVRMedStore((s) => s.removeAnnotation);
  const hasModel = useVRMedStore((s) => s.layers.length > 0);

  if (!hasModel || !organId) {
    return (
      <p className="px-4 py-10 text-center text-sm text-muted-foreground">
        Carregue um modelo para criar anotações.
      </p>
    );
  }

  const annotations = byOrgan[organId] ?? [];

  return (
    <div className="flex flex-col gap-3 p-3">
      <Button
        variant={annotationMode ? "default" : "outline"}
        onClick={() => setAnnotationMode(!annotationMode)}
      >
        <Plus />
        {annotationMode ? "Marcação ativa — toque no modelo" : "Adicionar anotação"}
      </Button>

      {annotationMode && (
        <p className="rounded-md bg-accent px-3 py-2 text-xs text-accent-foreground">
          Clique sobre uma estrutura do modelo 3D para marcar um ponto. Desative
          o modo quando terminar.
        </p>
      )}

      {annotations.length === 0 ? (
        <p className="px-2 py-6 text-center text-sm text-muted-foreground">
          Nenhuma anotação neste modelo ainda.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {annotations.map((annotation, index) => (
            <li
              key={annotation.id}
              className="rounded-lg border border-border p-2.5"
            >
              <div className="flex items-center gap-2">
                <span
                  className="grid size-6 shrink-0 place-items-center rounded-full text-xs font-semibold text-white"
                  style={{ backgroundColor: annotation.color }}
                >
                  {index + 1}
                </span>
                <Input
                  value={annotation.text}
                  placeholder="Descrição da estrutura"
                  onChange={(event) =>
                    updateAnnotation(organId, annotation.id, {
                      text: event.target.value,
                    })
                  }
                  className="h-8"
                />
              </div>
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="color"
                  value={annotation.color}
                  onChange={(event) =>
                    updateAnnotation(organId, annotation.id, {
                      color: event.target.value,
                    })
                  }
                  className="size-7 cursor-pointer rounded-md border border-border bg-transparent"
                  aria-label="Cor da anotação"
                />
                <label className="flex flex-1 cursor-pointer items-center gap-1.5 text-xs">
                  <Checkbox
                    checked={annotation.hideLabel}
                    onCheckedChange={(checked) =>
                      updateAnnotation(organId, annotation.id, {
                        hideLabel: checked === true,
                      })
                    }
                  />
                  Ocultar texto (quiz)
                </label>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => viewerBridge.frameTo(annotation.position)}
                  aria-label="Voar até a anotação"
                  title="Voar até"
                >
                  <Crosshair />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => removeAnnotation(organId, annotation.id)}
                  aria-label="Excluir anotação"
                  title="Excluir"
                >
                  <Trash2 />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <MapPin className="size-3" />
        As anotações são salvas por modelo e incluídas na exportação em PDF.
      </p>
    </div>
  );
}
