"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { normalizeContent, prepareModel } from "@/lib/model-utils";
import { translateMeshName } from "@/lib/anatomy-labels";
import { XRManipulation } from "@/components/viewer/XRManipulation";

/** Saída do scripts/achados-pulmao.py. */
export interface AchadosPulmao {
  enfisemaPctTotal: number;
  bboxMm: [number, number, number];
  lobos: Record<
    string,
    { volumeMl: number; enfisemaPct: number; huMedio: number }
  >;
  lesoes: {
    posNorm: [number, number, number];
    diametroMm: number;
    huMedio: number;
    lobo: string;
  }[];
}

// Convenção do paciente (medida no GLB reconstruído): -X = esquerda, -Z = anterior.
// O modelo ilustrativo (Sketchfab) fica de frente para a câmera (+Z = anterior),
// com a esquerda do paciente no +X da cena (posição anatômica). Logo, os dois
// eixos horizontais invertem. Se o modelo trocar, ajuste estes flips.
const FLIP_X = true;
const FLIP_Z = true;

export function rotuloLesao(l: AchadosPulmao["lesoes"][number]): string {
  const lobo = translateMeshName(l.lobo.replace(/_/g, " "));
  return `Achado candidato — Ø ${l.diametroMm} mm · ${lobo} (posição aproximada)`;
}

/**
 * Mapa de achados: o modelo ILUSTRATIVO de pulmão com os achados REAIS do
 * exame projetados por posição normalizada. A forma é genérica; as medidas
 * (enfisema, lesões) vêm da TC do paciente.
 */
export function MapaAchados({
  achados,
  onIdentify,
}: {
  achados: AchadosPulmao;
  onIdentify: (label: string) => void;
}) {
  const gltf = useGLTF("/models/healthy/pulmao.glb", "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  const pivot = useRef<THREE.Group>(null);
  const content = useRef<THREE.Group>(null);
  const marcadores = useRef<THREE.Group>(null);

  // Material único compartilhado por todos os marcadores (pulso barato).
  const matMarcador = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: "#7a1f1a",
        emissive: "#a33327",
        emissiveIntensity: 0.5,
        transparent: true,
        opacity: 0.92,
        depthTest: false,
      }),
    [],
  );

  useEffect(() => {
    const group = content.current;
    const alvo = marcadores.current;
    if (!group || !alvo) return;
    normalizeContent(group);
    prepareModel(group, "mesh");

    // Escurece o parênquima proporcionalmente ao enfisema medido (LAA-950).
    // 0% = cor original; ≥30% (grave) = ~metade do brilho.
    const fator = 1 - Math.min(achados.enfisemaPctTotal, 30) / 30 * 0.5;
    group.traverse((obj) => {
      if (obj instanceof THREE.Mesh) {
        const mat = obj.material as THREE.MeshStandardMaterial;
        if (mat?.color) mat.color.multiplyScalar(fator);
      }
    });

    // As posições vêm normalizadas no volume dos PULMÕES do paciente, então o
    // alvo é a bbox da malha dos pulmões — não a do modelo inteiro, que inclui
    // laringe/traqueia/tireoide. A malha dos pulmões é a mais larga em X.
    group.updateWorldMatrix(true, true);
    let boxPulmoes: THREE.Box3 | null = null;
    group.traverse((obj) => {
      if (!(obj instanceof THREE.Mesh)) return;
      const box = new THREE.Box3().setFromObject(obj);
      if (
        !boxPulmoes ||
        box.max.x - box.min.x > boxPulmoes.max.x - boxPulmoes.min.x
      ) {
        boxPulmoes = box;
      }
    });
    if (!boxPulmoes) return;
    const min = group.worldToLocal((boxPulmoes as THREE.Box3).min.clone());
    const max = group.worldToLocal((boxPulmoes as THREE.Box3).max.clone());
    const tam = new THREE.Vector3().subVectors(max, min);

    const escalaMm = tam.y / achados.bboxMm[1]; // unidades locais por mm
    alvo.clear();
    for (const lesao of achados.lesoes) {
      const [px, py, pz] = lesao.posNorm;
      const pos = new THREE.Vector3(
        min.x + (FLIP_X ? 1 - px : px) * tam.x,
        min.y + py * tam.y,
        min.z + (FLIP_Z ? 1 - pz : pz) * tam.z,
      );
      const raio = Math.max((lesao.diametroMm / 2) * escalaMm, 0.012);
      const marcador = new THREE.Mesh(
        new THREE.SphereGeometry(raio, 16, 12),
        matMarcador,
      );
      marcador.position.copy(pos);
      marcador.renderOrder = 10;
      marcador.userData.rotulo = rotuloLesao(lesao);
      alvo.add(marcador);
    }
    return () => {
      alvo.clear();
    };
  }, [scene, achados, matMarcador]);

  // Pulso suave dos marcadores — um material só, zero setState.
  useFrame(({ clock }) => {
    matMarcador.emissiveIntensity =
      0.45 + 0.35 * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 2.4));
  });

  const clicouMarcador = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    const rotulo = event.object.userData.rotulo as string | undefined;
    if (rotulo) onIdentify(rotulo);
  };

  return (
    <group ref={pivot} scale={1.4}>
      <group ref={content}>
        <primitive object={scene} />
        <group ref={marcadores} onClick={clicouMarcador} />
      </group>
      <XRManipulation target={pivot} />
    </group>
  );
}

useGLTF.preload("/models/healthy/pulmao.glb", "/draco/");
