"use client";

import { Html } from "@react-three/drei";
import { track } from "@/lib/analytics";
import { useVRMedStore } from "@/lib/store";
import { viewerBridge } from "@/lib/viewer-bridge";

/**
 * Marcadores numerados sobre as estruturas principais do modelo.
 * Clicar num ponto aproxima a câmera e identifica a estrutura na barra
 * inferior. Ficam ocultos no modo de marcação — lá o clique cria anotações.
 *
 * Usam oclusão (`occlude`): um ponto numa face virada para longe da câmera
 * fica escondido atrás do modelo — para vê-lo, gira-se até essa face. Isso
 * evita a poluição visual de ver pontos do lado oposto atravessando o 3D.
 */
export function StructureHotspots() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  const structures = useVRMedStore((s) => s.structures);
  const show = useVRMedStore((s) => s.showStructurePoints);
  const annotationMode = useVRMedStore((s) => s.annotationMode);
  const inspectedLabel = useVRMedStore((s) => s.inspectedLabel);
  const setInspectedLabel = useVRMedStore((s) => s.setInspectedLabel);

  if (!organId || !show || annotationMode || structures.length === 0) {
    return null;
  }

  return (
    <>
      {structures.map((structure, index) => {
        const active = inspectedLabel === structure.label;
        return (
          <Html
            key={structure.id}
            position={structure.position}
            center
            occlude
            zIndexRange={[18, 0]}
          >
            <button
              type="button"
              onClick={() => {
                setInspectedLabel(structure.label);
                viewerBridge.frameTo(structure.position);
                track("structure_inspected", {
                  organ: organId,
                  structure: structure.label,
                });
              }}
              className="group/point relative flex cursor-pointer items-center justify-center"
              aria-label={`Estrutura ${index + 1}: ${structure.label}`}
            >
              <span
                className={`grid size-6 place-items-center rounded-full text-[11px] font-bold shadow-md ring-2 transition-transform group-hover/point:scale-110 ${
                  active
                    ? "bg-white text-primary ring-primary"
                    : "bg-primary text-primary-foreground ring-white/85"
                }`}
              >
                {index + 1}
              </span>
              <span className="pointer-events-none absolute left-1/2 top-[calc(100%+4px)] -translate-x-1/2 whitespace-nowrap rounded-md bg-card px-2 py-1 text-xs font-medium text-card-foreground opacity-0 shadow-lg transition-opacity group-hover/point:opacity-100">
                {structure.label}
              </span>
            </button>
          </Html>
        );
      })}
    </>
  );
}
