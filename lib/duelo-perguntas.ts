import type { RodadaOnline } from "./duelo-salas.ts";

/** Conteúdo local para público geral. Fontes e limites em docs/TUTOR-E-DUELO.md. */
export const FONTES_DUELO = {
  coracao: "https://www.nhlbi.nih.gov/health/heart/blood-flow",
  rim: "https://www.niddk.nih.gov/health-information/kidney-disease/kidneys-how-they-work",
  digestao: "https://www.niddk.nih.gov/health-information/digestive-diseases/digestive-system-how-it-works",
  cerebro: "https://www.ninds.nih.gov/sites/default/files/2025-05/know-your-brain-brian-basics.pdf",
  voz: "https://www.nidcd.nih.gov/health/taking-care-your-voice",
} as const;

export interface PerguntaDuelo {
  id: string;
  organId: string;
  pontos: 100 | 200;
  pergunta: string;
  resposta: string;
  distratores: [string, string, string];
  explicacao: string;
  fonte: keyof typeof FONTES_DUELO;
}

const pergunta = (id: string, organId: string, pontos: 100 | 200, texto: string, resposta: string,
  distratores: [string, string, string], explicacao: string, fonte: PerguntaDuelo["fonte"]): PerguntaDuelo =>
  ({ id, organId, pontos, pergunta: texto, resposta, distratores, explicacao, fonte });

