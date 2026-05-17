"use client";

import { ArrowLeftRight, RotateCcw } from "lucide-react";
import { track } from "@/lib/analytics";
import { useVRMedStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import type { ClipAxis } from "@/types";

const AXES: { id: ClipAxis; label: string; hint: string }[] = [
  { id: "axial", label: "Axial", hint: "Plano horizontal (superior / inferior)" },
  { id: "sagital", label: "Sagital", hint: "Separa os lados esquerdo e direito" },
  { id: "coronal", label: "Coronal", hint: "Separa anterior e posterior" },
];

/** Painel de controle dos cortes anatômicos (clipping planes). */
export function ClippingPlaneControls() {
  const clipping = useVRMedStore((s) => s.clipping);
  const setClipPlane = useVRMedStore((s) => s.setClipPlane);
  const resetClipping = useVRMedStore((s) => s.resetClipping);
  const organId = useVRMedStore((s) => s.currentOrganId);
  const hasModel = useVRMedStore((s) => s.layers.length > 0);

  if (!hasModel) {
    return (
      <p className="px-4 py-10 text-center text-sm text-muted-foreground">
        Carregue um modelo para aplicar cortes anatômicos.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-3">
      <p className="text-xs text-muted-foreground">
        Ative planos de corte para revelar o interior do modelo. Cada plano é
        independente e pode ter o lado invertido.
      </p>

      {AXES.map((axis) => {
        const state = clipping[axis.id];
        return (
          <div key={axis.id} className="rounded-lg border border-border p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium">Corte {axis.label}</p>
                <p className="text-[11px] text-muted-foreground">{axis.hint}</p>
              </div>
              <Switch
                checked={state.enabled}
                aria-label={`Ativar corte ${axis.label}`}
                onCheckedChange={(checked) => {
                  setClipPlane(axis.id, { enabled: checked });
                  if (checked) {
                    track("clipping_plane_used", {
                      organ: organId,
                      axis: axis.id,
                    });
                  }
                }}
              />
            </div>
            <div
              className={cn(
                "mt-3 flex items-center gap-2 transition-opacity",
                !state.enabled && "pointer-events-none opacity-40",
              )}
            >
              <Slider
                value={[Math.round(state.position * 100)]}
                min={-100}
                max={100}
                step={1}
                disabled={!state.enabled}
                onValueChange={([value]) =>
                  setClipPlane(axis.id, { position: value / 100 })
                }
                aria-label={`Posição do corte ${axis.label}`}
                className="flex-1"
              />
              <Button
                variant={state.flipped ? "default" : "outline"}
                size="icon-sm"
                disabled={!state.enabled}
                onClick={() =>
                  setClipPlane(axis.id, { flipped: !state.flipped })
                }
                aria-label={`Inverter o lado do corte ${axis.label}`}
                title="Inverter o lado do corte"
              >
                <ArrowLeftRight />
              </Button>
            </div>
          </div>
        );
      })}

      <Button
        variant="ghost"
        size="sm"
        onClick={resetClipping}
        className="self-start"
      >
        <RotateCcw />
        Resetar cortes
      </Button>
    </div>
  );
}
