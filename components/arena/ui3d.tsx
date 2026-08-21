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
      // Texto não intercepta o laser: o clique atravessa até o modelo.
      raycast={() => null}
    >
      {children}
    </Text>
  );
}

/**
 * Textura de painel desenhada em runtime (canvas): cantos arredondados,
 * preenchimento com leve gradiente e borda de acento. Gerada localmente —
 * zero rede, zero asset — e cacheada por proporção e cor.
 */
const panelTextureCache = new Map<string, THREE.CanvasTexture>();

function panelTexture(
  aspect: number,
  fill: string,
  stroke: string,
  fillBottom = "#070b10",
): THREE.CanvasTexture {
  const key = `${aspect.toFixed(1)}|${fill}|${stroke}|${fillBottom}`;
  const cached = panelTextureCache.get(key);
  if (cached) return cached;

  const w = 512;
  const h = Math.round(Math.min(512, Math.max(96, 512 / aspect)));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;
  const r = Math.min(28, h * 0.22);

  ctx.beginPath();
  ctx.roundRect(3, 3, w - 6, h - 6, r);
  const gradient = ctx.createLinearGradient(0, 0, 0, h);
  gradient.addColorStop(0, fill);
  gradient.addColorStop(1, fillBottom);
  ctx.fillStyle = gradient;
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = stroke;
  ctx.stroke();

  const texture = new THREE.CanvasTexture(canvas);
  texture.anisotropy = 4;
  panelTextureCache.set(key, texture);
  return texture;
}

/** Painel de fundo arredondado, para dar leitura ao texto sobre qualquer cena. */
export function Panel({
  width,
  height,
  color = "#0d141c",
  opacity = 0.92,
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
      {/* raycast nulo: o painel é pano de fundo, não alvo do laser — sem
          isso ele bloquearia os cliques no modelo atrás dele. */}
      <mesh renderOrder={998} raycast={() => null}>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          map={panelTexture(width / height, color, "rgba(88,150,200,0.45)")}
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
          map={panelTexture(width / height, color, "rgba(255,255,255,0.55)", "#2d5a80")}
          transparent
          toneMapped={false}
          depthTest={false}
          side={THREE.DoubleSide}
        />
      </mesh>
      {/* Triângulo "play" em geometria pura: o botão continua reconhecível
          como clicável mesmo se a fonte falhar em carregar (rede ruim). */}
      <mesh
        position={[-width / 2 + height * 0.42, 0, 0.004]}
        rotation={[0, 0, -Math.PI / 2]}
        renderOrder={999}
        raycast={() => null}
      >
        <circleGeometry args={[height * 0.22, 3]} />
        <meshBasicMaterial color="#ffffff" toneMapped={false} depthTest={false} />
      </mesh>
      <Text3D position={[height * 0.14, 0, 0.005]} size={height * 0.42}>
        {label}
      </Text3D>
    </group>
  );
}
