"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Text3D, ARENA_COLORS } from "@/components/arena/ui3d";

export type HumorOponente = "idle" | "comemora" | "erra";

/**
 * Avatar do oponente: médico low-poly 100%% procedural.
 *
 * O plano previa buscar um modelo gratuito (Mixamo/Sketchfab) com fallback de
 * modelagem simples — este é o fallback, escolhido de saída porque é zero
 * download, zero licença para conferir e ~50 triângulos (nada no orçamento do
 * Quest). Trocar por um GLB depois é substituir este componente.
 */
export function Oponente({
  humor,
  nome,
  pontos,
  position,
}: {
  humor: HumorOponente;
  nome: string;
  pontos: number;
  position: [number, number, number];
}) {
  const corpo = useRef<THREE.Group>(null);
  const animacao = useRef(0);

  useFrame((state, delta) => {
    if (!corpo.current) return;
    const t = state.clock.elapsedTime;
    animacao.current += delta;
    if (humor === "comemora") {
      // Pulinhos de comemoração
      corpo.current.position.y = Math.abs(Math.sin(animacao.current * 9)) * 0.16;
      corpo.current.rotation.z = Math.sin(animacao.current * 9) * 0.06;
    } else if (humor === "erra") {
      // Murcha: inclina e abaixa
      corpo.current.position.y = -0.06;
      corpo.current.rotation.z = 0.14;
    } else {
      // Respiração parada de pé
      corpo.current.position.y = Math.sin(t * 1.6) * 0.015;
      corpo.current.rotation.z = 0;
      animacao.current = 0;
    }
  });

  return (
    <group position={position} rotation={[0, Math.PI, 0]}>
      <group ref={corpo}>
        {/* Pernas (calça de centro cirúrgico) */}
        {[-0.09, 0.09].map((x) => (
          <mesh key={x} position={[x, 0.42, 0]}>
            <boxGeometry args={[0.13, 0.84, 0.16]} />
            <meshStandardMaterial color="#2e5f6e" roughness={0.9} />
          </mesh>
        ))}
        {/* Tronco — jaleco branco */}
        <mesh position={[0, 1.12, 0]}>
          <boxGeometry args={[0.44, 0.62, 0.24]} />
          <meshStandardMaterial color="#eef1f2" roughness={0.8} />
        </mesh>
        {/* Abertura do jaleco (camisa) */}
        <mesh position={[0, 1.12, 0.125]}>
          <boxGeometry args={[0.1, 0.6, 0.005]} />
          <meshStandardMaterial color="#3a7d8c" roughness={0.9} />
        </mesh>
        {/* Braços */}
        {[-0.27, 0.27].map((x) => (
          <mesh key={x} position={[x, 1.08, 0]} rotation={[0, 0, x > 0 ? -0.12 : 0.12]}>
            <boxGeometry args={[0.1, 0.55, 0.12]} />
            <meshStandardMaterial color="#eef1f2" roughness={0.8} />
          </mesh>
        ))}
        {/* Mãos */}
        {[-0.31, 0.31].map((x) => (
          <mesh key={x} position={[x, 0.78, 0]}>
            <sphereGeometry args={[0.05, 8, 6]} />
            <meshStandardMaterial color="#c9987a" roughness={0.9} />
          </mesh>
        ))}
        {/* Cabeça */}
        <mesh position={[0, 1.56, 0]}>
          <sphereGeometry args={[0.14, 12, 10]} />
          <meshStandardMaterial color="#d3a284" roughness={0.9} />
        </mesh>
        {/* Touca cirúrgica */}
        <mesh position={[0, 1.65, 0]}>
          <sphereGeometry args={[0.145, 12, 6, 0, Math.PI * 2, 0, Math.PI * 0.45]} />
          <meshStandardMaterial color="#4d8a7a" roughness={0.9} />
        </mesh>
        {/* Estetoscópio (arco no pescoço) */}
        <mesh position={[0, 1.42, 0.1]} rotation={[Math.PI * 0.55, 0, 0]}>
          <torusGeometry args={[0.09, 0.012, 6, 12, Math.PI]} />
          <meshStandardMaterial color="#26303a" roughness={0.6} />
        </mesh>
      </group>

      {/* Placa: nome + pontos (vira para o jogador, que está do outro lado) */}
      <group rotation={[0, Math.PI, 0]} position={[0, 2.05, 0]}>
        <Text3D size={0.09} color={ARENA_COLORS.danger}>
          {nome}
        </Text3D>
        <Text3D position={[0, -0.14, 0]} size={0.11}>
          {String(pontos)}
        </Text3D>
      </group>
    </group>
  );
}
