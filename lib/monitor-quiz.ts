import { QUIZ_TIME_PER_QUESTION } from "./quiz.ts";
import type { QuizAnswer, QuizQuestion, Vec3 } from "@/types";
import type { VistaMonitor } from "./monitor-comparacao.ts";

export type PartidaMonitor = {
  questoes: QuizQuestion[]; respostas: QuizAnswer[]; indice: number;
  restante: number; concluida: boolean;
};
export type AcaoQuizMonitor =
  | { tipo: "responder"; questao: string; opcao: string }
  | { tipo: "tempo"; questao: string }
  | { tipo: "proxima"; questao: string };

export function iniciarQuizMonitor(questoes: QuizQuestion[]): PartidaMonitor {
  return { questoes, respostas: [], indice: 0, restante: QUIZ_TIME_PER_QUESTION, concluida: false };
}

/** O identificador impede dois controles, timeout ou clique antigo de responder outra questão. */
export function reduzirQuizMonitor(estado: PartidaMonitor, acao: AcaoQuizMonitor): PartidaMonitor {
  const atual = estado.questoes[estado.indice];
  if (!atual || estado.concluida || atual.id !== acao.questao) return estado;
  const respondida = estado.respostas.some((r) => r.questionId === atual.id);
  if (acao.tipo === "proxima") {
    if (!respondida) return estado;
    return estado.indice + 1 === estado.questoes.length
      ? { ...estado, concluida: true }
      : { ...estado, indice: estado.indice + 1, restante: QUIZ_TIME_PER_QUESTION };
  }
  if (respondida) return estado;
  if (acao.tipo === "tempo" && estado.restante > 1) return { ...estado, restante: estado.restante - 1 };
  if (acao.tipo === "responder" && !atual.options.includes(acao.opcao)) return estado;
  const selected = acao.tipo === "tempo" ? "" : acao.opcao;
  return { ...estado, restante: acao.tipo === "tempo" ? 0 : estado.restante,
    respostas: [...estado.respostas, { questionId: atual.id, selected, correct: selected === atual.correctAnswer }] };
}

/** A posição é a mesma anotação normalizada usada no visualizador, sem inventar estruturas. */
export function vistaParaPonto(ponto: Vec3): VistaMonitor {
  return { horizontal: -Math.atan2(ponto[0], ponto[2]),
    // Não olhar pelo eixo de um órgão comprido: preserva a silhueta anatômica.
    vertical: Math.max(-.6, Math.min(.6, Math.atan2(ponto[1], Math.hypot(ponto[0], ponto[2])))), zoom: 1 };
}

// Nunca abre o modelo de miologia proibido no Quest, mesmo entrando no VR após o quiz.
export function modeloPermitidoNoMonitor(id: string) { return id !== "myology"; }

export function paginasTextoMonitor(texto: string, limite = 110): string[] {
  const paginas: string[] = [];
  let restante = texto.trim();
  while (restante.length > limite) {
    const espaco = restante.lastIndexOf(" ", limite);
    const corte = espaco > limite / 2 ? espaco : limite;
    paginas.push(restante.slice(0, corte)); restante = restante.slice(corte).trimStart();
  }
  return [...paginas, restante];
}

/** Layout compartilhado pelos botões e testes de mira do Quiz. */
export const ALTERNATIVAS_MONITOR = Array.from({ length: 4 }, (_, i) => ({
  x: .244, y: .108 - i * .077, w: .468, h: .068,
}));
