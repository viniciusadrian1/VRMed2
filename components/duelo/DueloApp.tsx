"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { XR, XROrigin, useXR } from "@react-three/xr";
import { SairDoVR } from "@/components/xr/SairDoVR";
import { obterXRStore } from "@/lib/xr-store";
import { entrarNoXR } from "@/lib/xr-sessao";
import * as THREE from "three";
import { useMounted } from "@/hooks/use-mounted";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Text3D } from "@/components/arena/ui3d";
import { DueloGame, type Ambiente } from "./DueloGame";
import { ArenaMedicaRevisao } from "./ArenaMedicaRevisao";
import { useDueloOnline, type DueloOnline } from "./useDueloOnline";
import { ProvedorArena } from "./EstadoArena";
import { IluminacaoArena } from "./ArenaMedica";
import { AmbienteEscola, IluminacaoEscola } from "./AmbienteEscola";
import { MedidorDuelo } from "./MedidorDuelo";
import { posicaoCompetidorEscola } from "@/lib/escola-apresentacao";

const FLOOR_Y = -1.3;

// Inspeção só no desenvolvimento: produção e câmera XR ignoram estas vistas.
const VISTAS_ARENA: Record<string, [number, number, number]> = {
  fundo: [0, .3, 4.5], esquerda: [-4.5, .3, 2.1], direita: [4.5, .3, 2.1],
  "fundo-esquerda": [-3.4, .3, 4.3], "fundo-direita": [3.4, .3, 4.3],
};
const VISTAS_ESCOLA: Record<string, [number, number, number]> = {
  fundo: [0, .3, 3.8], esquerda: [-3.3, .3, .2], direita: [3.3, .05, .15],
  "fundo-esquerda": [-2.3, .3, 3.7], "fundo-direita": [2.3, .3, 3.7],
};

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

