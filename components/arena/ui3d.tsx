"use client";

import { useRef, type ReactNode } from "react";
import { Text } from "@react-three/drei";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { preloadFont } from "troika-three-text";
import * as THREE from "three";

/**
 * Primitivas de interface em espaço 3D para a Arena.
 *
 * Toda a UI do app é DOM (React/Tailwind) e **não é renderizada dentro de uma
 * sessão immersive-vr** — por isso nada de texto aparecia no headset. Aqui a
 * interface é geometria de verdade, desenhada na cena.
 *
 * A fonte é **local e explícita**: o `<Text>` do drei (troika) busca a fonte
 * padrão em cdn.jsdelivr.net e, sem rede, não desenha absolutamente nada.
 * No evento a rede pode cair, então a fonte viaja com o projeto.
 */
export const ARENA_FONT = "/fonts/inter-600.woff";

/**
 * Constrói o atlas da fonte antes da partida.
 *
 * Cada glifo novo obriga o troika a reconstruir o atlas SDF — se isso
 * acontecer no meio da rodada (um "ó" que ainda não apareceu, por exemplo),
 * o headset engasga. Pré-carregando dígitos, acentos e pontuação, o custo
 * fica todo no carregamento da página.
 */
// Só no navegador: o troika usa `self` e quebraria a pré-renderização.
if (typeof window !== "undefined") {
  preloadFont(
    {
      font: ARENA_FONT,
      characters:
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ·×ÁÂÃÀÇÉÊÍÓÔÕÚáâãàçéêíóôõú.,:!?()-",
    },
    () => {},
  );
}

/** Paleta da Arena — mesma linguagem clínica do resto do app. */
export const ARENA_COLORS = {
  primary: "#5896c8",
  panel: "#101820",
  text: "#f3f6f8",
  muted: "#9fb3c4",
  success: "#4fae89",
  danger: "#e06a5c",
} as const;

interface Text3DProps {
  children: ReactNode;
  position?: [number, number, number];
  size?: number;
  color?: string;
  /** Largura máxima antes de quebrar a linha, em metros. */
  maxWidth?: number;
  anchorY?: "top" | "middle" | "bottom";
}

/** Texto 3D com a fonte local já aplicada. Use sempre este, nunca o <Text> direto. */
export function Text3D({
  children,
  position,
  size = 0.12,
  color = ARENA_COLORS.text,
  maxWidth,
  anchorY = "middle",
}: Text3DProps) {
  return (
    <Text
      font={ARENA_FONT}
      position={position}
      fontSize={size}
      color={color}
      maxWidth={maxWidth}
      anchorX="center"
      anchorY={anchorY}
      textAlign="center"
      // Contorno escuro: o texto passa por cima de um modelo claro.
      outlineWidth={size * 0.05}
      outlineColor="#04070c"
      // Sem tonemapping o texto mantém o contraste dentro do headset.
      material-toneMapped={false}
      // A interface nunca pode ser engolida pelo modelo — o jogador pode
      // escalá-lo até 6× e cobrir o painel que ele precisa clicar.
      material-depthTest={false}
      renderOrder={999}
    >
      {children}
    </Text>
  );
}

/** Painel de fundo arredondado, para dar leitura ao texto sobre qualquer cena. */
export function Panel({
  width,
  height,
  color = ARENA_COLORS.panel,
  opacity = 0.85,
  position,
  children,
}: {
  width: number;
  height: number;
  color?: string;
  opacity?: number;
  position?: [number, number, number];
  children?: ReactNode;
}) {
  return (
    <group position={position}>
      <mesh renderOrder={998}>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={opacity}
          side={THREE.DoubleSide}
          toneMapped={false}
          depthTest={false}
        />
      </mesh>
      {children}
    </group>
  );
}

/**
 * Botão 3D: reage ao laser do controle (ou da mão) e ao gatilho.
 * Cresce um pouco sob o ponteiro — o único aviso visual de que é clicável
 * para quem nunca usou um headset.
 */
export function Button3D({
  label,
  onClick,
  width = 1.1,
  height = 0.3,
  position,
  color = ARENA_COLORS.primary,
}: {
  label: string;
  onClick: () => void;
  width?: number;
  height?: number;
  position?: [number, number, number];
  color?: string;
}) {
  const group = useRef<THREE.Group>(null);
  const hovered = useRef(false);
  const scale = useRef(1);

  useFrame((_, delta) => {
    if (!group.current) return;
    const target = hovered.current ? 1.08 : 1;
    // Suaviza a resposta para não "pular" com o tremor da mão.
    scale.current += (target - scale.current) * Math.min(1, delta * 12);
    group.current.scale.setScalar(scale.current);
  });

  const stop = (event: ThreeEvent<PointerEvent>) => event.stopPropagation();

  return (
    <group
      ref={group}
      position={position}
      onClick={(event) => {
        event.stopPropagation();
        onClick();
      }}
      onPointerOver={(event) => {
        stop(event);
        hovered.current = true;
      }}
      onPointerOut={() => {
        hovered.current = false;
      }}
    >
      <mesh renderOrder={998}>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          color={color}
          toneMapped={false}
          depthTest={false}
          side={THREE.DoubleSide}
        />
      </mesh>
      <Text3D position={[0, 0, 0.005]} size={height * 0.42}>
        {label}
      </Text3D>
    </group>
  );
}
