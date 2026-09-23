/** Estado exclusivamente visual: não arbitra respostas nem calcula pontuação. */
export interface EstadoArena {
  fase: string;
  resultado: "voce" | "adversario" | "tempo" | null;
  erro: boolean;
  tempo: number;
  rodada: number;
  combo: number;
  meus: number;
  outros: number;
}

export const ARENA_INICIAL: EstadoArena = {
  fase: "menu", resultado: null, erro: false, tempo: 18,
  rodada: 1, combo: 0, meus: 0, outros: 0,
};

export function sinalDaArena(estado: EstadoArena) {
  if (estado.fase === "fim") {
    if (estado.meus > estado.outros) return { cor: "#f5c781", rotulo: "VITÓRIA · BOM TRABALHO", pulso: false };
    if (estado.meus === estado.outros) return { cor: "#83c9e4", rotulo: "EMPATE · SIGA PRATICANDO", pulso: false };
    return { cor: "#83b6da", rotulo: "REVISAR E TENTAR DE NOVO", pulso: false };
  }
  if (estado.erro) return { cor: "#ed8a7b", rotulo: "REVISE SUA ESCOLHA", pulso: false };
  if (estado.fase === "feedback") {
    if (estado.resultado === "voce") return { cor: "#71e0b2", rotulo: "RESPOSTA CORRETA", pulso: true };
    if (estado.resultado === "adversario") return { cor: "#ed8a7b", rotulo: "OBSERVE A RESPOSTA", pulso: false };
    return { cor: "#f2be6b", rotulo: "TEMPO ESGOTADO · REVISE", pulso: false };
  }
  if (estado.fase === "rodada" && estado.tempo <= 5) return { cor: "#f2be6b", rotulo: "ÚLTIMOS SEGUNDOS", pulso: true };
  if (estado.fase === "contagem") return { cor: "#bce6f2", rotulo: "PREPARE-SE", pulso: false };
  if (estado.fase === "rodada") return { cor: "#77cfe3", rotulo: `RODADA ${estado.rodada} · IDENTIFIQUE`, pulso: false };
  return { cor: "#77cfe3", rotulo: "ARENA DE TREINAMENTO", pulso: false };
}
