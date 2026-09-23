import layout from "./escola-layout.json" with { type: "json" };

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
