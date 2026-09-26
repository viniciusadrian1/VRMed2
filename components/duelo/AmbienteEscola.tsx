"use client";

import { Suspense, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF, useTexture } from "@react-three/drei";
import * as THREE from "three";
import { Text3D } from "@/components/arena/ui3d";
import { BotaoDuelo as Button3D } from "./tipografia";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { sinalDaArena } from "@/lib/duelo-apresentacao";
import { ESCOLA, mostrarEsqueleto3D } from "@/lib/escola-apresentacao";
import { useEstadoArena } from "./EstadoArena";
import { Bloco, FaixaReativa, SinalEscola } from "./ArenaMedica";
import { ContatoEscola, OrientacaoEscola } from "./OrientacaoEscola";
import { SinalizacaoCenario } from "./SinalizacaoCenario";
import { PisoCenario } from "./PisoCenario";
import { useReflexosCenario } from "./useReflexosCenario";
import { SalaEscolaRevisao } from "./SalaEscolaRevisao";

const CENARIO = "/models/props/escola-medicina-direcao.glb";
const ESQUELETO = "/models/props/esqueleto-estudo.glb";
const PRANCHA = "/models/props/esqueleto-prancha.png";
const SEM_RAYCAST = () => null;

function SalaAutoral() {
  const gltf = useGLTF(CENARIO);
  const cena = useMemo(() => {
    const clone = gltf.scene.clone(true);
    clone.traverse((o) => { if (o instanceof THREE.Mesh) o.raycast = SEM_RAYCAST; });
    return clone;
  }, [gltf.scene]);
  useReflexosCenario(cena);
  return <primitive object={cena} dispose={null} />;
}

/** Clone com escala uniforme; não decima nem altera malhas anatômicas. */
function ModeloExposto({ url, altura }: { url: string; altura: number }) {
  const gltf = useGLTF(url, "/draco/");
  const modelo = useMemo(() => {
    const cena = gltf.scene.clone(true);
    cena.updateMatrixWorld(true);
    const caixa = new THREE.Box3().setFromObject(cena);
    const centro = caixa.getCenter(new THREE.Vector3());
    const escala = altura / Math.max(caixa.max.y - caixa.min.y, 1e-6);
    const raiz = new THREE.Group();
    raiz.add(cena); raiz.scale.setScalar(escala);
    raiz.position.set(-centro.x * escala, -caixa.min.y * escala, -centro.z * escala);
    raiz.traverse((o) => { if (o instanceof THREE.Mesh) o.raycast = SEM_RAYCAST; });
    return raiz;
  }, [gltf.scene, altura]);
  return <primitive object={modelo} dispose={null} />;
}

function PranchaOsteologia() {
  const textura = useTexture(PRANCHA, (carregada) => {
    // Metadado aplicado no carregamento, nunca como mutação durante o render.
    (carregada as THREE.Texture).colorSpace = THREE.SRGBColorSpace;
  });
  return <mesh position={[0, 0.97, -0.09]} raycast={SEM_RAYCAST}>
    <planeGeometry args={[0.92, 1.84]} />
    <meshBasicMaterial map={textura} toneMapped={false} />
  </mesh>;
}

function VitrineOsteologia({ detalhado, alternar }: { detalhado: boolean; alternar: () => void }) {
  const { fase } = useEstadoArena();
  const disponivel = fase === "menu" || fase === "fim";
  const mostrar = mostrarEsqueleto3D(fase, detalhado);
  return <group position={[1.82, ESCOLA.piso + 0.2, -2.40]}>
    <group pointerEvents="none">
      <Suspense fallback={null}>
        {mostrar ? <ErrorBoundary key="esqueleto" fallback={<PranchaOsteologia />}>
          <Suspense fallback={<PranchaOsteologia />}><ModeloExposto url={ESQUELETO} altura={1.73} /></Suspense>
        </ErrorBoundary> : <PranchaOsteologia />}
      </Suspense>
      <Bloco pos={[0, 1.89, .105]} tam={[1.08, .12, .025]} cor="#193c2f" />
      <Text3D tratamento="placa" position={[0, 1.89, 0.13]} size={0.035} maxWidth={1.02} color="#d9d9bf">
        {mostrar ? "Ossos e dentes · acervo 3D" : "Prancha de osteologia"}
      </Text3D>
      <Bloco pos={[.86, .78, .19]} tam={[.69, .34, .08]} cor="#193c2f" />
      <Text3D tratamento="placa" position={[.86, .68, .25]} size={0.026} maxWidth={.60} color="#c9d4c3">
        {disponivel ? "Detalhado · maior custo" : "Partida · órgão em foco"}
      </Text3D>
    </group>
    <Button3D position={[.86, .84, .25]} width={.64} height={0.14}
      label={mostrar ? "Usar prancha leve" : "Ver esqueleto 3D"}
      onClick={alternar} desabilitado={!disponivel} color="#31574d" />
  </group>;
}

