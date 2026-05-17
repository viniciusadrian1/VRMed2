"use client";

import { MeshDistortMaterial } from "@react-three/drei";

/**
 * Modelo de demonstração do modo comparação.
 * A versão patológica usa um material com distorção, ficando irregular e
 * mais opaca — o contraste visual evidencia a diferença com a versão saudável.
 */
export function ComparePlaceholder({
  variant,
}: {
  variant: "healthy" | "pathological";
}) {
  if (variant === "pathological") {
    return (
      <mesh castShadow receiveShadow>
        <icosahedronGeometry args={[1.1, 16]} />
        <MeshDistortMaterial
          color="#8f7d63"
          roughness={0.78}
          metalness={0.04}
          distort={0.34}
          speed={1.1}
        />
      </mesh>
    );
  }

  return (
    <mesh castShadow receiveShadow>
      <icosahedronGeometry args={[1.1, 16]} />
      <meshStandardMaterial color="#c8675b" roughness={0.5} metalness={0.05} />
    </mesh>
  );
}
