"use client";

import { Suspense, useLayoutEffect, useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const SEM_RAYCAST = () => null;
type Sala = "hospital" | "escola";

function PlacasExportadas({ sala }: { sala: Sala }) {
  const { scene } = useGLTF(`/models/props/sinalizacao-${sala}.glb`);
  const gl = useThree((s) => s.gl);
  useLayoutEffect(() => {
    // Filtro limitado para leitura oblíqua, aplicado uma vez à textura em cache.
    scene.traverse((obj) => {
      if (!(obj instanceof THREE.Mesh)) return;
      const materiais = Array.isArray(obj.material) ? obj.material : [obj.material];
      for (const material of materiais) {
        const mapa = (material as THREE.MeshStandardMaterial).map;
        if (mapa) {
          mapa.anisotropy = Math.min(4, gl.capabilities.getMaxAnisotropy());
          mapa.needsUpdate = true;
        }
      }
    });
  }, [scene, gl]);
  const cena = useMemo(() => {
    const clone = scene.clone(true);
    clone.traverse((obj) => {
      if (obj instanceof THREE.Mesh) obj.raycast = SEM_RAYCAST;
    });
    return clone;
  }, [scene]);
  // Geometria e textura pertencem ao cache do carregador, não ao clone.
  return <primitive object={cena} dispose={null} />;
}

/** Placas autoradas no Blender: texto impresso no próprio material, sem overlay. */
export function SinalizacaoCenario({ sala }: { sala: Sala }) {
  return <group pointerEvents="none" name={`sinalizacao-fisica-${sala}`}>
    <ErrorBoundary key={sala} fallback={null}>
      <Suspense fallback={null}><PlacasExportadas sala={sala} /></Suspense>
    </ErrorBoundary>
  </group>;
}
