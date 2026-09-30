import layout from "./sala-estudos-layout.json" with { type: "json" };

export const MODOS_ESTUDO = [
  { rotulo: "Estudo 3D", detalhe: "Explore a anatomia", href: "/viewer" },
  { rotulo: "Comparar", detalhe: "Observe as diferenças", href: "/compare" },
  { rotulo: "Quiz", detalhe: "Teste o que aprendeu", href: "/quiz" },
  { rotulo: "Clínica", detalhe: "Investigue um caso", href: "/clinica" },
  { rotulo: "Arena VR", detalhe: "Desafio individual", href: "/arena" },
  { rotulo: "Duelo 1×1", detalhe: "Aprenda competindo", href: "/duelo" },
] as const;

/** Mesmas medidas usadas pelo Blender, pela interface e pelos testes de mira. */
export const TELA_ESTUDO = layout.tela;
export const BOTAO_ESTUDO = layout.botao;
export function posicaoModoEstudo(indice: number): [number, number, number] {
  return [indice % 2 === 0 ? -BOTAO_ESTUDO.coluna : BOTAO_ESTUDO.coluna,
    BOTAO_ESTUDO.primeiraLinha - Math.floor(indice / 2) * BOTAO_ESTUDO.linha, .002];
}
