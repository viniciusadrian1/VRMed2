"use client";

import { useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { FaixaReativa } from "./ArenaMedica";

const CAMINHO = "/models/props/retaguarda-arena.glb";
const SEM_RAYCAST = () => null;
const APOIOS = [
  { x: -3.05, z: 2.50, largura: 1.60, fundo: 2.65 },
  { x: -1.83, z: 3.51, largura: .78, fundo: .85 },
  { x: 2.98, z: 4.15, largura: 2.65, fundo: .95 },
  { x: 4.07, z: 2.46, largura: .95, fundo: 1.75 },
  { x: 3.78, z: 1.12, largura: .85, fundo: .95 },
];

/** Contato estilizado no piso; cinco planos pequenos, sem shadow map. */
function ContatosDeApoio() {
  const mascara = useMemo(() => {
    const dados = new Uint8Array(32 * 32 * 4);
    for (let y = 0; y < 32; y++) for (let x = 0; x < 32; x++) {
      const r = Math.hypot((x - 15.5) / 15.5, (y - 15.5) / 15.5);
      const valor = Math.round(255 * Math.max(0, 1 - r) ** 1.4);
      dados.set([valor, valor, valor, 255], (y * 32 + x) * 4);
    }
    return dados;
  }, []);
  return <group pointerEvents="none">{APOIOS.map((p, i) => <mesh key={i}
    position={[p.x, .013, p.z]} rotation={[-Math.PI / 2, 0, 0]} raycast={SEM_RAYCAST}>
    <planeGeometry args={[p.largura, p.fundo]} />
    <meshBasicMaterial color="#071f26" opacity={.3} transparent depthWrite={false} toneMapped={false}>
      <dataTexture attach="alphaMap" args={[mascara, 32, 32, THREE.RGBAFormat]}
        needsUpdate minFilter={THREE.LinearFilter} magFilter={THREE.LinearFilter} />
    </meshBasicMaterial>
  </mesh>)}</group>;
}

/** Oito malhas de cenário autoral; todas fora da circulação e sem interação. */
export function RetaguardaHospital() {
  const gltf = useGLTF(CAMINHO);
  const cena = useMemo(() => {
    const clone = gltf.scene.clone(true);
    clone.traverse((obj) => { if (obj instanceof THREE.Mesh) obj.raycast = SEM_RAYCAST; });
    return clone;
  }, [gltf.scene]);
  return <group pointerEvents="none">
    <primitive object={cena} dispose={null} />
    <ContatosDeApoio />
    {/* Sinal discreto da partida ao olhar para trás, sem outra luz dinâmica. */}
    <FaixaReativa pos={[0, 2.55, 4.295]} tam={[2.30, .018, .012]} />
    <FaixaReativa pos={[-2.95, 2.12, 4.205]} tam={[2.05, .012, .012]} />
  </group>;
}

useGLTF.preload(CAMINHO);
