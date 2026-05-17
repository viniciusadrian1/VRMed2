import type { OrganCategory, OrganDefinition } from "@/types";

/**
 * Catálogo de órgãos disponíveis no VRmed.
 *
 * Para adicionar um novo órgão:
 *  1. Coloque o arquivo `.glb` saudável em `/public/models/healthy/<id>.glb`.
 *  2. (Opcional) Coloque a versão patológica em `/public/models/pathological/<id>.glb`.
 *  3. Crie a descrição em `/public/descriptions/<id>.json`.
 *  4. Adicione uma entrada neste catálogo.
 *
 * O visualizador exibe um modelo de demonstração procedural quando o `.glb`
 * correspondente ainda não foi adicionado — assim a aplicação permanece
 * funcional antes de receber os modelos definitivos.
 */
export const ORGANS: OrganDefinition[] = [
  {
    id: "coracao",
    name: "Coração",
    kind: "organ",
    category: "cardiovascular",
    modelPath: "/models/healthy/coracao.glb",
    pathologicalPath: "/models/pathological/coracao.glb",
    pathologyName: "Hipertrofia ventricular",
    blurb: "Bomba muscular com quatro câmaras e o sistema valvar.",
  },
  {
    id: "pulmao",
    name: "Pulmão",
    kind: "organ",
    category: "respiratorio",
    modelPath: "/models/healthy/pulmao.glb",
    pathologicalPath: "/models/pathological/pulmao.glb",
    pathologyName: "Enfisema pulmonar",
    blurb: "Órgão das trocas gasosas, da traqueia aos alvéolos.",
  },
  {
    id: "figado",
    name: "Fígado",
    kind: "organ",
    category: "digestorio",
    modelPath: "/models/healthy/figado.glb",
    pathologicalPath: "/models/pathological/figado.glb",
    pathologyName: "Cirrose hepática",
    blurb: "Maior glândula do corpo, central no metabolismo.",
  },
  {
    id: "cerebro",
    name: "Cérebro",
    kind: "organ",
    category: "nervoso",
    modelPath: "/models/healthy/cerebro.glb",
    blurb: "Centro de processamento do sistema nervoso.",
  },
  {
    id: "rim",
    name: "Rim",
    kind: "organ",
    category: "urinario",
    modelPath: "/models/healthy/rim.glb",
    blurb: "Filtragem do sangue e regulação hidroeletrolítica.",
  },
  {
    id: "estomago",
    name: "Estômago",
    kind: "organ",
    category: "digestorio",
    modelPath: "/models/healthy/estomago.glb",
    blurb: "Reservatório muscular da digestão inicial.",
  },
];

/**
 * Catálogo de sistemas anatômicos — modelos de corpo inteiro, cada um
 * focado em um sistema. As malhas desses modelos não têm nomes anatômicos,
 * então as camadas são agrupadas por material (tecido): `layerBy: "material"`.
 *
 * Para adicionar/atualizar um sistema, coloque o `.glb` em
 * `/public/models/systems/<id>.glb` (otimizado para web — veja o README).
 */
export const SYSTEMS: OrganDefinition[] = [
  {
    id: "myology",
    name: "Miologia",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/myology.glb",
    blurb: "Sistema muscular completo, em corpo inteiro.",
  },
  {
    id: "splanchnology",
    name: "Esplancnologia",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/splanchnology.glb",
    blurb: "Vísceras: órgãos torácicos e abdominais.",
  },
  {
    id: "angiology",
    name: "Angiologia",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/angiology.glb",
    blurb: "Sistema circulatório: artérias e veias.",
  },
  {
    id: "neurology",
    name: "Neurologia",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/neurology.glb",
    blurb: "Sistema nervoso central e periférico.",
  },
  {
    id: "arthrology",
    name: "Artrologia",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/arthrology.glb",
    blurb: "Articulações, cápsulas articulares e ligamentos.",
  },
  {
    id: "muscular_insertions",
    name: "Inserções musculares",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/muscular_insertions.glb",
    blurb: "Origens e inserções dos músculos sobre o esqueleto.",
  },
];

