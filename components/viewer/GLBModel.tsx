"use client";

import { useEffect, useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import { disposeMaterials } from "@/lib/model-utils";

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
}: {
  path: string;
  onReady: () => void;
}) {
  const gltf = useGLTF(path, DRACO_DECODER_PATH);
  const scene = useMemo(() => gltf.scene.clone(true), [gltf.scene]);

  useEffect(() => {
    onReady();
    return () => disposeMaterials(scene);
  }, [scene, onReady]);

  return <primitive object={scene} />;
}
