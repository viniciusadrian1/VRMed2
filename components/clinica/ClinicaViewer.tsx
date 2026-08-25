"use client";

import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Canvas, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { XR, XROrigin, createXRStore, useXR } from "@react-three/xr";
import * as THREE from "three";
import {
  identifyStructure,
  normalizeContent,
  prepareModel,
} from "@/lib/model-utils";
import { XRManipulation } from "@/components/viewer/XRManipulation";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Text3D } from "@/components/arena/ui3d";
import { useMounted } from "@/hooks/use-mounted";
import { MapaAchados, type AchadosPulmao } from "./MapaAchados";
import type { CasoClinico } from "./ClinicaApp";

const FLOOR_Y = -1.3;

/** Modelo do paciente: carrega, prepara e responde ao clique. */
function ModeloPaciente({
  glb,
  onIdentify,
}: {
  glb: string;
  onIdentify: (label: string) => void;
}) {
  const gltf = useGLTF(glb, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  const pivot = useRef<THREE.Group>(null);
  const content = useRef<THREE.Group>(null);

  useEffect(() => {
    const group = content.current;
    if (!group) return;
    normalizeContent(group);
    // prepareModel clona os materiais — obrigatório para não contaminar o
    // cache do useGLTF (compartilhado com o resto do app) — e marca cada
    // malha com sua camada. O retorno (lista de camadas) fica para a fase 2.
    prepareModel(group, "mesh");
  }, [scene]);

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    onIdentify(identifyStructure(event.object));
  };

  return (
    <group ref={pivot} scale={1.4}>
      <group ref={content} onClick={handleClick}>
        <primitive object={scene} />
      </group>
      <XRManipulation target={pivot} />
    </group>
  );
}

/** Conteúdo da cena; alterna controles de desktop × VR (padrão do Scene.tsx). */
function CenaClinica({
  glb,
  achados,
  onIdentify,
  labelVR,
}: {
  glb: string;
  achados: AchadosPulmao | null;
  onIdentify: (label: string) => void;
  labelVR: string | null;
}) {
  const inSession = useXR((state) => Boolean(state.session));

  return (
    <>
      <XROrigin position={[0, FLOOR_Y, 2.4]} />

      <ambientLight intensity={0.85} />
      <directionalLight position={[4, 6, 4]} intensity={1.9} color="#ffeedd" />
      <directionalLight position={[-5, 3, -4]} intensity={0.7} color="#9fc3dd" />
      <hemisphereLight args={["#dfe9f2", "#141a22", 1]} />

      {/* Palco: chão + anel, referência espacial (mesma linguagem da Arena). */}
      <mesh position={[0, FLOOR_Y, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[9, 64]} />
        <meshBasicMaterial color="#0c1219" />
      </mesh>
      <mesh position={[0, FLOOR_Y + 0.005, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.15, 1.28, 64]} />
        <meshBasicMaterial color="#5896c8" transparent opacity={0.6} />
      </mesh>
      <mesh>
        <sphereGeometry args={[28, 24, 16]} />
        <meshBasicMaterial color="#0a1017" side={THREE.BackSide} />
      </mesh>

      <ErrorBoundary
        fallback={
          <Text3D position={[0, 0.2, 0]} size={0.1} color="#e06a5c">
            Falha ao carregar o caso — recarregue a página
          </Text3D>
        }
      >
        <Suspense
          fallback={
            <Text3D position={[0, 0.2, 0]} size={0.1} color="#9fb3c4">
              Carregando o caso…
            </Text3D>
          }
        >
          {achados ? (
            <MapaAchados achados={achados} onIdentify={onIdentify} />
          ) : (
            <ModeloPaciente glb={glb} onIdentify={onIdentify} />
          )}
        </Suspense>
      </ErrorBoundary>

      {/* Em VR, o nome identificado precisa ser texto 3D (DOM é invisível). */}
      {inSession && labelVR && (
        <Text3D position={[0, 1.35, 0.6]} size={0.09} maxWidth={2.2}>
          {labelVR}
        </Text3D>
      )}

      {/* OrbitControls disputa a câmera do headset — só fora da sessão. */}
      {!inSession && (
        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.08}
          minDistance={1.2}
          maxDistance={10}
        />
      )}
    </>
  );
}

