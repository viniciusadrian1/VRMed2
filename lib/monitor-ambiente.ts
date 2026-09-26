import { sinalDaArena, type EstadoArena } from "./duelo-apresentacao.ts";

/** Monitor cenográfico comunica a partida, nunca sinais fisiológicos fictícios. */
export function monitorDoAmbiente(estado: EstadoArena) {
  const sinal = sinalDaArena(estado);
  let texto = "Em espera";
  if (estado.fase === "contagem") texto = "Prepare-se";
  if (estado.fase === "rodada") texto = estado.tempo <= 5 ? "Tempo final" : `Rodada ${estado.rodada}`;
  if (estado.combo > 1 && estado.fase === "rodada" && estado.tempo > 5) texto = `Sequência ×${estado.combo}`;
  if (estado.fase === "feedback") texto = estado.resultado === "voce" ? "Acerto" : "Revisar";
  if (estado.erro) texto = "Revisar";
  if (estado.fase === "fim") texto = estado.meus > estado.outros ? "Vitória" : estado.meus === estado.outros ? "Empate" : "Revisar";
  if (estado.fase === "encerrada") texto = "Encerrado";
  return { texto, cor: sinal.cor };
}
