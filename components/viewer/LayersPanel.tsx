"use client";

import { Eye, Focus, Palette, X } from "lucide-react";
import { track } from "@/lib/analytics";
import { useVRMedStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { MeshDepth } from "@/types";

const DEPTH_LABEL: Record<MeshDepth, string> = {
  external: "externa",
  intermediate: "intermediária",
  internal: "interna",
};

/** Seletor de cor de destaque por camada (opcional). */
function ColorControl({
  color,
  onChange,
}: {
  color: string | null;
  onChange: (color: string | null) => void;
}) {
  return (
    <div className="flex items-center">
      <label
        className="relative size-7 cursor-pointer overflow-hidden rounded-md border border-border"
        title="Cor de destaque"
      >
        <span
          className="block size-full"
          style={{ backgroundColor: color ?? "transparent" }}
        />
        {!color && (
          <span className="absolute inset-0 grid place-items-center text-muted-foreground">
            <Palette className="size-3.5" />
          </span>
        )}
        <input
          type="color"
          value={color ?? "#1e88e5"}
          onChange={(event) => onChange(event.target.value)}
          className="absolute inset-0 cursor-pointer opacity-0"
          aria-label="Cor de destaque da camada"
        />
      </label>
      {color && (
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onChange(null)}
          aria-label="Remover cor de destaque"
        >
          <X />
        </Button>
      )}
    </div>
  );
}

/** Painel de camadas anatômicas: visibilidade, opacidade, cor e raio-X. */
export function LayersPanel() {
  const layers = useVRMedStore((s) => s.layers);
  const organId = useVRMedStore((s) => s.currentOrganId);
  const xray = useVRMedStore((s) => s.xray);
  const applyXray = useVRMedStore((s) => s.applyXray);
  const setLayerVisibility = useVRMedStore((s) => s.setLayerVisibility);
  const setLayerOpacity = useVRMedStore((s) => s.setLayerOpacity);
  const setLayerColor = useVRMedStore((s) => s.setLayerColor);
  const isolateLayer = useVRMedStore((s) => s.isolateLayer);
  const showAllLayers = useVRMedStore((s) => s.showAllLayers);

  if (layers.length === 0) {
    return (
      <p className="px-4 py-10 text-center text-sm text-muted-foreground">
        Carregue um modelo para visualizar suas camadas anatômicas.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-3">
      <div className="flex items-center justify-between rounded-lg bg-muted px-3 py-2">
        <div className="flex items-center gap-2">
          <Switch
            checked={xray}
            aria-label="Modo raio-X"
            onCheckedChange={(checked) => {
              applyXray(checked);
              track("xray_mode_toggled", {
                organ: organId,
                enabled: checked,
              });
            }}
          />
          <span className="text-xs font-medium">Modo raio-X</span>
        </div>
        <Button variant="ghost" size="sm" onClick={showAllLayers}>
          <Eye />
          Mostrar tudo
        </Button>
      </div>

      <ul className="flex flex-col gap-2">
        {layers.map((layer) => (
          <li
            key={layer.name}
            className="rounded-lg border border-border p-2.5"
          >
            <div className="flex items-center gap-2">
              <Checkbox
                id={`layer-${layer.name}`}
                checked={layer.visible}
                onCheckedChange={(checked) => {
                  const visible = checked === true;
                  setLayerVisibility(layer.name, visible);
                  track("layer_visibility_changed", {
                    organ: organId,
                    layer: layer.name,
                    visible,
                  });
                }}
              />
              <label
                htmlFor={`layer-${layer.name}`}
                className="min-w-0 flex-1 cursor-pointer truncate text-sm font-medium"
              >
                {layer.label}
              </label>
              <span className="shrink-0 text-[10px] uppercase tracking-wide text-muted-foreground">
                {DEPTH_LABEL[layer.depth]}
              </span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => isolateLayer(layer.name)}
                    aria-label={`Isolar ${layer.label}`}
                  >
                    <Focus />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Isolar camada</TooltipContent>
              </Tooltip>
            </div>

            <div className="mt-2.5 flex items-center gap-2">
              <Slider
                value={[Math.round(layer.opacity * 100)]}
                min={0}
                max={100}
                step={1}
                onValueChange={([value]) =>
                  setLayerOpacity(layer.name, value / 100)
                }
                aria-label={`Opacidade de ${layer.label}`}
                className="flex-1"
              />
              <span className="w-9 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                {Math.round(layer.opacity * 100)}%
              </span>
              <ColorControl
                color={layer.color}
                onChange={(color) => setLayerColor(layer.name, color)}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
