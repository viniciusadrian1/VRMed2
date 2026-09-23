import layout from "./escola-layout.json" with { type: "json" };
import type { EstadoArena } from "./duelo-apresentacao.ts";

/** O acervo ósseo mantém 158.090 triângulos: não disputar GPU com a rodada. */
export function mostrarEsqueleto3D(fase: string, solicitado: boolean) {
  return solicitado && (fase === "menu" || fase === "fim");
}

export const ESCOLA = {
  ...layout,
  lousaX: 0.36,
  lousaZ: -1.06,
  larguraOpcao: 1.1,
  alturaOpcao: 0.094,
  passoOpcao: 0.115,
} as const;

/** Os dois postos compartilham as mesmas medidas com o gerador do cenário. */
export function posicaoCompetidorEscola(lado: "jogador" | "adversario"): [number, number, number] {
  return [lado === "jogador" ? ESCOLA.jogadorX : ESCOLA.adversarioX, ESCOLA.piso, ESCOLA.postoZ];
}

/** Os modelos olham para +Z; o adversário se orienta para o centro da lousa. */
export const ROTACAO_ADVERSARIO_ESCOLA = Math.atan2(ESCOLA.lousaX - ESCOLA.adversarioX, ESCOLA.lousaZ - ESCOLA.postoZ);

/** Orientação visual somente: não aciona respostas, timers ou navegação XR. */
export function orientacaoDaEscola(estado: EstadoArena) {
  switch (estado.fase) {
    case "codigo": return "Digite o código na lousa";
    case "sala": return "Aguarde o adversário";
    case "contagem": return "Prepare-se · acompanhe a contagem";
    case "rodada":
      if (estado.erro) return "Aguarde para tentar novamente";
      return estado.tempo <= 5 ? "Últimos segundos · escolha na lousa" : "Observe o órgão · responda na lousa";
    case "feedback": return "Confira a resposta destacada";
    case "fim": return "Seu resultado está na lousa";
    case "encerrada": return "Partida encerrada · veja a lousa";
    default: return "Escolha seu desafio na lousa";
  }
}
