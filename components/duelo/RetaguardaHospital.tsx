"use client";

import { useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { FaixaReativa } from "./ArenaMedica";
import { TelaoDuelo } from "./TelaoDuelo";
import { useEstadoArena } from "./EstadoArena";
import { monitorDoAmbiente } from "@/lib/monitor-ambiente";
import { useReflexosCenario } from "./useReflexosCenario";

const CAMINHO = "/models/props/retaguarda-arena-acabada.glb";
const SEM_RAYCAST = () => null;

/** Oito malhas de cenário autoral; todas fora da circulação e sem interação. */
export function RetaguardaHospital() {
  const monitor = monitorDoAmbiente(useEstadoArena());
  const gltf = useGLTF(CAMINHO);
  const cena = useMemo(() => {
    const clone = gltf.scene.clone(true);
    clone.traverse((obj) => { if (obj instanceof THREE.Mesh) obj.raycast = SEM_RAYCAST; });
    return clone;
  }, [gltf.scene]);
  useReflexosCenario(cena);
  return <group pointerEvents="none">
    <primitive object={cena} dispose={null} />
    {/* A mesma superfície do telão cobre a antiga inscrição fixa "Em espera". */}
    <group position={[-4.006, 1.715, 2.65]} rotation={[0, Math.PI / 2, 0]}>
      <TelaoDuelo compacto position={[0, 0, 0]} tamanho={[.70, .23]} texto={monitor.texto} cor={monitor.cor} />
    </group>
    {/* Contatos estáticos agora fazem parte do piso, sem cinco planos transparentes. */}
    {/* Sinal discreto da partida ao olhar para trás, sem outra luz dinâmica. */}
    <FaixaReativa pos={[0, 2.55, 4.295]} tam={[2.30, .018, .012]} />
    <FaixaReativa pos={[-2.95, 2.12, 4.205]} tam={[2.05, .012, .012]} />
  </group>;
}

useGLTF.preload(CAMINHO);
