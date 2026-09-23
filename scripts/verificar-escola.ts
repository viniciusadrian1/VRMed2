import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { createRayPointer } from "@pmndrs/pointer-events";
import { ESCOLA, mostrarEsqueleto3D } from "../lib/escola-apresentacao.ts";
import { deveAcionarBotao3D, fonteDoPonteiro, ORDEM_PONTEIRO_UI } from "../lib/botao3d-interacao.ts";

const jogo = readFileSync("components/duelo/DueloGame.tsx", "utf8");
const botao = readFileSync("components/duelo/BotaoLousa.tsx", "utf8");
assert.ok(jogo.includes('import { BotaoLousa } from "./BotaoLousa"'));
assert.ok(!jogo.includes("function BotaoLousa("), "não manter uma segunda implementação antiga");
assert.match(botao, /<Button3D/);
assert.ok(jogo.includes("i * ESCOLA.passoOpcao"));
assert.ok(ESCOLA.alturaOpcao < ESCOLA.passoOpcao, "intervalo neutro entre as alternativas");

// Geometria/posição da lousa com dois raios independentes; sem emular o headset.
const cena = new THREE.Scene();
const camera = new THREE.PerspectiveCamera();
const quadro = new THREE.Group();
quadro.position.set(ESCOLA.lousaX, 0, ESCOLA.lousaZ);
cena.add(quadro);
const escolhas: string[] = [];
let bloqueado = false;
const alvos = Array.from({ length: 4 }, (_, i) => {
  const alvo = new THREE.Mesh(new THREE.PlaneGeometry(ESCOLA.larguraOpcao, ESCOLA.alturaOpcao),
    new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
  alvo.name = "ABCD"[i]; alvo.position.y = -.055 - i * ESCOLA.passoOpcao;
  alvo.pointerEventsOrder = ORDEM_PONTEIRO_UI;
  alvo.addEventListener("pointerdown", (e) => {
    if (!bloqueado && deveAcionarBotao3D("pressionar", e)) escolhas.push(alvo.name);
  });
  alvo.addEventListener("click", (e) => {
    if (!bloqueado && deveAcionarBotao3D("clicar", e)) escolhas.push(alvo.name);
  });
  quadro.add(alvo); return alvo;
});
const controles = [-.2, .2].map((x) => {
  const espaco = new THREE.Object3D(); espaco.position.set(x, .05, 2.5); cena.add(espaco);
  return { espaco, ponteiro: createRayPointer(() => camera, { current: espaco }, {}) };
});
let tempo = 1000;
function mirar(controle: typeof controles[number], indice: number, dx = 0, dy = 0) {
  cena.updateMatrixWorld(true);
  const ponto = alvos[indice].localToWorld(new THREE.Vector3(dx, dy, 0));
  controle.espaco.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.espaco.position, ponto, new THREE.Vector3(0, 1, 0)));
  cena.updateMatrixWorld(true); controle.ponteiro.move(cena, { timeStamp: tempo });
}
for (const controle of controles) {
  for (let i = 0; i < 4; i++) {
    for (const [dx, dy] of [[0, 0], [.54, .044], [-.54, -.044]]) {
      mirar(controle, i, dx, dy);
      assert.ok(controle.ponteiro.getIntersection()?.object === alvos[i], "centro e bordas atingem a opção correta");
    }
    if (i < 3) {
      mirar(controle, i, 0, -ESCOLA.passoOpcao / 2);
      assert.ok(!alvos.some((alvo) => controle.ponteiro.getIntersection()?.object === alvo));
    }
    mirar(controle, i);
    const antes = escolhas.length;
    controle.ponteiro.down({ timeStamp: tempo, button: 0 });
    // Segurar e mover para outra opção antes de soltar não pode escolhê-la.
    mirar(controle, (i + 1) % 4);
    tempo += 700; controle.ponteiro.up({ timeStamp: tempo, button: 0 }); tempo += 1000;
    assert.deepEqual(escolhas.slice(antes), ["ABCD"[i]]);
  }
}
bloqueado = true;
mirar(controles[0], 0);
const antes = escolhas.length;
controles[0].ponteiro.down({ timeStamp: tempo, button: 0 });
controles[0].ponteiro.up({ timeStamp: tempo + 80, button: 0 });
assert.equal(escolhas.length, antes);
for (const lado of ["left", "right"]) {
  const fonte = { handedness: lado } as XRInputSource;
  assert.equal(fonteDoPonteiro({ pointerState: { inputSource: fonte } }), fonte);
}

for (const fase of ["contagem", "rodada", "feedback", "codigo", "sala"]) assert.equal(mostrarEsqueleto3D(fase, true), false);
assert.equal(mostrarEsqueleto3D("menu", true), true);
assert.equal(mostrarEsqueleto3D("fim", true), true);
assert.equal(mostrarEsqueleto3D("menu", false), false);
function glb(nome: string) {
  const dados = readFileSync(`public/models/props/${nome}.glb`);
  const json = JSON.parse(dados.toString("utf8", 20, 20 + dados.readUInt32LE(12)));
  const triangulos = json.meshes.reduce((s: number, m: { primitives: { indices: number }[] }) =>
    s + m.primitives.reduce((n, p) => n + json.accessors[p.indices].count / 3, 0), 0);
  return { dados, json, triangulos };
}
const escola = glb("escola-medicina");
assert.equal(escola.json.meshes.length, 10);
assert.ok(escola.triangulos < 25000 && escola.dados.length < 2_000_000);
assert.equal(escola.json.images?.length ?? 0, 0);
const osso = glb("esqueleto-estudo");
assert.equal(osso.triangulos, 158090, "ossos/dentes preservados, sem simplificação");
assert.equal(osso.json.meshes.length, 3);
assert.ok(osso.json.extensionsUsed.includes("KHR_draco_mesh_compression"));
const png = readFileSync("public/models/props/esqueleto-prancha.png");
assert.equal(png.readUInt32BE(16), 512); assert.equal(png.readUInt32BE(20), 1024);
console.log("ok: Escola — botões compartilhados, dois raios, bordas/intervalos, gatilho longo, fonte háptica, vitrine e orçamento");
