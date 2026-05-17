"use client";

import { useEffect } from "react";

/**
 * Camadas concêntricas do modelo de demonstração procedural.
 * Os nomes (skin / muscle / cortex / core) são reconhecidos pelos utilitários
 * de tradução e de categorização anatômica — assim camadas, raio-X e cortes
 * funcionam plenamente mesmo antes de um arquivo .glb real ser adicionado.
 */
const SHELLS: {
  name: string;
  radius: number;
  scale: [number, number, number];
  color: string;
}[] = [
  { name: "skin", radius: 1.0, scale: [1, 0.82, 0.92], color: "#d8c4b4" },
  { name: "muscle", radius: 0.78, scale: [1, 0.86, 0.95], color: "#bf564a" },
  { name: "cortex", radius: 0.52, scale: [1, 0.9, 0.94], color: "#e6e2d9" },
  { name: "core", radius: 0.28, scale: [1, 1, 1], color: "#0f4c81" },
];

/** Modelo anatômico procedural usado enquanto não há um .glb correspondente. */
export function PlaceholderOrgan({ onReady }: { onReady?: () => void }) {
  useEffect(() => {
    onReady?.();
  }, [onReady]);

  return (
    <group rotation={[0.1, 0.5, 0]}>
      {SHELLS.map((shell) => (
        <mesh
          key={shell.name}
          name={shell.name}
          scale={shell.scale}
          castShadow
          receiveShadow
        >
          <sphereGeometry args={[shell.radius, 56, 56]} />
          <meshStandardMaterial
            color={shell.color}
            roughness={0.55}
            metalness={0.05}
          />
        </mesh>
      ))}
    </group>
  );
}
