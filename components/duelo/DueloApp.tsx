"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { XR, XROrigin, createXRStore, useXR } from "@react-three/xr";
import * as THREE from "three";
import { useMounted } from "@/hooks/use-mounted";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Text3D } from "@/components/arena/ui3d";
import { DueloGame } from "./DueloGame";

const FLOOR_Y = -1.3;

/** Palco do duelo: duas metades espelhadas com divisória central baixa. */
function PalcoDuelo() {
  return (
    <group position={[0, FLOOR_Y, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[9, 64]} />
        <meshBasicMaterial color="#0c1219" />
      </mesh>
      {/* Anel do jogador e do oponente — áreas simétricas */}
      {[2.3, -2.3].map((z) => (
        <mesh key={z} position={[0, 0.005, z]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.85, 0.95, 48]} />
          <meshBasicMaterial
            color={z > 0 ? "#4fae89" : "#e06a5c"}
            transparent
            opacity={0.55}
          />
        </mesh>
      ))}
      {/* Divisória central: baixa — separa as estações sem esconder o modelo,
          que flutua acima dela (ponto em aberto do plano resolvido como
          separação simbólica). */}
      <mesh position={[0, 0.42, 0]}>
        <boxGeometry args={[4.6, 0.84, 0.07]} />
        <meshStandardMaterial color="#16222e" roughness={0.6} />
      </mesh>
      <mesh position={[0, 0.86, 0]}>
        <boxGeometry args={[4.6, 0.025, 0.09]} />
        <meshBasicMaterial color="#5896c8" />
      </mesh>
      {/* Pedestal de luz sob o modelo */}
      <mesh position={[0, 0.002, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[1.1, 48]} />
        <meshBasicMaterial color="#17324a" transparent opacity={0.85} />
      </mesh>
    </group>
  );
}

function CenaDuelo() {
  const inSession = useXR((state) => Boolean(state.session));

  return (
    <>
      <XROrigin position={[0, FLOOR_Y, 2.4]} />

      <ambientLight intensity={0.85} />
      <directionalLight position={[4, 6, 4]} intensity={1.9} color="#ffeedd" />
      <directionalLight position={[-5, 3, -4]} intensity={0.7} color="#9fc3dd" />
      <hemisphereLight args={["#dfe9f2", "#141a22", 1]} />

      <PalcoDuelo />
      <mesh>
        <sphereGeometry args={[28, 24, 16]} />
        <meshBasicMaterial color="#0a1017" side={THREE.BackSide} />
      </mesh>

      <ErrorBoundary
        fallback={
          <Text3D position={[0, 0.3, 0]} size={0.1} color="#e06a5c">
            Falha ao carregar os modelos — recarregue a página
          </Text3D>
        }
      >
        <Suspense
          fallback={
            <Text3D position={[0, 0.3, 0]} size={0.1} color="#9fb3c4">
              Preparando o duelo…
            </Text3D>
          }
        >
          <DueloGame />
        </Suspense>
      </ErrorBoundary>

      {!inSession && (
        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.08}
          target={[0, 0.15, 0]}
          minDistance={1.5}
          maxDistance={9}
          maxPolarAngle={Math.PI * 0.55}
        />
      )}
    </>
  );
}

/** Shell do Duelo: DOM fora da sessão + canvas isolado (padrão Arena/Clínica). */
export function DueloApp() {
  const mounted = useMounted();
  const [inSession, setInSession] = useState(false);
  const [xrError, setXrError] = useState<string | null>(null);

  const store = useMemo(
    () =>
      createXRStore({
        // Mesmo endurecimento da Arena (lições do Quest 2).
        baseAssetPath:
          typeof window !== "undefined"
            ? `${window.location.origin}/webxr-profiles/`
            : "https://localhost/webxr-profiles/",
        controller: { grabPointer: false, teleportPointer: false },
        hand: { model: false, grabPointer: false, touchPointer: false },
        anchors: false,
        meshDetection: false,
        planeDetection: false,
        hitTest: false,
        depthSensing: false,
        frameRate: false,
        foveation: 0.5,
      }),
    [],
  );

  useEffect(
    () => store.subscribe((state) => setInSession(Boolean(state.session))),
    [store],
  );

  const enterVR = useCallback(() => {
    setXrError(null);
    store.enterVR().catch((error: unknown) => {
      setXrError(error instanceof Error ? error.message : String(error));
    });
  }, [store]);

  if (!mounted) return null;

  return (
    <main className="relative h-dvh w-full overflow-hidden bg-[#101820]">
      {!inSession && (
        <>
          <Link
            href="/"
            className="absolute left-4 top-4 z-20 flex items-center gap-1.5 rounded-full border border-white/15 bg-black/50 px-4 py-2 text-sm font-medium text-white backdrop-blur hover:bg-black/70"
          >
            <ArrowLeft className="size-4" />
            VRmed
          </Link>
          <div className="pointer-events-none absolute inset-x-0 bottom-6 z-10 flex flex-col items-center gap-3">
            <button
              type="button"
              onClick={enterVR}
              className="pointer-events-auto rounded-full bg-[#5896c8] px-8 py-3 font-semibold text-[#0b1220] shadow-lg transition-transform hover:scale-105"
            >
              Entrar em VR
            </button>
            {xrError && (
              <p className="pointer-events-auto max-w-md rounded-lg border border-red-400/40 bg-red-950/70 px-4 py-2 text-xs text-red-200">
                Não foi possível iniciar o VR: {xrError}
              </p>
            )}
            <p className="max-w-lg px-4 text-center text-[11px] text-white/50">
              Duelo de conhecimento médico — funciona também no desktop com o
              mouse. Escolha a dificuldade no painel 3D.
            </p>
          </div>
        </>
      )}

      <Canvas
        shadows={false}
        dpr={1}
        frameloop="always"
        camera={{ position: [0, 0.5, 3.6], fov: 50 }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl }) => gl.setClearColor("#101820")}
      >
        <XR store={store}>
          <CenaDuelo />
        </XR>
      </Canvas>
    </main>
  );
}
