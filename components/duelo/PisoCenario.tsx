"use client";

import { Suspense, useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { ErrorBoundary } from "@/components/ErrorBoundary";

function PisoAutorado({ sala }: { sala: "hospital" | "escola" }) {
  const gltf = useGLTF(sala === "hospital"
    ? "/models/props/piso-hospital-direcao.glb" : "/models/props/piso-escola-direcao.glb");
  const cena = useMemo(() => {
    const clone = gltf.scene.clone(true);
    clone.traverse((obj) => { if (obj instanceof THREE.Mesh) obj.raycast = () => null; });
    return clone;
  }, [gltf.scene]);
  return <primitive object={cena} dispose={null} />;
}

/** Contatos calculados no Blender e incorporados ao piso opaco; sem overdraw de sombras. */
export function PisoCenario({ sala }: { sala: "hospital" | "escola" }) {
  const reserva = sala === "hospital" ? <mesh rotation={[-Math.PI / 2, 0, 0]} raycast={() => null}>
    <planeGeometry args={[9.2, 9.2]} /><meshStandardMaterial color="#3e5960" roughness={.85} />
  </mesh> : null;
  return <group pointerEvents="none">
    <ErrorBoundary fallback={reserva}><Suspense fallback={reserva}>
      <PisoAutorado sala={sala} />
    </Suspense></ErrorBoundary>
  </group>;
}
