import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createRayPointer } from "@pmndrs/pointer-events";
import { ORDEM_PONTEIRO_UI } from "../lib/botao3d-interacao.ts";

const dados = readFileSync("public/models/props/retaguarda-arena.glb");
const json = JSON.parse(dados.toString("utf8", 20, 20 + dados.readUInt32LE(12)));
assert.equal(json.meshes.length, 8);
assert.equal(json.materials.length, 8);
assert.equal(json.images?.length ?? 0, 0);
assert.equal(json.animations?.length ?? 0, 0);
assert.ok(dados.length < 1_600_000, "asset de apoio abaixo de 1,6 MB");
assert.ok(!json.extensionsRequired?.includes("KHR_draco_mesh_compression"));
const gltf = await new GLTFLoader().parseAsync(Uint8Array.from(dados).buffer, "");
gltf.scene.updateMatrixWorld(true);

// Espaço livre contínuo atrás do palco, incluindo o posto XR [0, -1.3, 2.55].
// É uma verificação geométrica, não um sistema físico de colisão/Guardian.
const corredor = new THREE.Box3(new THREE.Vector3(-1.4, .05, .6), new THREE.Vector3(1.4, 2.1, 4.1));
const limites = new THREE.Box3(new THREE.Vector3(-4.59, -.001, -.7), new THREE.Vector3(4.59, 3.59, 4.59));
const triangulo = new THREE.Triangle();
let quantidade = 0;
gltf.scene.traverse((obj) => {
  if (!(obj instanceof THREE.Mesh)) return;
  assert.ok(obj.matrixWorld.determinant() > 0, "sem espelhamento de normais");
  const vertices = obj.geometry.getAttribute("position");
  const normais = obj.geometry.getAttribute("normal");
  const indices = obj.geometry.getIndex();
  assert.ok(normais && normais.count === vertices.count);
  const n = new THREE.Vector3();
  for (let i = 0; i < normais.count; i++) {
    n.fromBufferAttribute(normais, i);
    assert.ok(Number.isFinite(n.lengthSq()) && n.lengthSq() > .9, "normais finitas e não nulas");
  }
  for (let i = 0; i < (indices?.count ?? vertices.count); i += 3) {
    [triangulo.a, triangulo.b, triangulo.c].forEach((p, j) => {
      p.fromBufferAttribute(vertices, indices?.getX(i + j) ?? i + j).applyMatrix4(obj.matrixWorld);
      assert.ok(limites.containsPoint(p), `geometria fora da área de apoio: ${obj.name}`);
    });
    assert.ok(!corredor.intersectsTriangle(triangulo), `corredor invadido por ${obj.name}`);
    quantidade++;
  }
});
assert.ok(quantidade < 22_000, "orçamento de geometria do apoio");

// Dois controles no posto real, com o novo GLB presente e excluído dos ponteiros.
const cena = new THREE.Scene();
gltf.scene.position.y = -1.3;
gltf.scene.pointerEvents = "none";
cena.add(gltf.scene);
const painel = new THREE.Group();
painel.position.set(.85, .15, -.65); painel.rotation.y = -.14; cena.add(painel);
const alvos = Array.from({ length: 4 }, (_, i) => {
  const alvo = new THREE.Mesh(new THREE.PlaneGeometry(1.55, .18), new THREE.MeshBasicMaterial());
  alvo.position.set(0, -.02 - i * .21, .01);
  alvo.pointerEventsOrder = ORDEM_PONTEIRO_UI;
  alvo.addEventListener("click", () => undefined);
  painel.add(alvo); return alvo;
});
for (const x of [-.2, .2]) {
  const controle = new THREE.Object3D(); controle.position.set(x, -.05, 2.45); cena.add(controle);
  const camera = new THREE.PerspectiveCamera();
  const ponteiro = createRayPointer(() => camera, { current: controle }, {});
  for (const alvo of alvos) for (const [dx, dy] of [[0, 0], [.765, .085], [-.765, -.085]]) {
    cena.updateMatrixWorld(true);
    const ponto = alvo.localToWorld(new THREE.Vector3(dx, dy, 0));
    controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position, ponto, new THREE.Vector3(0, 1, 0)));
    cena.updateMatrixWorld(true); ponteiro.move(cena, { timeStamp: 1000 });
    assert.equal(ponteiro.getIntersection()?.object, alvo);
  }
}
const componente = readFileSync("components/duelo/RetaguardaHospital.tsx", "utf8");
assert.match(componente, /return <group pointerEvents="none">/);
assert.match(componente, /obj\.raycast = SEM_RAYCAST/);
const app = readFileSync("components/duelo/DueloApp.tsx", "utf8");
assert.match(app, /process\.env\.NODE_ENV === "development"/);
assert.match(app, /if \(inSession\) return;/);
assert.ok(app.includes('[0, FLOOR_Y, 2.55]'), "origem XR da Arena preservada");
assert.ok(app.includes('[0.85, 0.48, 3.8]'), "câmera vertical permanece à frente da porta posterior");
console.log(`ok: retaguarda — ${quantidade} triângulos, 8 malhas, limites da sala, corredor livre, normais, dois raios e guardas de inspeção`);
