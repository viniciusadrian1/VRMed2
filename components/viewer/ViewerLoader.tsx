"use client";

import { useProgress } from "@react-three/drei";
import { BrandMark } from "@/components/layout/Logo";
import { Progress } from "@/components/ui/progress";

/** Overlay de carregamento do modelo 3D, alimentado pelo progresso do GLTF. */
export function ViewerLoader() {
  const { active, progress } = useProgress();

  if (!active) return null;

  return (
    <div
      className="absolute inset-0 z-20 grid place-items-center bg-background/70 backdrop-blur-sm"
      role="status"
      aria-live="polite"
    >
      <div className="flex w-60 flex-col items-center gap-3">
        <BrandMark className="size-11 animate-pulse" />
        <p className="text-sm font-medium">Carregando modelo 3D…</p>
        <Progress value={progress} className="w-full" />
        <p className="text-xs tabular-nums text-muted-foreground">
          {Math.round(progress)}%
        </p>
      </div>
    </div>
  );
}
