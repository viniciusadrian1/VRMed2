import * as THREE from "three";
import { categorizeMesh, translateMeshName } from "@/lib/anatomy-labels";
import type {
  ClipAxis,
  ClippingState,
  LayerState,
  LayerStrategy,
  ModelBounds,
  StructurePoint,
} from "@/types";

/** Eixo anatômico → vetor normal padrão do plano de corte. */
const AXIS_NORMAL: Record<ClipAxis, THREE.Vector3> = {
  axial: new THREE.Vector3(0, -1, 0), // plano horizontal (superior / inferior)
  sagital: new THREE.Vector3(-1, 0, 0), // separa lados esquerdo / direito
  coronal: new THREE.Vector3(0, 0, -1), // separa anterior / posterior
};

const CLIP_AXES: ClipAxis[] = ["axial", "sagital", "coronal"];

/** Normaliza um nome de material em um rótulo de tecido (remove sufixos .001). */
function normalizeMaterialName(raw: string): string {
  const cleaned = raw.replace(/\.\d+$/, "").trim();
  if (!cleaned || /^(none|default)$/i.test(cleaned)) return "Outros";
  return cleaned;
}

/**
 * Prepara um modelo recém-carregado: nomeia meshes anônimos, clona materiais
 * (para permitir opacidade e cor independentes) e guarda os valores originais.
 *
 * A cada mesh é atribuído um `userData.layerKey` — a chave da camada à qual
 * ele pertence. Com `layerBy: "mesh"` (órgãos), a chave é o nome da malha;
 * com `layerBy: "material"` (sistemas), é o nome do tecido/material.
 * Retorna a lista de camadas anatômicas detectadas.
 */
export function prepareModel(
  content: THREE.Object3D,
  layerBy: LayerStrategy = "mesh",
): LayerState[] {
  const layers: LayerState[] = [];
  const seen = new Set<string>();
  let index = 0;

  content.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;

    index += 1;
    if (!mesh.name) mesh.name = `Estrutura ${index}`;
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    const materials = Array.isArray(mesh.material)
      ? mesh.material
      : [mesh.material];
    const cloned = materials.map((mat) => {
      const copy = mat.clone();
      const std = copy as THREE.MeshStandardMaterial;
      copy.userData.originalColor = std.color ? std.color.clone() : null;
      copy.userData.clipCount = 0;
      return copy;
    });
    mesh.material = Array.isArray(mesh.material) ? cloned : cloned[0];

    // Define a qual camada este mesh pertence. Por malha (órgãos/regiões),
    // a chave é o nome da estrutura — malhas da mesma estrutura anatômica
    // compartilham a camada, evitando entradas repetidas no painel.
    const layerKey =
      layerBy === "material"
        ? normalizeMaterialName(cloned[0]?.name ?? "")
        : (structureNameOf(mesh) ?? mesh.name);
    mesh.userData.layerKey = layerKey;

    if (seen.has(layerKey)) return;
    seen.add(layerKey);
    // O rótulo usa a identificação completa (nome da estrutura ou tecido),
    // não o nome bruto da malha — que pode ser "Object_6" ou trazer sufixos.
    const identified = identifyStructure(mesh);
    layers.push({
      name: layerKey,
      label:
        identified === "Estrutura não identificada"
          ? `Estrutura ${layers.length + 1}`
          : identified,
      visible: true,
      opacity: 1,
      color: null,
      depth: categorizeMesh(layerKey),
    });
  });

  return layers;
}

/**
 * Limpa um nome bruto de nó/malha. Alguns exportadores guardam o nome da
 * estrutura no fim de um caminho de arquivo (".../preprocess/Trachea.obj").
 * Extrai esse nome final, remove a extensão, sublinhados iniciais e o
 * índice numérico de exportação no fim ("Pharynx_8" → "Pharynx").
 */
