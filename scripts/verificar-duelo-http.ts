import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { montarRodadasDuelo } from "../lib/duelo-perguntas.ts";
import { VERSAO_PROTOCOLO, type VisaoSala } from "../lib/duelo-salas.ts";

// Teste opt-in, somente no servidor local. Cria e encerra a própria sala.
const origem = new URL(process.argv[2] ?? "http://127.0.0.1:3002");
assert.ok(["localhost", "127.0.0.1", "[::1]"].includes(origem.hostname), "use somente localhost");
const endpoint = new URL("/api/duelo", origem);
const jogadores = [randomUUID(), randomUUID()];
const rodadas = montarRodadasDuelo([]);
const limite = AbortSignal.timeout(25_000);
const streams = new AbortController();
let codigo = "";

async function post(corpo: object, status = 200) {
  const resposta = await fetch(endpoint, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ v: VERSAO_PROTOCOLO, ...corpo }), signal: AbortSignal.timeout(5_000),
  });
  assert.equal(resposta.status, status, `status HTTP esperado: ${status}`);
  return resposta.json();
}

async function* visoes(jogador: string) {
  const url = new URL(endpoint);
  url.searchParams.set("sala", codigo); url.searchParams.set("jogador", jogador);
  const resposta = await fetch(url, { signal: AbortSignal.any([streams.signal, limite]) });
  assert.equal(resposta.status, 200);
  assert.ok(resposta.headers.get("content-type")?.includes("text/event-stream"));
  const leitor = resposta.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await leitor.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let fim: number;
      while ((fim = buffer.indexOf("\n\n")) >= 0) {
        const bloco = buffer.slice(0, fim); buffer = buffer.slice(fim + 2);
        for (const linha of bloco.split("\n")) {
          if (linha.startsWith("data: ")) yield JSON.parse(linha.slice(6)) as VisaoSala;
        }
      }
    }
  } finally { await leitor.cancel().catch(() => {}); leitor.releaseLock(); }
}

async function ate(fluxo: AsyncGenerator<VisaoSala>, fase: string, indice: number) {
  while (true) {
    const { done, value } = await fluxo.next();
    assert.ok(!done, "SSE não pode terminar durante a partida");
    if (value.fase === fase && value.indice === indice) return value;
  }
}

try {
  await post({ v: 1, acao: "criar", jogador: jogadores[0], rodadas }, 409);
  const adulteradas = structuredClone(rodadas);
  adulteradas[1].alvo = adulteradas[1].opcoes.find((o) => o !== adulteradas[1].alvo)!;
  await post({ acao: "criar", jogador: jogadores[0], rodadas: adulteradas }, 400);
  codigo = (await post({ acao: "criar", jogador: jogadores[0], rodadas })).sala;
  await post({ acao: "entrar", sala: codigo, jogador: jogadores[1] });
  const fluxos = jogadores.map(visoes);
  for (const indice of [0, 1]) {
    const [a, b] = await Promise.all(fluxos.map((f) => ate(f, "rodada", indice)));
    assert.equal(a.v, VERSAO_PROTOCOLO);
    assert.deepEqual(a.rodadas, b.rodadas, "os dois recebem perguntas e ordem idênticas");
    assert.deepEqual(a.rodadas, rodadas);
    const resposta = await post({ acao: "responder", sala: codigo, jogador: jogadores[0], indice, opcao: rodadas[indice].alvo, reacaoMs: 600 });
    assert.equal(resposta.resultado, "certo");
    const feedback = await Promise.all(fluxos.map((f) => ate(f, "feedback", indice)));
    const pontos = indice === 0 ? 100 : 300;
    assert.equal(feedback[0].eu.pontos, pontos);
    assert.equal(feedback[1].outro?.pontos, pontos);
    assert.equal(feedback[1].eu.pontos, 0);
  }
  console.log("ok: HTTP + SSE com dois clientes, identificação e conhecimento, placar compartilhado, versão antiga e adulteração recusadas");
} finally {
  if (codigo) await post({ acao: "sair", sala: codigo, jogador: jogadores[0] });
  streams.abort();
}
