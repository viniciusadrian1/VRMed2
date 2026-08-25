"use client";

import { useEffect, useMemo, useRef } from "react";
import type { ThreeEvent } from "@react-three/fiber";
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
// eixos horizontais invertem. O scripts/pintar-pulmao.py usa a MESMA convenção.
const FLIP_X = true;
const FLIP_Z = true;

function rotuloLesao(l: AchadosPulmao["lesoes"][number]): string {
  const lobo = translateMeshName(l.lobo.replace(/_/g, " "));
  return `Achado candidato — Ø ${l.diametroMm} mm · ${lobo} (posição aproximada)`;
}

/**
 * Mapa de achados: o GLB PERSONALIZADO do paciente — modelo ilustrativo cuja
 * textura foi pintada offline (scripts/pintar-pulmao.py) com os achados reais
 * da TC. As manchas fazem parte da textura; por cima ficam apenas zonas de
 * clique invisíveis para identificar cada achado.
 */
export function MapaAchados({
  mapaGlb,
  achados,
  onIdentify,
}: {
  mapaGlb: string;
  achados: AchadosPulmao;
  onIdentify: (label: string) => void;
}) {
  const gltf = useGLTF(mapaGlb, "/draco/");
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  const pivot = useRef<THREE.Group>(null);
  const content = useRef<THREE.Group>(null);
  const zonas = useRef<THREE.Group>(null);

  // Material invisível compartilhado: as zonas só existem para o raycast.
  const matZona = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0,
        depthWrite: false,
      }),
    [],
  );

  useEffect(() => {
    const group = content.current;
    const alvo = zonas.current;
    if (!group || !alvo) return;
    normalizeContent(group);
    prepareModel(group, "mesh");

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
      // Zona um pouco maior que a lesão, para o clique não exigir pontaria.
      const raio = Math.max((lesao.diametroMm / 2) * escalaMm * 1.6, 0.035);
      const zona = new THREE.Mesh(
        new THREE.SphereGeometry(raio, 12, 8),
        matZona,
      );
      zona.position.copy(pos);
      zona.userData.rotulo = rotuloLesao(lesao);
      alvo.add(zona);
    }
    return () => {
      alvo.clear();
    };
  }, [scene, achados, matZona]);

  const clicou = (event: ThreeEvent<MouseEvent>) => {
    const rotulo = event.object.userData.rotulo as string | undefined;
    if (rotulo) {
      event.stopPropagation();
      onIdentify(rotulo);
    }
  };

  return (
    <group ref={pivot} scale={1.4}>
      <group ref={content}>
        <primitive object={scene} />
        <group ref={zonas} onClick={clicou} />
      </group>
      <XRManipulation target={pivot} />
    </group>
  );
}
