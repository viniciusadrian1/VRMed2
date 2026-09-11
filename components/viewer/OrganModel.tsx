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
import { useXR } from "@react-three/xr";
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
import { TEXTO_PADRAO_ANOTACAO } from "@/lib/quiz";
import { useVRMedStore } from "@/lib/store";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { GLBModel } from "./GLBModel";
import { PlaceholderOrgan } from "./PlaceholderOrgan";
import { EntradaXR } from "./XRManipulation";

type Availability = "checking" | "real" | "placeholder";

/** Aplica camadas, cortes e wireframe ao modelo sempre que o estado muda. */
/**
 * Pose PROVISÓRIA do órgão em AR, relativa aos pés do usuário.
 *
 * Quem manda de verdade é o `EntradaXR`, que mede a cabeça no primeiro quadro
 * da sessão e recoloca o órgão à frente do olhar — sentado ou de pé. Esta
 * constante cobre os poucos quadros até o rastreio responder, e é o que fica
 * se ele nunca responder. Supõe alguém de pé, que é o caso comum; era a pose
 * fixa que existia antes, e sozinha ela deixava o órgão alto demais para quem
 * abrisse o modo sentado.
 *
 * Em VR o modelo fica em tamanho de vitrine (~2 unidades ≈ 2 m) e a pessoa
 * recua 3 m para vê-lo inteiro. Em AR não há 3 m para recuar — o estande é
 * pequeno, e é essa a razão de existir este modo. Então o órgão vem para a
 * frente do peito, do tamanho de uma bola: perto o bastante para alcançar com
 * a mão, pequeno o bastante para a pessoa dar a volta nele sem esbarrar em
 * nada. A partir daí os controles (e as duas mãos) reposicionam e
 * redimensionam à vontade.
 *
 * Aplicado no PRÓPRIO root do modelo, e não num grupo-pai: `XRManipulation`
 * mistura posição de mundo com posição local, e um pai com transformação
 * quebraria o arrastar e o aproximar.
 */
const AR_POSICAO: [number, number, number] = [0, 1.15, -0.75];
/** ~2 unidades × 0,22 ≈ 44 cm de altura. */
const AR_ESCALA = 0.22;

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
  const inspectedLabel = useVRMedStore((s) => s.inspectedLabel);
  const invalidate = useThree((s) => s.invalidate);
  const modo = useXR((state) => state.mode);
  const inSession = modo === "immersive-vr" || modo === "immersive-ar";
  const emAR = modo === "immersive-ar";
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

  // O destaque (emissive) segue o store: assim o X da InspectBar e os pontos
  // numerados também controlam a cor, não só o clique direto na malha.
  useEffect(() => {
    // Restaura o destaque anterior antes de aplicar o novo.
    const previous = highlightRef.current;
    if (previous) {
      previous.materials.forEach((material, index) =>
        material.emissive.copy(previous.originals[index]),
      );
    }
    highlightRef.current = null;

    if (!inspectedLabel || !modelReady || !contentRef.current) {
      invalidate();
      return;
    }

    // Todas as malhas com o mesmo rótulo são realçadas (uma estrutura pode ter
    // várias malhas). O Set deduplica materiais caso alguma seja compartilhada,
    // evitando clonar um "original" que já foi pintado de azul.
    const materials = new Set<THREE.MeshStandardMaterial>();
    contentRef.current.traverse((node) => {
      const mesh = node as THREE.Mesh;
      if (!mesh.isMesh) return;
      if (identifyStructure(mesh, organ?.name) !== inspectedLabel) return;
      const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      list.forEach((material) => {
        if (material && "emissive" in material) {
          materials.add(material as THREE.MeshStandardMaterial);
        }
      });
    });

    const collected = [...materials];
    highlightRef.current = {
      materials: collected,
      originals: collected.map((material) => material.emissive.clone()),
    };
    collected.forEach((material) => material.emissive.setHex(0x1f5fa8));
    invalidate();
  }, [inspectedLabel, modelReady, organ?.name, invalidate]);

  // Clique no modelo: cria anotação (modo marcação) ou identifica a estrutura.
  const handleModelClick = (event: ThreeEvent<MouseEvent>) => {
    if (!organId) return;
    event.stopPropagation();

    if (annotationMode) {
      addAnnotation(organId, {
        id: genId(),
        position: [event.point.x, event.point.y, event.point.z],
        text: TEXTO_PADRAO_ANOTACAO,
        color: "#0f4c81",
        hideLabel: false,
      });
      track("annotation_created", { organ: organId });
      return;
    }

    // Identifica a estrutura nomeada; sem nome (órgão de malha única),
    // identifyStructure recai no nome do órgão. O destaque é aplicado pelo
    // useEffect que observa `inspectedLabel`.
    setInspectedLabel(identifyStructure(event.object, organ?.name));
  };

  if (!organ || !organId) return null;

  return (
    <>
      <group
        ref={rootRef}
        position={emAR ? AR_POSICAO : [0, 0, 0]}
        scale={emAR ? AR_ESCALA : 1}
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
            // Se o .glb existir mas falhar ao decodificar (arquivo corrompido,
            // Draco indisponível), recai no modelo de demonstração em vez de
            // derrubar o canvas inteiro.
            <ErrorBoundary
              key={organId}
              onError={() => {
                setAvailability("placeholder");
                setModelKind("placeholder");
              }}
            >
              <Suspense fallback={null}>
                <GLBModel path={organ.modelPath} onReady={handleReady} />
              </Suspense>
            </ErrorBoundary>
          )}
          {availability === "placeholder" && (
            <PlaceholderOrgan onReady={handleReady} />
          )}
        </group>
        <ModelStateApplier rootRef={rootRef} />
      </group>

      {/*
       * Em VR e em AR o modelo é manipulado pelos controles do headset. Em AR,
       * antes disso, ele é colocado à frente de quem está olhando.
       *
       * `key={modo}` remonta tudo ao trocar de modo: a manipulação guarda a
       * pose inicial no primeiro quadro para o botão de reset, e sem remontar
       * o reset devolveria o órgão à pose do OUTRO modo.
       */}
      {inSession && modelReady && (
        <EntradaXR key={modo} modo={modo} target={rootRef} />
      )}

      {!inSession && transformMode !== "none" && modelReady && rootRef.current && (
        <TransformControls object={rootRef.current} mode={transformMode} />
      )}
    </>
  );
}
