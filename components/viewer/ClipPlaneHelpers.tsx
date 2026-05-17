"use client";

import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { getClipCut } from "@/lib/model-utils";
import { useVRMedStore } from "@/lib/store";
import type { ClipAxis } from "@/types";

const CLIP_AXES: ClipAxis[] = ["axial", "sagital", "coronal"];

/** Rotação do quad-helper para alinhar com o plano de cada eixo. */
const HELPER_ROTATION: Record<ClipAxis, [number, number, number]> = {
  axial: [-Math.PI / 2, 0, 0], // plano horizontal (XZ)
  sagital: [0, Math.PI / 2, 0], // plano sagital (YZ)
  coronal: [0, 0, 0], // plano coronal (XY)
};

/**
 * Visualização sutil dos planos de corte: um quad translúcido aparece sobre
 * cada plano ativo logo após o usuário ajustá-lo e some em ~1 segundo.
 */
export function ClipPlaneHelpers() {
  const clipping = useVRMedStore((s) => s.clipping);
  const bounds = useVRMedStore((s) => s.modelBounds);
  const clipTouchedAt = useVRMedStore((s) => s.clipTouchedAt);
  const invalidate = useThree((s) => s.invalidate);

  const materials = useRef<Record<ClipAxis, THREE.MeshBasicMaterial | null>>({
    axial: null,
    sagital: null,
    coronal: null,
  });

  useFrame(() => {
    const age = Date.now() - clipTouchedAt;
    const fade = Math.max(0, Math.min(1, 1 - age / 1000));
    let animating = false;

    for (const axis of CLIP_AXES) {
      const material = materials.current[axis];
      if (!material) continue;
      const visible = clipping[axis].enabled ? fade * 0.22 : 0;
      material.opacity = visible;
      if (clipping[axis].enabled && fade > 0) animating = true;
    }

    if (animating) invalidate();
  });

  if (!bounds) return null;

  return (
    <>
      {CLIP_AXES.map((axis) => {
        const state = clipping[axis];
        if (!state.enabled) return null;

        const cut = getClipCut(axis, state.position, bounds);
        const [cx, cy, cz] = bounds.center;
        const position: [number, number, number] =
          axis === "axial"
            ? [cx, cut, cz]
            : axis === "sagital"
              ? [cut, cy, cz]
              : [cx, cy, cut];

        return (
          <mesh
            key={axis}
            position={position}
            rotation={HELPER_ROTATION[axis]}
            renderOrder={999}
          >
            <planeGeometry args={[3, 3]} />
            <meshBasicMaterial
              ref={(material) => {
                materials.current[axis] = material;
              }}
              color="#0f4c81"
              transparent
              opacity={0}
              depthWrite={false}
              side={THREE.DoubleSide}
            />
          </mesh>
        );
      })}
    </>
  );
}
