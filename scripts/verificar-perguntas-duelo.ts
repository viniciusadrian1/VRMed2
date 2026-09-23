import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { PERGUNTAS_DUELO, MODELOS_DUELO, FONTES_DUELO, montarRodadasDuelo } from "../lib/duelo-perguntas.ts";
import { rodadasSchema } from "../lib/duelo-schema.ts";
import { criarSala, entrar, avancar, responder, visao, CONTAGEM_MS, JANELA_DECISAO_MS } from "../lib/duelo-salas.ts";

assert.equal(PERGUNTAS_DUELO.length, 30);
assert.equal(new Set(PERGUNTAS_DUELO.map((p) => p.id)).size, 30);
for (const m of MODELOS_DUELO) assert.ok(existsSync(`public${m.caminho}`));
for (const p of PERGUNTAS_DUELO) {
  assert.ok(p.pergunta.length <= 65, `${p.id}: enunciado curto no VR`);
  assert.ok(p.explicacao.length <= 90);
  assert.equal(new Set([p.resposta, ...p.distratores]).size, 4);
  assert.ok([p.resposta, ...p.distratores].every((o) => o.length <= 27), p.id);
  assert.ok(FONTES_DUELO[p.fonte]);
  assert.ok(MODELOS_DUELO.some((m) => m.id === p.organId));
}
const estruturas = ["Epiglote", "Traqueia", "Cartilagem tireóidea", "Osso hioide", "Epiglote"].map((label) => ({ label, position: [0, 0, 0] as [number, number, number] }));
let semente = 12345;
const random = () => { semente = (1664525 * semente + 1013904223) >>> 0; return semente / 2 ** 32; };
let recentes: string[] = [];
const vistas = new Set<string>();
for (let i = 0; i < 1000; i++) {
  const lista = montarRodadasDuelo(estruturas, recentes, random);
  assert.ok(rodadasSchema.safeParse(lista).success);
  assert.equal(lista.reduce((s, r) => s + r.pontos, 0), 1200);
  assert.equal(lista.filter((r) => r.tipo === "conhecimento").length, 5);
  assert.equal(lista.filter((r) => r.tipo === "estrutura").length, 1);
  const ids = lista.flatMap((r) => r.perguntaId ? [r.perguntaId] : []);
  assert.equal(new Set(ids).size, 5);
  if (i > 0) assert.ok(ids.every((id) => !recentes.slice(-5).includes(id)), "revanche não repete as cinco perguntas anteriores");
  ids.forEach((id) => vistas.add(id));
  recentes = [...recentes, ...ids].slice(-20);
}
assert.equal(vistas.size, 30, "todas as perguntas entram no sorteio");
assert.ok(rodadasSchema.safeParse(montarRodadasDuelo([], [], random)).success, "fallback sem estruturas tem oito rodadas válidas");
const rodadas = montarRodadasDuelo(estruturas, [], random);
const adulteradas = structuredClone(rodadas);
adulteradas[1].alvo = adulteradas[1].opcoes.find((o) => o !== adulteradas[1].alvo)!;
assert.equal(rodadasSchema.safeParse(adulteradas).success, false);
const sala = criarSala("9123", "ana", rodadas, 0);
entrar(sala, "bia", 0); avancar(sala, CONTAGEM_MS);
responder(sala, "ana", 0, rodadas[0].alvo, 1000, CONTAGEM_MS + 1000);
avancar(sala, CONTAGEM_MS + 1000 + JANELA_DECISAO_MS);
assert.equal(visao(sala, "ana", CONTAGEM_MS + 2000).eu.pontos, 100);
assert.deepEqual(visao(sala, "ana", 0).rodadas, visao(sala, "bia", 0).rodadas);
console.log("ok: 30 perguntas, fontes, textos VR, 1000 sorteios, variedade, gabaritos e compartilhamento online");
