"use client";

import {
  Box,
  Camera,
  CircleDot,
  Move3d,
  Rotate3d,
  RotateCcw,
  Scale3d,
  ScanLine,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { getOrganById } from "@/lib/organs";
import { useVRMedStore, type TransformMode } from "@/lib/store";
import { track } from "@/lib/analytics";
import { viewerBridge } from "@/lib/viewer-bridge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/** Botão de ícone com tooltip, usado na barra de ferramentas do visualizador. */
function ToolButton({
  label,
  icon,
  onClick,
  active,
  disabled,
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {/*
          Um <span> embrulha o botão para que a tooltip apareça mesmo quando
          ele está desabilitado (botões desabilitados não emitem eventos de
          ponteiro) — preserva a dica "por que está desabilitado".
        */}
        <span className="inline-flex">
          <Button
            variant={active ? "default" : "ghost"}
            size="icon"
            onClick={onClick}
            disabled={disabled}
            aria-label={label}
            aria-pressed={active}
          >
            {icon}
          </Button>
        </span>
      </TooltipTrigger>
      <TooltipContent side="right">{label}</TooltipContent>
    </Tooltip>
  );
}

/** Barra de ferramentas lateral fixa do visualizador 3D. */
export function ViewerControls() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  const hasModel = useVRMedStore((s) => s.layers.length > 0);
  const transformMode = useVRMedStore((s) => s.transformMode);
  const setTransformMode = useVRMedStore((s) => s.setTransformMode);
  const xray = useVRMedStore((s) => s.xray);
  const applyXray = useVRMedStore((s) => s.applyXray);
  const wireframe = useVRMedStore((s) => s.wireframe);
  const toggleWireframe = useVRMedStore((s) => s.toggleWireframe);
  const showStructurePoints = useVRMedStore((s) => s.showStructurePoints);
  const toggleStructurePoints = useVRMedStore((s) => s.toggleStructurePoints);
  const hasStructurePoints = useVRMedStore((s) => s.structures.length > 0);

  const toggleTransform = (mode: TransformMode) =>
    setTransformMode(transformMode === mode ? "none" : mode);

  const captureScreenshot = () => {
    const data = viewerBridge.capture();
    if (!data) return;
    const organ = getOrganById(organId);
    const link = document.createElement("a");
    link.href = data;
    link.download = `vrmed-${organ?.id ?? "modelo"}-${Date.now()}.png`;
    link.click();
  };

  const handleXray = () => {
    applyXray(!xray);
    track("xray_mode_toggled", { organ: organId, enabled: !xray });
  };

  return (
    <div className="flex w-14 shrink-0 flex-col items-center gap-1 border-r border-border bg-card py-3">
      <ToolButton
        label="Resetar vista"
        icon={<RotateCcw />}
        onClick={() => viewerBridge.resetCamera()}
        disabled={!hasModel}
      />
      <ToolButton
        label="Aproximar"
        icon={<ZoomIn />}
        onClick={() => viewerBridge.zoom(0.8)}
        disabled={!hasModel}
      />
      <ToolButton
        label="Afastar"
        icon={<ZoomOut />}
        onClick={() => viewerBridge.zoom(1.25)}
        disabled={!hasModel}
      />

      <Separator className="my-1.5 w-7" />

      <ToolButton
        label="Mover modelo"
        icon={<Move3d />}
        onClick={() => toggleTransform("translate")}
        active={transformMode === "translate"}
        disabled={!hasModel}
      />
      <ToolButton
        label="Rotacionar modelo"
        icon={<Rotate3d />}
        onClick={() => toggleTransform("rotate")}
        active={transformMode === "rotate"}
        disabled={!hasModel}
      />
      <ToolButton
        label="Escalar modelo"
        icon={<Scale3d />}
        onClick={() => toggleTransform("scale")}
        active={transformMode === "scale"}
        disabled={!hasModel}
      />

      <Separator className="my-1.5 w-7" />

      <ToolButton
        label={xray ? "Desativar raio-X" : "Modo raio-X"}
        icon={<ScanLine />}
        onClick={handleXray}
        active={xray}
        disabled={!hasModel}
      />
      <ToolButton
        label={wireframe ? "Ocultar aramado" : "Modo aramado"}
        icon={<Box />}
        onClick={toggleWireframe}
        active={wireframe}
        disabled={!hasModel}
      />
      <ToolButton
        label={
          hasStructurePoints
            ? showStructurePoints
              ? "Ocultar pontos de estrutura"
              : "Mostrar pontos de estrutura"
            : "Sem pontos de estrutura neste modelo"
        }
        icon={<CircleDot />}
        onClick={toggleStructurePoints}
        active={showStructurePoints && hasStructurePoints}
        disabled={!hasModel || !hasStructurePoints}
      />

      <Separator className="my-1.5 w-7" />

      <ToolButton
        label="Capturar imagem (PNG)"
        icon={<Camera />}
        onClick={captureScreenshot}
        disabled={!hasModel}
      />
    </div>
  );
}
