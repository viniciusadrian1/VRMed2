"use client";

import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { ContactShadows, Float } from "@react-three/drei";
import * as THREE from "three";

/** Camadas concêntricas que, ao serem cortadas, revelam a seção transversal. */
const LAYERS = [
  { radius: 1.0, color: "#d8c4b4" },
  { radius: 0.74, color: "#bf564a" },
  { radius: 0.5, color: "#e6e2d9" },
  { radius: 0.27, color: "#0f4c81" },
];

/** Esfera anatômica seccionada que gira lentamente — espelha a marca do VRmed. */
function CrossSectionModel() {
  const group = useRef<THREE.Group>(null);
  // Plano de corte fixo que expõe o interior das camadas.
  const clipPlane = useMemo(
    () => new THREE.Plane(new THREE.Vector3(0, 0, -1), 0.08),
    [],
  );

  useFrame((_, delta) => {
    if (group.current) group.current.rotation.y += delta * 0.3;
  });

  return (
    <Float speed={1.3} rotationIntensity={0.25} floatIntensity={0.45}>
      <group ref={group} rotation={[0.32, 0, 0.08]}>
        {LAYERS.map((layer) => (
          <mesh key={layer.radius} castShadow receiveShadow>
            <sphereGeometry args={[layer.radius, 64, 64]} />
            <meshStandardMaterial
              color={layer.color}
              roughness={0.5}
              metalness={0.04}
              clippingPlanes={[clipPlane]}
              clipShadows
              side={THREE.DoubleSide}
            />
          </mesh>
        ))}
        {/* Malha externa em arame — dá profundidade e leitura de "modelo 3D". */}
        <mesh>
          <sphereGeometry args={[1.16, 28, 28]} />
          <meshBasicMaterial
            color="#0f4c81"
            wireframe
            transparent
            opacity={0.12}
          />
        </mesh>
      </group>
    </Float>
  );
}

/**
 * Canvas 3D do hero da landing. Só é montado sob demanda (dynamic import) para
 * tirar o three.js do bundle inicial. Com `active=false` (fora da viewport ou
 * prefers-reduced-motion) o frameloop passa a "demand" e a cena fica estática,
 * economizando GPU — mesmo padrão de components/viewer/Scene.tsx.
 */
export function HeroCanvas({ active }: { active: boolean }) {
  return (
    <Canvas
      shadows
      dpr={[1, 1.5]}
      frameloop={active ? "always" : "demand"}
      camera={{ position: [0, 0.35, 3.5], fov: 42 }}
      gl={{ antialias: true, alpha: true }}
      onCreated={({ gl }) => {
        // Necessário para que os clipping planes sejam aplicados por material.
        gl.localClippingEnabled = true;
      }}
    >
      <ambientLight intensity={0.7} />
      <directionalLight
        position={[3, 5, 4]}
        intensity={2.4}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <directionalLight position={[-4, 2, -3]} intensity={0.6} color="#9fc3dd" />
      <CrossSectionModel />
      <ContactShadows
        position={[0, -1.3, 0]}
        opacity={0.35}
        scale={6}
        blur={2.6}
        far={3}
        frames={1}
      />
    </Canvas>
  );
}
