"use client";

import { useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";

const CAMINHO = "/models/props/entorno-arena.glb";

/** Oito malhas agrupadas por material; equipamentos autorais em escala métrica. */
export function EntornoHospital() {
  const gltf = useGLTF(CAMINHO);
  const cena = useMemo(() => {
    const clone = gltf.scene.clone(true);
    clone.traverse((obj) => {
      if (obj instanceof THREE.Mesh) obj.raycast = () => null;
    });
    return clone;
  }, [gltf.scene]);
  return <group pointerEvents="none"><primitive object={cena} dispose={null} /></group>;
}

useGLTF.preload(CAMINHO);