/** Visualizador isolado da Clínica (canvas e sessão XR próprios). */
export function ClinicaViewer({ caso }: { caso: CasoClinico }) {
  const mounted = useMounted();
  const [label, setLabel] = useState<string | null>(null);
  const [inSession, setInSession] = useState(false);
  const [xrError, setXrError] = useState<string | null>(null);
  const [achados, setAchados] = useState<AchadosPulmao | null>(null);
  // "mapa" = achados reais sobre o modelo ilustrativo; "malha" = superfície medida na TC.
  const [modo, setModo] = useState<"mapa" | "malha">(
    caso.achados ? "mapa" : "malha",
  );

  useEffect(() => {
    if (!caso.achados) return;
    let cancelado = false;
    fetch(caso.achados)
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data: AchadosPulmao) => {
        if (!cancelado) setAchados(data);
      })
      .catch(() => {
        if (!cancelado) setModo("malha");
      });
    return () => {
      cancelado = true;
    };
  }, [caso.achados]);

  const store = useMemo(
    () =>
      createXRStore({
        // Mesmo endurecimento da Arena (lições dos testes no Quest 2):
        // perfis locais em URL absoluta, só o ponteiro de raio, recursos de
        // realidade mista desligados e taxa de quadros intocada.
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
    <>
      {/* Barra de identificação (DOM, fora do VR) */}
      {/* Resumo dos achados medidos (só no modo mapa) */}
      {!inSession && modo === "mapa" && achados && (
        <div className="absolute right-4 top-16 z-10 w-64 rounded-xl border border-white/10 bg-black/60 p-4 text-white backdrop-blur">
          <h3 className="text-sm font-semibold">Achados do exame</h3>
          <dl className="mt-2 space-y-1 text-xs text-white/80">
            <div className="flex justify-between">
              <dt>Enfisema (LAA-950)</dt>
              <dd className="font-medium text-white">
                {achados.enfisemaPctTotal}%
              </dd>
            </div>
            <div className="flex justify-between">
              <dt>Opacidades candidatas</dt>
              <dd className="font-medium text-white">
                {achados.lesoes.length}
              </dd>
            </div>
          </dl>
          <p className="mt-3 text-[10px] leading-snug text-white/50">
            Medidas reais da TC projetadas num modelo ilustrativo — a posição
            dos marcadores é aproximada. Clique num marcador para detalhes.
          </p>
        </div>
      )}

      {!inSession && (
        <div className="pointer-events-none absolute inset-x-0 bottom-6 z-10 flex flex-col items-center gap-3">
          {caso.achados && (
            <div className="pointer-events-auto flex overflow-hidden rounded-full border border-white/15 bg-black/50 text-xs font-medium backdrop-blur">
              {(
                [
                  ["mapa", "Mapa de achados"],
                  ["malha", "Reconstrução real"],
                ] as const
              ).map(([valor, rotulo]) => (
                <button
                  key={valor}
                  type="button"
                  onClick={() => {
                    setModo(valor);
                    setLabel(null);
                  }}
                  className={
                    modo === valor
                      ? "bg-[#5896c8] px-4 py-1.5 text-[#0b1220]"
                      : "px-4 py-1.5 text-white/70 hover:text-white"
                  }
                >
                  {rotulo}
                </button>
              ))}
            </div>
          )}
          {label ? (
            <p className="rounded-full border border-white/15 bg-black/60 px-4 py-2 text-sm font-medium text-white backdrop-blur">
              Estrutura: <span className="text-[#7fb2d9]">{label}</span>
            </p>
          ) : (
            <p className="rounded-full border border-white/10 bg-black/40 px-4 py-1.5 text-xs text-white/70 backdrop-blur">
              Clique numa estrutura para identificá-la
            </p>
          )}
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
          <p className="max-w-xl px-4 text-center text-[11px] text-white/50">
            Visualização educacional a partir de exame real anonimizado — não
            substitui laudo ou avaliação médica. Fonte: {caso.fonteDados}
          </p>
        </div>
      )}

      <Canvas
        shadows={false}
        dpr={1}
        frameloop="always"
        camera={{ position: [0, 0.4, 3.0], fov: 50 }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl }) => gl.setClearColor("#101820")}
      >
        <XR store={store}>
          <CenaClinica
            glb={caso.glb}
            achados={modo === "mapa" ? achados : null}
            onIdentify={setLabel}
            labelVR={label}
          />
        </XR>
      </Canvas>
    </>
  );
}
