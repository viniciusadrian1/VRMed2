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
        // Modelos 3D de controle e mão também vêm de CDN; a Arena dispensa.
        controller: { model: false },
        hand: { model: false },
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
      {!inSession && (
        <button
          type="button"
          onClick={() => void store.enterVR()}
          className="absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary px-8 py-4 text-lg font-semibold text-primary-foreground shadow-xl"
        >
          Entrar em VR
        </button>
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