function cleanStructureName(raw: string): string {
  let name = (raw ?? "").trim();
  const slash = Math.max(name.lastIndexOf("/"), name.lastIndexOf("\\"));
  if (slash >= 0) name = name.slice(slash + 1);
  name = name.replace(
    /\.(obj|fbx|glb|gltf|gles|osgb|dae|stl|ply|blend|max|3ds)$/i,
    "",
  );
  // Prefixo de dataset (ex.: Visible Human "VH_M_" / "VH_F_").
  name = name.replace(/^vh[_\s][mf][_\s]/i, "");
  name = name.replace(/^[_\s]+/, "");
  name = name.replace(/[_\s]+\d+$/, "");
  return name.trim();
}

/**
 * Verifica se um nome é apenas um rótulo genérico de exportador
 * ("Object_12", "Mesh", "Sketchfab_Scene", "SubTool-9"…), sem valor
 * anatômico.
 */
function isGenericName(raw: string): boolean {
  const name = raw
    .trim()
    .toLowerCase()
    .replace(/[_.\-]+/g, " ")
    .trim();
  if (!name) return true;
  if (/^\d+$/.test(name)) return true;
  // Contém uma sequência hexadecimal longa — nome de arquivo/upload
  // (ex.: "15db5831…e4.fbx", cujo ponto o three.js remove ao carregar).
  if (/[0-9a-f]{16,}/.test(name.replace(/\s/g, ""))) return true;
  // Contêineres e artefatos de exportadores (Sketchfab, glTF, ZBrush, OSG,
  // Maya…) — nunca representam uma estrutura anatômica.
  if (
    /sketchfab|gltf|armature|visual scene|scene ?root|root ?node|osg|zbrush|materialmerger|subtool|shadinggroup|initialshading|lambert ?\d|phong ?\d/.test(
      name,
    )
  ) {
    return true;
  }
  // Rótulos genéricos numerados ou triviais.
  return /^(object|mesh|node|group|geometry|primitive|estrutura|scene|root|model|untitled|default ?material|material|element|item|surface|polysurface)\s*\d*$/.test(
    name,
  );
}

/** Nome do tecido (material) de uma malha, se for anatômico; senão "". */
function tissueFromMesh(mesh: THREE.Mesh): string {
  const materials = Array.isArray(mesh.material)
    ? mesh.material
    : [mesh.material];
  for (const material of materials) {
    const raw = (material?.name ?? "").trim();
    const cleaned = raw.replace(/\.\d+$/, "").trim();
    if (!cleaned || /^(none|default)$/i.test(cleaned)) continue;
    if (!isGenericName(cleaned)) return cleaned;
  }
  return "";
}

/**
 * Extrai o nome anatômico de uma estrutura a partir da malha ou de seus
 * ancestrais nomeados. Devolve `null` quando nenhum nó traz um nome
 * anatômico real (ex.: malhas só com "Object_6" ou nomes de tecido).
 */
function structureNameOf(object: THREE.Object3D): string | null {
  // Procura o primeiro ancestral com nome anatômico. Limita a subida para
  // não alcançar os contêineres da cena.
  let node: THREE.Object3D | null = object;
  let found: THREE.Object3D | null = null;
  let depth = 0;
  while (node && depth < 10) {
    const name = cleanStructureName(node.name ?? "");
    if (name && !isGenericName(name)) {
      found = node;
      break;
    }
    node = node.parent;
    depth += 1;
  }
  if (!found) return null;

  // Sobe para o ancestral canônico quando o nó-filho apenas acrescenta um
  // sufixo de material (ex.: malha "Hyoid_Hyoid_Mat_0" sob o nó "Hyoid").
  let best = found;
  let guard = 0;
  while (best.parent && guard < 6) {
    const parentName = cleanStructureName(best.parent.name ?? "");
    const bestName = cleanStructureName(best.name ?? "");
    if (
      parentName &&
      !isGenericName(parentName) &&
      bestName.toLowerCase().startsWith(parentName.toLowerCase())
    ) {
      best = best.parent;
      guard += 1;
    } else {
      break;
    }
  }
  return translateMeshName(cleanStructureName(best.name ?? ""));
}

