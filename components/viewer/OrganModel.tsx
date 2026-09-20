"use client";

import {
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  type RefObject,
} from "react";
import { useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { Billboard, TransformControls } from "@react-three/drei";
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
  medirNoEspacoDoPai,
  NOME_DO_ROOT,
  normalizeContent,
  prepareModel,
} from "@/lib/model-utils";
import { TEXTO_PADRAO_ANOTACAO } from "@/lib/quiz";
import { useVRMedStore } from "@/lib/store";
import { Text3D } from "@/components/arena/ui3d";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AnnotationHotspots } from "./AnnotationSystem";
import { ClipPlaneHelpers } from "./ClipPlaneHelpers";
import { GLBModel } from "./GLBModel";
import { PlaceholderOrgan } from "./PlaceholderOrgan";
import { StructureHotspots } from "./StructureHotspots";
import { EntradaXR } from "./XRManipulation";

type Availability = "checking" | "real" | "placeholder";

/** Rótulo legível no headset, com uma entrada curta e um ponto de ancoragem. */
function RotuloEstruturaVR({
  label,
  point,
}: {
  label: string;
  point: [number, number, number];
}) {
  const grupo = useRef<THREE.Group>(null);
  const progresso = useRef(0);

  useFrame((_, delta) => {
    progresso.current = Math.min(1, progresso.current + Math.min(delta, 1 / 30) * 8);
    const t = 1 - Math.pow(1 - progresso.current, 3);
    grupo.current?.scale.setScalar(0.82 + t * 0.18);
  });

  return (
    <group ref={grupo}>
      <mesh position={point} raycast={() => null}>
        <sphereGeometry args={[0.018, 10, 8]} />
        <meshBasicMaterial color="#ffd166" toneMapped={false} />
      </mesh>
      <Billboard
        position={[point[0] + 0.12, point[1] + 0.12, point[2]]}
        follow
        lockX={false}
        lockY={false}
        lockZ={false}
      >
        <Text3D size={0.075} color="#f3f6f8" maxWidth={0.9}>
          {label}
        </Text3D>
      </Billboard>
    </group>
  );
}

/** Aplica camadas, cortes e wireframe ao modelo sempre que o estado muda. */
/**
 * Pose PROVISÓRIA em sessão imersiva, relativa aos pés do usuário.
 *
 * Quem manda de verdade é o `EntradaXR`, que mede a cabeça no primeiro quadro
 * e recoloca o modelo à frente do olhar — sentado ou de pé. Esta constante
 * cobre os poucos quadros até o rastreio responder, e é o que fica se ele
 * nunca responder.
 *
 * Aplicada no PRÓPRIO root do modelo, e não num grupo-pai: `XRManipulation`
 * mistura posição de mundo com posição local, e um pai com transformação
 * quebraria o arrastar e o aproximar.
 */
const POSE_PROVISORIA: [number, number, number] = [0, 1.3, -0.8];

/**
 * Abertura pelo analógico esquerdo no VR: puxar para trás separa as partes,
 * empurrar para a frente junta, e soltar deixa onde está. Com o eixo no
 * máximo, abre por inteiro em ~1,5 s — rápido o bastante para não cansar,
 * devagar o bastante para ver cada osso sair do lugar.
 */
const SEGUNDOS_PARA_ABRIR = 1.5;
const CONTROLE_DA_ABERTURA = {
  mover: (eixo: number, delta: number) => {
    const { explosao, setExplosao } = useVRMedStore.getState();
    setExplosao(explosao + (eixo * delta) / SEGUNDOS_PARA_ABRIR);
  },
  // A/X fecha junto com o reset: a próxima pessoa começa do modelo inteiro.
  fechar: () => useVRMedStore.getState().setExplosao(0),
};

/**
 * Escala que devolve ao modelo o tamanho real declarado da estrutura.
 *
 * `normalizeContent` deixa todo modelo com o MAIOR eixo medindo exatamente 2
 * unidades, então a conta é direta: `real / 2`.
 *
 * A ALTURA não sai daqui. Ela é medida pelo `EntradaXR` no objeto já escalado,
 * ao entrar na sessão.
 *
 * Fora de AR/VR nada disso se aplica: numa tela plana o modelo ocupa a
 * viewport, que é o comportamento certo, e "tamanho real" não quer dizer nada.
 * Sem tamanho declarado, cai no comportamento antigo (escala 1).
 */