function CenaDuelo({ ambiente, online, esqueleto3D, alternarEsqueleto }: {
  ambiente: Ambiente; online: DueloOnline; esqueleto3D: boolean; alternarEsqueleto: () => void;
}) {
  const inSession = useXR((state) => Boolean(state.session));
  const escola = ambiente === "escola";
  const nomeVista = process.env.NODE_ENV === "development" && !inSession && typeof window !== "undefined"
    ? new URLSearchParams(window.location.search).get("inspecao") ?? "" : "";
  const vistas = escola ? VISTAS_ESCOLA : VISTAS_ARENA;
  const vistaLocal = Object.hasOwn(vistas, nomeVista) ? vistas[nomeVista] : undefined;
  // Tela em pé, o órgão vai para cima da lousa/do painel (ver DueloGame).
  // Escola: paisagem usa olhos a 1,60m do piso; retrato preserva o espaço
  // acima da lousa para o órgão, longe do seletor e do botão de VR do canto.
  // Hospital: o painel de 1,7m não cabe na largura com a câmera do VR, então
  // ela recua e centraliza no painel.
  const retrato = useThree((s) => s.size.width < s.size.height);
  const get = useThree((s) => s.get);
  // A prop `camera` do Canvas só vale na criação, e o Canvas não remonta ao
  // trocar de ambiente (a partida contra o bot vive no DueloGame) nem ao girar
  // o celular: a câmera é reposicionada aqui. Na sessão XR quem manda é o óculos.
  useEffect(() => {
    if (inSession) return;
    const [x, y, z] = vistaLocal ? (escola ? [.28, .3, .99] : [0, .3, 2.55]) : escola
      ? retrato
        ? [0.28, 0.15, 1.6]
        : [0.28, 0.3, 1.65]
      : retrato
        ? [0.85, 0.48, 3.8]
        : [0, 0.45, 3.8];
    get().camera.position.set(x, y, z);
    const camera = get().camera;
    if (camera instanceof THREE.PerspectiveCamera) {
      // No retrato, ampliar o campo em vez de recuar para dentro da porta.
      camera.fov = vistaLocal ? 75 : escola ? 55 : retrato ? 54 : 50;
      camera.updateProjectionMatrix();
    }
  }, [escola, retrato, inSession, get, vistaLocal]);

  return (
    <>
      {/* Dois postos em pé, sem assentos. A altura dos olhos vem do headset. */}
      <XROrigin position={escola ? posicaoCompetidorEscola("jogador") : [0, FLOOR_Y, 2.55]}>
        <SairDoVR position={[-0.45, 1.25, -0.5]} />
      </XROrigin>

      {escola ? <IluminacaoEscola /> : <IluminacaoArena />}

      <PalcoDuelo />
      {/* Cenário é enfeite: se um GLB dele falhar, o jogo segue sem a sala em
          vez de o erro subir pelo Canvas e derrubar a rota inteira. `key`
          para a troca de ambiente dar nova chance ao outro cenário. */}
      <ErrorBoundary key={ambiente} fallback={null}>
        <Suspense fallback={null}>
          {escola ? <AmbienteEscola detalhado={esqueleto3D} alternar={alternarEsqueleto} /> : <ArenaMedicaRevisao />}
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
            vistaLocal ?? (escola
              ? [0.36, 0, -1.06]
              : retrato
                ? [0.85, 0.35, -0.65]
                : [0, 0.15, -0.6])
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
  const [altaQualidade, setAltaQualidade] = useState(false);
  const [esqueleto3D, setEsqueleto3D] = useState(false);
  const [medir, setMedir] = useState(false);
  const [medicao, setMedicao] = useState("Aguardando 5 s de amostra…");
  const [ambiente, setAmbiente] = useState<Ambiente>("hospital");
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
                  ["hospital", "Arena médica"],
                ] as const
              ).map(([valor, rotulo]) => (
                <button
                  key={valor}
                  type="button"
                  aria-pressed={ambiente === valor}
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
          <div className="absolute bottom-4 left-4 z-20 flex max-w-[70%] flex-wrap items-center gap-2 text-xs text-slate-100">
            <button type="button" aria-pressed={altaQualidade} onClick={() => setAltaQualidade((v) => !v)} className="rounded-full border border-white/20 bg-slate-950/85 px-3 py-2" title="A nitidez alta usa mais GPU. Em VR o DPR permanece 1.">
              Nitidez: {altaQualidade ? "alta" : "padrão"}
            </button>
            <button type="button" aria-pressed={medir} onClick={() => { setMedir((v) => !v); setMedicao("Aguardando 5 s de amostra…"); }} className="rounded-full border border-white/20 bg-slate-950/85 px-3 py-2">Desempenho</button>
            {ambiente === "escola" && <button type="button" aria-pressed={esqueleto3D}
              onClick={() => setEsqueleto3D((v) => !v)}
              title="O esqueleto detalhado usa mais GPU e aparece apenas fora das rodadas."
              className="rounded-full border border-white/20 bg-slate-950/85 px-3 py-2">
              Esqueleto: {esqueleto3D ? "3D fora das rodadas" : "prancha leve"}
            </button>}
            {medir && <output className="rounded-lg bg-slate-950/90 px-3 py-2" aria-label="Medição local de desempenho">{medicao}</output>}
          </div>
        </>
      )}

      <Canvas
        role="application"
        aria-label="Duelo 1×1 em 3D. Menu: teclas 1 a 3 escolhem a dificuldade, 4 cria uma sala online e 5 entra numa sala pelo código; na rodada, 1 a 4 ou A a D respondem; ao final, Enter joga de novo; Esc volta ao menu."
        shadows={false}
        dpr={inSession ? 1 : altaQualidade ? 2 : 1}
        frameloop="always"
        camera={{
          position: ambiente === "escola" ? [0.28, -0.05, 1.0] : [0, 0.45, 3.8],
          fov: 50,
        }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl }) => gl.setClearColor("#101820")}
      >
        <XR store={store}>
          {medir && <MedidorDuelo publicar={setMedicao} />}
          <ProvedorArena><CenaDuelo ambiente={ambiente} online={online} esqueleto3D={esqueleto3D}
            alternarEsqueleto={() => setEsqueleto3D((v) => !v)} /></ProvedorArena>
        </XR>
      </Canvas>
    </main>
  );
}