export const PERGUNTAS_DUELO: PerguntaDuelo[] = [
  pergunta("cor-bomba", "coracao", 100, "Qual é a principal função do coração?", "Bombear sangue", ["Produzir bile", "Filtrar a urina", "Digerir alimentos"], "O coração impulsiona o sangue pelo corpo.", "coracao"),
  pergunta("cor-transporte", "coracao", 100, "O sangue leva aos órgãos...", "Oxigênio e nutrientes", ["Apenas água", "Somente gás carbônico", "Apenas células ósseas"], "O sangue distribui oxigênio e nutrientes.", "coracao"),
  pergunta("cor-valvas", "coracao", 200, "As válvulas do coração evitam...", "O refluxo do sangue", ["A formação da voz", "A digestão de gorduras", "A produção de urina"], "As válvulas ajudam o sangue a seguir em um sentido.", "coracao"),
  pergunta("cor-pulmoes", "coracao", 200, "Do coração, o sangue vai aos pulmões para...", "Receber oxigênio", ["Virar urina", "Produzir bile", "Formar ossos"], "Nos pulmões, o sangue recebe oxigênio.", "coracao"),
  pergunta("cor-arterias", "coracao", 200, "As artérias levam o sangue...", "Para fora do coração", ["Só para os rins", "Só para o cérebro", "Sempre sem oxigênio"], "Artérias conduzem sangue para fora do coração.", "coracao"),
  pergunta("cor-veias", "coracao", 200, "As veias conduzem o sangue...", "De volta ao coração", ["Para fora do coração", "Só para os pulmões", "Sempre sem oxigênio"], "Veias trazem o sangue de volta ao coração.", "coracao"),
  pergunta("rim-filtro", "rim", 100, "O rim ajuda a retirar resíduos de onde?", "Do sangue", ["Do ar inspirado", "Dos alimentos na boca", "Da pele apenas"], "Os rins filtram o sangue e formam a urina.", "rim"),
  pergunta("rim-produto", "rim", 100, "Qual líquido é produzido pelos rins?", "Urina", ["Bile", "Saliva", "Suco gástrico"], "A urina leva resíduos e água em excesso para fora.", "rim"),
  pergunta("rim-equilibrio", "rim", 200, "Além de filtrar, os rins equilibram...", "Água e sais", ["Sons e imagens", "Bile e saliva", "Luz e temperatura"], "Os rins ajustam a quantidade de água e sais no sangue.", "rim"),
  pergunta("rim-ureter", "rim", 200, "A urina sai dos rins e segue para...", "A bexiga", ["O estômago", "O coração", "Os pulmões"], "Os ureteres levam a urina dos rins à bexiga.", "rim"),
  pergunta("rim-reabsorve", "rim", 200, "Durante a filtragem, os rins...", "Recuperam o que é útil", ["Descartam todo o sangue", "Produzem ar", "Transformam sais em bile"], "Parte da água e das substâncias úteis retorna ao sangue.", "rim"),
  pergunta("rim-nefron", "rim", 200, "As pequenas unidades de filtro do rim são...", "Néfrons", ["Neurônios", "Alvéolos", "Válvulas"], "O néfron filtra e ajusta o líquido que formará a urina.", "rim"),
  pergunta("fig-bile", "figado", 100, "O fígado produz qual líquido digestivo?", "Bile", ["Urina", "Saliva", "Lágrimas"], "A bile produzida pelo fígado ajuda na digestão.", "digestao"),
  pergunta("fig-sistema", "figado", 100, "O fígado participa de qual processo?", "Digestão", ["Formação da voz", "Entrada de ar", "Percepção de luz"], "O fígado participa da digestão e processa nutrientes.", "digestao"),
  pergunta("fig-gorduras", "figado", 200, "A bile ajuda principalmente a digerir...", "Gorduras", ["Oxigênio", "Água", "Sais minerais"], "A bile auxilia a digestão das gorduras.", "digestao"),
  pergunta("fig-reserva", "figado", 200, "Onde a bile pode ficar armazenada?", "Na vesícula biliar", ["Na bexiga", "Nos pulmões", "No esôfago"], "A vesícula armazena bile; quem a produz é o fígado.", "digestao"),
  pergunta("dig-funcao", "estomago", 100, "O sistema digestório aproveita dos alimentos...", "Nutrientes", ["Sons", "Impulsos elétricos", "Ar dos pulmões"], "A digestão permite aproveitar os nutrientes da comida.", "digestao"),
  pergunta("dig-inicio", "estomago", 100, "Onde começa a digestão?", "Na boca", ["No rim", "No intestino grosso", "Na bexiga"], "Mastigação e saliva iniciam a digestão na boca.", "digestao"),
  pergunta("dig-absorcao", "estomago", 200, "A maior parte dos nutrientes é absorvida no...", "Intestino delgado", ["Esôfago", "Intestino grosso", "Estômago"], "O intestino delgado absorve a maior parte dos nutrientes.", "digestao"),
  pergunta("dig-movimento", "estomago", 200, "O alimento avança pelo tubo digestivo graças a...", "Contrações musculares", ["Batidas do coração", "Movimentos dos ossos", "Vibração da voz"], "Contrações em sequência empurram o alimento: peristaltismo.", "digestao"),
  pergunta("cer-funcao", "cerebro", 100, "O cérebro participa diretamente de...", "Pensar e aprender", ["Produzir bile", "Filtrar sangue", "Produzir urina"], "Redes de neurônios participam do pensamento e da aprendizagem.", "cerebro"),
  pergunta("cer-celula", "cerebro", 100, "Qual célula transmite sinais no sistema nervoso?", "Neurônio", ["Hemácia", "Plaqueta", "Célula muscular"], "Neurônios recebem e transmitem informações.", "cerebro"),
  pergunta("cer-sentidos", "cerebro", 200, "Para perceber uma imagem, o cérebro...", "Interpreta sinais dos olhos", ["Produz luz nos olhos", "Envia bile aos olhos", "Filtra o ar"], "O cérebro interpreta os sinais visuais recebidos.", "cerebro"),
  pergunta("cer-movimento", "cerebro", 200, "Ao decidir mover a mão, o cérebro envia...", "Sinais aos músculos", ["Bile para os dedos", "Ar para os ossos", "Urina para a pele"], "Sinais nervosos participam do controle dos movimentos.", "cerebro"),
  pergunta("cer-dobras", "cerebro", 200, "As dobras do córtex cerebral aumentam...", "A área da superfície", ["O volume de sangue total", "O tamanho dos olhos", "A quantidade de bile"], "As dobras permitem acomodar mais superfície no crânio.", "cerebro"),
  pergunta("cer-mensagens", "cerebro", 200, "Neurônios se comunicam com sinais...", "Elétricos e químicos", ["Apenas sonoros", "Apenas luminosos", "Apenas térmicos"], "A comunicação nervosa envolve sinais elétricos e químicos.", "cerebro"),
  pergunta("lar-voz", "larynx", 100, "A laringe participa da produção de...", "Voz", ["Urina", "Bile", "Saliva"], "As pregas vocais da laringe vibram para produzir som.", "voz"),
  pergunta("lar-ar", "larynx", 100, "O ar usado para produzir a voz vem...", "Dos pulmões", ["Do estômago", "Dos rins", "Do fígado"], "O ar que sai dos pulmões faz as pregas vocais vibrarem.", "voz"),
  pergunta("lar-vibra", "larynx", 200, "O que vibra na laringe para formar a voz?", "Pregas vocais", ["Dentes", "Lábios", "Costelas"], "As pregas vocais vibram com a passagem do ar.", "voz"),
  pergunta("lar-respira", "larynx", 200, "Ao respirar sem falar, as pregas vocais ficam...", "Afastadas", ["Sempre fechadas", "Sem receber sangue", "Rígidas como ossos"], "Afastadas, as pregas deixam o ar passar para respirar.", "voz"),
];

