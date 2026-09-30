import http from 'node:http';
import https from 'node:https';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';

// Mantém o teste original restrito a localhost e transporta apenas suas chamadas
// para a CX33 autorizada, atravessando o Nginx e validando o certificado público.
const raiz = resolve(import.meta.dirname, '../..');
const ponte = http.createServer((pedido, resposta) => {
  if (!pedido.url?.startsWith('/api/duelo')) {
    resposta.writeHead(404).end();
    return;
  }
  const remoto = https.request(new URL(pedido.url, 'https://2.28.109.190'), {
    method: pedido.method,
    headers: { ...pedido.headers, host: '2.28.109.190' },
  }, fluxo => {
    resposta.writeHead(fluxo.statusCode, fluxo.headers);
    fluxo.pipe(resposta);
  });
  remoto.on('error', () => {
    if (!resposta.headersSent) resposta.writeHead(502);
    resposta.end();
  });
  pedido.on('aborted', () => remoto.destroy());
  resposta.on('close', () => remoto.destroy());
  pedido.pipe(remoto);
});
await new Promise(resolve => ponte.listen(0, '127.0.0.1', resolve));
try {
  const porta = ponte.address().port;
  const filho = spawn(process.execPath, [
    '--experimental-strip-types', 'scripts/verificar-duelo-http.ts', `http://127.0.0.1:${porta}`,
  ], { cwd: raiz, stdio: 'inherit' });
  const codigo = await new Promise((resolve, reject) => {
    filho.on('exit', resolve);
    filho.on('error', reject);
  });
  if (codigo !== 0) throw new Error('Falha no teste público de Duelo.');
  console.log('ok: teste do Duelo atravessou HTTPS público/Nginx, com validação TLS normal.');
} finally {
  ponte.closeAllConnections();
  await new Promise(resolve => ponte.close(resolve));
}
