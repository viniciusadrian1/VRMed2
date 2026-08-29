"use client";

import { useMemo } from "react";
import { OrbitControls } from "@react-three/drei";
import { useXR, XROrigin } from "@react-three/xr";
import * as THREE from "three";
import { SalaInterativos } from "./SalaInterativos";

/**
 * O quarto da Sala de Estudos — 100% geometria procedural (caixas, cilindros,
 * texturas de canvas). Zero assets externos: carrega instantâneo, funciona
 * offline e não pesa nada no orçamento de 72fps do Quest.
 *
 * Layout (metros, chão em y=0): sala 5×3×5; mesa encostada na parede -Z;
 * janela na parede -X; jogador sentado/em pé de frente para a mesa.
 */

/** Céu da janela: gradiente + sol + morros, desenhado uma vez em canvas. */
function useCeuTexture(): THREE.CanvasTexture {
  return useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 192;
    const ctx = canvas.getContext("2d")!;
    const grad = ctx.createLinearGradient(0, 0, 0, 192);
    grad.addColorStop(0, "#8ec5e8");
    grad.addColorStop(0.6, "#dcebf5");
    grad.addColorStop(1, "#f4e8d0");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 256, 192);
    // Sol baixo, fim de tarde
    ctx.fillStyle = "#fff3c4";
    ctx.beginPath();
    ctx.arc(190, 70, 22, 0, Math.PI * 2);
    ctx.fill();
    // Morros em silhueta
    ctx.fillStyle = "#7fa98c";
    ctx.beginPath();
    ctx.moveTo(0, 192);
    ctx.quadraticCurveTo(60, 120, 130, 160);
    ctx.quadraticCurveTo(200, 190, 256, 150);
    ctx.lineTo(256, 192);
    ctx.closePath();
    ctx.fill();
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }, []);
}

