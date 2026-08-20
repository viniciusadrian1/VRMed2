/**
 * Verificação headless da Arena: valida com as funções REAIS de produção
 * (identifyStructure / translateMeshName) que os modelos das duas fases
 * produzem alvos jogáveis — sem precisar de headset.
 *
 * Rodar: npx -y tsx scripts/verify-arena.ts
 */
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { identifyStructure } from "../lib/model-utils";

function nodeNamesOf(glbPath: string): string[] {
  const buffer = readFileSync(glbPath);
  const jsonLength = buffer.readUInt32LE(12);
  const json = JSON.parse(buffer.toString("utf8", 20, 20 + jsonLength));
  return (json.nodes ?? [])
    .map((node: { name?: string }) => node.name ?? "")
    .filter(Boolean);
}

function check(stage: string, glbPath: string, minTargets: number) {
  const names = nodeNamesOf(glbPath);
  // Reproduz a hierarquia real: cada nó vira uma malha nomeada, e a
  // identificação sobe pelos ancestrais como no app.
  const labels = new Set<string>();
  for (const name of names) {
    const mesh = new THREE.Mesh();
    mesh.name = name;
    const label = identifyStructure(mesh);
    if (label !== "Estrutura não identificada") labels.add(label);
  }

  const list = [...labels];
  console.log(`\n=== ${stage} (${glbPath}) ===`);
  console.log(`nós nomeados: ${names.length} | alvos únicos: ${list.length}`);
  console.log(list.map((l) => `  · ${l}`).join("\n"));

  console.assert(
    list.length >= minTargets,
    `FALHOU: ${stage} rendeu ${list.length} alvos (< ${minTargets})`,
  );
  console.assert(
    list.every((l) => l.trim().length > 2),
    `FALHOU: ${stage} tem rótulo vazio/curto demais`,
  );
  return list.length >= minTargets;
}

const ok1 = check("Fase 1 · Laringe", "public/models/organs/larynx.glb", 12);
const ok2 = check("Fase 2 · Fígado", "public/models/healthy/figado.glb", 15);

console.log(ok1 && ok2 ? "\n✅ Arena verificada: as duas fases têm alvos suficientes." : "\n❌ VERIFICAÇÃO FALHOU");
process.exit(ok1 && ok2 ? 0 : 1);