/**
 * Determina o rótulo de uma estrutura clicada. Procura, em ordem:
 *  1. um nome anatômico na própria malha ou em algum ancestral;
 *  2. a camada (`layerKey`) atribuída na preparação do modelo;
 *  3. o nome do tecido (material) lido diretamente da malha.
 * Nunca devolve nomes genéricos de exportador como "Object_6"; quando
 * nada é identificável, devolve `fallback` (ex.: o nome do órgão, útil em
 * modelos de um único órgão sem malhas nomeadas).
 */
export function identifyStructure(
  object: THREE.Object3D,
  fallback = "Estrutura não identificada",
): string {
  // 1. Nome anatômico no objeto ou em ancestrais.
  const named = structureNameOf(object);
  if (named) return named;

  // 2. Camada atribuída em prepareModel (o tecido, nos modelos de sistema).
  const layerKey = (object.userData.layerKey as string | undefined)?.trim();
  if (layerKey && layerKey !== "Outros" && !isGenericName(layerKey)) {
    return translateMeshName(layerKey);
  }

  // 3. Tecido lido diretamente do material da malha clicada.
  const mesh = object as THREE.Mesh;
  if (mesh.isMesh) {
    const tissue = tissueFromMesh(mesh);
    if (tissue) return translateMeshName(tissue);
  }

  return fallback;
}

/**
 * Detecta os pontos numerados das estruturas do modelo.
 *
 * Por precisão — esta é uma aplicação da área da saúde — só gera pontos
 * para estruturas com nome anatômico real no arquivo: um ponto por
 * estrutura nomeada, no seu centro. Modelos sem malhas nomeadas (sistemas
 * agrupados por tecido, órgãos de malha única, exportações genéricas) não
 * recebem nenhum ponto, evitando marcadores repetidos ou sem sentido.
 */
export function detectStructures(content: THREE.Object3D): StructurePoint[] {
  content.updateWorldMatrix(true, true);

  // Agrupa as malhas pela estrutura nomeada a que pertencem.
  const groups = new Map<string, THREE.Mesh[]>();
  content.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh || !mesh.geometry) return;
    const name = structureNameOf(mesh);
    if (name) groups.set(name, [...(groups.get(name) ?? []), mesh]);
  });

  const points: StructurePoint[] = [];
  const vertex = new THREE.Vector3();

  for (const [name, meshes] of groups) {
    // Marca a estrutura no seu vértice mais externo (mais distante do centro
    // do modelo — a origem, após a normalização). O ponto fica na superfície
    // exposta, então a oclusão o esconde quando essa face está virada para
    // longe da câmera, evitando bagunça visual.
    let marker: THREE.Vector3 | null = null;
    let maxDistSq = -1;
    for (const mesh of meshes) {
      const attribute = mesh.geometry.getAttribute("position");
      if (!attribute || attribute.count === 0) continue;
      const step = Math.max(1, Math.floor(attribute.count / 300));
      for (let i = 0; i < attribute.count; i += step) {
        vertex.fromBufferAttribute(attribute, i);
        mesh.localToWorld(vertex);
        const distSq = vertex.lengthSq();
        if (distSq > maxDistSq) {
          maxDistSq = distSq;
          marker = vertex.clone();
        }
      }
    }
    if (marker) {
      // Afasta levemente da superfície para a oclusão não esconder o ponto
      // contra a própria malha em que ele se apoia.
      marker.multiplyScalar(1.03);
      points.push({
        id: `structure-${points.length}`,
        label: name,
        position: [marker.x, marker.y, marker.z],
      });
    }
  }

  return points;
}

/**
 * Centraliza e escala o conteúdo para caber em um cubo de ~2 unidades.
 *
 * É idempotente: zera a transformação antes de medir, para que medir um
 * modelo já normalizado devolva o mesmo resultado. Sem isso, uma segunda
 * chamada (ex.: efeitos remontados pelo React) leria o modelo de 2 unidades
 * e o "renormalizaria" com escala 1, desfazendo o ajuste — fatal para
 * modelos cujas unidades de origem diferem muito (ex.: milímetros).
 */
