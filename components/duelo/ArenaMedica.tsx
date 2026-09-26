"use client";

import { Suspense, useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { useXR } from "@react-three/xr";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { Text3D } from "@/components/arena/ui3d";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { sinalDaArena } from "@/lib/duelo-apresentacao";
import { useEstadoArena } from "./EstadoArena";

export const CONSOLE_POS: [number, number, number] = [0.85, 0.15, -0.65];
export const CONSOLE_ROT: [number, number, number] = [0, -0.14, 0];
export const LETREIRO_POS: [number, number, number] = [0, 1.51, -3.12];
const SEM_RAYCAST = () => null;

export function IluminacaoArena() {
  const estado = useEstadoArena();
  const sinal = sinalDaArena(estado);
  const chave = useRef<THREE.DirectionalLight>(null);
  const recorte = useRef<THREE.DirectionalLight>(null);
  const cor = useMemo(() => new THREE.Color(sinal.cor), [sinal.cor]);
  const vitoria = estado.fase === "fim" && estado.meus > estado.outros;
  const corChave = useMemo(() => new THREE.Color(vitoria ? "#ffe1ba" : "#fff0d9"), [vitoria]);
  useFrame((_, delta) => {
    const passo = 1 - Math.exp(-Math.min(delta, 0.1) * 3);
    chave.current?.color.lerp(corChave, passo);
    recorte.current?.color.lerp(cor, passo);
  });
  return <>
    {/* Cor de estado só no recorte traseiro: a luz principal mantém a anatomia. */}
    <directionalLight ref={chave} position={[-1, 3, 4]} intensity={2.9} color="#fff0d9" />
    <directionalLight ref={recorte} position={[3, 3, -4]} intensity={0.85} color="#77cfe3" />
    <hemisphereLight args={["#daeaf0", "#263e46", 0.8]} />
  </>;
}

/** Blocos arquitetônicos opacos: sem sombras dinâmicas ou intercepção do laser. */
export function Bloco({ pos, tam, cor = "#223e49", metal = 0.12 }: {
  pos: [number, number, number]; tam: [number, number, number]; cor?: string; metal?: number;
}) {
  return <mesh position={pos} raycast={SEM_RAYCAST}><boxGeometry args={tam} /><meshStandardMaterial color={cor} roughness={0.65} metalness={metal} /></mesh>;
}

/** Luz de estado é emissiva, não uma luz extra por prop. Pulso lento, sem flashes. */
export function FaixaReativa({ pos, tam }: { pos: [number, number, number]; tam: [number, number, number] }) {
  const estado = useEstadoArena();
  const sinal = sinalDaArena(estado);
  const material = useRef<THREE.MeshBasicMaterial>(null);
  const reduzir = useRef(false);
  const alvo = useMemo(() => new THREE.Color(sinal.cor), [sinal.cor]);
  useEffect(() => {
    const consulta = window.matchMedia("(prefers-reduced-motion: reduce)");
    const atualizar = () => { reduzir.current = consulta.matches; };
    atualizar(); consulta.addEventListener("change", atualizar);
    return () => consulta.removeEventListener("change", atualizar);
  }, []);
  useFrame(({ clock }, delta) => {
    if (!material.current) return;
    material.current.color.lerp(alvo, 1 - Math.exp(-Math.min(delta, 0.1) * 5));
    material.current.opacity = sinal.pulso && !reduzir.current ? 0.88 + 0.12 * Math.sin(clock.elapsedTime * Math.PI * 1.2) : 1;
  });
  return <mesh position={pos} raycast={SEM_RAYCAST}><boxGeometry args={tam} /><meshBasicMaterial ref={material} color="#77cfe3" toneMapped={false} transparent depthWrite={false} /></mesh>;
}

function BancadaAutoral() {
  const gltf = useGLTF("/models/props/bancada-arena.glb");
  const cena = useMemo(() => {
    const clone = gltf.scene.clone(true);
    clone.traverse((obj) => { if (obj instanceof THREE.Mesh) obj.raycast = SEM_RAYCAST; });
    return clone;
  }, [gltf.scene]);
  return <primitive object={cena} dispose={null} />;
}

function PreviaAnatomica({ empilhar }: { empilhar: boolean }) {
  const gltf = useGLTF("/models/healthy/coracao.glb", "/draco/");
  const previa = useMemo(() => {
    const cena = gltf.scene.clone(true);
    cena.updateMatrixWorld(true);
    const caixa = new THREE.Box3().setFromObject(cena);
    const centro = caixa.getCenter(new THREE.Vector3());
    const tamanho = caixa.getSize(new THREE.Vector3());
    const escala = 0.86 / Math.max(tamanho.x, tamanho.y, tamanho.z, 1e-6);
    const grupo = new THREE.Group();
    grupo.add(cena);
    grupo.scale.setScalar(escala);
    grupo.position.copy(centro.multiplyScalar(-escala));
    grupo.traverse((obj) => { if (obj instanceof THREE.Mesh) obj.raycast = SEM_RAYCAST; });
    return grupo;
  }, [gltf.scene]);
  return <group position={empilhar ? [1.9, 2.75, 0] : [0, 1.52, 0]} scale={empilhar ? 0.69 : 1}><primitive object={previa} dispose={null} /></group>;
}

export function PalcoAnatomico() {
  const estado = useEstadoArena();
  const retrato = useThree((s) => s.size.width < s.size.height);
  const emXR = useXR((s) => Boolean(s.session));
  const sinal = sinalDaArena(estado);
  return (
    <group position={[-1.05, -1.3, -0.5]}>
      <ErrorBoundary fallback={<Bloco pos={[0, 0.38, 0]} tam={[1.1, 0.76, 0.9]} />}>
        <Suspense fallback={<Bloco pos={[0, 0.38, 0]} tam={[1.1, 0.76, 0.9]} />}><BancadaAutoral /></Suspense>
      </ErrorBoundary>
      <FaixaReativa pos={[0, 0.77, 0.55]} tam={[0.95, 0.018, 0.018]} />
      {estado.fase === "menu" && <ErrorBoundary fallback={null}><Suspense fallback={null}><PreviaAnatomica empilhar={retrato && !emXR} /></Suspense></ErrorBoundary>}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.872, 0]} raycast={SEM_RAYCAST}>
        <ringGeometry args={[0.40, 0.425, 64]} /><meshBasicMaterial color={sinal.cor} toneMapped={false} />
      </mesh>
      <Bloco pos={[0, 0.635, 0.535]} tam={[1.02, 0.20, 0.035]} cor="#102c35" />
      <Text3D tratamento="placa" position={[0, 0.683, 0.558]} size={0.038} color="#c3dfe6">Estação anatômica</Text3D>
      <Text3D tratamento="tela" position={[0, 0.605, 0.558]} size={0.034} color={sinal.cor} maxWidth={0.98}>{estado.fase === "menu" ? "Modelo de demonstração" : sinal.rotulo}</Text3D>
    </group>
  );
}