/**
 * Catálogo de anatomia regional — modelos detalhados de uma região do corpo
 * (cabeça, pescoço, pelve). Diferente dos sistemas, estes modelos têm malhas
 * ou nós nomeados, então as camadas são agrupadas por malha (`layerBy:"mesh"`,
 * o padrão) e o clique identifica a estrutura individual.
 *
 * Coloque o `.glb` otimizado em `/public/models/organs/<id>.glb`.
 */
export const REGIONS: OrganDefinition[] = [
  {
    id: "larynx",
    name: "Laringe",
    modelPath: "/models/organs/larynx.glb",
    blurb: "Cartilagens, membranas e ligamentos da laringe.",
  },
  {
    id: "larynx_muscles",
    name: "Laringe — músculos e ligamentos",
    modelPath: "/models/organs/larynx_muscles.glb",
    blurb: "Laringe com a musculatura e os ligamentos associados.",
  },
  {
    id: "pharynx",
    name: "Faringe e assoalho da boca",
    modelPath: "/models/organs/pharynx.glb",
    blurb: "Faringe, musculatura suprahióidea e assoalho bucal.",
  },
  {
    id: "parapharyngeal",
    name: "Espaço parafaríngeo",
    modelPath: "/models/organs/parapharyngeal.glb",
    blurb: "Espaço parafaríngeo e suas relações anatômicas.",
  },
  {
    id: "inner_ear",
    name: "Orelha interna",
    modelPath: "/models/organs/inner_ear.glb",
    blurb: "Cóclea, vestíbulo e canais semicirculares.",
  },
  {
    id: "pelvis_ligaments",
    name: "Ligamentos da pelve feminina",
    modelPath: "/models/organs/pelvis_ligaments.glb",
    blurb: "Ligamentos e estruturas de sustentação da pelve feminina.",
  },
];

/** Catálogo completo: sistemas + anatomia regional + órgãos individuais. */
export const ALL_MODELS: OrganDefinition[] = [
  ...SYSTEMS,
  ...REGIONS,
  ...ORGANS,
];

/**
 * Diferenças anatômicas chave entre o modelo saudável e o patológico,
 * exibidas como legenda no modo de comparação.
 */
export const COMPARISON_NOTES: Record<string, string[]> = {
  coracao: [
    "Espessamento acentuado da parede do ventrículo esquerdo.",
    "Redução do volume da câmara ventricular.",
    "Aumento da demanda de oxigênio pelo miocárdio.",
    "Maior rigidez da parede, prejudicando o enchimento diastólico.",
  ],
  pulmao: [
    "Destruição das paredes alveolares e perda de septos.",
    "Alvéolos dilatados que se fundem em espaços maiores.",
    "Perda da elasticidade do tecido pulmonar.",
    "Aprisionamento de ar e redução da área de troca gasosa.",
  ],
  figado: [
    "Substituição progressiva do parênquima por tecido fibroso.",
    "Formação de nódulos de regeneração.",
    "Superfície irregular e consistência endurecida.",
    "Comprometimento difuso das funções metabólicas.",
  ],
};

/** Rótulos legíveis para cada categoria anatômica. */
export const CATEGORY_LABELS: Record<OrganCategory, string> = {
  cardiovascular: "Sistema cardiovascular",
  respiratorio: "Sistema respiratório",
  digestorio: "Sistema digestório",
  nervoso: "Sistema nervoso",
  urinario: "Sistema urinário",
  musculoesqueletico: "Sistema musculoesquelético",
};

/** Localiza um modelo (órgão ou sistema) pelo seu id. */
export function getOrganById(
  id: string | null | undefined,
): OrganDefinition | undefined {
  if (!id) return undefined;
  return ALL_MODELS.find((model) => model.id === id);
}

/** Órgãos que possuem um par patológico cadastrado. */
export function getComparableOrgans(): OrganDefinition[] {
  return ORGANS.filter((organ) => Boolean(organ.pathologicalPath));
}

/** Caminho do JSON de descrição de um órgão. */
export function getDescriptionPath(id: string): string {
  return `/descriptions/${id}.json`;
}

/** Caminho do áudio pré-gravado (fallback do TTS). */
export function getAudioFallbackPath(id: string): string {
  return `/audio/${id}.mp3`;
}