export function normalizeContent(content: THREE.Object3D): void {
  // Zera a transformação para medir o modelo cru.
  content.scale.setScalar(1);
  content.position.set(0, 0, 0);
  content.updateMatrix();
  content.updateMatrixWorld(true);

  const box = new THREE.Box3().setFromObject(content);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 2 / maxDim;

  content.scale.setScalar(scale);
  content.position.set(
    -center.x * scale,
    -center.y * scale,
    -center.z * scale,
  );
  // Recalcula a matriz a partir da nova escala/posição — o grupo gerenciado
  // pelo React pode ter `matrixAutoUpdate` desativado.
  content.updateMatrix();
  content.updateMatrixWorld(true);
}

/** Bounding box do conteúdo (após normalização), base dos cálculos de corte. */
export function getModelBounds(content: THREE.Object3D): ModelBounds {
  const box = new THREE.Box3().setFromObject(content);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  return {
    center: [center.x, center.y, center.z],
    size: [size.x, size.y, size.z],
  };
}

/** Localização do corte de um eixo, em coordenadas do mundo. */
export function getClipCut(
  axis: ClipAxis,
  position: number,
  bounds: ModelBounds,
): number {
  const [cx, cy, cz] = bounds.center;
  const [sx, sy, sz] = bounds.size;
  const half = (axis === "axial" ? sy : axis === "sagital" ? sx : sz) / 2;
  const centerComponent = axis === "axial" ? cy : axis === "sagital" ? cx : cz;
  return centerComponent + position * half;
}

/** Constrói os THREE.Plane ativos a partir do estado de corte e do bounding box. */
export function computeClippingPlanes(
  clipping: ClippingState,
  bounds: ModelBounds,
): THREE.Plane[] {
  const planes: THREE.Plane[] = [];

  for (const axis of CLIP_AXES) {
    const state = clipping[axis];
    if (!state.enabled) continue;

    const cut = getClipCut(axis, state.position, bounds);
    const normal = AXIS_NORMAL[axis].clone();
    let constant = cut;
    if (state.flipped) {
      normal.negate();
      constant = -cut;
    }
    planes.push(new THREE.Plane(normal, constant));
  }

  return planes;
}

/** Aplica visibilidade, opacidade, cor, wireframe e cortes ao modelo. */
export function applyModelState(
  root: THREE.Object3D,
  layers: LayerState[],
  planes: THREE.Plane[],
  wireframe: boolean,
): void {
  const byName = new Map(layers.map((layer) => [layer.name, layer]));

  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    const layer = byName.get(mesh.userData.layerKey as string);
    if (!layer) return;

    mesh.visible = layer.visible;
    const materials = Array.isArray(mesh.material)
      ? mesh.material
      : [mesh.material];

    for (const mat of materials) {
      const m = mat as THREE.MeshStandardMaterial;
      m.opacity = layer.opacity;
      m.transparent = layer.opacity < 0.999;
      // Estruturas semitransparentes não escrevem profundidade — evita artefatos.
      m.depthWrite = layer.opacity >= 0.999;
      m.side = THREE.DoubleSide;
      if ("wireframe" in m) m.wireframe = wireframe;

      if (m.color) {
        const original = m.userData.originalColor as THREE.Color | null;
        if (layer.color) m.color.set(layer.color);
        else if (original) m.color.copy(original);
      }

      m.clippingPlanes = planes;
      m.clipShadows = true;
      // O shader só precisa ser recompilado quando o nº de planos muda.
      if (m.userData.clipCount !== planes.length) {
        m.userData.clipCount = planes.length;
        m.needsUpdate = true;
      }
    }
  });
}

/** Libera os materiais clonados de um modelo ao trocá-lo (cumpre dispose()). */
export function disposeMaterials(root: THREE.Object3D): void {
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    const materials = Array.isArray(mesh.material)
      ? mesh.material
      : [mesh.material];
    materials.forEach((m) => m.dispose());
  });
}
