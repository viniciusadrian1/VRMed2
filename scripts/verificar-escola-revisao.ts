import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createRayPointer } from "@pmndrs/pointer-events";
import { ESCOLA, posicaoCompetidorEscola } from "../lib/escola-apresentacao.ts";
import { ORDEM_PONTEIRO_UI } from "../lib/botao3d-interacao.ts";

const decoracao = new THREE.Group();
for (const [nome, maxMalhas, maxTris, maxBytes] of [
  ["escola-medicina-revisao", 19, 75_000, 6_500_000],
  ["piso-escola-revisao", 1, 2, 150_000],
] as const) {
  const dados = readFileSync(`public/models/props/${nome}.glb`);
  assert.equal(dados.toString("utf8", 0, 4), "glTF");
  assert.equal(dados.readUInt32LE(8), dados.length);
  const tamanho = dados.readUInt32LE(12);
  const json = JSON.parse(dados.toString("utf8", 20, 20 + tamanho));
  const bin = dados.subarray(28 + tamanho);
  assert.ok(dados.length <= maxBytes && json.meshes.length <= maxMalhas);
  assert.equal(json.animations?.length ?? 0, 0);
  assert.equal(json.cameras?.length ?? 0, 0);
  assert.ok(!json.extensionsUsed?.includes("KHR_lights_punctual"));
  assert.ok(!json.extensionsRequired?.includes("KHR_draco_mesh_compression"));
  assert.ok(json.buffers.every((b: { uri?: string }) => !b.uri));
  for (const img of json.images) {
    assert.ok(!img.uri, "texturas incorporadas, sem CDN");
    const view = json.bufferViews[img.bufferView];
    const png = bin.subarray(view.byteOffset, view.byteOffset + view.byteLength);
    assert.equal(png.subarray(1, 4).toString(), "PNG");
    assert.ok(png.readUInt32BE(16) <= 2048 && png.readUInt32BE(20) <= 2048);
  }
  assert.ok(json.materials.every((m: { alphaMode?: string }) => (m.alphaMode ?? "OPAQUE") === "OPAQUE"));
  const loader = new GLTFLoader().register(() => ({ name: "TesteGeometricoSemPixels",
    loadTexture: () => Promise.resolve(new THREE.Texture()) }));
  const { scene } = await loader.parseAsync(Uint8Array.from(dados).buffer, "");
  scene.updateMatrixWorld(true);
  const piso = nome.startsWith("piso-");
  if (!piso) {
    const raio = new THREE.Raycaster(new THREE.Vector3(-3.05, .95, 0), new THREE.Vector3(0, 0, -1));
    const hit = raio.intersectObject(scene, true)[0];
    assert.ok(hit?.uv && hit.object instanceof THREE.Mesh);
    assert.ok(!Array.isArray(hit.object.material) && hit.object.material.name.includes("Encadernacao"));
    assert.ok(hit.uv.x > .02 && hit.uv.x < .12 && hit.uv.y > .1 && hit.uv.y < .49,
      "lombada usa UV autoral, não o mapa vazio criado ao unir camadas de nomes diferentes");
    assert.ok(hit.face && hit.face.normal.z > .9, "a lombada recebe luz pela face externa");
  }
  let tris = 0;
  const corpos = (["jogador", "adversario"] as const).map(lado => {
    const [x, , z] = posicaoCompetidorEscola(lado);
    return new THREE.Box3(new THREE.Vector3(x - .3, .05, z - .3), new THREE.Vector3(x + .3, 2.05, z + .3));
  });
  const corredor = new THREE.Box3(new THREE.Vector3(-.8, .05, 1.5), new THREE.Vector3(.8, 2.05, 3.3));
  scene.traverse(obj => {
    if (!(obj instanceof THREE.Mesh)) return;
    assert.ok(obj.matrixWorld.determinant() > 0);
    const pos = obj.geometry.getAttribute("position"), norm = obj.geometry.getAttribute("normal");
    const uv = obj.geometry.getAttribute("uv"), cor = obj.geometry.getAttribute("color");
    const idx = obj.geometry.getIndex();
    assert.equal(norm.count, pos.count); assert.equal(uv.count, pos.count);
    if (!piso) assert.equal(cor.count, pos.count);
    for (let i = 0; i < pos.count; i++) {
      const n = new THREE.Vector3().fromBufferAttribute(norm, i);
      assert.ok(Number.isFinite(n.lengthSq()) && Math.abs(n.lengthSq() - 1) < .01);
      assert.ok(Number.isFinite(uv.getX(i)) && Number.isFinite(uv.getY(i)));
    }
    const tri = new THREE.Triangle();
    for (let i = 0; i < (idx?.count ?? pos.count); i += 3) {
      [tri.a, tri.b, tri.c].forEach((p, j) => {
        p.fromBufferAttribute(pos, idx?.getX(i + j) ?? i + j).applyMatrix4(obj.matrixWorld);
        assert.ok([p.x, p.y, p.z].every(Number.isFinite));
        assert.ok(Math.abs(p.x) <= 3.61 && Math.abs(p.z) <= 4.01 && p.y >= -.01 && p.y <= 3.29);
      });
      if (!piso) assert.ok(![...corpos, corredor].some(b => b.intersectsTriangle(tri)), "corpos e corredor livres");
      tris++;
    }
    obj.raycast = () => null;
  });
  assert.ok(tris <= maxTris);
  decoracao.add(scene);
  console.log(`ok: ${nome} — ${tris} triângulos, ${json.meshes.length} malhas, ${dados.length} bytes`);
}

