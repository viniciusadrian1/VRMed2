import { getOrganById } from "./organs.ts";

/** Sugestões educativas, não respostas clínicas nem promessas de segmentação do GLB. */
export const PERGUNTAS_POR_MODELO: Record<string, readonly string[]> = {
  coracao: ["Como o coração bombeia o sangue pelo corpo?", "Qual é a diferença entre átrios e ventrículos?", "Para que servem as valvas do coração?"],
  pulmao: ["Como os pulmões fazem as trocas gasosas?", "Qual caminho o ar percorre até os alvéolos?", "Como o diafragma participa da respiração?"],
  figado: ["Quais são as principais funções do fígado?", "Qual é a relação entre fígado, bile e digestão?", "Como o fígado participa do metabolismo?"],
  cerebro: ["Quais são as principais regiões do cérebro?", "Como o cérebro participa dos movimentos?", "Como o cérebro se comunica com o restante do corpo?"],
  rim: ["Como o rim participa da formação da urina?", "O que é um néfron e qual é sua função?", "Como os rins regulam a água e os sais do corpo?"],
  estomago: ["Qual caminho o alimento percorre da boca ao reto?", "Qual é a diferença entre digestão e absorção?", "Como estômago e intestinos participam da digestão?"],
  larynx: ["Qual é a função da laringe?", "Como a laringe participa da produção da voz?", "Como a laringe ajuda a proteger a via aérea?"],
  larynx_muscles: ["Como os músculos da laringe movimentam as pregas vocais?", "Qual é a função dos ligamentos da laringe?", "Como a laringe regula a passagem de ar e a voz?"],
  pharynx: ["Como a faringe participa da deglutição?", "Qual é a diferença entre faringe e laringe?", "Qual é a função dos músculos do assoalho da boca?"],
  parapharyngeal: ["Onde fica o espaço parafaríngeo?", "Quais são as relações anatômicas do espaço parafaríngeo?", "Por que estudar os espaços profundos do pescoço?"],
  inner_ear: ["Como a cóclea participa da audição?", "Como a orelha interna participa do equilíbrio?", "Qual é a função dos canais semicirculares?"],
  pelvis_ligaments: ["Qual é a função dos ligamentos da pelve?", "Como os ligamentos ajudam a estabilizar a pelve?", "Qual é a diferença entre ligamentos e músculos do assoalho pélvico?"],
  cranio: ["Quais são os principais ossos do crânio e da face?", "O que são as suturas do crânio?", "Como a mandíbula se articula com o crânio?"],
  myology: ["Como os músculos produzem movimento?", "Qual é a diferença entre músculos agonistas e antagonistas?", "Como os músculos se organizam pelo corpo?"],
  splanchnology: ["Quais vísceras ficam no tórax e no abdome?", "Como os órgãos internos se relacionam no espaço?", "Como os sistemas das vísceras trabalham em conjunto?"],
  angiology: ["Qual é a diferença entre artérias, veias e capilares?", "Como se conectam a circulação pulmonar e a sistêmica?", "Como o sangue retorna ao coração?"],
  neurology: ["Como se dividem os sistemas nervosos central e periférico?", "Qual é a função dos nervos pelo corpo?", "Como informações sensitivas e motoras percorrem o sistema nervoso?"],
  arthrology: ["Quais são os principais tipos de articulação?", "Qual é a função da cápsula articular?", "Como os ligamentos ajudam a estabilizar as articulações?"],
  muscular_insertions: ["Qual é a diferença entre origem e inserção muscular?", "Como o ponto de inserção influencia o movimento?", "Qual é a relação entre músculos, tendões e ossos?"],
};

export function perguntasDoModelo(id: string | null | undefined): readonly string[] {
  if (!id) return [];
  const modelo = getOrganById(id);
  if (!modelo) return [];
  return PERGUNTAS_POR_MODELO[id] ?? [
    `Quais estruturas compõem ${modelo.name}?`,
    `Como funciona ${modelo.name}?`,
    `Quais relações anatômicas devo estudar em ${modelo.name}?`,
  ];
}
