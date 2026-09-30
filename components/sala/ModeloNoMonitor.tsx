"use client";

import { Suspense, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal, useFrame, useThree } from "@react-three/fiber";
import { useFBO, useGLTF } from "@react-three/drei";
import { Color, Group, PerspectiveCamera, Scene, UnsignedByteType } from "three";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Text3D } from "@/components/arena/ui3d";
import { normalizeContent } from "@/lib/model-utils";
import { RESOLUCAO_MODELO_MONITOR, type VistaMonitor } from "@/lib/monitor-comparacao";
import { renderizarModeloNoMonitor } from "@/lib/monitor-render";
import type { Vec3 } from "@/types";

export type EstadoModeloMonitor = "verificando" | "carregando" | "pronto" | "ausente" | "erro";

function Anatomia({ caminho, pronto }: { caminho: string; pronto: () => void }) {
  const { scene } = useGLTF(caminho, "/draco/");
  // Transformações próprias, geometria e materiais do cache não são alterados.
  const modelo = useMemo(() => {
    const grupo = new Group(); grupo.add(scene.clone(true)); normalizeContent(grupo); return grupo;
  }, [scene]);
  useLayoutEffect(pronto, [pronto, modelo]);
  return <primitive object={modelo} dispose={null} />;
}

/** Uma textura da GPU, não uma captura de HTML nem outro Canvas/WebGL. */
function ImagemModelo({ caminho, vista, position, pronto, falhou, ponto }: {
  caminho: string; vista: VistaMonitor; position: [number, number, number];
  pronto: () => void; falhou: () => void;
  ponto?: Vec3;
}) {
  const [cena] = useState(() => { const scene = new Scene(); scene.background = new Color("#11252d"); return scene; });
  const [camera] = useState(() => { const c = new PerspectiveCamera(38, 2, .05, 30); c.position.z = 4; return c; });
  const alvo = useFBO(...RESOLUCAO_MODELO_MONITOR, { samples: 0, type: UnsignedByteType, generateMipmaps: false });
  const sujo = useRef(true);
  const canvas = useThree((s) => s.gl.domElement);
  const carregou = useCallback(() => { sujo.current = true; pronto(); }, [pronto]);
  useLayoutEffect(() => { sujo.current = true; }, [vista, alvo, ponto]);
  useEffect(() => {
    const restaurar = () => { sujo.current = true; };
    canvas.addEventListener("webglcontextrestored", restaurar);
    return () => canvas.removeEventListener("webglcontextrestored", restaurar);
  }, [canvas]);

  useFrame(({ gl }) => {
    if (!sujo.current || gl.getContext().isContextLost()) return;
    // Uma renderização somente ao carregar/girar/aproximar. O monitor parado
    // não redesenha os órgãos a cada frame nem interfere na câmera XR.
    renderizarModeloNoMonitor(gl, alvo, cena, camera); sujo.current = false;
  }, -1);

  return <>
    {createPortal(<group pointerEvents="none">
      <ambientLight intensity={.75} />
      <directionalLight position={[3, 4, 5]} intensity={2} color="#fff2e2" />
      <directionalLight position={[-3, 2, -3]} intensity={.6} color="#c4ddf1" />
      <group rotation={[vista.vertical, vista.horizontal, 0]} scale={vista.zoom}>
        <ErrorBoundary fallback={null} onError={falhou}>
          <Suspense fallback={null}><Anatomia caminho={caminho} pronto={carregou} /></Suspense>
        </ErrorBoundary>
        {ponto && <mesh position={ponto}>
          <sphereGeometry args={[.05, 16, 12]} />
          <meshBasicMaterial color="#ffce52" toneMapped={false} />
        </mesh>}
      </group>
    </group>, cena)}
    <mesh position={position} pointerEvents="none">
      <planeGeometry args={[.462, .231]} />
      <meshBasicMaterial map={alvo.texture} toneMapped={false} />
    </mesh>
  </>;
}

export function ModeloNoMonitor({ caminho, vista, x, ponto, onEstado }: {
  caminho: string; vista: VistaMonitor; x: number; ponto?: Vec3;
  onEstado?: (estado: EstadoModeloMonitor) => void;
}) {
  const [estado, setEstado] = useState<EstadoModeloMonitor>("verificando");
  useEffect(() => { onEstado?.(estado); }, [estado, onEstado]);
  useEffect(() => {
    const abort = new AbortController();
    const prazo = setTimeout(() => { abort.abort(); setEstado("erro"); }, 15_000);
    fetch(caminho, { method: "HEAD", signal: abort.signal })
      .then((res) => { if (!abort.signal.aborted) setEstado(res.ok ? "carregando" : res.status === 404 ? "ausente" : "erro"); })
      .catch(() => { if (!abort.signal.aborted) setEstado("erro"); })
      .finally(() => clearTimeout(prazo));
    return () => { clearTimeout(prazo); abort.abort(); };
  }, [caminho]);
  const pronto = useCallback(() => setEstado("pronto"), []);
  const falhou = useCallback(() => { useGLTF.clear(caminho); setEstado("erro"); }, [caminho]);
  return <group>
    {(estado === "carregando" || estado === "pronto") && <ImagemModelo caminho={caminho} vista={vista} position={[x, .015, .0015]} pronto={pronto} falhou={falhou} ponto={ponto} />}
    {estado !== "pronto" && <Text3D tratamento="tela" position={[x, .015, .0025]} size={.024} maxWidth={.42}>
      {estado === "ausente" ? "Modelo ainda não disponível.\nSem substituto anatômico." : estado === "erro" ? "Falha ao carregar.\nTroque o órgão para tentar novamente." : "Carregando modelo…"}
    </Text3D>}
  </group>;
}
