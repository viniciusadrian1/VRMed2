import type { MeshDepth } from "@/types";

/**
 * Mapa de tradução de nomes de mesh em inglês padrão para português.
 * Aplicado quando o GLB usa a nomenclatura anatômica anglófona habitual.
 */
const LABEL_MAP: Record<string, string> = {
  skin: "Pele",
  epidermis: "Epiderme",
  dermis: "Derme",
  fat: "Tecido adiposo",
  adipose: "Tecido adiposo",
  muscle: "Músculo",
  muscles: "Musculatura",
  bone: "Osso",
  bones: "Ossos",
  skeleton: "Esqueleto",
  cartilage: "Cartilagem",
  tendon: "Tendão",
  ligament: "Ligamento",
  vessel: "Vaso sanguíneo",
  vessels: "Vasos sanguíneos",
  artery: "Artéria",
  arteries: "Artérias",
  aorta: "Aorta",
  vein: "Veia",
  veins: "Veias",
  nerve: "Nervo",
  nerves: "Nervos",
  organ: "Órgão",
  heart: "Coração",
  ventricle: "Ventrículo",
  atrium: "Átrio",
  valve: "Valva",
  lung: "Pulmão",
  lungs: "Pulmões",
  bronchus: "Brônquio",
  trachea: "Traqueia",
  alveoli: "Alvéolos",
  liver: "Fígado",
  lobe: "Lobo",
  kidney: "Rim",
  cortex: "Córtex",
  medulla: "Medula",
  brain: "Cérebro",
  cerebellum: "Cerebelo",
  stomach: "Estômago",
  mucosa: "Mucosa",
  membrane: "Membrana",
  cavity: "Cavidade",
  chamber: "Câmara",
  tissue: "Tecido",
  core: "Núcleo",
  inner: "Camada interna",
  outer: "Camada externa",
  middle: "Camada intermediária",
  // Tecidos dos modelos de sistema (Z-Anatomy).
  eye: "Olho",
  cornea: "Córnea",
  iris: "Íris",
  bronchi: "Brônquios",
  intestine: "Intestino",
  nucleus: "Núcleo",
  teeth: "Dentes",
  suture: "Sutura",
  gland: "Glândula",
  ductus: "Ducto",
  peritoneum: "Peritônio",
  capsule: "Cápsula",
  lcr: "Líquor",
  epiglottis: "Epiglote",
  // Frases completas (o nome é normalizado com espaços antes da busca).
  "articular capsule": "Cápsula articular",
  "white matter": "Substância branca",
  "muscular origin": "Origem muscular",
  "muscular ending": "Inserção muscular",
  // Estruturas da laringe (modelo "anatomy_of_the_larynx").
  "thryoid cartilage": "Cartilagem tireóidea",
  "cricoid cartilage": "Cartilagem cricóidea",
  "right arytenoid cartilage": "Cartilagem aritenóidea direita",
  "left arytenoid cartilage": "Cartilagem aritenóidea esquerda",
  "right corniculate cartilage": "Cartilagem corniculada direita",
  "left corniculate cartilage": "Cartilagem corniculada esquerda",
  "corniculate cartilage": "Cartilagem corniculada",
  "vocal ligament": "Ligamento vocal",
  "vical ligament01": "Ligamento vocal",
  "thyroepiglottic ligament": "Ligamento tireoepiglótico",
  thyroepiglottic1: "Ligamento tireoepiglótico",
  "hyoepiglottic ligament": "Ligamento hioepiglótico",
  "median cricothyroid ligament": "Ligamento cricotireóideo mediano",
  "r vestibular ligament": "Ligamento vestibular direito",
  "l vestibular ligament": "Ligamento vestibular esquerdo",
  "right thyroid ligament": "Ligamento tireóideo direito",
  "left thyroid ligament": "Ligamento tireóideo esquerdo",
  "right thyroid membrane": "Membrana tireóidea direita",
  "left thyroid membrane": "Membrana tireóidea esquerda",
  hyoid: "Osso hioide",
  epoglottis: "Epiglote",
  // Estruturas da laringe (modelo "larynx_with_muscles_and_ligaments").
  "top half larynx": "Laringe (metade superior)",
  "bottom half larynx": "Laringe (metade inferior)",
  "thryhyoid membrane": "Membrana tíreo-hióidea",
  "thyrohyoid membrane": "Membrana tíreo-hióidea",
  cricotrachael: "Ligamento cricotraqueal",
  aryepiglottic: "Prega ariepiglótica",
  // Estruturas da faringe e do espaço parafaríngeo.
  pharynx: "Faringe",
  stylohyoid: "Músculo estilo-hióideo",
  genioglossus: "Músculo genioglosso",
  "genioglossus etc": "Músculo genioglosso",
  "stylo and hyoglossus": "Músculos estiloglosso e hioglosso",
  "stylo muscles": "Músculos estiloides",
  "mylohyoid and geniohyoid": "Músculos milo-hióideo e gênio-hióideo",
  "mylo and geniohyoid": "Músculos milo-hióideo e gênio-hióideo",
  "sternohyoid sternothryoid and thyrohyoid":
    "Músculos esterno-hióideo, esternotireóideo e tíreo-hióideo",
  "levator and tensor": "Levantador e tensor do véu palatino",
  "spehnoid and lateral pterygoid": "Esfenoide e pterigóideo lateral",
  "median glossoepiglottic fold": "Prega glossoepiglótica mediana",
  "glosoepiglottic fold": "Prega glossoepiglótica",
  "pharyngobasilar fascia": "Fáscia faringobasilar",
  "parapharyngeal vessels": "Vasos parafaríngeos",
  parotid: "Glândula parótida",
  vagus: "Nervo vago",
  "recurrent laryngeal": "Nervo laríngeo recorrente",
  "cervical nerve": "Nervo cervical",
  "cervical vertebrae": "Vértebras cervicais",
  occipital: "Osso occipital",
  "mandibular teeth": "Dentes mandibulares",
  "palatine maxilla and teeth": "Palato, maxila e dentes",
  "paltine and teeth2": "Palato e dentes",
  "clavicle and sternum": "Clavícula e esterno",
  "skull bones and other muscless2": "Ossos do crânio e músculos associados",
  // Estruturas do fígado (modelo "vh_m_liver", Visible Human).
  "bare area of liver": "Área nua do fígado",
  "liver capsule": "Cápsula do fígado",
  "diaphragmatic surface": "Face diafragmática",
  "suprarenal impression of liver": "Impressão suprarrenal",
  "renal impression of liver": "Impressão renal",
  "gastric impression of liver": "Impressão gástrica",
  "colic impression of liver": "Impressão cólica",
  "esophageal impression of liver": "Impressão esofágica",
  "duodenal impression of liver": "Impressão duodenal",
  "porta hepatis": "Porta hepática",
  "couinaud liver segment": "Segmento de Couinaud",
  "caudate lobe of liver": "Lobo caudado",
  "quadrate lobe of liver": "Lobo quadrado",
  "right lobe of liver": "Lobo direito do fígado",
  "left lobe of liver": "Lobo esquerdo do fígado",
  "left lateral lobe": "Lobo lateral esquerdo",
  "left medial lobe": "Lobo medial esquerdo",
  "right posteroinferior segment": "Segmento posteroinferior direito",
  "right posterosuperior segment": "Segmento posterossuperior direito",
  "right anterosuperior segment": "Segmento anterossuperior direito",
  "right anteroinferior segment": "Segmento anteroinferior direito",
  "left anterolateral segment": "Segmento anterolateral esquerdo",
  "left posterolateral segment": "Segmento posterolateral esquerdo",
  "left superiomedial segment": "Segmento superomedial esquerdo",
  "left inferomedial segment": "Segmento inferomedial esquerdo",
  "ligament of liver": "Ligamento do fígado",
  "falciform ligament": "Ligamento falciforme",
  "coronary ligament of liver": "Ligamento coronário do fígado",
  "triangular ligament of liver": "Ligamento triangular do fígado",
  "round ligament of liver": "Ligamento redondo do fígado",
  "hepataduodenal ligament": "Ligamento hepatoduodenal",
  "ligamentum venosum": "Ligamento venoso",
};

