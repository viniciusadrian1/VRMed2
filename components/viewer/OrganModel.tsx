"use client";

import {
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type RefObject,
} from "react";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { TransformControls } from "@react-three/drei";
import * as THREE from "three";
import { track } from "@/lib/analytics";
import { genId } from "@/lib/format";
import { getOrganById } from "@/lib/organs";
import {
  applyModelState,
  computeClippingPlanes,
  detectStructures,
  getModelBounds,
  identifyStructure,
  normalizeContent,
  prepareModel,
} from "@/lib/model-utils";
import { useVRMedStore } from "@/lib/store";
import { GLBModel } from "./GLBModel";
import { PlaceholderOrgan } from "./PlaceholderOrgan";

type Availability = "checking" | "real" | "placeholder";

/** Aplica camadas, cortes e wireframe ao modelo sempre que o estado muda. */
function ModelStateApplier({
  rootRef,
}: {
  rootRef: RefObject<THREE.Group | null>;
}) {
  const layers = useVRMedStore((s) => s.layers);
  const clipping = useVRMedStore((s) => s.clipping);
  const wireframe = useVRMedStore((s) => s.wireframe);
  const bounds = useVRMedStore((s) => s.modelBounds);
  const invalidate = useThree((s) => s.invalidate);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || !bounds || layers.length === 0) return;
    applyModelState(
      root,
      layers,
      computeClippingPlanes(clipping, bounds),
      wireframe,
    );
    invalidate();
  }, [layers, clipping, wireframe, bounds, invalidate, rootRef]);

  return null;
}

/**
 * Carrega e gerencia o modelo do órgão atual.
 * Tenta o arquivo .glb real; se ausente, usa o modelo de demonstração.
 * Detecta camadas, normaliza a escala e expõe o gizmo de manipulação.
 */
export function OrganModel() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  const setLayers = useVRMedStore((s) => s.setLayers);
  const setStructures = useVRMedStore((s) => s.setStructures);
  const setModelKind = useVRMedStore((s) => s.setModelKind);
  const setModelBounds = useVRMedStore((s) => s.setModelBounds);
  const transformMode = useVRMedStore((s) => s.transformMode);
  const annotationMode = useVRMedStore((s) => s.annotationMode);
  const addAnnotation = useVRMedStore((s) => s.addAnnotation);
  const setInspectedLabel = useVRMedStore((s) => s.setInspectedLabel);
  const invalidate = useThree((s) => s.invalidate);
  const organ = getOrganById(organId);

  const rootRef = useRef<THREE.Group>(null);
  const contentRef = useRef<THREE.Group>(null);
  // Destaque (emissive) da estrutura atualmente identificada.
  const highlightRef = useRef<{
    materials: THREE.MeshStandardMaterial[];
    originals: THREE.Color[];
  } | null>(null);

  const [availability, setAvailability] = useState<Availability>("checking");
  const [modelReady, setModelReady] = useState(false);

  useEffect(() => {
    if (!organId) return;
    const def = getOrganById(organId);
    if (!def) return;
    setAvailability("checking");
    setModelReady(false);
    highlightRef.current = null;
    let cancelled = false;
    fetch(def.modelPath, { method: "HEAD" })
      .then((res) => {
        if (cancelled) return;
        const kind = res.ok ? "real" : "placeholder";
        setAvailability(kind);
        setModelKind(kind);
      })
      .catch(() => {
        if (cancelled) return;
        setAvailability("placeholder");
        setModelKind("placeholder");
      });
    return () => {
      cancelled = true;
    };
  }, [organId, setModelKind]);

  // Disparado quando o conteúdo 3D termina de montar/carregar.
  const handleReady = useCallback(() => {
    const content = contentRef.current;
    if (!content) return;
    normalizeContent(content);
    setModelBounds(getModelBounds(content));
    // Sistemas agrupam camadas por tecido (material); órgãos, por malha.
    const def = getOrganById(organId);
    const layerBy = def?.layerBy ?? "mesh";
    setLayers(prepareModel(content, layerBy));
    // Os pontos só aparecem em modelos cujas malhas têm nomes anatômicos
    // reais (a função decide); os demais não recebem marcadores.
    setStructures(detectStructures(content));
    setModelReady(true);
  }, [organId, setLayers, setStructures, setModelBounds]);

  // Restaura o cursor padrão ao desmontar (modelo trocado ou página deixada).
  useEffect(() => {
    return () => {
      document.body.style.cursor = "";
    };
  }, []);

  // Realça a estrutura clicada, restaurando o destaque anterior.
  const highlightMesh = (mesh: THREE.Mesh) => {
    const previous = highlightRef.current;
    if (previous) {
      previous.materials.forEach((material, index) =>
        material.emissive.copy(previous.originals[index]),
      );
    }
    const materials = (
      Array.isArray(mesh.material) ? mesh.material : [mesh.material]
    ).filter(
      (material): material is THREE.MeshStandardMaterial =>
        Boolean(material) && "emissive" in material,
    );
    highlightRef.current = {
      materials,
      originals: materials.map((material) => material.emissive.clone()),
    };
    materials.forEach((material) => material.emissive.setHex(0x1f5fa8));
  };

  // Clique no modelo: cria anotação (modo marcação) ou identifica a estrutura.
  const handleModelClick = (event: ThreeEvent<MouseEvent>) => {
    if (!organId) return;
    event.stopPropagation();

    if (annotationMode) {
      addAnnotation(organId, {
        id: genId(),
        position: [event.point.x, event.point.y, event.point.z],
        text: "Nova anotação",
        color: "#0f4c81",
        hideLabel: false,
      });
      track("annotation_created", { organ: organId });
      return;
    }

    // Identifica a estrutura nomeada; sem nome (órgão de malha única),
    // identifyStructure recai no nome do órgão.
    setInspectedLabel(identifyStructure(event.object, organ?.name));
    highlightMesh(event.object as THREE.Mesh);
    invalidate();
  };

  if (!organ || !organId) return null;

  return (
    <>
      <group
        ref={rootRef}
        onClick={handleModelClick}
        onPointerOver={(event) => {
          event.stopPropagation();
          document.body.style.cursor = annotationMode
            ? "crosshair"
            : "pointer";
        }}
        onPointerOut={() => {
          document.body.style.cursor = "";
        }}
      >
        <group key={`${organId}-${availability}`} ref={contentRef}>
          {availability === "real" && (
            <Suspense fallback={null}>
              <GLBModel path={organ.modelPath} onReady={handleReady} />
            </Suspense>
          )}
          {availability === "placeholder" && (
            <PlaceholderOrgan onReady={handleReady} />
          )}
        </group>
        <ModelStateApplier rootRef={rootRef} />
      </group>

      {transformMode !== "none" && modelReady && rootRef.current && (
        <TransformControls object={rootRef.current} mode={transformMode} />
      )}
    </>
  );
}
