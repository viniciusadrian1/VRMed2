import { getOrganById } from "./organs.ts";

const TERMOS: Record<string, string> = {
  coracao: "átrio, ventrículo, miocárdio, endocárdio, aorta, valva mitral, tricúspide",
  pulmao: "brônquio, bronquíolo, alvéolo, pleura, traqueia, hematose",
  figado: "hepatócito, lóbulo hepático, veia porta, vesícula biliar, cirrose",
  rim: "néfron, glomérulo, córtex renal, medula renal, pelve renal, ureter",
  cerebro: "córtex cerebral, cerebelo, tronco encefálico, hemisfério, neurônio",
  cranio: "mandíbula, maxila, esfenoide, etmoide, zigomático, sutura, forame",
  larynx: "laringe, traqueia, epiglote, cartilagem tireóidea, cricóidea, aritenóidea, hioide, ligamento vocal",
  larynx_muscles: "laringe, cricotireóideo, cricoaritenóideo, tireoaritenóideo, prega vocal",
  pharynx: "faringe, nasofaringe, orofaringe, laringofaringe, suprahióideo",
  parapharyngeal: "espaço parafaríngeo, faringe, carótida, jugular, processo estiloide",
  inner_ear: "cóclea, vestíbulo, canais semicirculares, nervo vestibulococlear",
  pelvis_ligaments: "pelve, ligamento sacroilíaco, sacrotuberal, sacroespinhal, sínfise púbica",
};

/** Só dados públicos do catálogo. Nunca aceitar um prompt livre do cliente. */
export function contextoTranscricao(id: string | null | undefined): string {
  const orgao = id && id.length <= 64 ? getOrganById(id) : undefined;
  const orientacao = "Transcreva apenas a fala em português do Brasil, sem responder à pergunta, resumir ou completar trechos inaudíveis. Contexto: estudo de anatomia no VRmed.";
  if (!orgao) return orientacao;
  return `${orientacao} Modelo em estudo: ${orgao.name}. Vocabulário possível: ${TERMOS[orgao.id] ?? orgao.name}. Use estes termos somente se forem falados.`;
}
