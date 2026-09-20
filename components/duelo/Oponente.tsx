"use client";

import { Suspense, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Billboard, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { Text3D } from "@/components/arena/ui3d";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export type HumorOponente = "idle" | "comemora" | "erra";
export type TipoOponente = "iniciante" | "residente" | "especialista";

const MODELOS_BOTS: Record<TipoOponente, string> = {
  iniciante: "/models/props/dr-caloni.glb",
  residente: "/models/props/dra-reis.glb",
  especialista: "/models/props/dr-chefe.glb",
};

// Pré-carrega o modelo já existente
useGLTF.preload(MODELOS_BOTS.iniciante);

/**
 * Carrega o modelo 3D GLB correspondente ao médico selecionado.
 */
function ModeloGLB({ url }: { url: string }) {
  const gltf = useGLTF(url);
  const scene = useMemo(() => {
    const clone = gltf.scene.clone(true);
    clone.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.raycast = () => null;
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        for (const mat of mats) {
          if (mat instanceof THREE.MeshStandardMaterial) {
            if (mat.normalMap) {
              mat.normalScale.set(0.12, 0.12);
            }
            mat.roughness = 0.65;
            mat.metalness = 0.0;
            mat.needsUpdate = true;
          }
        }
      }
    });
    return clone;
  }, [gltf.scene]);

  return (
    <group position={[0, 0, 0]} scale={1.78}>
      <primitive object={scene} />
      {/* Luz de retrato facial suave */}
      <pointLight position={[0, 0.92, 0.85]} intensity={3.2} distance={4.5} color="#fff6eb" decay={2} />
      <pointLight position={[-0.4, 0.85, 0.6]} intensity={1.8} distance={4} color="#f0f7ff" decay={2} />
    </group>
  );
}

/**
 * Avatar procedural com características específicas de cada personagem.
 * Usado como fallback caso o arquivo GLB daquele personagem específico ainda não tenha sido gerado.
 */
function AvatarProcedural({ tipo }: { tipo: TipoOponente }) {
  const isReis = tipo === "residente";
  const isChefe = tipo === "especialista";

  // Tons de pele
  const corPele = isChefe ? "#50311f" : isReis ? "#c49275" : "#d3a284";
  // Cor da roupa sob o jaleco
  const corScrub = isChefe ? "#253b59" : isReis ? "#1f8796" : "#2e5f6e";
  // Cabelo/Barba
  const corCabelo = isChefe ? "#d1d5db" : isReis ? "#3b261a" : "#2f3842";

  return (
    <group>
      {/* Pernas (calça do scrub/social) */}
      {[-0.09, 0.09].map((x) => (
        <mesh key={x} position={[x, 0.42, 0]}>
          <boxGeometry args={[0.13, 0.84, 0.16]} />
          <meshStandardMaterial color={isChefe ? "#333b47" : corScrub} roughness={0.9} />
        </mesh>
      ))}

      {/* Sapatos */}
      {[-0.09, 0.09].map((x) => (
        <mesh key={`pe-${x}`} position={[x, 0.04, 0.03]}>
          <boxGeometry args={[0.12, 0.08, 0.22]} />
          <meshStandardMaterial color={isReis ? "#e5e7eb" : "#181d24"} roughness={0.8} />
        </mesh>
      ))}

      {/* Tronco — jaleco branco */}
      <mesh position={[0, 1.12, 0]}>
        <boxGeometry args={[0.44, 0.62, 0.24]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.75} />
      </mesh>

      {/* Abertura do jaleco */}
      <mesh position={[0, 1.12, 0.125]}>
        <boxGeometry args={[0.1, 0.6, 0.005]} />
        <meshStandardMaterial color={corScrub} roughness={0.9} />
      </mesh>

      {/* Gravata (Dr. Chefe) */}
      {isChefe && (
        <mesh position={[0, 1.1, 0.128]}>
          <boxGeometry args={[0.04, 0.35, 0.004]} />
          <meshStandardMaterial color="#831843" roughness={0.7} />
        </mesh>
      )}

      {/* Braços com manga do jaleco */}
      {[-0.27, 0.27].map((x) => (
        <mesh key={x} position={[x, 1.08, 0]} rotation={[0, 0, x > 0 ? -0.12 : 0.12]}>
          <boxGeometry args={[0.1, 0.55, 0.12]} />
          <meshStandardMaterial color="#f8fafc" roughness={0.75} />
        </mesh>
      ))}

      {/* Mãos */}
      {[-0.31, 0.31].map((x) => (
        <mesh key={x} position={[x, 0.78, 0]}>
          <sphereGeometry args={[0.05, 8, 6]} />
          <meshStandardMaterial color={corPele} roughness={0.9} />
        </mesh>
      ))}

      {/* Cabeça */}
      <mesh position={[0, 1.56, 0]}>
        <sphereGeometry args={[0.14, 14, 12]} />
        <meshStandardMaterial color={corPele} roughness={0.9} />
      </mesh>

      {/* Cabelo */}
      {isReis ? (
        // Coque feminino no topo
        <mesh position={[0, 1.71, -0.02]}>
          <sphereGeometry args={[0.075, 10, 8]} />
          <meshStandardMaterial color={corCabelo} roughness={0.8} />
        </mesh>
      ) : isChefe ? (
        // Barba grisalha do Dr. Chefe
        <mesh position={[0, 1.51, 0.08]} rotation={[0.2, 0, 0]}>
          <boxGeometry args={[0.15, 0.08, 0.12]} />
          <meshStandardMaterial color={corCabelo} roughness={0.9} />
        </mesh>
      ) : null}

      {/* Estetoscópio no pescoço */}
      <mesh position={[0, 1.42, 0.1]} rotation={[Math.PI * 0.55, 0, 0]}>
        <torusGeometry args={[0.09, 0.012, 6, 12, Math.PI]} />
        <meshStandardMaterial color="#1e293b" roughness={0.5} metalness={0.4} />
      </mesh>
    </group>
  );
}

