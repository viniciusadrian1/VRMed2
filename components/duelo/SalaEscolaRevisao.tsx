"use client";

import { useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { useReflexosCenario } from "./useReflexosCenario";

function Reflexos({ cena }: { cena: THREE.Object3D }) {
  useReflexosCenario(cena);
  return null;
}

function Modelo({ url, reflexos = false }: { url: string; reflexos?: boolean }) {
  const { scene } = useGLTF(url);
  const cena = useMemo(() => {
    const clone = scene.clone(true);
    clone.traverse(obj => { if (obj instanceof THREE.Mesh) obj.raycast = () => null; });
    return clone;
  }, [scene]);
  return <>{reflexos && <Reflexos cena={cena} />}<primitive object={cena} dispose={null} /></>;
}

/** Escola aprovada como padrão; os assets anteriores permanecem disponíveis para recuperação. */
export function SalaEscolaRevisao() {
  return <group pointerEvents="none">
    <Modelo url="/models/props/escola-medicina-revisao.glb" reflexos />
    <Modelo url="/models/props/piso-escola-revisao.glb" />
  </group>;
}
