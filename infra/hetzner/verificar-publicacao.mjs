import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';

// Testes contra a máquina autorizada, com validação TLS normal, sem ignorar certificados.
const origem = 'https://2.28.109.190';
const raiz = resolve(import.meta.dirname, '../..');
for (const rota of ['/', '/duelo', '/sala', '/viewer', '/clinica', '/quiz']) {
  const resposta = await fetch(origem + rota, { signal: AbortSignal.timeout(20_000) });
  assert.equal(resposta.status, 200, rota);
  assert.match(resposta.headers.get('permissions-policy') ?? '', /xr-spatial-tracking=\(self\)/);
  console.log(`ok: HTTPS ${rota}, permissão WebXR preservada`);
  await resposta.body?.cancel();
}
const http = await fetch('http://2.28.109.190/duelo', { redirect: 'manual' });
assert.equal(http.status, 308);
assert.equal(http.headers.get('location'), `${origem}/duelo`);
for (const rota of ['/admin/feedback', '/admin/insights', '/.env', '/.git/config']) {
  const resposta = await fetch(origem + rota);
  assert.ok([401, 403, 404].includes(resposta.status));
  console.log(`ok: acesso bloqueado ${rota}`);
  await resposta.body?.cancel();
}
for (const arquivo of ['models/props/sala-estudos-revisao.glb', 'models/props/monitor-estudos-revisao.glb', 'models/props/arena-medica-revisao.glb', 'models/props/escola-medicina-revisao.glb', 'models/organs/cranio.glb', 'models/healthy/coracao.glb', 'models/organs/larynx.glb', 'draco/draco_decoder.wasm']) {
  const local = readFileSync(resolve(raiz, 'public', arquivo));
  const resposta = await fetch(`${origem}/${arquivo}`, { signal: AbortSignal.timeout(40_000) });
  assert.equal(resposta.status, 200, arquivo);
  const remoto = Buffer.from(await resposta.arrayBuffer());
  const hash = b => createHash('sha256').update(b).digest('hex');
  assert.equal(hash(remoto), hash(local), arquivo);
  console.log(`ok: asset íntegro ${arquivo} (${remoto.length} bytes)`);
}
const mapa = await (await fetch(`${origem}/sitemap.xml`)).text();
assert.ok(mapa.includes(origem) && !mapa.includes('localhost'));
const invalido = await fetch(`${origem}/api/chat`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
});
assert.equal(invalido.status, 400);
// Uma chamada sintética ao tutor, sem informações pessoais ou dados clínicos.
const tutor = await fetch(`${origem}/api/chat`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ messages: [{ role: 'user', content: 'Em uma frase curta, diga qual é a função geral do coração.' }], currentOrgan: 'Coração' }),
  signal: AbortSignal.timeout(60_000),
});
assert.equal(tutor.status, 200, 'Tutor deve responder pela chave autorizada');
const leitor = tutor.body.getReader();
let bytes = 0;
let partes = 0;
while (true) {
  const { done, value } = await leitor.read();
  if (done) break;
  bytes += value.length;
  partes++;
}
assert.ok(bytes > 20);
console.log(`ok: tutor real respondeu por HTTPS (${partes} partes, ${bytes} bytes); texto não registrado`);
