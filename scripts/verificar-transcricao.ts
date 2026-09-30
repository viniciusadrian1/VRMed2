import assert from "node:assert/strict";
import { test, mock } from "node:test";
import { readFileSync } from "node:fs";
import { criarHandlerTranscricao } from "../lib/transcricao-servidor.ts";
import { criarDitadoTutor } from "../lib/ditado-tutor.ts";
import { anexarDitado, AUDIO_MAX_BYTES, formatoAudio, paginasDitado, TRANSCRICAO_MAX_CARACTERES } from "../lib/transcricao.ts";
import { contextoTranscricao } from "../lib/transcricao-contexto.ts";

// Somente dados e adaptadores sintéticos: não captura microfone nem chama a OpenAI.
const tick = async () => { for (let i = 0; i < 10; i++) await Promise.resolve(); };
function adiado<T>() {
  let resolve!: (valor: T) => void;
  let reject!: (erro: unknown) => void;
  const promise = new Promise<T>((ok, falha) => { resolve = ok; reject = falha; });
  return { promise, resolve, reject };
}
function requisicao(opcoes: { headers?: Record<string, string>; bytes?: number; signal?: AbortSignal; body?: ReadableStream<Uint8Array>; url?: string } = {}) {
  return new Request(opcoes.url ?? "https://vrmed.test/api/transcricao", {
    method: "POST", headers: { "content-type": "audio/webm;codecs=opus", origin: "https://vrmed.test", ...opcoes.headers },
    body: opcoes.body ?? new Uint8Array(opcoes.bytes ?? 200), signal: opcoes.signal,
    ...{ duplex: "half" },
  });
}
function gravacao(opcoes: { obter?: () => Promise<MediaStream>; enviar?: (blob: Blob, sinal: AbortSignal, modelo: string | null) => Promise<string>; falhaStop?: boolean } = {}) {
  let interrompido = false, envios = 0;
  const textos: string[] = [];
  const track = { stop: () => { interrompido = true; }, onended: null as (() => void) | null };
  const stream = { getTracks: () => [track] } as unknown as MediaStream;
  const gravador = {
    mimeType: "audio/webm", state: "inactive", ondataavailable: null as ((e: { data: Blob }) => void) | null,
    onstop: null as (() => void) | null, onerror: null as (() => void) | null,
    start() { this.state = "recording"; },
    stop() {
      if (opcoes.falhaStop) throw new Error("Gravador encerrado");
      this.state = "inactive";
      queueMicrotask(() => { this.ondataavailable?.({ data: new Blob([new Uint8Array(200)], { type: "audio/webm" }) }); this.onstop?.(); });
    },
  };
  const controle = criarDitadoTutor((texto) => textos.push(texto), {
    obterMicrofone: opcoes.obter ?? (() => Promise.resolve(stream)),
    gravador: () => gravador as unknown as MediaRecorder,
    enviar: async (blob, sinal, modelo) => { envios++; assert.ok(interrompido, "captura termina antes do upload"); return opcoes.enviar ? opcoes.enviar(blob, sinal, modelo) : "Qual a função do coração?"; },
  });
  return { controle, textos, gravador, stream, track, interrompido: () => interrompido, envios: () => envios };
}