function Quarto() {
  const ceu = useCeuTexture();
  return (
    <group>
      {/* Chão de madeira quente */}
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[5, 5]} />
        <meshStandardMaterial color="#6d543f" roughness={0.85} />
      </mesh>
      {/* Tapete redondo */}
      <mesh position={[0, 0.005, -1.2]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[1.3, 40]} />
        <meshStandardMaterial color="#4a5568" roughness={1} />
      </mesh>
      {/* Teto */}
      <mesh position={[0, 3, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <planeGeometry args={[5, 5]} />
        <meshStandardMaterial color="#efe7da" roughness={1} />
      </mesh>
      {/* Paredes (cores levemente diferentes dão leitura de volume) */}
      <mesh position={[0, 1.5, -2.5]}>
        <planeGeometry args={[5, 3]} />
        <meshStandardMaterial color="#d8cdbc" roughness={1} />
      </mesh>
      <mesh position={[0, 1.5, 2.5]} rotation={[0, Math.PI, 0]}>
        <planeGeometry args={[5, 3]} />
        <meshStandardMaterial color="#d8cdbc" roughness={1} />
      </mesh>
      <mesh position={[-2.5, 1.5, 0]} rotation={[0, Math.PI / 2, 0]}>
        <planeGeometry args={[5, 3]} />
        <meshStandardMaterial color="#cfc2ae" roughness={1} />
      </mesh>
      <mesh position={[2.5, 1.5, 0]} rotation={[0, -Math.PI / 2, 0]}>
        <planeGeometry args={[5, 3]} />
        <meshStandardMaterial color="#cfc2ae" roughness={1} />
      </mesh>

      {/* Janela na parede -X: moldura + vista + peitoril */}
      <group position={[-2.49, 1.7, -0.6]} rotation={[0, Math.PI / 2, 0]}>
        <mesh>
          <planeGeometry args={[1.7, 1.25]} />
          <meshBasicMaterial map={ceu} toneMapped={false} />
        </mesh>
        {/* Moldura */}
        {[
          { p: [0, 0.65, 0.01] as const, s: [1.8, 0.08, 0.06] as const },
          { p: [0, -0.65, 0.01] as const, s: [1.8, 0.08, 0.06] as const },
          { p: [-0.87, 0, 0.01] as const, s: [0.08, 1.4, 0.06] as const },
          { p: [0.87, 0, 0.01] as const, s: [0.08, 1.4, 0.06] as const },
          { p: [0, 0, 0.01] as const, s: [0.05, 1.4, 0.04] as const },
          { p: [0, 0, 0.01] as const, s: [1.8, 0.05, 0.04] as const },
        ].map((peca, i) => (
          <mesh key={i} position={[...peca.p]}>
            <boxGeometry args={[...peca.s]} />
            <meshStandardMaterial color="#f5efe4" roughness={0.9} />
          </mesh>
        ))}
      </group>

      {/* Mesa de estudos */}
      <group position={[0, 0, -1.9]}>
        <mesh position={[0, 0.74, 0]}>
          <boxGeometry args={[1.9, 0.05, 0.75]} />
          <meshStandardMaterial color="#8a6a4a" roughness={0.7} />
        </mesh>
        {[
          [-0.88, -0.31],
          [0.88, -0.31],
          [-0.88, 0.31],
          [0.88, 0.31],
        ].map(([x, z], i) => (
          <mesh key={i} position={[x, 0.36, z]}>
            <boxGeometry args={[0.06, 0.72, 0.06]} />
            <meshStandardMaterial color="#5e4632" roughness={0.8} />
          </mesh>
        ))}
      </group>

      {/* Cadeira */}
      <group position={[0, 0, -1.15]}>
        <mesh position={[0, 0.45, 0]}>
          <boxGeometry args={[0.45, 0.05, 0.45]} />
          <meshStandardMaterial color="#3f4b5c" roughness={0.9} />
        </mesh>
        <mesh position={[0, 0.75, 0.22]}>
          <boxGeometry args={[0.45, 0.55, 0.05]} />
          <meshStandardMaterial color="#3f4b5c" roughness={0.9} />
        </mesh>
        {[
          [-0.19, -0.19],
          [0.19, -0.19],
          [-0.19, 0.19],
          [0.19, 0.19],
        ].map(([x, z], i) => (
          <mesh key={i} position={[x, 0.21, z]}>
            <boxGeometry args={[0.04, 0.42, 0.04]} />
            <meshStandardMaterial color="#2b323d" roughness={0.8} />
          </mesh>
        ))}
      </group>

      {/* Planta no canto */}
      <group position={[2, 0, -2]}>
        <mesh position={[0, 0.16, 0]}>
          <cylinderGeometry args={[0.14, 0.11, 0.32, 12]} />
          <meshStandardMaterial color="#a8552f" roughness={0.9} />
        </mesh>
        {[0, 1.1, 2.3, 3.6, 4.8].map((ang, i) => (
          <mesh
            key={i}
            position={[Math.cos(ang) * 0.08, 0.5 + (i % 2) * 0.12, Math.sin(ang) * 0.08]}
            rotation={[0.5 * Math.cos(ang), 0, 0.5 * Math.sin(ang)]}
          >
            <coneGeometry args={[0.07, 0.42, 6]} />
            <meshStandardMaterial color="#3e7a4a" roughness={0.9} />
          </mesh>
        ))}
      </group>

      {/* Luminária de teto (o ponto de luz quente fica nela) */}
      <group position={[0, 2.96, -1.2]}>
        <mesh position={[0, -0.12, 0]}>
          <cylinderGeometry args={[0.015, 0.015, 0.24, 6]} />
          <meshStandardMaterial color="#3a3a3a" />
        </mesh>
        <mesh position={[0, -0.3, 0]}>
          <sphereGeometry args={[0.11, 16, 12]} />
          <meshStandardMaterial
            color="#fff2d8"
            emissive="#ffdf9e"
            emissiveIntensity={1.6}
          />
        </mesh>
      </group>

      {/* Quadro decorativo na parede de trás (só cor, aconchego) */}
      <mesh position={[1.5, 1.8, -2.48]}>
        <planeGeometry args={[0.6, 0.45]} />
        <meshStandardMaterial color="#2f5d50" roughness={1} />
      </mesh>
      <mesh position={[1.5, 1.8, -2.485]}>
        <planeGeometry args={[0.68, 0.53]} />
        <meshStandardMaterial color="#4a3826" roughness={0.9} />
      </mesh>
    </group>
  );
}

/**
 * Conteúdo 3D da Sala (dentro do <XR>): quarto + itens interativos + luzes.
 * OrbitControls só fora da sessão (regra do projeto: disputa a câmera do headset).
 */
export function CenaSala({ onAbrirTutorDom }: { onAbrirTutorDom: () => void }) {
  const inSession = useXR((state) => Boolean(state.session));

  return (
    <>
      {/* Sentado à mesa: origem um pouco atrás da cadeira. */}
      <XROrigin position={[0, 0, -0.55]} />

      {/* Luz: quente da luminária + fria fraca da janela + ambiente baixa. */}
      <ambientLight intensity={0.45} color="#f5ead8" />
      <pointLight
        position={[0, 2.6, -1.2]}
        intensity={11}
        distance={7}
        decay={1.6}
        color="#ffd9a0"
      />
      <directionalLight
        position={[-4, 2.2, -0.5]}
        intensity={0.8}
        color="#bcd6e8"
      />

      <Quarto />
      <SalaInterativos onAbrirTutorDom={onAbrirTutorDom} />

      {!inSession && (
        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.08}
          target={[0, 1.05, -1.85]}
          minDistance={0.4}
          maxDistance={3.4}
          // Não deixa a câmera atravessar o chão nem o teto.
          maxPolarAngle={Math.PI * 0.55}
        />
      )}
    </>
  );
}
