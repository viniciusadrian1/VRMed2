import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Usar somente o WAV sintético de QA; nunca grava o microfone nem lê a chave.
const caminho = process.argv[2];
if (!caminho) throw new Error('Informe o WAV sintético com a frase de teste sobre ciclo pulmonar.');
const audio = readFileSync(caminho);
assert.equal(audio.toString('ascii', 0, 4), 'RIFF');
assert.ok(audio.length < 2 * 1024 * 1024);
const origem = 'https://2.28.109.190';
const transcricao = await fetch(`${origem}/api/transcricao`, {
  method: 'POST', headers: { 'content-type': 'audio/wav', origin: origem }, body: audio,
  signal: AbortSignal.timeout(60_000),
});
const dados = await transcricao.json();
assert.equal(transcricao.status, 200);
assert.match(dados.texto.toLowerCase(), /ciclo pulmonar/);
console.log(`ok: ditado sintético via HTTPS/OpenAI (${dados.texto.length} caracteres), sem registro do conteúdo`);

// Passa do antigo teto de 512 KiB, mas não chega à OpenAI: origem recusada pelo app.
const recusada = await fetch(`${origem}/api/transcricao`, {
  method: 'POST', headers: { 'content-type': 'audio/wav', origin: 'https://example.invalid' },
  body: Buffer.alloc(800 * 1024), signal: AbortSignal.timeout(30_000),
});
assert.equal(recusada.status, 403);
assert.match((await recusada.json()).error, /Origem/);
const grande = await fetch(`${origem}/api/transcricao`, {
  method: 'POST', headers: { 'content-type': 'audio/wav', origin: origem },
  body: Buffer.alloc(2 * 1024 * 1024 + 1), signal: AbortSignal.timeout(30_000),
});
assert.equal(grande.status, 413);
await grande.body?.cancel();
console.log('ok: proxy admite o limite novo e preserva proteção de origem e teto de 2 MiB');