await test("API: arquivo nomeado, conteúdo e texto; resposta sem cache", async () => {
  const handler = criarHandlerTranscricao(async (arquivo, sinal) => {
    assert.equal(arquivo.name, "pergunta.webm"); assert.equal(arquivo.type, "audio/webm");
    assert.equal(arquivo.size, 200); assert.equal(sinal.aborted, false);
    return "  Qual a função do coração?  ";
  });
  const resposta = await handler(requisicao());
  assert.equal(resposta.status, 200); assert.equal(resposta.headers.get("cache-control"), "no-store");
  assert.deepEqual(await resposta.json(), { texto: "Qual a função do coração?" });
});
await test("API: vocabulário do catálogo, sem aceitar prompt ou dados livres do cliente", async () => {
  assert.match(contextoTranscricao("larynx"), /cartilagem tireóidea/);
  assert.match(contextoTranscricao("cranio"), /esfenoide/);
  assert.doesNotMatch(contextoTranscricao("rim"), /epiglote/);
  assert.equal(contextoTranscricao("INJETAR_CONTEUDO"), contextoTranscricao(null));
  assert.equal(contextoTranscricao("a".repeat(10000)), contextoTranscricao(null));
  const handler = criarHandlerTranscricao(async (_, __, contexto) => {
    assert.equal(contexto, contextoTranscricao("coracao")); return "Qual a função do miocárdio?";
  });
  assert.equal((await handler(requisicao({ headers: { "x-vrmed-modelo": "coracao", "x-prompt": "INJETAR_CONTEUDO" } }))).status, 200);
});
await test("Ditado: modelo acompanha a gravação e troca cancela respostas antigas", async () => {
  let recebido: string | null = null;
  const g = gravacao({ enviar: async (_, __, modelo) => { recebido = modelo; return "Qual a função da epiglote?"; } });
  g.controle.atualizarModelo("larynx"); await g.controle.iniciar(); g.controle.parar(); await tick();
  assert.equal(recebido, "larynx"); g.controle.cancelar();
  const tardio = adiado<string>();
  const outro = gravacao({ enviar: async () => tardio.promise });
  outro.controle.atualizarModelo("rim"); await outro.controle.iniciar(); outro.controle.parar(); await tick();
  outro.controle.atualizarModelo("coracao"); tardio.resolve("Resposta do rim"); await tick();
  assert.equal(outro.textos.length, 0); assert.equal(outro.controle.getSnapshot().fase, "pronto"); outro.controle.cancelar();
});
await test("API: origem, proxy HTTPS, MIME e limites bloqueiam antes do provedor", async () => {
  let chamadas = 0;
  const handler = criarHandlerTranscricao(async () => { chamadas++; return "Texto"; });
  assert.equal((await handler(requisicao({ headers: { origin: "https://outro.test" } }))).status, 403);
  assert.equal((await handler(requisicao({ headers: { "sec-fetch-site": "cross-site" } }))).status, 403);
  assert.equal((await handler(requisicao({ headers: { "content-type": "text/plain" } }))).status, 415);
  assert.equal((await handler(requisicao({ headers: { "content-length": String(AUDIO_MAX_BYTES + 1) } }))).status, 413);
  assert.equal((await handler(requisicao({ bytes: AUDIO_MAX_BYTES + 1 }))).status, 413);
  assert.equal((await handler(requisicao({ bytes: 0 }))).status, 400);
  assert.equal(chamadas, 0);
  assert.equal((await handler(requisicao({ url: "http://localhost:3000/api/transcricao", headers: { host: "vrmed.test", "x-forwarded-proto": "https" } }))).status, 200);
  assert.equal((await handler(requisicao({ headers: { origin: "https://invasor.test", "x-forwarded-host": "invasor.test" } }))).status, 403);
});
await test("API: valida o tamanho acumulado de upload em blocos", async () => {
  const body = new ReadableStream<Uint8Array>({ start(c) { c.enqueue(new Uint8Array(AUDIO_MAX_BYTES)); c.enqueue(new Uint8Array(1)); c.close(); } });
  const handler = criarHandlerTranscricao(async () => assert.fail("Não deve enviar"));
  assert.equal((await handler(requisicao({ body }))).status, 413);
});
await test("API: upload parado expira, libera leitor e vaga", async () => {
  let cancelados = 0;
  const handler = criarHandlerTranscricao(async () => "Texto", Date.now, 15);
  const parados = Array.from({ length: 4 }, (_, i) => handler(requisicao({ headers: { "x-forwarded-for": String(i) }, body: new ReadableStream({ cancel() { cancelados++; } }) })));
  assert.equal((await handler(requisicao())).status, 429);
  assert.deepEqual((await Promise.all(parados)).map((r) => r.status), [504, 504, 504, 504]);
  assert.equal(cancelados, 4);
  assert.equal((await handler(requisicao())).status, 200);
});
await test("API: cancelar upload ou provedor não retorna texto", async () => {
  const aborto = new AbortController(); let cancelado = false;
  const handler = criarHandlerTranscricao(async () => assert.fail("Não deve chamar"));
  const pendente = handler(requisicao({ signal: aborto.signal, body: new ReadableStream({ cancel() { cancelado = true; } }) }));
  aborto.abort(); assert.equal((await pendente).status, 499); assert.ok(cancelado);
  const fim = adiado<string>(), outro = new AbortController();
  const handler2 = criarHandlerTranscricao(async () => fim.promise);
  const resposta = handler2(requisicao({ signal: outro.signal }));
  await tick(); outro.abort(); fim.resolve("Texto tardio");
  assert.equal((await resposta).status, 499);
});
await test("API: prazo inclui o provedor e erros não vazam detalhes", async () => {
  const timeout = criarHandlerTranscricao(async (_, sinal) => new Promise((_, rejeitar) => sinal.addEventListener("abort", () => rejeitar(sinal.reason))), Date.now, 15);
  assert.equal((await timeout(requisicao())).status, 504);
  for (const [erro, status] of [[{ status: 400 }, 400], [{ status: 429 }, 429], [{ status: 429, code: "insufficient_quota" }, 503], [{ status: 401 }, 503]] as const) {
    const handler = criarHandlerTranscricao(async () => { throw { ...erro, message: "SEGREDO_SINTETICO" }; });
    const r = await handler(requisicao()); assert.equal(r.status, status); assert.doesNotMatch(await r.text(), /SEGREDO/);
  }
});
await test("API: silêncio, texto longo e limite por IP/global", async () => {
  for (const texto of ["  ", "x".repeat(TRANSCRICAO_MAX_CARACTERES + 1)]) {
    assert.equal((await criarHandlerTranscricao(async () => texto)(requisicao())).status, 422);
  }
  let tempo = 60_000;
  const handler = criarHandlerTranscricao(async () => "texto", () => tempo);
  for (let i = 0; i < 6; i++) assert.equal((await handler(requisicao())).status, 200);
  assert.equal((await handler(requisicao())).status, 429);
  tempo += 60_000; assert.equal((await handler(requisicao())).status, 200);
  const global = criarHandlerTranscricao(async () => "texto");
  for (let i = 0; i < 60; i++) assert.equal((await global(requisicao({ headers: { "x-forwarded-for": String(i) } }))).status, 200);
  assert.equal((await global(requisicao({ headers: { "x-forwarded-for": "nova-origem" } }))).status, 429);
});
await test("Ditado: grava explicitamente, para microfone e preenche uma vez", async () => {
  const g = gravacao();
  assert.equal(g.controle.getSnapshot().fase, "pronto"); assert.equal(g.envios(), 0);
  await g.controle.iniciar(); assert.equal(g.controle.getSnapshot().fase, "gravando");
  g.controle.parar(); g.controle.parar(); await tick();
  assert.equal(g.controle.getSnapshot().fase, "concluido"); assert.equal(g.envios(), 1);
  assert.deepEqual(g.textos, ["Qual a função do coração?"]); g.controle.cancelar();
});
await test("Ditado: cancelar descarta sem upload, inclusive permissão tardia", async () => {
  const g = gravacao(); await g.controle.iniciar(); g.controle.cancelar(); await tick();
  assert.ok(g.interrompido()); assert.equal(g.envios(), 0); assert.deepEqual(g.textos, []);
  const perm = adiado<MediaStream>(); const tardio = gravacao({ obter: () => perm.promise });
  const inicio = tardio.controle.iniciar(); tardio.controle.cancelar(); perm.resolve(tardio.stream); await inicio;
  assert.ok(tardio.interrompido()); assert.equal(tardio.controle.getSnapshot().fase, "pronto");
});
await test("Ditado: resposta atrasada é descartada, microfone exclusivo", async () => {
  const resposta = adiado<string>(); let sinal: AbortSignal | undefined;
  const g = gravacao({ enviar: async (_, s) => { sinal = s; return resposta.promise; } });
  const outro = gravacao(); await g.controle.iniciar(); await outro.controle.iniciar();
  assert.match(outro.controle.getSnapshot().mensagem, /outro painel/);
  g.controle.parar(); await tick(); g.controle.cancelar(); assert.ok(sinal?.aborted);
  await outro.controle.iniciar(); assert.equal(outro.controle.getSnapshot().fase, "gravando");
  resposta.resolve("Ignorar resposta tardia"); await tick(); assert.deepEqual(g.textos, []); outro.controle.cancelar();
});
await test("Ditado: permissão negada e microfone indisponível têm mensagens úteis", async () => {
  for (const [name, trecho] of [["NotAllowedError", /não autorizado/], ["NotFoundError", /Nenhum microfone/], ["NotReadableError", /ocupado/]] as const) {
    const g = gravacao({ obter: async () => { throw new DOMException("Detalhe interno", name); } });
    await g.controle.iniciar(); assert.match(g.controle.getSnapshot().mensagem, trecho); assert.equal(g.envios(), 0); g.controle.cancelar();
  }
});
await test("Ditado: falha ao parar, desconexão e excesso de bytes liberam microfone", async () => {
  const falha = gravacao({ falhaStop: true }); await falha.controle.iniciar(); falha.controle.parar();
  assert.equal(falha.controle.getSnapshot().fase, "erro"); assert.ok(falha.interrompido());
  const desconectado = gravacao(); await desconectado.controle.iniciar(); desconectado.track.onended?.();
  assert.equal(desconectado.controle.getSnapshot().fase, "erro"); assert.ok(desconectado.interrompido());
  const grande = gravacao(); await grande.controle.iniciar();
  grande.gravador.ondataavailable?.({ data: new Blob([new Uint8Array(AUDIO_MAX_BYTES + 1)]) });
  await tick(); assert.equal(grande.controle.getSnapshot().fase, "erro"); assert.equal(grande.envios(), 0); assert.ok(grande.interrompido());
});
await test("Ditado: 60s, permissão 30s e transcrição 50s são limitadas", async () => {
  mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  let agora = 0; mock.method(performance, "now", () => agora);
  try {
    const g = gravacao(); await g.controle.iniciar(); agora = 60_000; mock.timers.tick(60_000); await tick();
    assert.ok(g.interrompido()); assert.equal(g.envios(), 1); assert.equal(g.controle.getSnapshot().fase, "concluido"); g.controle.cancelar();
    const perm = adiado<MediaStream>(); const espera = gravacao({ obter: () => perm.promise });
    const iniciando = espera.controle.iniciar(); mock.timers.tick(30_000);
    assert.equal(espera.controle.getSnapshot().fase, "erro"); perm.resolve(espera.stream); await iniciando; assert.ok(espera.interrompido());
    const retorno = adiado<string>(); const lento = gravacao({ enviar: () => retorno.promise });
    await lento.controle.iniciar(); lento.controle.parar(); await tick(); mock.timers.tick(50_000);
    assert.equal(lento.controle.getSnapshot().fase, "erro"); retorno.resolve("Tardio"); await tick(); assert.deepEqual(lento.textos, []);
  } finally { mock.restoreAll(); mock.timers.reset(); }
});
await test("Texto: formatos, rascunho e paginação sem perder conteúdo", () => {
  assert.equal(formatoAudio("audio/mp4;codecs=mp4a")?.extensao, "m4a"); assert.equal(formatoAudio("text/html"), null);
  assert.equal(anexarDitado("Pergunta:", " qual a função? "), "Pergunta: qual a função?");
  const texto = "Qual a função do coração e dos pulmões? ".repeat(30).trim();
  const paginas = paginasDitado(texto);
  assert.ok(paginas.length > 1); assert.equal(paginas.join(" ").replace(/\s+/g, " "), texto);
  for (const pagina of paginas) { assert.ok(pagina.split("\n").length <= 7); assert.ok(pagina.split("\n").every((l) => l.length <= 42)); }
});
await test("Integração: todos os tutores, revisão explícita, cancelamento XR e segredo servidor", () => {
  const chat = readFileSync("components/chat/ChatPanel.tsx", "utf8");
  const sala = readFileSync("components/sala/SalaApp.tsx", "utf8");
  const vr = readFileSync("components/sala/SalaInterativos.tsx", "utf8");
  const hook = readFileSync("hooks/use-ditado-tutor.ts", "utf8");
  for (const dom of [chat, sala]) { assert.match(dom, /<ControlesDitado/); assert.match(dom, /ditado\.ocupado/); }
  assert.match(chat, /janelaAberta/); assert.match(vr, /Enviar pergunta/); assert.match(vr, /paginasDitado/);
  for (const evento of ["visibilitychange", "pagehide", "end"]) assert.ok(hook.includes(`"${evento}"`));
  assert.match(hook, /desvincular\(\);/);
  assert.doesNotMatch(hook, /obterXRStore|createXRStore/, "cada modo passa sua própria sessão, sem criar outra store XR");
  assert.match(readFileSync("components/viewer/PainelSiteXR.tsx", "utf8"), /sessao=\{sessao\}/);
  assert.match(readFileSync("components/viewer/Scene.tsx", "utf8"), /dispatchEvent\(new Event\(CANCELAR_DITADO\)\)/);
  for (const arquivo of [chat, sala, vr, hook, readFileSync("lib/ditado-tutor.ts", "utf8")]) assert.doesNotMatch(arquivo, /OPENAI_API_KEY|audio\.transcriptions\.create/);
});
