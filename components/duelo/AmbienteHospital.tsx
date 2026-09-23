"use client";

import { Suspense, useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { Text3D } from "@/components/arena/ui3d";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Bloco, ConsoleArena, FaixaReativa, MonitorArena, PalcoAnatomico } from "./ArenaMedica";
import { EntornoHospital } from "./EntornoHospital";

/**
 * Arena médica do Duelo: bancada anatômica, console de competição e pórtico
 * reativo. A arquitetura organiza o foco; os equipamentos dão escala à sala.
 *
 * Híbrido: sala procedural + entorno autoral agrupado por material. Cadeira
 * e cortina do acervo seguem no fundo (créditos dos originais no CREDITS.md).
 * Cada prop se auto-normaliza: mede o próprio arquivo solto da cena, escala
 * para a altura-alvo e assenta a base no y=0 do grupo.
 */

const FLOOR_Y = -1.3;

function Prop({
  url,
  alturaAlvo,
  position,
  rotationY = 0,
}: {
  url: string;
  /** Altura final desejada, em metros. */
  alturaAlvo: number;
  position: [number, number, number];
  rotationY?: number;
}) {
  const gltf = useGLTF(url, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  const grupo = useRef<THREE.Group>(null);

  const ajuste = useMemo(() => {
    scene.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(scene);
    const tam = box.getSize(new THREE.Vector3());
    const centro = box.getCenter(new THREE.Vector3());
    const s = alturaAlvo / Math.max(tam.y, 1e-6);
    return {
      escala: s,
      pos: [-centro.x * s, -box.min.y * s, -centro.z * s] as [
        number,
        number,
        number,
      ],
    };
  }, [scene, alturaAlvo]);

  // Decoração pura: nenhum prop intercepta o laser/mouse do jogo.
  useLayoutEffect(() => {
    grupo.current?.traverse((obj) => {
      if (obj instanceof THREE.Mesh) obj.raycast = () => null;
    });
  }, [scene]);

  return (
    <group ref={grupo} position={position} rotation={[0, rotationY, 0]}>
      <group position={ajuste.pos} scale={ajuste.escala}>
        <primitive object={scene} dispose={null} />
      </group>
    </group>
  );
}

/** Piso técnico com juntas discretas, desenhado localmente em canvas. */
function usePisoTexture(): THREE.CanvasTexture {
  return useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#3e5960";
    ctx.fillRect(0, 0, 512, 512);
    ctx.strokeStyle = "#354b52";
    ctx.lineWidth = 2;
    for (let i = 0; i <= 8; i += 1) {
      ctx.beginPath(); ctx.moveTo(i * 64, 0); ctx.lineTo(i * 64, 512); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * 64); ctx.lineTo(512, i * 64); ctx.stroke();
    }
    // brilho sutil nos azulejos alternados
    ctx.fillStyle = "rgba(255,255,255,0.025)";
    for (let x = 0; x < 8; x += 1)
      for (let y = 0; y < 8; y += 1)
        if ((x + y) % 2 === 0) ctx.fillRect(x * 64 + 4, y * 64 + 4, 56, 56);
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(2, 2);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }, []);
}

/** Telão do cronômetro estilo LED (a moldura; o número vem do DueloGame). */
function TelaoLed({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh>
        <boxGeometry args={[2.5, 0.84, 0.16]} />
        <meshStandardMaterial color="#101820" roughness={0.4} />
      </mesh>
      <mesh position={[0, 0, 0.082]}>
        <planeGeometry args={[2.34, 0.69]} />
        <meshStandardMaterial color="#050c12" emissive="#0a2a33" emissiveIntensity={0.8} />
      </mesh>
      <FaixaReativa pos={[0, -0.40, 0.085]} tam={[2.4, 0.018, 0.015]} />
    </group>
  );
}

const HOSPITAL_DIR = "/models/hospital";

