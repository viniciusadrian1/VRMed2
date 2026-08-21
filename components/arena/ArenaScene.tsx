"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { XR, XROrigin, createXRStore } from "@react-three/xr";
import * as THREE from "three";
import { useMounted } from "@/hooks/use-mounted";
import { ArenaGame } from "./ArenaGame";
import { ARENA_COLORS } from "./ui3d";

/** Altura do chão — o modelo é normalizado em ~2 unidades centradas na origem. */
const FLOOR_Y = -1.3;

/**
 * Versão visível da Arena — bump a cada mudança que vai a teste.
 * O navegador do Quest cacheia builds antigas de forma agressiva; sem este
 * carimbo, já testamos versão velha achando que era a nova.
 */
const ARENA_BUILD = "v8 · visual + tombar";

/**
 * Palco da Arena: plataforma circular com anéis concêntricos e brilho sob o
 * modelo — vitrine de museu no lugar do gridHelper de ferramenta de debug.
 * Geometria pura: zero rede, zero asset.
 */
function ArenaStage() {
  return (
    <group position={[0, FLOOR_Y, 0]}>
      {/* Base da plataforma */}
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[9, 64]} />
        <meshBasicMaterial color="#0c1219" />
      </mesh>
      {/* Anéis concêntricos, esmaecendo para fora */}
      {[
        { inner: 1.15, outer: 1.28, opacity: 0.75 },
        { inner: 2.4, outer: 2.46, opacity: 0.3 },
        { inner: 4.2, outer: 4.24, opacity: 0.16 },
        { inner: 6.4, outer: 6.43, opacity: 0.08 },
      ].map((ring) => (
        <mesh
          key={ring.inner}
          position={[0, 0.005, 0]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <ringGeometry args={[ring.inner, ring.outer, 64]} />
          <meshBasicMaterial
            color="#5896c8"
            transparent
            opacity={ring.opacity}
          />
        </mesh>
      ))}
      {/* Brilho suave sob o órgão — o "pedestal de luz" da vitrine */}
      <mesh position={[0, 0.002, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[1.1, 48]} />
        <meshBasicMaterial
          color="#17324a"
          transparent
          opacity={0.85}
        />
      </mesh>
      {/* Raios de referência discretos (substituem a grade) */}
      {Array.from({ length: 12 }, (_, i) => {
        const angle = (i / 12) * Math.PI * 2;
        return (
          <mesh
            key={i}
            position={[Math.cos(angle) * 5.2, 0.004, Math.sin(angle) * 5.2]}
            rotation={[-Math.PI / 2, 0, angle]}
          >
            <planeGeometry args={[3.4, 0.015]} />
            <meshBasicMaterial color="#24425e" transparent opacity={0.35} />
          </mesh>
        );
      })}
    </group>
  );
}

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
  /**
   * Erro ao entrar/configurar a sessão VR, para mostrar NA TELA. Sem isso a
   * falha vira um console.error que ninguém lê no headset — foi assim que
   * "não aparece nada, só fundo escuro" virou um mistério de dias.
   */
  const [xrError, setXrError] = useState<string | null>(null);

  const store = useMemo(
    () =>
      createXRStore({
        // PRECISA ser URL absoluta: a biblioteca resolve os perfis com
        // `new URL(caminho, baseAssetPath)`, e um caminho relativo não é uma
        // base válida — lança "Invalid URL", o erro é engolido num
        // console.error e o controle simplesmente nunca é criado (sem laser,
        // sem gatilho, sem nada). Foi exatamente o bug do primeiro teste.
        baseAssetPath:
          typeof window !== "undefined"
            ? `${window.location.origin}/webxr-profiles/`
            : "https://localhost/webxr-profiles/",
        // SÓ o ponteiro de raio fica ativo. O ponteiro de "grab" é uma esfera
        // curta no próprio controle, e o CombinedPointer ativa apenas o
        // ponteiro de MENOR distância: quando o jogador aproxima o órgão
        // (analógico ↕) e ele envolve a mão, o grab vence e o raio é
        // DESATIVADO — o gatilho para de clicar onde a mira aponta. A nossa
        // manipulação lê o grip direto do gamepad, então não perde nada.
        controller: { grabPointer: false, teleportPointer: false },
        // O modelo 3D da mão vem de outro CDN; o rastreamento (pinça)
        // funciona igual sem ele. Mesma regra do grab vale para o toque.
        hand: { model: false, grabPointer: false, touchPointer: false },
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
        // NÃO mexer na taxa de quadros. A biblioteca aplica o valor com
        // session.updateTargetFrameRate() dentro do mesmo passo que configura
        // a sessão inteira — e essa chamada pode ser REJEITADA dependendo do
        // estado do aparelho (economia de bateria, térmico), matando a sessão
        // meio-inicializada: o headset mostra só o vazio escuro do sistema
        // com o guardian. Era o "às vezes aparece, às vezes não" do Quest 2.
        // O padrão do aparelho já é 72; o ganho não paga o risco.
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
      const message =
        error instanceof Error ? error.message : String(error ?? "erro");
      setXrError(message);
    });
  }, [store]);

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
              onClick={enterVR}
              className="pointer-events-auto mt-1 rounded-full bg-[#5896c8] px-12 py-4 text-lg font-semibold text-[#0b1220] shadow-[0_0_45px_rgba(88,150,200,0.45)] transition-transform hover:scale-105"
            >
              Entrar em VR
            </button>
            {xrError && (
              <p
                role="alert"
                className="pointer-events-auto max-w-lg rounded-lg border border-red-400/40 bg-red-950/60 px-4 py-2.5 text-sm text-red-200"
              >
                Não foi possível iniciar o VR: <code className="text-xs">{xrError}</code>
                <br />
                <span className="text-red-200/70">
                  Fotografe esta mensagem e envie para a equipe.
                </span>
              </p>
            )}
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
              Requer um headset compatível com WebXR (Meta Quest) ·{" "}
              <span className="font-mono">{ARENA_BUILD}</span>
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

          <ambientLight intensity={0.85} />
          {/* Luz principal levemente quente + contraluz fria: dá volume ao
              órgão em vez do achatado de luz branca uniforme. */}
          <directionalLight position={[4, 6, 4]} intensity={1.9} color="#ffeedd" />
          <directionalLight position={[-5, 3, -4]} intensity={0.7} color="#9fc3dd" />
          <hemisphereLight args={["#dfe9f2", "#141a22", 1]} />

          <ArenaStage />

          {/* Cúpula com gradiente: profundidade em volta, em vez do vazio
              preto de fundo (referência espacial + acabamento). */}
          <mesh>
            <sphereGeometry args={[28, 24, 16]} />
            <meshBasicMaterial color="#0a1017" side={THREE.BackSide} />
          </mesh>

          {/*
            Sentinela de renderização: 3 barras pequenas na periferia, em
            geometria pura (sem fonte, sem rede, sem modelo). Aparecem no
            PRIMEIRO quadro. Barras visíveis + resto ausente = falha de
            carregamento; nem barras = a sessão não renderiza. Agora que a
            cena está estável, ficam discretas — mas continuam lá.
          */}
          <group position={[-5.5, FLOOR_Y + 0.15, -3]} scale={0.35}>
            <mesh position={[0, 0, 0]}>
              <boxGeometry args={[0.12, 0.8, 0.12]} />
              <meshBasicMaterial color="#e06a5c" />
            </mesh>
            <mesh position={[0.2, 0.1, 0]}>
              <boxGeometry args={[0.12, 1.0, 0.12]} />
              <meshBasicMaterial color="#5896c8" />
            </mesh>
            <mesh position={[0.4, 0.2, 0]}>
              <boxGeometry args={[0.12, 1.2, 0.12]} />
              <meshBasicMaterial color="#4fae89" />
            </mesh>
          </group>

          <ArenaGame />
        </XR>
      </Canvas>
    </>
  );
}
