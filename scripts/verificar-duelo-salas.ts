/**
 * Joga partidas inteiras do duelo online com relógio falso, sem rede.
 * Reprova se alguma regra de `lib/duelo-salas.ts` quebrar.
 *
 * Rodar: npm run verify:duelo (Node 22+)
 */
import assert from "node:assert/strict";
import {
  CONTAGEM_MS,
  FEEDBACK_MS,
  JANELA_DECISAO_MS,
  RODADA_MS,
  ABANDONO_MS,
  SALA_ESPERA_ORFA_MS,
  avancar,
  descartavel,
  conectar,
  criarSala,
  desconectar,
  entrar,
  gerarCodigo,
  pedirRevanche,
  proximoPrazo,
  responder,
  sair,
  visao,
  type RodadaOnline,
} from "../lib/duelo-salas.ts";

const rodadas: RodadaOnline[] = Array.from({ length: 8 }, (_, i) => ({
  tipo: i % 2 ? "estrutura" : "orgao",
  pontos: i % 2 ? 200 : 100,
  alvo: `alvo${i}`,
  opcoes: [`alvo${i}`, "x", "y", "z"],
}));

/** Avança o relógio falso até o próximo prazo, como faria o setTimeout. */
function passar(sala: ReturnType<typeof criarSala>, relogio: { t: number }) {
  const p = proximoPrazo(sala);
  assert.ok(p !== null, "havia prazo");
  relogio.t = Math.max(relogio.t, p);
  avancar(sala, relogio.t);
}

// ---- pareamento e contagem
const relogio = { t: 1000 };
const sala = criarSala("4821", "ana", rodadas, relogio.t);
conectar(sala, "ana", relogio.t);
assert.equal(visao(sala, "ana", relogio.t).fase, "aguardando");
assert.equal(entrar(sala, "bia", relogio.t), "ok");
conectar(sala, "bia", relogio.t);
assert.equal(entrar(sala, "caio", relogio.t), "cheia");
assert.equal(sala.fase, "contagem");
assert.equal(visao(sala, "bia", relogio.t).restanteMs, CONTAGEM_MS);
passar(sala, relogio);
assert.equal(sala.fase, "rodada");
assert.equal(sala.indice, 0);

// ---- acerto quase simultâneo: chega primeiro quem reagiu DEPOIS
relogio.t += 3000;
assert.equal(responder(sala, "ana", 0, "x", 2500, relogio.t), "errado");
assert.equal(responder(sala, "ana", 0, "alvo0", 2900, relogio.t), "certo");
relogio.t += 200; // o clique da bia foi antes, mas a rede dela é mais lenta
assert.equal(responder(sala, "bia", 0, "alvo0", 2400, relogio.t), "certo");
passar(sala, relogio); // fecha a janela
assert.equal(sala.fase, "feedback");
const vAna = visao(sala, "ana", relogio.t);
assert.equal(vAna.outro?.pontos, 100, "bia reagiu mais rápido e leva");
assert.equal(vAna.eu.pontos, 0);
assert.equal(vAna.ultimo?.tipo === "ponto" && vAna.ultimo.quem, "outro");

// ---- acerto depois que a janela fechou não vale
assert.equal(responder(sala, "ana", 0, "alvo0", 100, relogio.t), "tarde");

// ---- tempo de reação não pode ser menor que zero nem maior que o decorrido
passar(sala, relogio); // feedback → rodada 1
assert.equal(sala.indice, 1);
relogio.t += 1000;
responder(sala, "ana", 1, "alvo1", -5000, relogio.t);
relogio.t += 100;
responder(sala, "bia", 1, "alvo1", 999_999, relogio.t);
assert.equal(sala.candidatos[1].reacaoMs, 1100, "limitado ao que o servidor viu passar");
passar(sala, relogio);
assert.equal(visao(sala, "ana", relogio.t).eu.pontos, 200);

// ---- resposta de rodada antiga é descartada
passar(sala, relogio); // → rodada 2
assert.equal(responder(sala, "ana", 1, "alvo1", 500, relogio.t), "tarde");

// ---- rodada sem acerto esgota o tempo
const inicio2 = relogio.t;
passar(sala, relogio);
assert.equal(relogio.t - inicio2, RODADA_MS);
assert.equal(sala.fase, "feedback");
assert.equal(sala.ultimo?.tipo, "tempo");

// ---- o resto da partida sem ninguém responder termina em "fim"
while (sala.fase !== "fim") passar(sala, relogio);
assert.equal(sala.indice, 7);
assert.equal(proximoPrazo(sala), null);

