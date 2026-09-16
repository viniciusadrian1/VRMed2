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
 * A escala real não sai dos arquivos. Só os seis sistemas estão em metros; os
 * outros doze vêm em unidades arbitrárias (o Sketchfab e o ZBrush reescalam na
 * exportação) — inclusive os que parecem milímetros: a laringe dá ~1,1 mm por
 * unidade, a orelha interna ~2,1 mm. A escala tem de ser declarada, e fica
 * declarada aqui, em um lugar só, visível e corrigível.
 *
 * **O que o número mede, exatamente:** o comprimento real, em cm, do que ocupa
 * o MAIOR eixo da caixa do arquivo INTEIRO — todas as malhas, vértice a
 * vértice. `normalizeContent` põe esse eixo em 2 unidades e o visualizador o
 * devolve a `tamanhoRealCm`. Não é "o tamanho do órgão" do livro: o arquivo do
 * coração traz o arco da aorta, então o maior eixo vai do ápice à ponta dos
 * ramos do arco, e é esse vão que tem de medir o valor real. A primeira versão
 * usou o tamanho do órgão isolado e deixou quase tudo 20 a 40% pequeno (o
 * pulmão com tamanho de criança, o trato digestório com 25 cm).
 *
 * **Como foram obtidos:** para cada arquivo, o conteúdo foi identificado em
 * vistas ortográficas; pelo menos dois marcos anatômicos independentes foram
 * medidos em unidades cruas (ex.: largura e comprimento base-ápice do
 * coração) e comparados a valores de adulto da literatura (Gray's Anatomy,
 * StatPearls, estudos morfométricos), cada um dando um fator cm/unidade; os
 * fatores tinham de concordar, e o resultado passou por duas conferências
 * independentes. O comentário de cada entrada diz o que o maior eixo cobre:
 * se alguém recortar o arquivo (tirar o ureter do rim, a traqueia do pulmão),
 * o número tem de ser refeito.
 *
 * **O que estes números são:** valores de referência de anatomia adulta,
 * usados só para dimensionar o modelo em AR e VR.
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
    // Ápice → ponta dos ramos do arco aórtico (coração com os vasos da base).
    tamanhoRealCm: 14,
  },
  {
    id: "pulmao",
    name: "Pulmão",
    kind: "organ",
    category: "respiratorio",
    modelPath: "/models/healthy/pulmao.glb",
    blurb: "Órgão das trocas gasosas, da traqueia aos alvéolos.",
    // Base do pulmão → topo da via aérea: os dois pulmões + laringe e traqueia.
    tamanhoRealCm: 42,
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
    // Diâmetro anteroposterior do fígado inteiro, com os ligamentos.
    tamanhoRealCm: 21.5,
  },
  {
    id: "cerebro",
    name: "Cérebro",
    kind: "organ",
    category: "nervoso",
    modelPath: "/models/healthy/cerebro.glb",
    blurb: "Centro de processamento do sistema nervoso.",
    // Polo frontal → polo occipital.
    tamanhoRealCm: 17,
  },
  {
    id: "rim",
    name: "Rim",
    kind: "organ",
    category: "urinario",
    modelPath: "/models/healthy/rim.glb",
    // Par do Comparar no lugar do pulmão, que nunca recebeu o modelo com
    // enfisema (o enfisema real está na Clínica, a partir de TC).
    pathologicalPath: "/models/pathological/rim.glb",
    pathologyName: "Doença renal policística",
    blurb: "Filtragem do sangue e regulação hidroeletrolítica.",
    // Ápice da suprarrenal → corte do ureter (rim com suprarrenal, vasos e ureter).
    tamanhoRealCm: 15,
  },
  {
    id: "estomago",
    name: "Sistema digestório",
    kind: "organ",
    category: "digestorio",
    modelPath: "/models/healthy/estomago.glb",
    blurb: "Trato digestório completo, da boca ao reto.",
    // Boca → reto: o trato digestório inteiro. O `id` e o arquivo continuam
    // "estomago" (nome antigo do item) para não quebrar sessões salvas.
    tamanhoRealCm: 70,
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
    // Estatura, sola → topo da cabeça. Os seis sistemas vêm em metros e em
    // pé; o valor só confirma o que o arquivo já traz.
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
    // Corno maior do hioide → coto de traqueia abaixo da cricoide.
    tamanhoRealCm: 8.8,
  },
  {
    id: "larynx_muscles",
    name: "Laringe — músculos e ligamentos",
    modelPath: "/models/organs/larynx_muscles.glb",
    blurb: "Laringe com a musculatura e os ligamentos associados.",
    // Ápice da epiglote → coto de traqueia.
    tamanhoRealCm: 9,
  },
  {
    id: "pharynx",
    name: "Faringe e assoalho da boca",
    modelPath: "/models/organs/pharynx.glb",
    blurb: "Faringe, musculatura suprahióidea e assoalho bucal.",
    // Escama do temporal → manúbrio (hemissecção de cabeça e pescoço).
    tamanhoRealCm: 23.5,
  },
  {
    id: "parapharyngeal",
    name: "Espaço parafaríngeo",
    modelPath: "/models/organs/parapharyngeal.glb",
    blurb: "Espaço parafaríngeo e suas relações anatômicas.",
    // Occipital (lambda) → abertura piriforme: hemicabeça, eixo anteroposterior.
    tamanhoRealCm: 17.5,
  },
  {
    id: "inner_ear",
    name: "Orelha interna",
    modelPath: "/models/organs/inner_ear.glb",
    blurb: "Cóclea, vestíbulo e canais semicirculares.",
    // Plano-bússola de orientação → nervos; inclui a orelha média.
    tamanhoRealCm: 3.7,
  },
  {
    id: "pelvis_ligaments",
    name: "Ligamentos da pelve feminina",
    modelPath: "/models/organs/pelvis_ligaments.glb",
    blurb: "Ligamentos e estruturas de sustentação da pelve feminina.",
    // Ponta a ponta dos cotos dos fêmures (entre as cristas ilíacas, ~29 cm).
    tamanhoRealCm: 37,
  },
  {
    id: "cranio",
    name: "Crânio",
    modelPath: "/models/organs/cranio.glb",
    blurb: "Ossos do crânio e da face, que se separam para estudo um a um.",
    // Vértice → mento, com a mandíbula. O arquivo já vem em centímetros, e os
    // outros dois eixos batem com um crânio adulto: 13,9 cm de largura e
    // 17,6 cm de comprimento.
    tamanhoRealCm: 20.8,
    // A animação do arquivo abre de 0 a 4 s e fecha de 4 a 8 s.
    explosao: { ateSegundos: 4, rotulo: "Separar os ossos" },
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
  figado: [
    "Substituição progressiva do parênquima por tecido fibroso.",
    "Formação de nódulos de regeneração.",
    "Superfície irregular e consistência endurecida.",
    "Comprometimento difuso das funções metabólicas.",
  ],
  rim: [
    "Numerosos cistos cheios de líquido ocupam e substituem o parênquima.",
    "Rim muito aumentado de volume e de contorno irregular (aqui os dois são exibidos do mesmo tamanho, sem a proporção real).",
    "Perda progressiva de néfrons funcionais, com queda da filtração.",
    "Associa-se a hipertensão arterial e pode evoluir para insuficiência renal.",
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
