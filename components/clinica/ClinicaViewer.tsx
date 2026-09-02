"use client";

import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import { Canvas, useThree, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { XR, XROrigin, useXR } from "@react-three/xr";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import {
  identifyStructure,
  normalizeContent,
  prepareModel,
} from "@/lib/model-utils";
import { obterXRStore } from "@/lib/xr-store";
import { XRManipulation } from "@/components/viewer/XRManipulation";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Text3D } from "@/components/arena/ui3d";
import { useMounted } from "@/hooks/use-mounted";
import { MapaAchados, type AchadosPulmao } from "./MapaAchados";
import type { CasoClinico } from "./ClinicaApp";

const FLOOR_Y = -1.3;

/**
 * Planos de corte em coordenadas de MUNDO. O pipeline exporta o paciente com
 * a frente em −Z e a direita em +X (RAS); o ModeloPaciente gira 180° em Y para
 * a vista inicial ser de frente, como um atlas: no mundo a frente fica em +Z
 * e a direita do paciente em −X (à esquerda de quem olha). O three.js
 * descarta o lado negativo do plano, então cada normal aponta para o que FICA.
 */
const CORTES = {
  axial: { normal: [0, -1, 0] as const, rotulo: "Axial" }, // tira o que está acima
  coronal: { normal: [0, 0, -1] as const, rotulo: "Coronal" }, // tira a frente (+Z)
  sagital: { normal: [-1, 0, 0] as const, rotulo: "Sagital" }, // tira o lado esquerdo (+X)
} as const;
type Corte = keyof typeof CORTES | "nenhum";
// normalizeContent deixa o modelo em ±1 e o pivô escala 1,4 → cabe em ±1,5.
const ALCANCE = 1.5;

/** Mapa de ambiente local (sem CDN): brilho úmido e sombra suave nos órgãos.
 *  Declarativo (attach) porque o React Compiler proíbe mutar `scene`. */
function AmbienteLuz() {
  const gl = useThree((state) => state.gl);
  const ambiente = useMemo(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    const textura = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    return textura;
  }, [gl]);
  useEffect(() => () => ambiente.dispose(), [ambiente]);
  return <primitive object={ambiente} attach="environment" />;
}