/** Carcaça, suporte e cabeçalho dão um lugar físico à interface já existente. */
export function ConsoleArena() {
  const estado = useEstadoArena();
  return (
    <group position={CONSOLE_POS} rotation={CONSOLE_ROT}>
      <Bloco pos={[0, -0.2, -0.10]} tam={[1.84, 2.02, 0.17]} cor="#122c36" />
      <Bloco pos={[0, -0.2, -0.008]} tam={[1.72, 1.89, 0.018]} cor="#111e29" />
      <FaixaReativa pos={[0, 0.84, -0.02]} tam={[1.82, 0.026, 0.08]} />
      <Bloco pos={[0, -1.29, -0.15]} tam={[0.3, 0.35, 0.24]} />
      <Bloco pos={[0, -1.4, 0]} tam={[1.15, 0.10, 0.7]} cor="#183440" />
      <Text3D tratamento="tela" position={[-0.76, 0.77, 0.006]} anchorX="left" align="left" size={0.039} color="#c3dfe6">VRmed / Duelo</Text3D>
      <Text3D tratamento="tela" position={[0.76, 0.77, 0.006]} anchorX="right" align="right" size={0.032} color={estado.combo > 1 ? "#f5c781" : "#97cad4"}>
        {estado.combo > 1 ? `Sequência ×${estado.combo}` : "Treinamento 1×1"}
      </Text3D>
    </group>
  );
}

/** Monitor lateral comunica o mesmo estado por cor E texto, sem simular dados clínicos. */
export function MonitorArena({ pos, titulo }: { pos: [number, number, number]; titulo: string }) {
  const estado = useEstadoArena();
  const sinal = sinalDaArena(estado);
  return <group position={pos}>
    <Bloco pos={[0, 0, 0]} tam={[1.08, 0.69, 0.14]} cor="#102732" />
    <Text3D tratamento="tela" position={[-0.46, 0.22, 0.08]} anchorX="left" align="left" size={0.033} maxWidth={0.92} color="#abcdd6">{titulo}</Text3D>
    <Text3D tratamento="tela" position={[0, 0.03, 0.08]} size={0.056} color={sinal.cor} maxWidth={0.94}>{sinal.rotulo}</Text3D>
    <FaixaReativa pos={[0, -0.23, 0.08]} tam={[0.88, 0.022, 0.015]} />
    <Text3D tratamento="tela" position={[0, -0.29, 0.08]} size={0.028} maxWidth={0.96} color="#9cb2ba">Sinal de jogo · não clínico</Text3D>
  </group>;
}

/** A lousa também participa do feedback; o cenário Escola continua disponível. */
export function SinalEscola() {
  const sinal = sinalDaArena(useEstadoArena());
  return <group>
    <FaixaReativa pos={[0.36, 0.31, -1.065]} tam={[1.12, 0.012, 0.01]} />
    <Text3D tratamento="interface" position={[0.36, 0.35, -1.06]} size={0.023} color={sinal.cor}>{sinal.rotulo}</Text3D>
  </group>;
}
