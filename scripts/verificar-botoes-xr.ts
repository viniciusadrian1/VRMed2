import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { createRayPointer } from "@pmndrs/pointer-events";
import { CAMADAS_UI3D, deveAcionarBotao3D, ORDEM_PONTEIRO_UI } from "../lib/botao3d-interacao.ts";

// Usa a biblioteca instalada de raycast/eventos, não um clique HTML simulado.
const cena = new THREE.Scene();
const camera = new THREE.PerspectiveCamera();
const painel = new THREE.Group();
painel.position.set(0.85, 0.10, -0.65);
painel.rotation.y = -0.14;
cena.add(painel);
const alvos: THREE.Mesh[] = [];
const antigas: string[] = [];
const escolhas: string[] = [];
let desabilitado = false;
for (let i = 0; i < 4; i++) {
  const botao = new THREE.Mesh(new THREE.PlaneGeometry(1.55, 0.18), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
  botao.name = "ABCD"[i];
  botao.position.set(0, -0.02 - i * 0.21, 0.01);
  botao.pointerEventsOrder = ORDEM_PONTEIRO_UI;
  botao.addEventListener("pointerdown", (evento) => {
    if (!desabilitado && deveAcionarBotao3D("pressionar", evento)) escolhas.push(botao.name);
  });
  botao.addEventListener("click", (evento) => {
    antigas.push(botao.name);
    if (!desabilitado && deveAcionarBotao3D("clicar", evento)) escolhas.push(botao.name);
  });
  painel.add(botao); alvos.push(botao);
}
const espaco = new THREE.Object3D();
espaco.position.set(0.2, 0.05, 2.5);
cena.add(espaco);
const ponteiro = createRayPointer(() => camera, { current: espaco }, {});
let instante = 1000;
function mirar(indice: number, x = 0, y = 0) {
  cena.updateMatrixWorld(true);
  const ponto = alvos[indice].localToWorld(new THREE.Vector3(x, y, 0));
  // -Z é a frente do controle, ao contrário do lookAt de um Object3D genérico.
  espaco.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(espaco.position, ponto, new THREE.Vector3(0, 1, 0)));
  cena.updateMatrixWorld(true);
  ponteiro.move(cena, { timeStamp: instante });
}
function apertar() { ponteiro.down({ timeStamp: instante, button: 0 }); }
function soltar(duracao: number) { instante += duracao; ponteiro.up({ timeStamp: instante, button: 0 }); instante += 1000; }

mirar(0); apertar(); soltar(700);
assert.deepEqual(antigas, [], "reprodução: onClick padrão perde gatilho segurado por 700 ms");
assert.deepEqual(escolhas, ["A"], "selectstart confirma sem depender da duração");
mirar(1); apertar(); soltar(80);
assert.deepEqual(escolhas, ["A", "B"], "aperto rápido não duplica no click de soltura");
mirar(2); apertar(); mirar(3); soltar(120);
assert.deepEqual(escolhas, ["A", "B", "C"], "mover o laser ao soltar não seleciona D");
desabilitado = true; mirar(3); apertar(); soltar(60);
assert.equal(escolhas.length, 3, "feedback/desabilitado não responde");
desabilitado = false;

// Inclui bordas antes atingidas pela compressão de 0,96 e o corredor entre opções.
for (let i = 0; i < 4; i++) {
  for (const [x, y] of [[0, 0], [0.765, 0.085], [-0.765, -0.085]]) {
    mirar(i, x, y);
    assert.equal(ponteiro.getIntersection()?.object, alvos[i]);
  }
  if (i < 3) {
    mirar(i, 0, -0.105);
    assert.ok(!alvos.includes(ponteiro.getIntersection()?.object as THREE.Mesh), "o espaço entre alternativas é neutro");
  }
}

// Prioridade do painel combina com o depthTest=false: cenário não rouba o laser.
const bloqueio = new THREE.Mesh(new THREE.PlaneGeometry(9, 9), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
bloqueio.position.z = 1;
bloqueio.addEventListener("click", () => { throw new Error("decoração recebeu escolha"); });
cena.add(bloqueio);
mirar(3); assert.equal(ponteiro.getIntersection()?.object, alvos[3]);

assert.equal(deveAcionarBotao3D("pressionar", { pointerType: "mouse", button: 0 }), false);
assert.equal(deveAcionarBotao3D("clicar", { pointerType: "mouse", button: 0 }), true);
assert.equal(deveAcionarBotao3D("clicar", { pointerType: "touch", button: 0 }), true);
assert.equal(deveAcionarBotao3D("clicar", { button: 2 }), false);
const fonte = readFileSync("components/arena/ui3d.tsx", "utf8");
assert.match(fonte, /<group ref=\{group\} pointerEvents="none">/, "animação separada do alvo estável");
assert.match(fonte, /pointerEventsOrder=\{ORDEM_PONTEIRO_UI\}/);
assert.ok(CAMADAS_UI3D.painel < CAMADAS_UI3D.botao && CAMADAS_UI3D.botao < CAMADAS_UI3D.contorno && CAMADAS_UI3D.contorno < CAMADAS_UI3D.texto);
assert.match(fonte, /renderOrder=\{CAMADAS_UI3D.botao\}/);
assert.match(fonte, /renderOrder=\{CAMADAS_UI3D.painel\}/);
console.log("ok: gatilho lento/rápido, sem duplicação ou troca na soltura, bordas A–D, intervalos, bloqueios e mouse");
