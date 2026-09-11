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
 *
 * ---------------------------------------------------------------------------
 * `tamanhoRealCm` — por que existe, e o que ele NÃO é
 * ---------------------------------------------------------------------------
 *
 * Em AR e VR o metro é real: se o modelo aparece com 40 cm, ele tem 40 cm na
 * sala. Sem uma escala declarada, o coração aparecia MAIOR que o modelo de
 * corpo inteiro da miologia, porque o visualizador normaliza todo modelo para
 * um cubo de 2 unidades e a diferença de tamanho entre as estruturas se perdia.
 *
 * A escala real não sai dos arquivos. Medindo a caixa delimitadora crua dos
 * 18 `.glb` (maior eixo, via `scripts/check-bounds.mjs`), as unidades não batem
 * entre si:
 *
 *   sistemas (6)        1,696 a 1,700   → metros, corpo de 1,70 m
 *   inner_ear              17,52        → milímetros
 *   larynx                 78,48        → milímetros
 *   larynx_muscles         63,07        → milímetros
 *   parapharyngeal        144,26        → milímetros
 *   coracao                 9,19        → nem metro nem milímetro
 *   rim                     4,65        → nem metro nem milímetro
 *   pharynx                 2,17        → nem metro nem milímetro
 *   figado saudável         1,23  ·  figado patológico  0,70  → nem entre si
 *
 * Nenhum arquivo declara a unidade que usa, e o fígado saudável e o patológico
 * discordam entre si. Não há como derivar do arquivo; a escala tem de ser
 * declarada, e fica declarada aqui, em um lugar só, visível e corrigível.
 *
 * **O que estes números são:** a maior dimensão da estrutura no adulto, em
 * centímetros, em valor de referência de literatura anatômica, usada só para
 * dimensionar o modelo em AR e VR. Nos seis sistemas o número apenas concorda
 * com o que o arquivo já trazia (1,70 m); nas quatro regiões em milímetros,
 * idem.
 *
 * **O que estes números NÃO são:** medição de nenhum caso, dado de pesquisa,
 * nem afirmação sobre o caso de origem do modelo. Eles não entram em métrica
 * nenhuma e não saem daqui para lugar algum além da escala de exibição. Fora
 * de AR/VR o modelo continua normalizado, porque numa tela plana "tamanho
 * real" não quer dizer nada.
 *
 * `node scripts/conferir-escala-xr.mjs` mostra, para cada modelo, com quantos
 * centímetros ele vai aparecer — e reprova se algum ficar sem declaração.
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
    tamanhoRealCm: 12,
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
    tamanhoRealCm: 30,
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
    tamanhoRealCm: 22,
  },
  {
    id: "cerebro",
    name: "Cérebro",
    kind: "organ",
    category: "nervoso",
    modelPath: "/models/healthy/cerebro.glb",
    blurb: "Centro de processamento do sistema nervoso.",
    tamanhoRealCm: 17,
  },
  {
    id: "rim",
    name: "Rim",
    kind: "organ",
    category: "urinario",
    modelPath: "/models/healthy/rim.glb",
    blurb: "Filtragem do sangue e regulação hidroeletrolítica.",
    tamanhoRealCm: 11,
  },
  {
    id: "estomago",
    name: "Estômago",
    kind: "organ",
    category: "digestorio",
    modelPath: "/models/healthy/estomago.glb",
    blurb: "Reservatório muscular da digestão inicial.",
    tamanhoRealCm: 25,
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
    tamanhoRealCm: 170,
  },
  {
    id: "splanchnology",
    name: "Esplancnologia",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/splanchnology.glb",
    blurb: "Vísceras: órgãos torácicos e abdominais.",
    tamanhoRealCm: 170,
  },
  {
    id: "angiology",
    name: "Angiologia",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/angiology.glb",
    blurb: "Sistema circulatório: artérias e veias.",
    tamanhoRealCm: 170,
  },
  {
    id: "neurology",
    name: "Neurologia",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/neurology.glb",
    blurb: "Sistema nervoso central e periférico.",
    tamanhoRealCm: 170,
  },
  {
    id: "arthrology",
    name: "Artrologia",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/arthrology.glb",
    blurb: "Articulações, cápsulas articulares e ligamentos.",
    tamanhoRealCm: 170,
  },
  {
    id: "muscular_insertions",
    name: "Inserções musculares",
    kind: "system",
    layerBy: "material",
    modelPath: "/models/systems/muscular_insertions.glb",
    blurb: "Origens e inserções dos músculos sobre o esqueleto.",
    tamanhoRealCm: 170,
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
    tamanhoRealCm: 8,
  },
  {
    id: "larynx_muscles",
    name: "Laringe — músculos e ligamentos",
    modelPath: "/models/organs/larynx_muscles.glb",
    blurb: "Laringe com a musculatura e os ligamentos associados.",
    tamanhoRealCm: 6,
  },
  {
    id: "pharynx",
    name: "Faringe e assoalho da boca",
    modelPath: "/models/organs/pharynx.glb",
    blurb: "Faringe, musculatura suprahióidea e assoalho bucal.",
    tamanhoRealCm: 15,
  },
  {
    id: "parapharyngeal",
    name: "Espaço parafaríngeo",
    modelPath: "/models/organs/parapharyngeal.glb",
    blurb: "Espaço parafaríngeo e suas relações anatômicas.",
    tamanhoRealCm: 14,
  },
  {
    id: "inner_ear",
    name: "Orelha interna",
    modelPath: "/models/organs/inner_ear.glb",
    blurb: "Cóclea, vestíbulo e canais semicirculares.",
    tamanhoRealCm: 2,
  },
  {
    id: "pelvis_ligaments",
    name: "Ligamentos da pelve feminina",
    modelPath: "/models/organs/pelvis_ligaments.glb",
    blurb: "Ligamentos e estruturas de sustentação da pelve feminina.",
    tamanhoRealCm: 28,
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
