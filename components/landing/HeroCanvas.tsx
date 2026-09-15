"use client";

import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { Center, ContactShadows, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { SafeEnvironment } from "@/components/viewer/SafeEnvironment";

const CORACAO = "/models/healthy/coracao.glb";

/**
 * Coração anatômico real (o mesmo modelo do visualizador) carregado no hero.
 * Centralizado e escalado para caber no enquadramento; o resto (girar/arrastar)
 * fica com o OrbitControls.
 */
function CoracaoModel() {
  const { scene } = useGLTF(CORACAO, "/draco/");

  // Clona (não contamina o cache do useGLTF) e mede para escalar ao quadro.
  const { objeto, escala } = useMemo(() => {
    const clone = scene.clone(true);
    const caixa = new THREE.Box3().setFromObject(clone);
    const tamanho = caixa.getSize(new THREE.Vector3());
    const maior = Math.max(tamanho.x, tamanho.y, tamanho.z) || 1;
    return { objeto: clone, escala: 2.3 / maior };
  }, [scene]);

  // <Center> resolve o posicionamento na origem; a escala vai no grupo (sem
  // mutar o objeto, o que o React Compiler lint reprova).
  return (
    <Center>
      <group scale={escala}>
        <primitive object={objeto} />
      </group>
    </Center>
  );
}

/**
 * Canvas 3D do hero: o coração real, que a pessoa pode girar com o mouse ou o
 * dedo. Montado sob demanda (dynamic import) para tirar o three.js do bundle
 * inicial. Com `active=false` (fora da viewport ou prefers-reduced-motion) o
 * frameloop vira "demand" e a auto-rotação para — economizando GPU. O arrastar
 * do usuário continua funcionando (o OrbitControls invalida o frame ao mudar).
 */
export function HeroCanvas({ active }: { active: boolean }) {
  return (
    <Canvas
      // O OrbitControls grava touch-action:none inline neste div e prendia a
      // rolagem da landing no celular. O !important devolve o arrasto vertical
      // à página; o horizontal continua girando o coração.
      className="touch-pan-y!"
      shadows
      dpr={[1, 1.5]}
      frameloop={active ? "always" : "demand"}
      camera={{ position: [0, 0.1, 4.2], fov: 42 }}
      gl={{ antialias: true, alpha: true }}
    >
      <ambientLight intensity={0.6} />
      <directionalLight position={[3, 5, 4]} intensity={2.2} castShadow shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[-4, 2, -3]} intensity={0.5} color="#9fc3dd" />

      <Suspense fallback={null}>
        <CoracaoModel />
        {/* Brilho úmido de órgão via mapa de ambiente LOCAL (sem CDN). */}
        <SafeEnvironment />
      </Suspense>

      <ContactShadows position={[0, -1.4, 0]} opacity={0.32} scale={7} blur={2.6} far={3} frames={1} />

      <OrbitControls
        makeDefault
        enablePan={false}
        enableZoom={false}
        autoRotate={active}
        autoRotateSpeed={0.9}
        dampingFactor={0.12}
        minPolarAngle={Math.PI * 0.2}
        maxPolarAngle={Math.PI * 0.82}
      />
    </Canvas>
  );
}

useGLTF.preload(CORACAO, "/draco/");
