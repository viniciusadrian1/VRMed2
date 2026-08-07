"use client";

import { useEffect, useMemo, useRef } from "react";
import { useGLTF } from "@react-three/drei";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import * as THREE from "three";
import {
  detectStructures,
  identifyStructure,
  normalizeContent,
} from "@/lib/model-utils";
import { XRManipulation } from "@/components/viewer/XRManipulation";
import { ARENA_COLORS } from "./ui3d";
import type { ArenaStructure } from "./types";

/** Decodificador Draco local — o mesmo do visualizador, funciona offline. */
const DRACO_PATH = "/draco/";

/**
 * Modelo da Arena: carrega o GLB, extrai as estruturas nomeadas e responde
 * ao gatilho, avisando qual estrutura foi atingida.
 *
 * O modelo fica dentro de um grupo próprio (`pivot`) que o `XRManipulation`
 * move e escala. O marcador de dica é **filho desse mesmo grupo**: as posições
 * devolvidas por `detectStructures` são de mundo, então guardá-las cruas faria
 * a dica ficar para trás assim que o jogador pegasse o órgão. Convertendo para
 * o espaço local do pivot, ela acompanha movimento, giro e escala de graça.
 */
export function ArenaModel({
  path,
  scale = 1.6,
  roundId,
  onStructuresReady,
  onHit,
  hintPosition,
  interactive = true,
  spinning = false,
}: {
  path: string;
  scale?: number;
  /** Muda a cada rodada: devolve o modelo à pose original para o próximo da fila. */
  roundId: number;
  onStructuresReady: (structures: ArenaStructure[]) => void;
  onHit: (label: string, point: THREE.Vector3) => void;
  /** Posição (local) da estrutura a destacar como dica, ou null. */
  hintPosition: THREE.Vector3 | null;
  interactive?: boolean;
  /** Giro lento de vitrine (modo ocioso). */
  spinning?: boolean;
}) {
  const gltf = useGLTF(path, DRACO_PATH);
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);

  const pivot = useRef<THREE.Group>(null);
  const spinner = useRef<THREE.Group>(null);
  const content = useRef<THREE.Group>(null);
  const hint = useRef<THREE.Mesh>(null);

  // Normaliza e extrai as estruturas assim que o modelo entra na cena.
  useEffect(() => {
    const group = content.current;
    const root = pivot.current;
    if (!group || !root) return;

    normalizeContent(group);
    group.updateWorldMatrix(true, true);

    // A cena da Arena não tem mapa de ambiente (o preset do drei busca um HDR
    // na rede — proibido no evento). Sem envmap, material PBR metálico
    // renderiza quase preto. Clona os materiais (para não contaminar o cache
    // do useGLTF, compartilhado com o visualizador) e limita o metalness.
    group.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      const materials = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material];
      const cloned = materials.map((mat) => {
        const copy = mat.clone() as THREE.MeshStandardMaterial;
        if ("metalness" in copy) copy.metalness = Math.min(copy.metalness, 0.1);
        if ("roughness" in copy) copy.roughness = Math.max(copy.roughness, 0.55);
        return copy;
      });
      mesh.material = Array.isArray(mesh.material) ? cloned : cloned[0];
    });

    const points = detectStructures(group);
    // Converte de mundo para o espaço do pivot (ver comentário do componente).
    const structures: ArenaStructure[] = points.map((point) => ({
      id: point.id,
      label: point.label,
      local: root.worldToLocal(new THREE.Vector3(...point.position)),
    }));

    onStructuresReady(structures);
  }, [scene, onStructuresReady]);

  /**
   * Devolve o modelo à pose original a cada rodada.
   *
   * O `XRManipulation` muta a transformação do pivot diretamente. Sem este
   * reset explícito, o jogador que empurrasse o órgão para trás deixaria a
   * cena quebrada para o próximo da fila — e como o "voltar ao original"
   * captura a pose na montagem, ele passaria a restaurar justamente a pose
   * ruim. Num estande isso degrada a cada rodada até alguém recarregar a
   * página. Nunca confiar em desmontagem para limpar estado imperativo.
   */
  useEffect(() => {
    const root = pivot.current;
    if (!root) return;
    root.position.set(0, 0, 0);
    root.quaternion.identity();
    root.scale.setScalar(scale);
    // O giro de vitrine também zera: as posições das estruturas (e a dica)
    // foram capturadas com o giro em zero.
    spinner.current?.rotation.set(0, 0, 0);
  }, [roundId, scale]);

  useFrame((state, delta) => {
    // Giro lento de vitrine, só no ocioso (o grupo `spinner` gira em torno do
    // centro do modelo; o pivot fica livre para o XRManipulation).
    if (spinning && spinner.current) {
      spinner.current.rotation.y += Math.min(delta, 1 / 30) * 0.35;
    }
    // Pulso suave da dica — chama atenção sem entregar de forma agressiva.
    if (hint.current) {
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.25;
      hint.current.scale.setScalar(pulse);
    }
  });

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    if (!interactive) return;
    event.stopPropagation();
    onHit(identifyStructure(event.object), event.point);
  };

  return (
    <group ref={pivot} scale={scale}>
      {/* O conteúdo é centrado na origem pelo normalizeContent, então o
          spinner gira o modelo em torno do próprio centro. */}
      <group ref={spinner}>
        <group ref={content} onClick={handleClick}>
          <primitive object={scene} />
        </group>
      </group>

      {/* Dica: esfera luminosa sobre a estrutura procurada.
          `raycast` nulo é essencial — senão ela intercepta o laser e vira um
          escudo bem em cima da estrutura que o jogador precisa acertar. */}
      {hintPosition && (
        <mesh ref={hint} position={hintPosition} raycast={() => null}>
          <sphereGeometry args={[0.05, 16, 16]} />
          <meshBasicMaterial
            color={ARENA_COLORS.primary}
            transparent
            opacity={0.75}
            toneMapped={false}
          />
        </mesh>
      )}

      {/* Pegar, mover e escalar com controles ou mãos. */}
      <XRManipulation target={pivot} />
    </group>
  );
}

useGLTF.preload("/models/organs/larynx.glb", DRACO_PATH);
