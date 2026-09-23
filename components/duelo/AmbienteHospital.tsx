"use client";

import { Suspense, useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { Text3D } from "@/components/arena/ui3d";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Bloco, ConsoleArena, FaixaReativa, MonitorArena, PalcoAnatomico } from "./ArenaMedica";

/**
 * Arena médica do Duelo: bancada anatômica, console de competição e pórtico
 * reativo. A arquitetura organiza o foco; os equipamentos dão escala à sala.
 *
 * Híbrido: sala procedural (zero download) + props GLB curados pelo grupo
 * (Sketchfab CC-BY, dieta simplify/webp/draco — créditos no CREDITS.md).
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
        <primitive object={scene} />
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

/** Prateleira procedural com potes coloridos (como na foto de referência). */
function Prateleira({ position, largura = 2 }: { position: [number, number, number]; largura?: number }) {
  const cores = ["#7b9da7", "#bfb798", "#65978e", "#a7736c"];
  const potes = Math.floor(largura / 0.28);
  return (
    <group position={position}>
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[largura, 0.05, 0.35]} />
        <meshStandardMaterial color="#344a54" roughness={0.7} />
      </mesh>
      {Array.from({ length: potes }, (_, i) => {
        const cor = cores[i % cores.length];
        const x = -largura / 2 + 0.2 + i * 0.28;
        return (
          <group key={i} position={[x, 0.025, 0]}>
            <mesh position={[0, 0.11, 0]}>
              <cylinderGeometry args={[0.08, 0.08, 0.22, 12]} />
              <meshStandardMaterial color={cor} roughness={0.35} />
            </mesh>
            <mesh position={[0, 0.245, 0]}>
              <cylinderGeometry args={[0.085, 0.085, 0.05, 12]} />
              <meshStandardMaterial color="#e8e2d4" roughness={0.6} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

/** Pôster de anatomia procedural (moldura + corpo esquemático). */
function Poster({ position, rotationY = 0 }: { position: [number, number, number]; rotationY?: number }) {
  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <mesh>
        <planeGeometry args={[0.72, 0.98]} />
        <meshStandardMaterial color="#f4efe2" roughness={0.9} />
      </mesh>
      <mesh position={[0, 0.28, 0.005]}>
        <circleGeometry args={[0.09, 16]} />
        <meshStandardMaterial color="#d3a284" roughness={0.9} />
      </mesh>
      <mesh position={[0, -0.05, 0.005]}>
        <capsuleGeometry args={[0.13, 0.3, 4, 10]} />
        <meshStandardMaterial color="#e0b5a0" roughness={0.9} />
      </mesh>
      <mesh position={[0, -0.02, 0.012]}>
        <capsuleGeometry args={[0.05, 0.1, 4, 8]} />
        <meshStandardMaterial color="#c96a5a" roughness={0.8} />
      </mesh>
      {[0.38, -0.42].map((y) => (
        <mesh key={y} position={[0, y, 0.006]}>
          <planeGeometry args={[0.5, 0.045]} />
          <meshStandardMaterial color="#9db8c9" roughness={0.9} />
        </mesh>
      ))}
    </group>
  );
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
    <group>
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
        <Bloco pos={[lado * 3.25, 0.5, -4.0]} tam={[1.8, 1.0, 0.85]} cor="#526e73" />
        <Bloco pos={[lado * 3.25, 1.03, -4.0]} tam={[1.9, 0.08, 0.94]} cor="#c3c9b9" />
        {[-0.42, 0.42].map((x) => <Bloco key={x} pos={[lado * 3.25 + x, 0.51, -3.56]} tam={[0.75, 0.81, 0.04]} cor="#76928e" />)}
        <FaixaReativa pos={[lado * 1.65, 0.036, 0.05]} tam={[0.03, 0.012, 1.5]} />
      </group>)}

      {/* Prateleiras de potes + pôsteres nas paredes */}
      <Prateleira position={[-3.3, 2.35, -MEIA + 0.2]} largura={1.8} />
      <Prateleira position={[-3.3, 1.8, -MEIA + 0.2]} largura={1.8} />
      <Prateleira position={[-MEIA + 0.2, 1.9, 1.6]} largura={2.2} />
      <Poster position={[3.4, 2.35, -MEIA + 0.02]} />
      <Poster position={[-MEIA + 0.02, 1.8, -1.2]} rotationY={Math.PI / 2} />

      {/* Telão LED do cronômetro no alto, entre os dois lados */}
      <TelaoLed position={[0, 2.81, -3.22]} />
      <MonitorArena pos={[-3.1, 1.8, -2.55]} titulo="ESTAÇÃO DO ADVERSÁRIO" />

      {/* Props GLB do grupo (dieta aplicada) */}
      <ErrorBoundary fallback={null}><Suspense fallback={null}>
        {/* Mesa de instrumentos do jogador e do bot */}
        <Prop url={`${HOSPITAL_DIR}/trolley.glb`} alturaAlvo={0.9} position={[2.8, 0, -1.3]} rotationY={-0.35} />
        <Prop url={`${HOSPITAL_DIR}/trolley.glb`} alturaAlvo={0.9} position={[-2.6, 0, -3.25]} rotationY={Math.PI} />
        {/* Monitores de sinais vitais nas paredes laterais */}
        <Prop url={`${HOSPITAL_DIR}/monitor-hr.glb`} alturaAlvo={0.55} position={[-MEIA + 0.25, 1.85, 3.0]} rotationY={Math.PI / 2} />
        <Prop url={`${HOSPITAL_DIR}/monitor-hr.glb`} alturaAlvo={0.55} position={[-MEIA + 0.25, 1.85, -3.0]} rotationY={Math.PI / 2} />
        {/* Ultrassom no canto de trás */}
        <Prop url={`${HOSPITAL_DIR}/ultrassom.glb`} alturaAlvo={1.45} position={[3.5, 0, -2.4]} rotationY={-Math.PI / 4} />
        {/* Cortina hospitalar no canto oposto */}
        <Prop url={`${HOSPITAL_DIR}/cortina-monitor.glb`} alturaAlvo={2.1} position={[-4.0, 0, 0.2]} rotationY={Math.PI / 2} />
        {/* Cadeira de rodas encostada */}
        <Prop url={`${HOSPITAL_DIR}/cadeira-rodas.glb`} alturaAlvo={1.0} position={[3.6, 0, 2.8]} rotationY={-Math.PI / 2.5} />
      </Suspense></ErrorBoundary>
    </group>
    </group>
  );
}

// Todos: o Suspense é um só, então as mesas (à frente do jogador) só
// aparecem quando o último prop chega.
for (const nome of ["trolley", "monitor-hr", "ultrassom", "cortina-monitor", "cadeira-rodas"]) {
  useGLTF.preload(`${HOSPITAL_DIR}/${nome}.glb`, "/draco/");
}