export function IluminacaoEscola() {
  const estado = useEstadoArena();
  const recorte = useRef<THREE.DirectionalLight>(null);
  const cor = useMemo(() => new THREE.Color(sinalDaArena(estado).cor), [estado]);
  useFrame((_, delta) => recorte.current?.color.lerp(cor, 1 - Math.exp(-Math.min(delta, .1) * 3)));
  return <>
    {/* Luz principal neutra/quente preserva as cores anatômicas. */}
    <directionalLight position={[-3, 4, 3]} intensity={2.5} color="#fff0d9" />
    <directionalLight ref={recorte} position={[3, 3, -4]} intensity={0.5} color="#a8d5c5" />
    <hemisphereLight args={["#e2eee5", "#434334", 0.8]} />
  </>;
}

// A revisão aprovada é o padrão; false permite recuperar a sala anterior sem apagar seus assets.
export function AmbienteEscola({ detalhado, alternar, revisao = true }: {
  detalhado: boolean; alternar: () => void; revisao?: boolean;
}) {
  const estado = useEstadoArena();
  const sinal = sinalDaArena(estado);
  return <>
    <group pointerEvents="none">
      <group position={[0, ESCOLA.piso, 0]}>
        <ErrorBoundary fallback={<Bloco pos={[.36, 1.18, -1.12]} tam={[1.35, 1.02, .08]} cor="#193c2f" />}>
          <Suspense fallback={null}>{revisao ? <SalaEscolaRevisao /> : <SalaAutoral />}</Suspense>
        </ErrorBoundary>
        <SinalizacaoCenario sala="escola" />
        {!revisao && <PisoCenario sala="escola" />}
      </group>
      <SinalEscola />
      <ContatoEscola />
      <OrientacaoEscola />
      <FaixaReativa pos={[-.78, -.51, -.554]} tam={[.85, .012, .015]} />
      <mesh position={[-.78, -.454, -.95]} rotation={[-Math.PI / 2, 0, 0]} raycast={SEM_RAYCAST}>
        <ringGeometry args={[.27, .283, 48]} /><meshBasicMaterial color={sinal.cor} toneMapped={false} />
      </mesh>
      {estado.fase === "menu" && <group position={[-.78, -.43, -.95]}>
        <ErrorBoundary fallback={null}><Suspense fallback={null}>
          <ModeloExposto url="/models/healthy/coracao.glb" altura={.63} />
        </Suspense></ErrorBoundary>
      </group>}
      <Bloco pos={[-.78, -.63, -.587]} tam={[.72, .10, .016]} cor="#193c2f" />
      <Text3D tratamento="placa" position={[-.78, -.63, -.575]} size={.041} color="#ede5cf">Observe o órgão</Text3D>
      <Bloco pos={[.36, -.775, -.985]} tam={[1.08, .17, .027]} cor="#193c2f" />
      <Text3D tratamento="tela" position={[.36, -.735, -.965]} size={.034} color={sinal.cor}>
        {estado.combo > 1 ? `Sequência ×${estado.combo} · continue assim` : "Observe · identifique · aprenda"}
      </Text3D>
      {Array.from({ length: 8 }, (_, i) => <mesh key={i} position={[.08 + i * .08, -.81, -.965]} raycast={SEM_RAYCAST}>
        <circleGeometry args={[.018, 12]} />
        <meshBasicMaterial color={estado.fase === "menu" ? "#657567" : i < estado.rodada ? sinal.cor : "#657567"} toneMapped={false} />
      </mesh>)}
      <FaixaReativa pos={[-3.30, -.24, -1.8]} tam={[.018, .015, 2.0]} />
      <FaixaReativa pos={[1.82, .84, -2.16]} tam={[1.10, .016, .014]} />
    </group>
    <VitrineOsteologia detalhado={detalhado} alternar={alternar} />
  </>;
}

// Sem preload da sala anterior: preservada para recuperação, não é baixada na versão padrão.
// Sem preload do esqueleto: no Quest ele só é pedido por escolha explícita.