function escalaReal(tamanhoRealCm: number | undefined): number | null {
  if (!tamanhoRealCm) return null;
  return tamanhoRealCm / 100 / 2;
}

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
  const inSession = useXR(
    (state) => state.mode === "immersive-vr" || state.mode === "immersive-ar",
  );

  // Planos no espaço do root (o dos bounds) e as cópias em MUNDO que os
  // materiais recebem. O three só aceita corte em mundo; medidos no root, os
  // planos acompanham o gizmo em vez de cortar na pose antiga.
  const planosNoRoot = useRef<THREE.Plane[]>([]);
  const planosNoMundo = useRef<THREE.Plane[]>([]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || !bounds || layers.length === 0) return;
    // Não há controle de corte dentro da sessão de AR/VR, então ele fica
    // desligado nela e volta ao sair.
    planosNoRoot.current = inSession ? [] : computeClippingPlanes(clipping, bounds);
    planosNoMundo.current = planosNoRoot.current.map((plano) => plano.clone());
    applyModelState(root, layers, planosNoMundo.current, wireframe);
    invalidate();
  }, [layers, clipping, wireframe, bounds, invalidate, rootRef, inSession]);

  // Leva os planos para o mundo a cada quadro, antes de desenhar. Os materiais
  // guardam estas mesmas instâncias de Plane, então mudar o valor não
  // recompila shader. No frameloop "demand" o TransformControls já pede o
  // quadro enquanto arrasta.
  useFrame(() => {
    const root = rootRef.current;
    if (!root || planosNoMundo.current.length === 0) return;
    root.updateWorldMatrix(true, false);
    planosNoMundo.current.forEach((plano, i) =>
      plano.copy(planosNoRoot.current[i]).applyMatrix4(root.matrixWorld),
    );
  });

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
  const setInspectedPoint = useVRMedStore((s) => s.setInspectedPoint);
  const inspectedLabel = useVRMedStore((s) => s.inspectedLabel);
  const inspectedPoint = useVRMedStore((s) => s.inspectedPoint);
  const invalidate = useThree((s) => s.invalidate);
  const modo = useXR((state) => state.mode);
  const inSession = modo === "immersive-vr" || modo === "immersive-ar";
  const organ = getOrganById(organId);
  // Em AR e VR o metro é real; na tela plana, não. Só dentro da sessão o
  // modelo sai da normalização e passa a ter o tamanho que a estrutura tem.
  const escala = inSession ? escalaReal(organ?.tamanhoRealCm) : null;

  const rootRef = useRef<THREE.Group>(null);
  const [rootObject, setRootObject] = useState<THREE.Group | null>(null);
  const contentRef = useRef<THREE.Group>(null);
  // Destaque (emissive) da estrutura atualmente identificada.
  const highlightRef = useRef<{
    materials: THREE.MeshStandardMaterial[];
    originals: THREE.Color[];
  } | null>(null);

  const [availability, setAvailability] = useState<Availability>("checking");
  const [modelReady, setModelReady] = useState(false);
  const setRoot = useCallback((node: THREE.Group | null) => {
    rootRef.current = node;
    setRootObject(node);
  }, []);

  useEffect(() => {
    if (!organId) return;
    const def = getOrganById(organId);
    if (!def) return;
    // O modelo anterior precisa desaparecer imediatamente enquanto o HEAD
    // assíncrono decide entre GLB real e placeholder.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset visual necessário na troca de órgão
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

  // Zera a pose do root ao trocar de órgão e ao voltar ao 2D. O gizmo mexe
  // direto no Object3D e `position`/`scale` não mudam entre órgãos, então o
  // R3F não reaplica as props (e `rotation` nem é prop): o próximo órgão
  // nasceria girado, movido ou escalado. Dentro da sessão quem manda na pose é
  // o `EntradaXR`.
  useEffect(() => {
    if (inSession) return;
    const root = rootRef.current;
    if (!root) return;
    root.position.set(0, 0, 0);
    root.rotation.set(0, 0, 0);
    root.scale.setScalar(1);
    invalidate();
  }, [organId, inSession, invalidate]);

  // Disparado quando o conteúdo 3D termina de montar/carregar.
  const handleReady = useCallback(() => {
    const content = contentRef.current;
    if (!content) return;
    normalizeContent(content);
    // Bounds e pontos também no espaço do root: com a sessão aberta ele está
    // escalado e na altura dos olhos, e medidos em mundo os cortes e pontos
    // ficariam lá depois de voltar ao 2D.
    setModelBounds(medirNoEspacoDoPai(content, () => getModelBounds(content)));
    // Sistemas agrupam camadas por tecido (material); órgãos, por malha.
    const def = getOrganById(organId);
    const layerBy = def?.layerBy ?? "mesh";
    setLayers(prepareModel(content, layerBy));
    // Os pontos só aparecem em modelos cujas malhas têm nomes anatômicos
    // reais (a função decide); os demais não recebem marcadores.
    setStructures(medirNoEspacoDoPai(content, () => detectStructures(content)));
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
      let mundo = event.point.clone();
      const loja = useVRMedStore.getState();
      if (loja.explosao > 0.001) {
        // Anotações vivem na pose FECHADA (é nela que aparecem). Com o crânio
        // aberto o clique acertou o osso deslocado: guarda o ponto no osso,
        // fecha — o GLBModel aplica a pose na hora, o `set` é síncrono — e
        // relê a posição com o osso no lugar.
        const noOsso = event.object.worldToLocal(mundo);
        loja.setExplosao(0);
        event.object.updateWorldMatrix(true, false);
        mundo = event.object.localToWorld(noOsso);
      }
      // Gravada no espaço do root, como os pontos: `event.point` é mundo e,
      // com o modelo movido pelo gizmo, a anotação ficaria fora dele ao
      // recarregar. Anotações antigas (root na origem) continuam valendo.
      const ponto = rootRef.current ? rootRef.current.worldToLocal(mundo) : mundo;
      addAnnotation(organId, {
        id: genId(),
        position: [ponto.x, ponto.y, ponto.z],
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
    const label = identifyStructure(event.object, organ?.name);
    const local = rootRef.current
      ? rootRef.current.worldToLocal(event.point.clone())
      : event.point;
    setInspectedLabel(label);
    setInspectedPoint([local.x, local.y, local.z]);
  };

  if (!organ || !organId) return null;

  return (
    <>
      <group
        ref={setRoot}
        name={NOME_DO_ROOT}
        position={inSession ? POSE_PROVISORIA : [0, 0, 0]}
        scale={escala ?? 1}
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
                <GLBModel
                  path={organ.modelPath}
                  onReady={handleReady}
                  explosao={organ.explosao}
                />
              </Suspense>
            </ErrorBoundary>
          )}
          {availability === "placeholder" && (
            <PlaceholderOrgan onReady={handleReady} />
          )}
        </group>
        <ModelStateApplier rootRef={rootRef} />
        {/*
         * Dentro do root, e não como irmãos: bounds, pontos e anotações são
         * medidos no espaço dele, então marcadores e quad do corte seguem o
         * gizmo. Html é DOM, invisível na sessão.
         */}
        {!inSession && (
          <>
            <ClipPlaneHelpers />
            <StructureHotspots />
            <AnnotationHotspots />
          </>
        )}
        {inSession && inspectedLabel && inspectedPoint && (
          <RotuloEstruturaVR
            key={inspectedLabel}
            label={inspectedLabel}
            point={inspectedPoint}
          />
        )}
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
        <EntradaXR
          key={modo}
          target={rootRef}
          explosao={organ.explosao ? CONTROLE_DA_ABERTURA : undefined}
        />
      )}

      {!inSession && transformMode !== "none" && modelReady && rootObject && (
        <TransformControls object={rootObject} mode={transformMode} />
      )}
    </>
  );
}
