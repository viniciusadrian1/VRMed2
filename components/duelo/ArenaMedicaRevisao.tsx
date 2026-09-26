"use client";

import { useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { Bloco, ConsoleArena, FaixaReativa, PalcoAnatomico } from "./ArenaMedica";
import { useReflexosCenario } from "./useReflexosCenario";
import { useEstadoArena } from "./EstadoArena";
import { TelaoDuelo } from "./TelaoDuelo";
import { monitorDoAmbiente } from "@/lib/monitor-ambiente";

const AMBIENTE = "/models/props/arena-medica-revisao.glb";
const PISO = "/models/props/piso-arena-revisao.glb";

function Reflexos({ cena }: { cena: THREE.Object3D }) {
  useReflexosCenario(cena);
  return null;
}

function ModeloDecorativo({ caminho, reflexos = false }: { caminho: string; reflexos?: boolean }) {
  const gltf = useGLTF(caminho);
  const cena = useMemo(() => {
    const clone = gltf.scene.clone(true);
    clone.traverse(obj => { if (obj instanceof THREE.Mesh) obj.raycast = () => null; });
    return clone;
  }, [gltf.scene]);
  return <>{reflexos && <Reflexos cena={cena} />}<primitive object={cena} dispose={null} /></>;
}

/** Arena aprovada como padrão; cenário anterior preservado em AmbienteHospital. */
export function ArenaMedicaRevisao() {
  const monitor = monitorDoAmbiente(useEstadoArena());
  return <group pointerEvents="none">
    <PalcoAnatomico />
    <ConsoleArena />
    <group position={[0, -1.3, 0]}>
      <ModeloDecorativo caminho={AMBIENTE} reflexos />
      <ModeloDecorativo caminho={PISO} />
      {/* Mesmas referências espaciais do placar e dos estados, sem mover os alvos. */}
      <Bloco pos={[0, 2.81, -3.22]} tam={[2.5, .84, .16]} cor="#132a32" />
      <FaixaReativa pos={[0, 2.41, -3.133]} tam={[2.4, .018, .015]} />
      {[-1.95, 1.95].map(x => <FaixaReativa key={x} pos={[x, 1.95, -3.105]} tam={[.024, 2.3, .012]} />)}
      <group position={[-3.975, 1.76, 2.65]} rotation={[0, Math.PI / 2, 0]}>
        <TelaoDuelo compacto position={[0, 0, 0]} tamanho={[.70, .40]} texto={monitor.texto} cor={monitor.cor} />
      </group>
      <FaixaReativa pos={[0, 2.56, 4.30]} tam={[2.15, .018, .012]} />
    </group>
  </group>;
}