/** Termos que indicam estruturas externas (pele/gordura). */
const EXTERNAL_HINTS = [
  "skin",
  "epiderm",
  "derm",
  "fat",
  "adipose",
  "surface",
  "outer",
  "pele",
  "externa",
];

/** Termos que indicam estruturas intermediárias (musculatura). */
const INTERMEDIATE_HINTS = [
  "muscle",
  "tendon",
  "ligament",
  "fascia",
  "musculo",
  "muscular",
  "middle",
  "intermedi",
];

/** Normaliza o nome de um mesh para comparação (minúsculas, sem separadores). */
function normalize(raw: string): string {
  return raw.toLowerCase().replace(/[_\-.]+/g, " ").trim();
}

/** Converte "Heart_Left_Ventricle" em "Coração · Ventrículo esquerdo". */
export function translateMeshName(raw: string): string {
  const normalized = normalize(raw);
  // Correspondência de frase completa (ex.: "white matter" → "Substância branca").
  if (LABEL_MAP[normalized]) return LABEL_MAP[normalized];
  const words = normalized.split(/\s+/).filter(Boolean);

  const translated = words.map((word) => {
    const hit = LABEL_MAP[word];
    if (hit) return hit;
    // Capitaliza palavras desconhecidas (provavelmente já em português).
    return word.charAt(0).toUpperCase() + word.slice(1);
  });

  if (translated.length === 0) return raw;
  return translated.join(" ");
}

/**
 * Estima a profundidade anatômica de um mesh a partir do seu nome.
 * Usado pelo modo raio-x para definir opacidades padrão por camada.
 */
export function categorizeMesh(raw: string): MeshDepth {
  const normalized = normalize(raw);
  if (EXTERNAL_HINTS.some((hint) => normalized.includes(hint))) {
    return "external";
  }
  if (INTERMEDIATE_HINTS.some((hint) => normalized.includes(hint))) {
    return "intermediate";
  }
  return "internal";
}

/** Opacidade aplicada a cada profundidade no preset do modo raio-x. */
export const XRAY_OPACITY: Record<MeshDepth, number> = {
  external: 0.15,
  intermediate: 0.4,
  internal: 1,
};