// ---- revanche só com os dois; quem pede primeiro manda as rodadas
const outras = rodadas.map((r) => ({ ...r, alvo: r.alvo + "b", opcoes: [r.alvo + "b", "x", "y", "z"] }));
pedirRevanche(sala, "bia", outras, relogio.t);
assert.equal(sala.fase, "fim");
assert.equal(visao(sala, "ana", relogio.t).outro?.querRevanche, true);
pedirRevanche(sala, "ana", rodadas, relogio.t);
assert.equal(sala.fase, "contagem");
assert.equal(sala.rodadas[0].alvo, "alvo0b");
assert.equal(sala.partida, 2);
assert.equal(visao(sala, "ana", relogio.t).eu.pontos, 0);

// ---- abandono: desconectado por mais que o limite encerra
passar(sala, relogio); // → rodada
desconectar(sala, "bia", relogio.t);
const limite = relogio.t + ABANDONO_MS;
while (sala.fase !== "encerrada") passar(sala, relogio);
assert.ok(relogio.t <= limite, "encerrou no prazo de abandono");
assert.equal(visao(sala, "ana", relogio.t).saiu, "outro");

// ---- reconectar antes do limite não encerra
const s2 = criarSala("1111", "a", rodadas, 0);
entrar(s2, "b", 0);
conectar(s2, "a", 0);
conectar(s2, "b", 0);
desconectar(s2, "b", 1000);
conectar(s2, "b", 1000 + ABANDONO_MS - 1);
avancar(s2, 1000 + ABANDONO_MS + CONTAGEM_MS + FEEDBACK_MS);
assert.notEqual(s2.fase, "encerrada");

// ---- sair encerra na hora
sair(s2, "a", 5000);
assert.equal(s2.fase, "encerrada");
assert.equal(visao(s2, "b", 5000).saiu, "outro");
assert.equal(entrar(s2, "c", 5000), "encerrada");

// ---- janela de decisão fecha mesmo se o prazo da rodada passar no meio
const s3 = criarSala("2222", "a", rodadas, 0);
entrar(s3, "b", 0);
avancar(s3, CONTAGEM_MS);
const fimRodada = CONTAGEM_MS + RODADA_MS;
responder(s3, "a", 0, "alvo0", 17_900, fimRodada - 100);
assert.equal(responder(s3, "b", 0, "alvo0", 17_950, fimRodada + 100), "certo");
avancar(s3, fimRodada - 100 + JANELA_DECISAO_MS);
assert.equal(s3.jogadores[0].pontos, 100);

// ---- quem entra e nunca conecta cai no abandono
const s4 = criarSala("3333", "a", rodadas, 0);
conectar(s4, "a", 0);
entrar(s4, "fantasma", 1000);
while (s4.fase !== "encerrada" && s4.fase !== "fim") {
  const p = proximoPrazo(s4);
  assert.ok(p !== null);
  avancar(s4, p);
}
assert.equal(s4.fase, "encerrada", "fantasma não prende a partida");
assert.equal(visao(s4, "a", 99_999).saiu, "outro");

// ---- queda na tela de espera não encerra a partida quando ela começa
const s5 = criarSala("4444", "a", rodadas, 0);
conectar(s5, "a", 0);
desconectar(s5, "a", 1000);
entrar(s5, "b", 61_000);
conectar(s5, "b", 61_000);
avancar(s5, 61_005);
assert.equal(s5.fase, "contagem", "a queda antiga não vale como abandono");
conectar(s5, "a", 62_000);
avancar(s5, 61_000 + ABANDONO_MS + 1);
assert.notEqual(s5.fase, "encerrada");

// ---- sala esperando sem ninguém ouvindo some antes das outras
const s6 = criarSala("5555", "a", rodadas, 0);
assert.equal(descartavel(s6, 1, SALA_ESPERA_ORFA_MS), false, "com ouvinte fica");
assert.equal(descartavel(s6, 0, SALA_ESPERA_ORFA_MS - 1), false);
assert.equal(descartavel(s6, 0, SALA_ESPERA_ORFA_MS), true);

// ---- códigos
assert.match(gerarCodigo(new Set()), /^\d{4}$/);
assert.equal(gerarCodigo(new Set(["1000"]), (() => { let n = 0; return () => (n++ === 0 ? 0 : 0.5); })()), "5500");

console.log("ok: duelo online — pareamento, janela de acertos, reação, tempo, revanche, abandono, saída");
