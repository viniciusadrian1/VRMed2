import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createRayPointer } from "@pmndrs/pointer-events";
import { ORDEM_PONTEIRO_UI } from "../lib/botao3d-interacao.ts";
import { ESCOLA } from "../lib/escola-apresentacao.ts";

interface Placa { id: string; posicao: [number, number, number]; largura: number; altura: number; giro?: number }
const config = JSON.parse(readFileSync("lib/sinalizacao-duelo.json", "utf8")) as { placas: Record<string, Placa[]> };

for (const [sala, placas] of Object.entries(config.placas)) {
  const dados = readFileSync(`public/models/props/sinalizacao-${sala}.glb`);
  const tamanhoJson = dados.readUInt32LE(12);
  const json = JSON.parse(dados.toString("utf8", 20, 20 + tamanhoJson));
  const binario = dados.subarray(20 + tamanhoJson + 8);
  assert.equal(json.meshes.length, 3, "três malhas para todas as placas da sala");
  assert.equal(json.materials.length, 3);
  assert.equal(json.images.length, 1, "um atlas incorporado; nenhuma captura HTML em runtime");
  assert.equal(json.animations?.length ?? 0, 0);
  assert.equal(json.cameras?.length ?? 0, 0);
  assert.ok(dados.length < 420_000, "orçamento do arquivo com textura");
  assert.ok(!json.extensionsRequired?.includes("KHR_draco_mesh_compression"), "asset pequeno dispensa decodificação Draco");
  const imagem = json.images[0];
  assert.equal(imagem.uri, undefined, "textura não depende de URL externa");
  assert.equal(imagem.mimeType, "image/png");
  const view = json.bufferViews[imagem.bufferView];
  const png = binario.subarray(view.byteOffset, view.byteOffset + view.byteLength);
  assert.equal(png.subarray(1, 4).toString(), "PNG");
  assert.equal(png.readUInt32BE(16), 2048);
  assert.equal(png.readUInt32BE(20), sala === "hospital" ? 1024 : 512);
  for (const mat of json.materials) {
    assert.equal(mat.alphaMode ?? "OPAQUE", "OPAQUE");
    assert.ok(!mat.doubleSided, "normais corretas, sem forçar DoubleSide");
    assert.ok(!mat.extensions?.KHR_materials_unlit, "placa e tinta recebem luz");
    assert.ok(!mat.emissiveFactor?.some((v: number) => v > 0), "tinta não emite luz");
  }
  const impressao = json.materials.find((m: { name: string }) => m.name.includes("Impressao"));
  assert.equal(impressao.pbrMetallicRoughness.metallicFactor, 0);
  assert.ok(Math.abs(impressao.pbrMetallicRoughness.roughnessFactor - .82) < 1e-6);
  assert.ok(impressao.pbrMetallicRoughness.baseColorTexture);

  // Node não rasteriza imagens. O PNG real foi inspecionado acima; o navegador
  // valida os pixels. Aqui o carregador real verifica geometria, UVs e materiais.
  const loader = new GLTFLoader().register(() => ({ name: "TexturaParaTesteGeometrico",
    loadTexture: () => Promise.resolve(new THREE.Texture()) }));
  const { scene } = await loader.parseAsync(Uint8Array.from(dados).buffer, "");
  scene.updateMatrixWorld(true);
  let triangulos = 0;
  let face: THREE.Mesh | undefined;
  const corredor = new THREE.Box3(new THREE.Vector3(-1.4, .05, .6), new THREE.Vector3(1.4, 2.1, 4.1));
  scene.traverse((obj) => {
    if (!(obj instanceof THREE.Mesh)) return;
    if (obj.name.includes("Impressao")) face = obj;
    assert.ok(obj.matrixWorld.determinant() > 0);
    const pos = obj.geometry.getAttribute("position"), normal = obj.geometry.getAttribute("normal");
    const uv = obj.geometry.getAttribute("uv"), indices = obj.geometry.getIndex();
    assert.equal(pos.count, normal.count);
    const n = new THREE.Vector3();
    for (let i = 0; i < pos.count; i++) {
      n.fromBufferAttribute(normal, i);
      assert.ok(Number.isFinite(n.lengthSq()) && Math.abs(n.lengthSq() - 1) < .01);
      if (obj === face) assert.ok(uv.getX(i) >= 0 && uv.getX(i) <= 1 && uv.getY(i) >= 0 && uv.getY(i) <= 1);
    }
    const tri = new THREE.Triangle();
    for (let i = 0; i < (indices?.count ?? pos.count); i += 3) {
      [tri.a, tri.b, tri.c].forEach((v, j) => {
        v.fromBufferAttribute(pos, indices?.getX(i + j) ?? i + j).applyMatrix4(obj.matrixWorld);
        assert.ok([v.x, v.y, v.z].every(Number.isFinite));
      });
      assert.ok(!corredor.intersectsTriangle(tri), "corredor e posto do jogador livres");
      triangulos++;
    }
  });
  assert.ok(triangulos < 2500);
  assert.ok(face);
  for (const placa of placas) {
    const posicao = new THREE.Vector3(...placa.posicao);
    if (sala === "escola" && placa.id === "lousa") posicao.y += ESCOLA.elevacaoLousa;
    const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), placa.giro ?? 0);
    const normal = new THREE.Vector3(0, 0, 1).applyQuaternion(q);
    for (const dx of [-.4, 0, .4]) for (const dy of [-.25, 0, .25]) {
      const origem = new THREE.Vector3(dx * placa.largura, dy * placa.altura, 1).applyQuaternion(q).add(posicao);
      const hits = new THREE.Raycaster(origem, normal.clone().negate()).intersectObject(scene, true);
      assert.equal(hits[0]?.object, face, `${placa.id}: inscrição opaca à frente da carcaça`);
      assert.ok(Math.abs(hits[0].distance - .9727) < .0001, `${placa.id}: escala, frente e profundidade corretas`);
    }
  }

  // Dois controles apontam para os botões reais mesmo com todas as placas carregadas.
  const cena = new THREE.Scene(); scene.position.y = -1.3; scene.pointerEvents = "none"; cena.add(scene);
  const painel = new THREE.Group();
  const escola = sala === "escola";
  painel.position.set(escola ? .36 : .85, escola ? ESCOLA.elevacaoLousa : .15, escola ? -1.06 : -.65);
  painel.rotation.y = escola ? 0 : -.14; cena.add(painel);
  const largura = escola ? 1.1 : 1.55, altura = escola ? .094 : .18;
  const alvos = Array.from({ length: 4 }, (_, i) => {
    const alvo = new THREE.Mesh(new THREE.PlaneGeometry(largura, altura), new THREE.MeshBasicMaterial());
    alvo.position.set(0, escola ? -.055-i*.115 : -.02-i*.21, .01);
    alvo.pointerEventsOrder = ORDEM_PONTEIRO_UI; alvo.addEventListener("click", () => undefined);
    painel.add(alvo); return alvo;
  });
  for (const x of [-.2, .2]) {
    const controle = new THREE.Object3D(); controle.position.set(x, -.05, escola ? 1.55 : 2.45); cena.add(controle);
    const ponteiro = createRayPointer(() => new THREE.PerspectiveCamera(), { current: controle }, {});
    for (const alvo of alvos) for (const [dx, dy] of [[0, 0], [.48, .45], [-.48, -.45]]) {
      cena.updateMatrixWorld(true);
      const alvoMundo = alvo.localToWorld(new THREE.Vector3(dx*largura, dy*altura, 0));
      controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position, alvoMundo, new THREE.Vector3(0, 1, 0)));
      cena.updateMatrixWorld(true); ponteiro.move(cena, { timeStamp: 1000 });
      assert.equal(ponteiro.getIntersection()?.object, alvo);
    }
  }
  console.log(`ok: ${sala}: ${placas.length} placas, ${triangulos} triângulos, ${dados.length} bytes; atlas, normais, profundidade, corredor e dois controles`);
}
const componente = readFileSync("components/duelo/SinalizacaoCenario.tsx", "utf8");
assert.match(componente, /pointerEvents="none"/);
assert.match(componente, /obj\.raycast = SEM_RAYCAST/);
assert.match(componente, /dispose=\{null\}/, "cache não destruído ao trocar ambiente");
assert.doesNotMatch(componente, /useFrame|Text3D|CanvasTexture|FontFace/, "placas pré-produzidas, sem texto sobreposto ou rasterização em runtime");
