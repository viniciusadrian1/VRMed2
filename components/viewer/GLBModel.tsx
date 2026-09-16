"use client";

import { useEffect, useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { disposeMaterials } from "@/lib/model-utils";
import { useVRMedStore } from "@/lib/store";
import type { OrganDefinition } from "@/types";

/**
 * Caminho local do decodificador Draco (servido de /public/draco).
 * Hospedar os arquivos localmente evita depender de uma CDN externa — o
 * visualizador funciona offline e não quebra se a CDN estiver indisponível.
 */
const DRACO_DECODER_PATH = "/draco/";

/**
 * Carrega um modelo `.glb` via useGLTF (com suporte a Draco).
 * A cena é clonada para isolar esta instância do cache do loader; os materiais
 * clonados são liberados ao desmontar, cumprindo o requisito de `dispose()`.
 */
export function GLBModel({
  path,
  onReady,
  explosao,
}: {
  path: string;
  onReady: () => void;
  /** Modelo que se separa em partes pela animação do arquivo (o crânio). */
  explosao?: OrganDefinition["explosao"];
}) {
  const gltf = useGLTF(path, DRACO_DECODER_PATH);
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);
  const invalidate = useThree((s) => s.invalidate);
  const ateSegundos = explosao?.ateSegundos;

  useEffect(() => {
    onReady();
    return () => disposeMaterials(scene);
  }, [scene, onReady]);

  // Abertura: a animação do arquivo nunca toca sozinha. O instante dela segue
  // `explosao` do store — o controle deslizante na tela e o analógico
  // esquerdo no VR — e o modelo fica parado onde a pessoa soltou.
  //
  // Depois do efeito acima de propósito: a normalização mede o modelo
  // fechado, e só então a pose da abertura é aplicada.
  useEffect(() => {
    const clipe = gltf.animations[0];
    if (!ateSegundos || !clipe) return;
    const mixer = new THREE.AnimationMixer(scene);
    const acao = mixer.clipAction(clipe);
    acao.play();
    acao.paused = true;
    const aplicar = (fracao: number) => {
      acao.time = THREE.MathUtils.clamp(fracao, 0, 1) * ateSegundos;
      mixer.update(0); // aplica a pose do instante, sem avançar o relógio
      invalidate();
    };
    aplicar(useVRMedStore.getState().explosao);
    const cancelar = useVRMedStore.subscribe((estado, antes) => {
      if (estado.explosao !== antes.explosao) aplicar(estado.explosao);
    });
    return () => {
      cancelar();
      mixer.stopAllAction();
      mixer.uncacheRoot(scene);
    };
  }, [scene, gltf.animations, ateSegundos, invalidate]);

  return <primitive object={scene} />;
}
