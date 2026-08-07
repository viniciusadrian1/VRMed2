"use client";

import { useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { XR, XROrigin, createXRStore } from "@react-three/xr";
import { useMounted } from "@/hooks/use-mounted";
import { ArenaGame } from "./ArenaGame";
import { ARENA_COLORS } from "./ui3d";

/** Altura do chão — o modelo é normalizado em ~2 unidades centradas na origem. */
const FLOOR_Y = -1.3;

/**
 * Cena da Arena: canvas e sessão XR próprios, isolados do visualizador.
 *
 * `baseAssetPath` aponta para perfis de controle servidos pelo próprio app.
 * Isso não é um detalhe de performance: o estado do controle só é criado
 * depois que o perfil é baixado (`@pmndrs/xr/controller/state.js`), então com
 * o CDN inacessível o controle simplesmente **não existe** — sem laser, sem
 * gatilho, sem jogo. Só as mãos continuariam funcionando, o que seria um
 * pesadelo para diagnosticar no meio do evento.
 */
export function ArenaScene() {
  const mounted = useMounted();
  const [inSession, setInSession] = useState(false);

  const store = useMemo(
    () =>
      createXRStore({
        baseAssetPath: "/webxr-profiles/",
        // Os modelos 3D dos controles ficam LIGADOS e são servidos daqui.
        // Ver o controle desenhado na frente do rosto é o que ensina um leigo
        // qual botão apertar — sem isso ele fica com um raio saindo do nada.
        // Recursos de realidade mista desligados: por padrão a biblioteca os
        // pede como opcionais, e detecção de planos/malhas pode disparar o
        // diálogo de dados espaciais da Meta — um pop-up do sistema na cara
        // de um leigo, com o júri assistindo pelo monitor.
        anchors: false,
        meshDetection: false,
        planeDetection: false,
        hitTest: false,
        depthSensing: false,
        // 72fps fixo: num estande o headset esquenta, e mirar 90/120 no
        // Quest 3 só antecipa o throttling térmico.
        frameRate: () => 72,
        foveation: 0.5,
      }),
    [],
  );

  useEffect(
    () => store.subscribe((state) => setInSession(Boolean(state.session))),
    [store],
  );

  if (!mounted) return null;

  return (
    <>
      {/*
        Fora da sessão, toda a interface é DOM — limpa e organizada por cima
        do modelo girando. A UI 3D do jogo só existe DENTRO do VR (onde DOM é
        invisível); misturar as duas na mesma tela era o que deixava a página
        bagunçada, com painéis 3D atravessando o texto.
      */}
      {!inSession && (
        <div className="pointer-events-none absolute inset-0 z-10 flex flex-col">
          <header className="flex items-center gap-2.5 p-6">
            <span className="size-2.5 rounded-full bg-[#5896c8]" />
            <span className="text-sm font-semibold uppercase tracking-[0.2em] text-white/80">
              VRmed
            </span>
          </header>

          <div className="mt-auto flex flex-col items-center gap-5 bg-gradient-to-t from-black/80 via-black/40 to-transparent px-6 pb-16 pt-28 text-center">
            <h1 className="font-serif text-5xl font-medium tracking-tight text-white md:text-6xl">
              Arena
            </h1>
            <p className="max-w-md text-pretty text-base text-white/70">
              Encontre as estruturas anatômicas contra o relógio — 60 segundos
              dentro do corpo humano.
            </p>
            <button
              type="button"
              onClick={() => void store.enterVR()}
              className="pointer-events-auto mt-1 rounded-full bg-[#5896c8] px-12 py-4 text-lg font-semibold text-[#0b1220] shadow-[0_0_45px_rgba(88,150,200,0.45)] transition-transform hover:scale-105"
            >
              Entrar em VR
            </button>
            <div className="flex flex-wrap items-center justify-center gap-2 text-xs text-white/60">
              <span className="rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5">
                1 · Mire com o laser
              </span>
              <span className="rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5">
                2 · Puxe o gatilho
              </span>
              <span className="rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5">
                3 · Marque pontos em 60s
              </span>
            </div>
            <p className="text-[11px] text-white/40">
              Requer um headset compatível com WebXR (Meta Quest)
            </p>
          </div>
        </div>
      )}

      <Canvas
        // Sem sombras nem dpr alto: o orçamento do Quest é estéreo a 72–90fps.
        shadows={false}
        dpr={1}
        frameloop="always"
        camera={{ position: [0, 0.4, 3.2], fov: 50 }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ scene, gl }) => {
          gl.setClearColor(ARENA_COLORS.panel);
          scene.background = null;
        }}
      >
        <XR store={store}>
          {/* Jogador de pé, a 2,6 m do modelo. */}
          <XROrigin position={[0, FLOOR_Y, 2.6]} />

          <ambientLight intensity={0.9} />
          <directionalLight position={[4, 6, 4]} intensity={1.8} />
          <directionalLight
            position={[-5, 2, -4]}
            intensity={0.5}
            color="#9fc3dd"
          />
          <hemisphereLight args={["#dfe9f2", "#1b2229", 1]} />

          {/* Chão: referência espacial — sem ele o headset é um vazio preto. */}
          <gridHelper
            args={[24, 24, "#3d7ab0", "#243542"]}
            position={[0, FLOOR_Y, 0]}
          />
          <mesh
            position={[0, FLOOR_Y + 0.01, 0]}
            rotation={[-Math.PI / 2, 0, 0]}
          >
            <ringGeometry args={[1.15, 1.35, 48]} />
            <meshBasicMaterial
              color={ARENA_COLORS.primary}
              transparent
              opacity={0.5}
            />
          </mesh>

          <ArenaGame />
        </XR>
      </Canvas>
    </>
  );
}
