"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { XR, XROrigin, useXR } from "@react-three/xr";
import { SairDoVR } from "@/components/xr/SairDoVR";
import { obterXRStore } from "@/lib/xr-store";
import * as THREE from "three";
import { useMounted } from "@/hooks/use-mounted";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Text3D } from "@/components/arena/ui3d";
import { DueloGame, type Ambiente } from "./DueloGame";
import { AmbienteHospital } from "./AmbienteHospital";

const FLOOR_Y = -1.3;

// Cenário "Cute Magic Stylized LowPoly" exportado do Unity pelo grupo
// (29MB de projeto → 142KB: glTFast + webp + draco).
//
// ESCALA HUMANA (teste no Quest): a mobília do pacote é gigante — mesa a
// 1,04 un. acima do piso, assento a ~0,5 un., e o piso tem 0,30 un. de
// espessura. Escala 0,72 põe a mesa em 75cm e o assento em ~38cm; o grupo
// desce 0,30×0,72 para o TOPO do piso cair exatamente em FLOOR_Y (antes o
// jogador ficava 48cm abaixo do piso e via a lousa por baixo da mesa).
const CENARIO_GLB = "/models/props/cenario-duelo.glb";
export const ESCOLA_S = 0.72;
export const ESCOLA_OFF_Y = FLOOR_Y - 0.3 * ESCOLA_S;

function CenarioDuelo() {
  const gltf = useGLTF(CENARIO_GLB, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  return (
    <group position={[0, ESCOLA_OFF_Y, 0]} scale={ESCOLA_S}>
      <primitive object={scene} />
    </group>
  );
}
useGLTF.preload(CENARIO_GLB, "/draco/");

/** Chão escuro por baixo/fora da sala (a sala de aula ambienta o resto). */
function PalcoDuelo() {
  return (
    <group position={[0, FLOOR_Y - 0.01, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[12, 64]} />
        <meshBasicMaterial color="#0c1219" />
      </mesh>
    </group>
  );
}

function CenaDuelo({ ambiente }: { ambiente: Ambiente }) {
  const inSession = useXR((state) => Boolean(state.session));
  const escola = ambiente === "escola";

  return (
    <>
      {/* Escola: origem no piso, exatamente sob o assento da cadeira da
          direita — quem senta de verdade fica com os olhos ~1,2m acima, na
          altura da lousa; quem fica de pé vê por cima da mesa. Hospital: de
          pé atrás da sua mesa de instrumentos. */}
      <XROrigin position={escola ? [0.28, FLOOR_Y, 0.99] : [0, FLOOR_Y, 2.55]}>
        <SairDoVR position={[-0.45, escola ? 0.95 : 1.25, -0.5]} />
      </XROrigin>

      <ambientLight intensity={0.85} />
      <directionalLight position={[4, 6, 4]} intensity={1.9} color="#ffeedd" />
      <directionalLight position={[-5, 3, -4]} intensity={0.7} color="#9fc3dd" />
      <hemisphereLight args={["#dfe9f2", "#141a22", 1]} />

      <PalcoDuelo />
      <Suspense fallback={null}>
        {escola ? <CenarioDuelo /> : <AmbienteHospital />}
      </Suspense>
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
          <DueloGame ambiente={ambiente} />
        </Suspense>
      </ErrorBoundary>

      {!inSession && (
        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.08}
          target={escola ? [0.36, -0.2, -1.06] : [0.35, 0.1, -0.5]}
          minDistance={escola ? 0.8 : 1.5}
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
  const [ambiente, setAmbiente] = useState<Ambiente>("escola");

  const store = obterXRStore();

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
            {/* Seletor de ambiente do duelo */}
            <div className="pointer-events-auto flex overflow-hidden rounded-full border border-white/15 bg-black/50 text-sm font-medium backdrop-blur">
              {(
                [
                  ["escola", "🏫 Escola"],
                  ["hospital", "🏥 Hospital"],
                ] as const
              ).map(([valor, rotulo]) => (
                <button
                  key={valor}
                  type="button"
                  onClick={() => setAmbiente(valor)}
                  className={
                    ambiente === valor
                      ? "bg-[#5896c8] px-5 py-2 text-[#0b1220]"
                      : "px-5 py-2 text-white/70 hover:text-white"
                  }
                >
                  {rotulo}
                </button>
              ))}
            </div>
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
              mouse ou o teclado (1–3 escolhe a dificuldade, 1–4/A–D responde,
              Enter repete).
            </p>
          </div>
        </>
      )}

      <Canvas
        key={ambiente}
        role="application"
        aria-label="Duelo 1×1 em 3D. Menu: teclas 1 a 3 escolhem a dificuldade; na rodada, 1 a 4 ou A a D respondem; ao final, Enter joga de novo."
        shadows={false}
        dpr={1}
        frameloop="always"
        camera={{
          // Ambas no ponto de vista do VR (sentado na escola, de pé no
          // hospital): o desktop não pode esconder o que o headset vê.
          position: ambiente === "escola" ? [0.28, -0.05, 1.0] : [0, 0.3, 2.55],
          fov: 50,
        }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl }) => gl.setClearColor("#101820")}
      >
        <XR store={store}>
          <CenaDuelo ambiente={ambiente} />
        </XR>
      </Canvas>
    </main>
  );
}
