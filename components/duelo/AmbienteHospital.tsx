"use client";

import { Suspense, useLayoutEffect, useMemo, useRef } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";

/**
 * Ambiente "Hospital" do Duelo — inspirado na referência do grupo: laboratório
 * médico estilizado com piso de azulejo menta, prateleiras de potes coloridos,
 * pôsteres de anatomia, telão de cronômetro e mesas de instrumentos.
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

/** Piso de azulejos menta desenhado em canvas (referência da foto). */
function usePisoTexture(): THREE.CanvasTexture {
  return useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#8fceb9";
    ctx.fillRect(0, 0, 512, 512);
    ctx.strokeStyle = "#6fb3a0";
    ctx.lineWidth = 6;
    for (let i = 0; i <= 8; i += 1) {
      ctx.beginPath(); ctx.moveTo(i * 64, 0); ctx.lineTo(i * 64, 512); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, i * 64); ctx.lineTo(512, i * 64); ctx.stroke();
    }
    // brilho sutil nos azulejos alternados
    ctx.fillStyle = "rgba(255,255,255,0.07)";
    for (let x = 0; x < 8; x += 1)
      for (let y = 0; y < 8; y += 1)
        if ((x + y) % 2 === 0) ctx.fillRect(x * 64 + 4, y * 64 + 4, 56, 56);
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(3, 3);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }, []);
}

/** Prateleira procedural com potes coloridos (como na foto de referência). */
function Prateleira({ position, largura = 2 }: { position: [number, number, number]; largura?: number }) {
  const cores = ["#b98ae0", "#e6a4c4", "#8ad0e0", "#a8e08a", "#e0c98a", "#e08a8a", "#8a9ee0"];
  const potes = Math.floor(largura / 0.28);
  return (
    <group position={position}>
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[largura, 0.05, 0.35]} />
        <meshStandardMaterial color="#a07850" roughness={0.7} />
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
        <boxGeometry args={[1.5, 0.62, 0.1]} />
        <meshStandardMaterial color="#101820" roughness={0.4} />
      </mesh>
      <mesh position={[0, 0, 0.052]}>
        <planeGeometry args={[1.38, 0.5]} />
        <meshStandardMaterial color="#050c12" emissive="#0a2a33" emissiveIntensity={0.8} />
      </mesh>
      {/* moldura neon */}
      <mesh position={[0, 0, 0.055]}>
        <ringGeometry args={[0.0, 0.0, 4]} />
        <meshBasicMaterial visible={false} />
      </mesh>
    </group>
  );
}

const HOSPITAL_DIR = "/models/hospital";

/** Sala + props. As posições assumem jogador em z≈+2.4 e bot em z≈-2.4. */
export function AmbienteHospital() {
  const piso = usePisoTexture();
  const MEIA = 4.6; // meia-largura da sala

  return (
    <group position={[0, FLOOR_Y, 0]}>
      {/* Piso de azulejo menta */}
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[MEIA * 2, MEIA * 2]} />
        <meshStandardMaterial map={piso} roughness={0.5} />
      </mesh>
      {/* Paredes creme com faixa verde-hospital */}
      {[
        { p: [0, 1.5, -MEIA] as const, r: 0 },
        { p: [0, 1.5, MEIA] as const, r: Math.PI },
        { p: [-MEIA, 1.5, 0] as const, r: Math.PI / 2 },
        { p: [MEIA, 1.5, 0] as const, r: -Math.PI / 2 },
      ].map((w, i) => (
        <group key={i} position={[...w.p]} rotation={[0, w.r, 0]}>
          <mesh>
            <planeGeometry args={[MEIA * 2, 3]} />
            <meshStandardMaterial color="#efe6cf" roughness={1} />
          </mesh>
          <mesh position={[0, -0.9, 0.01]}>
            <planeGeometry args={[MEIA * 2, 0.5]} />
            <meshStandardMaterial color="#9db8a8" roughness={1} />
          </mesh>
        </group>
      ))}
      {/* Teto */}
      <mesh position={[0, 3, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <planeGeometry args={[MEIA * 2, MEIA * 2]} />
        <meshStandardMaterial color="#f2ede1" roughness={1} />
      </mesh>

      {/* Divisória central translúcida (vidro, como na referência) */}
      <group position={[1.9, 0, 0]}>
        <mesh position={[0, 1.1, 0]}>
          <boxGeometry args={[2.6, 2.2, 0.04]} />
          <meshStandardMaterial
            color="#bfe4ea"
            transparent
            opacity={0.22}
            roughness={0.1}
          />
        </mesh>
        <mesh position={[0, 2.22, 0]}>
          <boxGeometry args={[2.7, 0.06, 0.08]} />
          <meshStandardMaterial color="#8aa4ad" roughness={0.5} />
        </mesh>
      </group>

      {/* Prateleiras de potes + pôsteres nas paredes */}
      <Prateleira position={[-2.6, 2.0, -MEIA + 0.2]} largura={2.4} />
      <Prateleira position={[-2.6, 1.45, -MEIA + 0.2]} largura={2.4} />
      <Prateleira position={[-MEIA + 0.2, 1.9, 1.6]} largura={2.2} />
      <Poster position={[0.6, 1.9, -MEIA + 0.02]} />
      <Poster position={[1.6, 1.85, -MEIA + 0.02]} />
      <Poster position={[-MEIA + 0.02, 1.8, -1.2]} rotationY={Math.PI / 2} />

      {/* Telão LED do cronômetro no alto, entre os dois lados */}
      <TelaoLed position={[0, 2.55, -3.2]} />

      {/* Props GLB do grupo (dieta aplicada) */}
      <Suspense fallback={null}>
        {/* Mesa de instrumentos do jogador e do bot */}
        <Prop url={`${HOSPITAL_DIR}/trolley.glb`} alturaAlvo={1.0} position={[0, 0, 1.35]} />
        <Prop url={`${HOSPITAL_DIR}/trolley.glb`} alturaAlvo={1.0} position={[0, 0, -1.35]} rotationY={Math.PI} />
        {/* Monitores de sinais vitais nas paredes laterais */}
        <Prop url={`${HOSPITAL_DIR}/monitor-hr.glb`} alturaAlvo={0.55} position={[-MEIA + 0.25, 1.85, 3.0]} rotationY={Math.PI / 2} />
        <Prop url={`${HOSPITAL_DIR}/monitor-hr.glb`} alturaAlvo={0.55} position={[-MEIA + 0.25, 1.85, -3.0]} rotationY={Math.PI / 2} />
        {/* Ultrassom no canto de trás */}
        <Prop url={`${HOSPITAL_DIR}/ultrassom.glb`} alturaAlvo={1.45} position={[3.4, 0, -3.4]} rotationY={-Math.PI / 4} />
        {/* Cortina hospitalar no canto oposto */}
        <Prop url={`${HOSPITAL_DIR}/cortina-monitor.glb`} alturaAlvo={2.1} position={[-3.4, 0, -3.2]} rotationY={Math.PI / 5} />
        {/* Cadeira de rodas encostada */}
        <Prop url={`${HOSPITAL_DIR}/cadeira-rodas.glb`} alturaAlvo={1.0} position={[3.6, 0, 2.8]} rotationY={-Math.PI / 2.5} />
      </Suspense>
    </group>
  );
}

useGLTF.preload(`${HOSPITAL_DIR}/trolley.glb`, "/draco/");
useGLTF.preload(`${HOSPITAL_DIR}/monitor-hr.glb`, "/draco/");