/**
 * Balão de reação expressiva 3D acima da cabeça do oponente.
 */
function ReacaoHumor({ humor }: { humor: HumorOponente }) {
  if (humor === "idle") return null;

  return (
    <Billboard position={[0.28, 1.98, 0]} lockX lockZ>
      {humor === "comemora" ? (
        <group>
          <Text3D size={0.16} color="#ffd166">
            !
          </Text3D>
        </group>
      ) : (
        <group>
          <Text3D size={0.15} color="#7dd3fc">
            ?
          </Text3D>
        </group>
      )}
    </Billboard>
  );
}

export function Oponente({
  humor,
  nome,
  tipo = "iniciante",
  position,
  rotationY = Math.PI,
  escala = 1,
}: {
  humor: HumorOponente;
  nome: string;
  tipo?: TipoOponente;
  position: [number, number, number];
  rotationY?: number;
  escala?: number;
}) {
  const corpo = useRef<THREE.Group>(null);
  const animacao = useRef(0);

  useFrame((state, delta) => {
    if (!corpo.current) return;
    const t = state.clock.elapsedTime;
    animacao.current += delta;

    if (humor === "comemora") {
      corpo.current.position.y = Math.abs(Math.sin(animacao.current * 9)) * 0.14;
      corpo.current.rotation.z = Math.sin(animacao.current * 9) * 0.04;
    } else if (humor === "erra") {
      corpo.current.position.y = -0.04;
      corpo.current.rotation.z = 0.10;
    } else {
      corpo.current.position.y = Math.sin(t * 1.6) * 0.012;
      corpo.current.rotation.z = 0;
      animacao.current = 0;
    }
  });

  const modeloUrl = MODELOS_BOTS[tipo];

  return (
    <group position={position} rotation={[0, rotationY, 0]} scale={escala}>
      <group ref={corpo}>
        <ErrorBoundary fallback={<AvatarProcedural tipo={tipo} />}>
          <Suspense fallback={<AvatarProcedural tipo={tipo} />}>
            <ModeloGLB url={modeloUrl} />
          </Suspense>
        </ErrorBoundary>
      </group>

      {/* Balão de reação expressiva */}
      <ReacaoHumor humor={humor} />

      {/* Placa com o nome do oponente */}
      <Billboard position={[0, 1.95, 0]} lockX lockZ>
        <Text3D size={0.09} color="#ff6b57">
          {nome}
        </Text3D>
      </Billboard>
    </group>
  );
}