/** Modelo do paciente: carrega, prepara materiais, corte e envelope. */
function ModeloPaciente({
  glb,
  plano,
  mostrarEnvelope,
  onIdentify,
  onCarregado,
}: {
  glb: string;
  plano: RefObject<THREE.Plane>;
  mostrarEnvelope: boolean;
  onIdentify: (label: string) => void;
  onCarregado: (info: { temCamaras: boolean }) => void;
}) {
  const gltf = useGLTF(glb, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  const pivot = useRef<THREE.Group>(null);
  const content = useRef<THREE.Group>(null);

  useEffect(() => {
    const group = content.current;
    if (!group) return;
    normalizeContent(group);
    // prepareModel clona os materiais (não contamina o cache do useGLTF) e
    // marca cada malha com sua camada.
    prepareModel(group, "mesh");
    let temCamaras = false;
    group.traverse((obj) => {
      if (obj.name.startsWith("heart_")) temCamaras = true;
    });
    group.traverse((obj) => {
      if (!(obj instanceof THREE.Mesh)) return;
      const mat = obj.material as THREE.MeshStandardMaterial;
      if (!("roughness" in mat)) return;
      // Com câmaras no GLB, o rótulo `heart` é o envelope epicárdico: fica
      // translúcido por cima das câmaras (e pode ser escondido).
      const envelope = temCamaras && obj.name === "heart";
      obj.userData.envelope = envelope;
      // Órgão vivo é úmido, não plástico: rugosidade média + mapa de ambiente.
      mat.roughness = 0.5;
      mat.metalness = 0;
      mat.envMapIntensity = 0.7;
      // Corte: a parede interna precisa aparecer (DoubleSide), menos no
      // envelope translúcido, onde as duas faces se somam e turvam a vista.
      mat.side = envelope ? THREE.FrontSide : THREE.DoubleSide;
      mat.clippingPlanes = [plano.current];
      if (envelope) {
        mat.transparent = true;
        mat.opacity = 0.22;
        mat.depthWrite = false;
        obj.renderOrder = 2;
      }
      mat.needsUpdate = true;
    });
    onCarregado({ temCamaras });
  }, [scene, plano, onCarregado]);

  useEffect(() => {
    content.current?.traverse((obj) => {
      if (obj.userData.envelope) obj.visible = mostrarEnvelope;
    });
  }, [mostrarEnvelope, scene]);

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    // O raycast do three não filtra `visible` nem `clippingPlanes`: pula o
    // envelope oculto e as faces do lado removido pelo corte. Em VR o
    // pointer-events entrega `intersections` vazio → usa o próprio hit.
    const hits = event.intersections.length ? event.intersections : [event];
    const hit = hits.find(
      (h) => h.object.visible && plano.current.distanceToPoint(h.point) >= 0,
    );
    if (!hit) return;
    event.stopPropagation();
    onIdentify(identifyStructure(hit.object));
  };

  return (
    // Meia-volta: o pipeline exporta a frente do paciente em −Z; a câmera e
    // o XROrigin ficam em +Z, então sem isto a primeira vista era das costas.
    <group ref={pivot} scale={1.4} rotation={[0, Math.PI, 0]}>
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
  mapaGlb,
  achados,
  plano,
  mostrarEnvelope,
  onIdentify,
  onCarregado,
  labelVR,
}: {
  glb: string;
  mapaGlb: string | null;
  achados: AchadosPulmao | null;
  plano: RefObject<THREE.Plane>;
  mostrarEnvelope: boolean;
  onIdentify: (label: string) => void;
  onCarregado: (info: { temCamaras: boolean }) => void;
  labelVR: string | null;
}) {
  const inSession = useXR((state) => Boolean(state.session));

  return (
    <>
      <XROrigin position={[0, FLOOR_Y, 2.4]} />

      {/* Uma luz direcional + ambiente por mapa: luz ambiente dupla achatava
          o relevo (Meta: 1 luz com PBR é o orçamento do Quest 2). */}
      <AmbienteLuz />
      <directionalLight position={[4, 6, 4]} intensity={2.2} color="#ffeedd" />
      <hemisphereLight args={["#dfe9f2", "#141a22", 0.25]} />

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
          {achados && mapaGlb ? (
            <MapaAchados
              mapaGlb={mapaGlb}
              achados={achados}
              onIdentify={onIdentify}
            />
          ) : (
            <ModeloPaciente
              glb={glb}
              plano={plano}
              mostrarEnvelope={mostrarEnvelope}
              onIdentify={onIdentify}
              onCarregado={onCarregado}
            />
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
  // "malha" = superfície medida na TC (padrão); "mapa" = achados sobre o
  // modelo ilustrativo (alternativa, enquanto não há modelo de artista melhor).
  const [modo, setModo] = useState<"mapa" | "malha">("malha");
  const [corte, setCorte] = useState<Corte>("nenhum");
  const [posicao, setPosicao] = useState(0.5);
  const [temCamaras, setTemCamaras] = useState(false);
  const [mostrarEnvelope, setMostrarEnvelope] = useState(true);

  // Um plano só, compartilhado pelos materiais (ref: o React Compiler proíbe
  // mutar valores de useMemo); os estados o reposicionam no efeito.
  const plano = useRef(new THREE.Plane(new THREE.Vector3(0, -1, 0), 100));
  useEffect(() => {
    const p = plano.current;
    if (corte === "nenhum") {
      p.constant = 100; // fora do modelo: nada é cortado
      return;
    }
    const [x, y, z] = CORTES[corte].normal;
    p.normal.set(x, y, z);
    // posicao 0 = plano na borda (sem corte) … 1 = atravessou o modelo inteiro
    p.constant = ALCANCE - posicao * 2 * ALCANCE;
  }, [corte, posicao]);

  const aoCarregar = useCallback((info: { temCamaras: boolean }) => {
    setTemCamaras(info.temCamaras);
  }, []);

  useEffect(() => {
    if (!caso.achados || !caso.mapaGlb) return;
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
  }, [caso.achados, caso.mapaGlb]);

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
    <>
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
            Textura gerada a partir das medidas da TC sobre um modelo
            ilustrativo — a posição das manchas é aproximada. Clique numa
            mancha escura para detalhes.
          </p>
        </div>
      )}

      {/* Corte por plano + envelope (só na reconstrução real, fora do VR) */}
      {!inSession && modo === "malha" && (
        <div className="absolute right-4 top-16 z-10 w-60 rounded-xl border border-white/10 bg-black/60 p-3 text-white backdrop-blur">
          <p className="text-xs font-semibold">Corte</p>
          <div className="mt-2 grid grid-cols-4 gap-1 text-[11px]">
            {(["nenhum", "axial", "coronal", "sagital"] as const).map((valor) => (
              <button
                key={valor}
                type="button"
                onClick={() => setCorte(valor)}
                className={
                  corte === valor
                    ? "rounded-md bg-[#5896c8] px-1 py-1 text-[#0b1220]"
                    : "rounded-md border border-white/15 px-1 py-1 text-white/70 hover:text-white"
                }
              >
                {valor === "nenhum" ? "Sem" : CORTES[valor].rotulo}
              </button>
            ))}
          </div>
          {corte !== "nenhum" && (
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={posicao}
              onChange={(event) => setPosicao(Number(event.target.value))}
              aria-label="Posição do corte"
              className="mt-3 w-full accent-[#5896c8]"
            />
          )}
          {temCamaras && (
            <button
              type="button"
              onClick={() => setMostrarEnvelope((v) => !v)}
              className="mt-3 w-full rounded-md border border-white/15 px-2 py-1 text-[11px] text-white/80 hover:text-white"
            >
              Envelope do coração: {mostrarEnvelope ? "visível" : "oculto"}
            </button>
          )}
          <p className="mt-2 text-[10px] leading-snug text-white/50">
            {temCamaras
              ? "Câmaras e artéria pulmonar são malhas próprias; o miocárdio rotulado é só o do ventrículo esquerdo."
              : "Superfície medida na TC; detalhes menores que 3 mm não são representados."}
          </p>
        </div>
      )}

      {!inSession && (
        <div className="pointer-events-none absolute inset-x-0 bottom-6 z-10 flex flex-col items-center gap-3">
          {caso.achados && caso.mapaGlb && (
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
        // NeutralToneMapping preserva o matiz do vermelho (ACES dessatura);
        // localClippingEnabled liga os planos de corte por material.
        gl={{
          antialias: true,
          alpha: false,
          toneMapping: THREE.NeutralToneMapping,
          localClippingEnabled: true,
        }}
        scene={{ environmentIntensity: 0.7 }}
        onCreated={({ gl }) => gl.setClearColor("#101820")}
      >
        <XR store={store}>
          <CenaClinica
            glb={caso.glb}
            mapaGlb={caso.mapaGlb ?? null}
            achados={modo === "mapa" ? achados : null}
            plano={plano}
            mostrarEnvelope={mostrarEnvelope}
            onIdentify={setLabel}
            onCarregado={aoCarregar}
            labelVR={label}
          />
        </XR>
      </Canvas>
    </>
  );
}
