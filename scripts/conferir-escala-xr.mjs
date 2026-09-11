/**
 * Confere a escala com que cada modelo do catálogo vai aparecer em AR e VR.
 *
 * POR QUE ISTO EXISTE
 *
 * Em AR e VR o metro é real: se o modelo aparece com 40 cm, ele tem 40 cm na
 * sala. Os `.glb` do catálogo, porém, vêm em unidades diferentes uns dos
 * outros e nenhum declara qual usa — medindo a caixa crua, os sistemas estão
 * em metros, algumas regiões em milímetros e os órgãos em nada reconhecível.
 * Por isso o tamanho real é DECLARADO em `lib/organs.ts`, no campo
 * `tamanhoRealCm`, e é ele que o visualizador usa.
 *
 * Um número declarado é um número que alguém pode esquecer de pôr, ou errar
 * por uma casa decimal — e o erro só apareceria dentro do headset. Este script
 * fecha as duas portas: mede o arquivo, aplica a mesma conta do visualizador e
 * mostra com quantos centímetros a estrutura vai aparecer. Reprova se faltar
 * declaração ou se o resultado for implausível.
 *
 *   node scripts/conferir-escala-xr.mjs
 */
import { readFileSync } from "node:fs";
import { medirGLB } from "./check-bounds.mjs";

/**
 * Lê o catálogo sem importar TypeScript: corta em cada `id: "..."` e pega o
 * `modelPath` e o `tamanhoRealCm` daquele bloco.
 */
function lerCatalogo() {
  const src = readFileSync("lib/organs.ts", "utf8");
  const partes = src.split(/\bid: "/).slice(1);
  const itens = [];
  for (const parte of partes) {
    const id = parte.slice(0, parte.indexOf('"'));
    const bloco = parte.slice(0, parte.indexOf("},") + 1);
    const modelPath = bloco.match(/modelPath: "([^"]+)"/)?.[1];
    const cm = bloco.match(/tamanhoRealCm: ([\d.]+)/)?.[1];
    if (id && modelPath) {
      itens.push({ id, modelPath, cm: cm ? Number(cm) : undefined });
    }
  }
  return itens;
}

/** Mesmo limiar do `EntradaXR`: acima disto o modelo apoia no chão. */
const ALTURA_PARA_APOIAR_NO_CHAO = 1.0;
/** Faixa plausível para a MAIOR dimensão de uma estrutura anatômica. */
const MENOR_ACEITAVEL_CM = 1;
const MAIOR_ACEITAVEL_CM = 210;

const itens = lerCatalogo();
const problemas = [];

console.log(
  "modelo".padEnd(22) +
    "declarado".padStart(11) +
    "  →  altura em cena".padEnd(26) +
    "onde",
);
console.log("-".repeat(74));

for (const it of itens) {
  if (it.cm == null) {
    problemas.push(`${it.id}: sem tamanhoRealCm no catálogo`);
    console.log(`${it.id.padEnd(22)}${"AUSENTE".padStart(11)}`);
    continue;
  }
  if (it.cm < MENOR_ACEITAVEL_CM || it.cm > MAIOR_ACEITAVEL_CM) {
    problemas.push(
      `${it.id}: ${it.cm} cm fora da faixa plausível ` +
        `(${MENOR_ACEITAVEL_CM}–${MAIOR_ACEITAVEL_CM} cm)`,
    );
  }

  let cru;
  try {
    cru = medirGLB("public" + it.modelPath);
  } catch {
    // Arquivo ausente é esperado enquanto o modelo não chegou: o visualizador
    // cai no modelo de demonstração. Não é motivo para reprovar.
    console.log(
      `${it.id.padEnd(22)}${(it.cm + " cm").padStart(11)}   (sem .glb)`,
    );
    continue;
  }

  // A mesma conta do visualizador: `normalizeContent` deixa o maior eixo com
  // 2 unidades, e a escala de XR devolve `tamanhoRealCm` a esse maior eixo.
  const maior = Math.max(cru.x, cru.y, cru.z);
  const alturaM = (cru.y / maior) * (it.cm / 100);
  const apoia = alturaM >= ALTURA_PARA_APOIAR_NO_CHAO;

  console.log(
    it.id.padEnd(22) +
      `${it.cm} cm`.padStart(11) +
      `  →  ${(alturaM * 100).toFixed(1)} cm de altura`.padEnd(26) +
      (apoia ? "apoiado no chão" : "flutuando à frente"),
  );
}

console.log();
if (problemas.length) {
  for (const p of problemas) console.log("FALHA:", p);
  console.log(`\n${problemas.length} problema(s).`);
  process.exit(1);
}
console.log(`${itens.length} modelos, todos com tamanho declarado e plausível.`);