/** Sala + props. As posições assumem jogador em z≈+2.4 e bot em z≈-2.4. */
export function AmbienteHospital() {
  const piso = usePisoTexture();
  const sala = useRef<THREE.Group>(null);
  useEffect(() => () => piso.dispose(), [piso]);
  useLayoutEffect(() => {
    sala.current?.traverse((obj) => { if (obj instanceof THREE.Mesh) obj.raycast = () => null; });
  }, []);
  const MEIA = 4.6; // meia-largura da sala

  return (
    <group pointerEvents="none">
      <PalcoAnatomico />
      <ConsoleArena />
    <group ref={sala} position={[0, FLOOR_Y, 0]}>
      {/* Piso técnico dessaturado: não disputa atenção com a anatomia. */}
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[MEIA * 2, MEIA * 2]} />
        <meshStandardMaterial map={piso} roughness={0.85} />
      </mesh>
      {/* Paredes creme com faixa verde-hospital */}
      {[
        { p: [0, 1.8, -MEIA] as const, r: 0 },
        { p: [0, 1.8, MEIA] as const, r: Math.PI },
        { p: [-MEIA, 1.8, 0] as const, r: Math.PI / 2 },
        { p: [MEIA, 1.8, 0] as const, r: -Math.PI / 2 },
      ].map((w, i) => (
        <group key={i} position={[...w.p]} rotation={[0, w.r, 0]}>
          <mesh>
            <planeGeometry args={[MEIA * 2, 3.6]} />
            <meshStandardMaterial color="#9eaaa5" roughness={1} />
          </mesh>
          <mesh position={[0, -1.15, 0.01]}>
            <planeGeometry args={[MEIA * 2, 1.3]} />
            <meshStandardMaterial color="#264d59" roughness={1} />
          </mesh>
          <Bloco pos={[0, -0.47, 0.04]} tam={[MEIA * 2, 0.06, 0.07]} cor="#455e66" />
          <Bloco pos={[0, -1.73, 0.04]} tam={[MEIA * 2, 0.13, 0.07]} cor="#1d323b" />
        </group>
      ))}
      {/* Teto */}
      <mesh position={[0, 3.6, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <planeGeometry args={[MEIA * 2, MEIA * 2]} />
        <meshBasicMaterial color="#233e48" />
      </mesh>

      {/* Pórtico e fundo recuado: a área de respostas permanece sem vidro. */}
      {[-2.6, 2.6].map((x) => <group key={`luz-teto-${x}`}>
        <Bloco pos={[x, 3.56, -1.2]} tam={[0.55, 0.06, 3.4]} cor="#132b36" />
        <mesh position={[x, 3.52, -1.2]} rotation={[Math.PI / 2, 0, 0]} raycast={() => null}>
          <planeGeometry args={[0.32, 3.1]} /><meshBasicMaterial color="#b4d6d6" toneMapped={false} />
        </mesh>
      </group>)}
      <Bloco pos={[0, 1.95, -4.48]} tam={[3.7, 2.7, 0.12]} cor="#19343f" />
      {[-1.95, 1.95].map((x) => <group key={x}>
        <Bloco pos={[x, 1.8, -3.25]} tam={[0.14, 3.6, 0.23]} cor="#213e49" />
        <FaixaReativa pos={[x, 1.95, -3.12]} tam={[0.024, 2.3, 0.014]} />
      </group>)}
      <Bloco pos={[0, 3.28, -3.25]} tam={[4.04, 0.16, 0.24]} />
      <Text3D position={[0, 3.12, -3.1]} size={0.095} color="#c6dfe2">VRmed / ARENA MÉDICA</Text3D>
      <Bloco pos={[0, 0.015, -0.6]} tam={[3.7, 0.025, 2.35]} cor="#253f48" />
      {[-1, 1].map((lado) => <group key={lado}>
        <FaixaReativa pos={[lado * 1.65, 0.036, 0.05]} tam={[0.03, 0.012, 1.5]} />
        <FaixaReativa pos={[lado * 3.32, 3.0, -4.23]} tam={[1.78, 0.016, 0.018]} />
      </group>)}

      {/* Equipamentos e arquitetura lateral autorais; o centro fica intacto. */}
      <ErrorBoundary fallback={null}><Suspense fallback={null}>
        <EntornoHospital />
      </Suspense></ErrorBoundary>

      {/* Telão LED do cronômetro no alto, entre os dois lados */}
      <TelaoLed position={[0, 2.81, -3.22]} />
      <MonitorArena pos={[-3.12, 1.57, -3.36]} titulo="ESTAÇÃO DO ADVERSÁRIO" />

      {/* Props GLB do grupo (dieta aplicada) */}
      <ErrorBoundary fallback={null}><Suspense fallback={null}>
        {/* Acervo preservado em zonas de apoio, sem atravessar a bancada. */}
        <Prop url={`${HOSPITAL_DIR}/cortina-monitor.glb`} alturaAlvo={2.1} position={[-4.0, 0, 2.3]} rotationY={Math.PI / 2} />
        {/* Cadeira de rodas encostada */}
        <Prop url={`${HOSPITAL_DIR}/cadeira-rodas.glb`} alturaAlvo={1.0} position={[3.6, 0, 2.8]} rotationY={-Math.PI / 2.5} />
      </Suspense></ErrorBoundary>
    </group>
    </group>
  );
}

// Só os dois props mantidos no cenário; o entorno tem seu próprio Suspense.
for (const nome of ["cortina-monitor", "cadeira-rodas"]) {
  useGLTF.preload(`${HOSPITAL_DIR}/${nome}.glb`, "/draco/");
}
