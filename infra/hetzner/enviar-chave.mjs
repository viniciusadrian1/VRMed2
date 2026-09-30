import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import path from 'node:path';

// Reutilização autorizada; o segredo trafega apenas pela entrada padrão do SSH.
// Não registrar o conteúdo nem copiar outras variáveis do ambiente local.
const origem = process.argv[2];
if (!origem) throw new Error('Informe a raiz local do VRmed.');
const requireOrigem = createRequire(path.join(origem, 'package.json'));
requireOrigem('@next/env').loadEnvConfig(origem);
const chave = process.env.OPENAI_API_KEY?.trim();
if (!chave || /[\r\n]/.test(chave)) throw new Error('Chave ausente ou formato inválido.');
const resultado = spawnSync('ssh', [
  '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
  'root@2.28.109.190',
  'umask 077; test ! -e /opt/vrmed/.env || exit 9; cat > /opt/vrmed/.env; chmod 600 /opt/vrmed/.env',
], { input: `OPENAI_API_KEY=${chave}\n`, encoding: 'utf8', timeout: 30_000 });
if (resultado.status !== 0) throw new Error('Transferência não concluída; verificar SSH ou arquivo existente, sem sobrescrevê-lo.');
console.log('OPENAI_API_KEY configurada em /opt/vrmed/.env; conteúdo não exibido.');