export const MODELOS_DUELO = [
  { id: "coracao", nome: "Coração", caminho: "/models/healthy/coracao.glb" },
  { id: "figado", nome: "Fígado", caminho: "/models/healthy/figado.glb" },
  { id: "cerebro", nome: "Cérebro", caminho: "/models/healthy/cerebro.glb" },
  { id: "rim", nome: "Rim", caminho: "/models/healthy/rim.glb" },
  // O arquivo contém o trato inteiro, não só o estômago.
  { id: "estomago", nome: "Sistema digestório", caminho: "/models/healthy/estomago.glb" },
  { id: "larynx", nome: "Laringe", caminho: "/models/organs/larynx.glb" },
] as const;

function embaralhar<T>(itens: readonly T[], random: () => number) {
  const lista = [...itens];
  for (let i = lista.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [lista[i], lista[j]] = [lista[j], lista[i]];
  }
  return lista;
}

/** Duas identificações, cinco questões acessíveis e um desafio de estrutura real. */
export function montarRodadasDuelo(
  estruturas: { label: string; position: [number, number, number] }[],
  recentes: string[] = [], random: () => number = Math.random,
): RodadaOnline[] {
  const resultado: RodadaOnline[] = [];
  const usadas = new Set<string>();
  const identificacoes = embaralhar(MODELOS_DUELO.filter((m) => m.id !== "larynx"), random);
  const unicas = [...new Map(estruturas.map((e) => [e.label, e])).values()];
  for (let i = 0; i < 8; i++) {
    const pontos = i % 2 ? 200 : 100;
    if (i === 0 || i === 4) {
      const modelo = identificacoes[i === 0 ? 0 : 1];
      resultado.push({ tipo: "orgao", pontos: 100, alvo: modelo.nome, modelo: modelo.caminho,
        opcoes: embaralhar([modelo.nome, ...embaralhar(MODELOS_DUELO.filter((m) => m.id !== modelo.id).map((m) => m.nome), random).slice(0, 3)], random),
        pergunta: modelo.id === "estomago" ? "Qual sistema é este?" : "Qual órgão é este?" });
      continue;
    }
    if (i === 7 && unicas.length >= 4) {
      const alvo = embaralhar(unicas, random)[0];
      resultado.push({ tipo: "estrutura", pontos: 200, alvo: alvo.label, marcador: alvo.position,
        opcoes: embaralhar([alvo.label, ...embaralhar(unicas.filter((e) => e.label !== alvo.label).map((e) => e.label), random).slice(0, 3)], random) });
      continue;
    }
    const anterior = resultado.at(-1)?.modelo;
    const candidatas = embaralhar(PERGUNTAS_DUELO.filter((p) => p.pontos === pontos && !usadas.has(p.id)), random);
    // Primeiro evita repetir perguntas recentes, depois evita repetir o órgão vizinho.
    candidatas.sort((a, b) => Number(recentes.includes(a.id)) - Number(recentes.includes(b.id)) ||
      Number(MODELOS_DUELO.find((m) => m.id === a.organId)?.caminho === anterior) - Number(MODELOS_DUELO.find((m) => m.id === b.organId)?.caminho === anterior));
    const p = candidatas[0];
    usadas.add(p.id);
    resultado.push({ tipo: "conhecimento", pontos, alvo: p.resposta,
      modelo: MODELOS_DUELO.find((m) => m.id === p.organId)!.caminho,
      perguntaId: p.id, pergunta: p.pergunta, explicacao: p.explicacao,
      opcoes: embaralhar([p.resposta, ...p.distratores], random) });
  }
  return resultado;
}

/** O servidor não aceita uma pergunta de conhecimento com gabarito adulterado. */
export function conhecimentoValido(r: RodadaOnline) {
  const p = PERGUNTAS_DUELO.find((p) => p.id === r.perguntaId);
  return Boolean(p && r.pontos === p.pontos && r.alvo === p.resposta && r.pergunta === p.pergunta &&
    r.explicacao === p.explicacao && r.modelo === MODELOS_DUELO.find((m) => m.id === p.organId)?.caminho &&
    r.opcoes.length === 4 && new Set(r.opcoes).size === 4 && r.opcoes.every((o) => [p.resposta, ...p.distratores].includes(o)));
}
