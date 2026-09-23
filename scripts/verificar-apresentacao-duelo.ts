import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import * as THREE from "three";
import { ARENA_INICIAL, sinalDaArena } from "../lib/duelo-apresentacao.ts";
import { aplicarMaterialOsso } from "../lib/material-osso.ts";

const sinal = (dados: Partial<typeof ARENA_INICIAL>) => sinalDaArena({ ...ARENA_INICIAL, ...dados });
assert.match(sinal({}).rotulo, /TREINAMENTO/);
assert.match(sinal({ fase: "contagem" }).rotulo, /PREPARE/);
assert.match(sinal({ fase: "rodada", tempo: 6 }).rotulo, /IDENTIFIQUE/);
assert.equal(sinal({ fase: "rodada", tempo: 5 }).cor, "#f2be6b");
assert.equal(sinal({ fase: "rodada", tempo: 0 }).pulso, true);
assert.equal(sinal({ fase: "feedback", resultado: "voce", tempo: 0 }).cor, "#71e0b2");
assert.equal(sinal({ fase: "rodada", erro: true, tempo: 4 }).cor, "#ed8a7b");
assert.match(sinal({ fase: "feedback", resultado: "adversario" }).rotulo, /OBSERVE/);
assert.match(sinal({ fase: "feedback", resultado: "tempo" }).rotulo, /REVISE/);
assert.match(sinal({ fase: "fim", meus: 100, outros: 0 }).rotulo, /VITÓRIA/);
assert.match(sinal({ fase: "fim", meus: 0, outros: 100 }).rotulo, /REVISAR/);
assert.match(sinal({ fase: "fim", meus: 100, outros: 100 }).rotulo, /EMPATE/);

const raiz = new THREE.Group();
const geometria = new THREE.BoxGeometry();
const osso = new THREE.Mesh(geometria, new THREE.MeshStandardMaterial());
const dente = new THREE.Mesh(geometria, new THREE.MeshStandardMaterial());
osso.name = "Frontal_bone"; dente.name = "Upper_teeth";
raiz.add(osso, dente);
aplicarMaterialOsso(raiz);
assert.equal(osso.geometry, geometria, "o acabamento não substitui a geometria");
assert.equal(osso.material.roughness, 0.72);
assert.equal(dente.material.roughness, 0.38);
assert.equal(osso.material.metalness, 0);
assert.equal(osso.material.color.getHexString(), "cbbfaa");
assert.equal(osso.material.userData.originalColor.getHexString(), "cbbfaa");

function lerGlb(caminho: string) {
  const dados = readFileSync(caminho);
  return { dados, json: JSON.parse(dados.toString("utf8", 20, 20 + dados.readUInt32LE(12))) };
}
const cranio = lerGlb("public/models/organs/cranio.glb");
assert.equal(createHash("sha256").update(cranio.dados).digest("hex"), "849278d46cc5756074e237e725341a9cf30778fee913c70b5bd00803ed44d2e5", "crânio original preservado byte a byte");
assert.equal(cranio.json.meshes.length, 25);
assert.equal(cranio.json.animations[0].channels.length, 22);
const entorno = lerGlb("public/models/props/entorno-arena.glb");
assert.equal(entorno.json.meshes.length, 8, "decoração agrupada em oito malhas");
assert.ok(entorno.dados.length < 2_000_000, "orçamento do entorno sem texturas externas");
const triangulosEntorno = entorno.json.meshes.reduce((soma: number, malha: { primitives: { indices: number }[] }) =>
  soma + malha.primitives.reduce((n, p) => n + entorno.json.accessors[p.indices].count / 3, 0), 0);
assert.ok(triangulosEntorno < 25_000);
assert.equal(entorno.json.images?.length ?? 0, 0);
assert.equal(entorno.json.animations?.length ?? 0, 0);
for (const nome of ["dr-caloni", "dra-reis", "dr-chefe"]) {
  const { json, dados } = lerGlb(`public/models/props/${nome}-arena.glb`);
  assert.ok(json.extensionsUsed.includes("KHR_draco_mesh_compression"));
  const indices = json.meshes[0].primitives[0].indices;
  assert.ok(json.accessors[indices].count / 3 <= 45000, `${nome}: orçamento de personagem`);
  assert.ok(dados.length < 4_000_000);
}
const jogo = readFileSync("components/duelo/DueloGame.tsx", "utf8");
assert.ok(jogo.includes("if (scene.parent !== g) g.add(scene)"), "remonte de efeitos recoloca o clone");
assert.ok(jogo.includes('key={`slot-modelo-${indice}`}'), "cada rodada tem contêiner próprio");
assert.ok(jogo.includes("scene.removeFromParent()"), "o órgão antigo é removido");
assert.ok(jogo.includes("dispose={null}"), "a geometria compartilhada não é descartada");
console.log("ok: sinais da arena, acabamento de osso, integridade do crânio, entorno, variantes leves e guardas de ciclo do modelo");