const cena = new THREE.Scene(); decoracao.position.y = ESCOLA.piso; decoracao.pointerEvents = "none"; cena.add(decoracao);
const alvos = Array.from({ length: 4 }, (_, i) => {
  const o = new THREE.Mesh(new THREE.PlaneGeometry(ESCOLA.larguraOpcao, ESCOLA.alturaOpcao), new THREE.MeshBasicMaterial());
  o.position.set(ESCOLA.lousaX, -.055 - i * ESCOLA.passoOpcao, ESCOLA.lousaZ);
  o.pointerEventsOrder = ORDEM_PONTEIRO_UI; o.addEventListener("click", () => undefined); cena.add(o); return o;
});
for (const dx of [-.2, .2]) {
  const controle = new THREE.Object3D(); controle.position.set(ESCOLA.jogadorX + dx, -.05, ESCOLA.postoZ - .1); cena.add(controle);
  const ponteiro = createRayPointer(() => new THREE.PerspectiveCamera(), { current: controle }, {});
  for (const alvo of alvos) for (const [x, y] of [[0, 0], [-.54, -.044], [.54, .044]]) {
    cena.updateMatrixWorld(true); const ponto = alvo.localToWorld(new THREE.Vector3(x, y, 0));
    controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position, ponto, new THREE.Vector3(0, 1, 0)));
    cena.updateMatrixWorld(true); ponteiro.move(cena, { timeStamp: 1000 });
    assert.equal(ponteiro.getIntersection()?.object, alvo);
  }
}
const ambiente = readFileSync("components/duelo/AmbienteEscola.tsx", "utf8");
assert.ok(ambiente.includes("revisao = true") && ambiente.includes("<SalaAutoral />"),
  "Escola aprovada como padrão, mantendo implementação anterior recuperável");
assert.ok(ambiente.includes("revisao ? <SalaEscolaRevisao /> : <SalaAutoral />"));
assert.ok(!ambiente.includes("useGLTF.preload(CENARIO)"), "não baixar o cenário anterior na versão padrão");
assert.ok(ambiente.includes("!revisao && <PisoCenario"), "não sobrepor pisos");
assert.ok(ambiente.includes("<VitrineOsteologia detalhado={detalhado} alternar={alternar} />"));
const modelo = readFileSync("components/duelo/SalaEscolaRevisao.tsx", "utf8");
assert.ok(modelo.includes('pointerEvents="none"') && modelo.includes("obj.raycast = () => null"));
assert.ok(modelo.includes("dispose={null}") && !/castShadow|onClick|onPointer/.test(modelo));
const app = readFileSync("components/duelo/DueloApp.tsx", "utf8");
assert.ok(!app.includes("revisão experimental"), "não publicar o comparador de desenvolvimento");
assert.ok(!/revisao=\{false\}/.test(app), "não desativar a revisão aprovada no Duelo");
for (const arquivo of ["escola-medicina-direcao.glb", "piso-escola-direcao.glb", "esqueleto-estudo.glb"]) {
  assert.ok(readFileSync(`public/models/props/${arquivo}`).length > 0, "preservar acervo anterior");
}
console.log("ok: Escola revisada como padrão, anterior preservada, anatomia e 24 alvos de dois controles preservados");
