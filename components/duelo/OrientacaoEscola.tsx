"use client";

import { useMemo } from "react";
import * as THREE from "three";
import { Text3D } from "@/components/arena/ui3d";
import { ESCOLA, orientacaoDaEscola } from "@/lib/escola-apresentacao";
import { sinalDaArena } from "@/lib/duelo-apresentacao";
import { Bloco, FaixaReativa } from "./ArenaMedica";
import { useEstadoArena } from "./EstadoArena";

const SEM_RAYCAST = () => null;

/** Plaquetas de orientação apoiadas nas mesas; não são novos botões. */
export function OrientacaoEscola() {
  const estado = useEstadoArena();
  const sinal = sinalDaArena(estado);
  const zMesa = ESCOLA.postoZ - ESCOLA.mesaRecuo;
  return <group pointerEvents="none">
    {([true, false] as const).map((local) => <group key={String(local)}
      position={[local ? ESCOLA.jogadorX : ESCOLA.adversarioX, ESCOLA.piso + .90, zMesa + .12]}
      rotation={[-.35, 0, 0]}>
      <Bloco pos={[0, -.075, -.025]} tam={[.93, .12, .09]} cor="#28443f" />
      <Bloco pos={[0, 0, 0]} tam={[1.04, .18, .035]} cor="#142f30" />
      <Bloco pos={[-.485, 0, .023]} tam={[.02, .15, .008]} cor={local ? "#81d4e6" : "#ebbc72"} />
      <Text3D position={[0, .038, .025]} size={.041} color={local ? "#c8f2f7" : "#ffe2b0"}>
        {local ? "01 · SEU POSTO" : "02 · ADVERSÁRIO"}
      </Text3D>
      <Text3D position={[0, -.026, .025]} size={.027} maxWidth={.95} color={local ? sinal.cor : "#d9e6dd"}>
        {local ? orientacaoDaEscola(estado) : "Mesmo desafio · ao seu lado"}
      </Text3D>
      {local && <FaixaReativa pos={[0, -.074, .022]} tam={[.86, .006, .008]} />}
    </group>)}
  </group>;
}

/** Contato suave estilizado, não shadow map: planos de baixo custo no piso. */
export function ContatoEscola() {
  const { fase } = useEstadoArena();
  const mascara = useMemo(() => {
    const pixels = new Uint8Array(32 * 32 * 4);
    for (let y = 0; y < 32; y++) for (let x = 0; x < 32; x++) {
      const r = Math.hypot((x - 15.5) / 15.5, (y - 15.5) / 15.5);
      const valor = Math.round(255 * Math.max(0, 1 - r) ** 1.4);
      pixels.set([valor, valor, valor, 255], (y * 32 + x) * 4);
    }
    return pixels;
  }, []);
  const apoios = [
    { x: -.78, z: -.95, w: 1.35, h: 1.0, opacidade: .32 },
    { x: 1.82, z: -2.44, w: 1.5, h: .9, opacidade: .26 },
    ...[ESCOLA.jogadorX, ESCOLA.adversarioX].map((x) => ({ x, z: ESCOLA.postoZ - ESCOLA.mesaRecuo, w: 1.85, h: 1.1, opacidade: .24 })),
    ...(!["menu", "codigo", "sala"].includes(fase)
      ? [{ x: ESCOLA.adversarioX, z: ESCOLA.postoZ, w: .7, h: .6, opacidade: .32 }] : []),
  ];
  return <group pointerEvents="none">{apoios.map((p, i) => <mesh key={i}
    position={[p.x, ESCOLA.piso + .013, p.z]} rotation={[-Math.PI / 2, 0, 0]} raycast={SEM_RAYCAST}>
    <planeGeometry args={[p.w, p.h]} />
    <meshBasicMaterial color="#152626" transparent opacity={p.opacidade} depthWrite={false} toneMapped={false}>
      <dataTexture attach="alphaMap" args={[mascara, 32, 32, THREE.RGBAFormat]}
        needsUpdate minFilter={THREE.LinearFilter} magFilter={THREE.LinearFilter} />
    </meshBasicMaterial>
  </mesh>)}</group>;
}
