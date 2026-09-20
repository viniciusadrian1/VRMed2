"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { XR, XROrigin, useXR } from "@react-three/xr";
import { SairDoVR } from "@/components/xr/SairDoVR";
import { obterXRStore } from "@/lib/xr-store";
import { entrarNoXR } from "@/lib/xr-sessao";
import * as THREE from "three";
import { useMounted } from "@/hooks/use-mounted";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { LuzEstudio, Text3D } from "@/components/arena/ui3d";
import { DueloGame, type Ambiente } from "./DueloGame";
import { AmbienteHospital } from "./AmbienteHospital";
import { useDueloOnline, type DueloOnline } from "./useDueloOnline";

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
  const scene = useMemo(() => {
    const clone = gltf.scene.clone(true);
    // Remove / oculta as cadeiras do cenário para dar espaço livre aos competidores
    clone.traverse((child) => {
      if (
        child.name.toLowerCase().includes("chair") ||
        child.name.toLowerCase().includes("cadeira")
      ) {
        child.visible = false;
      }
    });
    return clone;
  }, [gltf.scene]);

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

function CenaDuelo({ ambiente, online }: { ambiente: Ambiente; online: DueloOnline }) {
  const inSession = useXR((state) => Boolean(state.session));
  const escola = ambiente === "escola";
  // Tela em pé, o órgão vai para cima da lousa/do painel (ver DueloGame).
  // Escola: câmera e alvo sobem 0,2m juntos — a cena desce inteira, sem mudar a
  // composição, e o órgão sai de baixo do seletor e do botão de VR do canto.
  // Hospital: o painel de 1,7m não cabe na largura com a câmera do VR, então
  // ela recua e centraliza no painel.
  const retrato = useThree((s) => s.size.width < s.size.height);
  const get = useThree((s) => s.get);
  // A prop `camera` do Canvas só vale na criação, e o Canvas não remonta ao
  // trocar de ambiente (a partida contra o bot vive no DueloGame) nem ao girar
  // o celular: a câmera é reposicionada aqui. Na sessão XR quem manda é o óculos.
  useEffect(() => {
    if (inSession) return;
    const [x, y, z] = escola
      ? retrato
        ? [0.28, 0.15, 1.0]
        : [0.28, -0.05, 1.0]
      : retrato
        ? [0.72, 0.35, 3.6]
        : [0, 0.3, 2.55];
    get().camera.position.set(x, y, z);
  }, [escola, retrato, inSession, get]);

  return (
    <>
      {/* Escola: origem no piso, exatamente sob o assento da direita — quem fica de pé
          vê por cima da mesa. Hospital: de pé atrás da sua mesa de instrumentos. */}
      <XROrigin position={escola ? [0.28, FLOOR_Y, 0.99] : [0, FLOOR_Y, 2.55]}>
        <SairDoVR position={[-0.45, escola ? 0.95 : 1.25, -0.5]} />
      </XROrigin>

      <LuzEstudio />
      {/* Luz ambiente equilibrada para clarear a sala e eliminar sombras duras/escuras */}
      <ambientLight intensity={1.1} color="#f8fafc" />
      <directionalLight position={[0, 4, 3]} intensity={0.9} color="#fffaf0" />

      <PalcoDuelo />
      {/* Cenário é enfeite: se um GLB dele falhar, o jogo segue sem a sala em
          vez de o erro subir pelo Canvas e derrubar a rota inteira. `key`
          para a troca de ambiente dar nova chance ao outro cenário. */}
      <ErrorBoundary key={ambiente} fallback={null}>
        <Suspense fallback={null}>
          {escola ? <CenarioDuelo /> : <AmbienteHospital />}
        </Suspense>
      </ErrorBoundary>
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
          <DueloGame ambiente={ambiente} online={online} />
        </Suspense>
      </ErrorBoundary>

      {!inSession && (
        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.08}
          target={
            escola
              ? retrato
                ? [0.36, 0, -1.06]
                : [0.36, -0.2, -1.06]
              : retrato
                ? [0.72, 0.35, -0.5]
                : [0.35, 0.1, -0.5]
          }
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
  // Fora do <Canvas>: a conexão da partida online não pode depender da árvore
  // 3D (erro de modelo, remontagem do canvas).
  const online = useDueloOnline();

  const store = obterXRStore();

  useEffect(
    () => store.subscribe((state) => setInSession(Boolean(state.session))),
    [store],
  );

  const enterVR = useCallback(() => {
    setXrError(null);
    entrarNoXR(store, () => store.enterVR()).catch((error: unknown) => {
      setXrError(error instanceof Error ? error.message : String(error));
    });
  }, [store]);

  if (!mounted) return null;

  return (
    <main id="conteudo-principal" className="relative h-dvh w-full overflow-hidden bg-[#101820]">
      {!inSession && (
        <>
          <Link
            href="/viewer"
            className="absolute left-4 top-4 z-20 flex items-center gap-1.5 rounded-full border border-white/15 bg-black/50 px-4 py-2 text-sm font-medium text-white backdrop-blur hover:bg-black/70"
          >
            <ArrowLeft className="size-4" />
            VRmed
          </Link>
          {/* Controles no canto de cima */}
          <div className="pointer-events-none absolute right-4 top-4 z-20 flex flex-col items-end gap-2">
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
              className="pointer-events-auto rounded-full bg-[#5896c8] px-6 py-2 font-semibold text-[#0b1220] shadow-lg transition-transform hover:scale-105"
            >
              Entrar em VR
            </button>
            {xrError && (
              <p className="pointer-events-auto max-w-xs rounded-lg border border-red-400/40 bg-red-950/70 px-4 py-2 text-xs text-red-200">
                Não foi possível iniciar o VR: {xrError}
              </p>
            )}
          </div>
          <p className="sr-only">
            Duelo de conhecimento médico — contra um bot ou contra um amigo,
            cada um no seu óculos. No desktop: 1–3 escolhe o bot, 4 cria uma
            sala, 5 entra numa sala, 1–4/A–D responde, Enter repete, Esc volta
            ao menu.
          </p>
        </>
      )}

      <Canvas
        role="application"
        aria-label="Duelo 1×1 em 3D. Menu: teclas 1 a 3 escolhem a dificuldade, 4 cria uma sala online e 5 entra numa sala pelo código; na rodada, 1 a 4 ou A a D respondem; ao final, Enter joga de novo; Esc volta ao menu."
        shadows={false}
        dpr={1}
        frameloop="always"
        camera={{
          position: ambiente === "escola" ? [0.28, -0.05, 1.0] : [0, 0.3, 2.55],
          fov: 50,
        }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl }) => gl.setClearColor("#101820")}
      >
        <XR store={store}>
          <CenaDuelo ambiente={ambiente} online={online} />
        </XR>
      </Canvas>
    </main>
  );
}
