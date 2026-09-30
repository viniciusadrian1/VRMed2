import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createRayPointer } from "@pmndrs/pointer-events";
import layout from "../lib/sala-estudos-layout.json" with { type: "json" };
import { MODOS_ESTUDO, TELA_ESTUDO, BOTAO_ESTUDO, posicaoModoEstudo } from "../lib/sala-monitor.ts";
import { raioMonitorEstudos } from "../lib/sala-monitor-interacao.ts";
import { deveAcionarBotao3D } from "../lib/botao3d-interacao.ts";

const geometria = new THREE.Group();
for (const [arquivo, limiteMalhas, limiteTris, limiteBytes] of [
  [layout.ambiente, 13, 55_000, 4_800_000], [layout.monitor, 3, 5_000, 450_000],
] as const) {
  const dados = readFileSync(`public${arquivo}`);
  assert.equal(dados.toString("utf8", 0, 4), "glTF");
  assert.equal(dados.readUInt32LE(8), dados.length);
  const tamanho = dados.readUInt32LE(12);
  const json = JSON.parse(dados.toString("utf8", 20, 20 + tamanho));
  assert.ok(dados.length < limiteBytes && json.meshes.length <= limiteMalhas);
  assert.equal(json.animations?.length ?? 0, 0);
  assert.equal(json.cameras?.length ?? 0, 0);
  assert.ok(!json.extensionsUsed?.includes("KHR_lights_punctual"));
  assert.ok(json.buffers.every((b: { uri?: string }) => !b.uri));
  assert.ok(json.images?.every((i: { uri?: string }) => !i.uri) ?? true);
  assert.ok(json.materials.every((m: { alphaMode?: string }) => (m.alphaMode ?? "OPAQUE") === "OPAQUE"));
  const loader = new GLTFLoader().register(() => ({ name: "VerificacaoSemPixels", loadTexture: () => Promise.resolve(new THREE.Texture()) }));
  const { scene } = await loader.parseAsync(Uint8Array.from(dados).buffer, "");
  scene.updateMatrixWorld(true);
  let tris = 0;
  const tronco = new THREE.Box3(new THREE.Vector3(-.28, .84, -1.43), new THREE.Vector3(.28, 1.75, -.87));
  scene.traverse((obj) => {
    if (!(obj instanceof THREE.Mesh)) return;
    const pos = obj.geometry.getAttribute("position"), normal = obj.geometry.getAttribute("normal"), uv = obj.geometry.getAttribute("uv");
    const indice = obj.geometry.index;
    assert.equal(pos.count, normal.count); assert.equal(pos.count, uv.count);
    for (let i = 0; i < pos.count; i++) {
      assert.ok(Math.abs(new THREE.Vector3().fromBufferAttribute(normal, i).lengthSq() - 1) < .01);
      assert.ok(Number.isFinite(uv.getX(i)) && Number.isFinite(uv.getY(i)));
    }
    const tri = new THREE.Triangle();
    for (let i = 0; i < (indice?.count ?? pos.count); i += 3) {
      [tri.a, tri.b, tri.c].forEach((v, j) => v.fromBufferAttribute(pos, indice?.getX(i + j) ?? i + j).applyMatrix4(obj.matrixWorld));
      assert.ok(!tronco.intersectsTriangle(tri), "assento/cabeça do aluno precisam ficar livres");
      tris++;
    }
  });
  assert.ok(tris < limiteTris);
  geometria.add(scene);
  console.log(`ok: ${arquivo}: ${tris} triângulos, ${json.meshes.length} malhas, ${dados.length} bytes`);
}
geometria.updateMatrixWorld(true);
const tampo = new THREE.Raycaster(new THREE.Vector3(-.7, 1, -1.7), new THREE.Vector3(0, -1, 0)).intersectObject(geometria, true)[0];
assert.ok(tampo && Math.abs(tampo.point.y - .765) < .001, "livro/rádio continuam apoiados a 76,5 cm");

const cena = new THREE.Scene(), tela = new THREE.Group();
tela.position.fromArray(TELA_ESTUDO.posicao); cena.add(tela);
const alvos = MODOS_ESTUDO.map((modo, i) => {
  assert.ok(readFileSync(`app${modo.href}/page.tsx`, "utf8").length > 0);
  const pos = posicaoModoEstudo(i);
  assert.ok(Math.abs(pos[0]) + BOTAO_ESTUDO.largura / 2 < TELA_ESTUDO.largura / 2);
  assert.ok(Math.abs(pos[1]) + BOTAO_ESTUDO.altura / 2 < TELA_ESTUDO.altura / 2);
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(BOTAO_ESTUDO.largura, BOTAO_ESTUDO.altura), new THREE.MeshBasicMaterial());
  mesh.position.fromArray(pos); mesh.raycast = raioMonitorEstudos;
  mesh.addEventListener("click", () => undefined); tela.add(mesh); return mesh;
});
let casos = 0;
for (const altura of [.85, 1.1, 1.4]) for (const mao of [-.22, .22]) for (const z of [-1.4, -.8]) {
  const controle = new THREE.Object3D(); controle.position.set(mao, altura, z); cena.add(controle);
  const ponteiro = createRayPointer(() => new THREE.PerspectiveCamera(), { current: controle }, {});
  for (const alvo of alvos) for (const [x, y] of [[0, 0], [-.22, -.047], [.22, .047]]) {
    cena.updateMatrixWorld(true);
    const ponto = alvo.localToWorld(new THREE.Vector3(x, y, 0));
    controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position, ponto, new THREE.Vector3(0, 1, 0)));
    cena.updateMatrixWorld(true); ponteiro.move(cena, { timeStamp: 1000 });
    assert.equal(ponteiro.getIntersection()?.object, alvo, "a mira deve acertar somente a alternativa apontada");
    const raio = new THREE.Raycaster(controle.position, ponto.clone().sub(controle.position).normalize(), 0, controle.position.distanceTo(ponto) - .001);
    assert.equal(raio.intersectObject(geometria, true).length, 0, "monitor, mesa ou decoração não podem cobrir o alvo");
    casos++;
  }
  cena.remove(controle);
}
for (const olhosY of [1.05, 1.25, 1.65]) for (const alvo of alvos) {
  const origem = new THREE.Vector3(0, olhosY, -1.15), ponto = alvo.getWorldPosition(new THREE.Vector3());
  const raio = new THREE.Raycaster(origem, ponto.clone().sub(origem).normalize(), 0, origem.distanceTo(ponto) - .001);
  assert.equal(raio.intersectObject(geometria, true).length, 0, "visão sentada e em pé livre");
}
const tras = new THREE.Raycaster(new THREE.Vector3(-.245, 1.296, -3), new THREE.Vector3(0, 0, 1));
assert.equal(tras.intersectObject(tela, true).length, 0, "tela não é clicável pelo verso");
assert.ok(deveAcionarBotao3D("pressionar", { pointerType: "ray", button: 0 }));
assert.ok(!deveAcionarBotao3D("clicar", { pointerType: "ray", button: 0 }));
const fonte = readFileSync("components/sala/MonitorEstudos.tsx", "utf8");
assert.ok(!fonte.includes("<Panel") && !fonte.includes("html2canvas") && !fonte.includes("useFrame"));
assert.ok(fonte.includes("sairENavegar(session, modo.href)") && fonte.includes('tratamento="tela"'));
assert.ok(readFileSync("components/sala/SalaInterativos.tsx", "utf8").includes('revisao ? <MonitorEstudos'));
console.log(`ok: ${casos} alvos/cantos com ambas as mãos; visão sentada, tela física e retorno clássico`);
