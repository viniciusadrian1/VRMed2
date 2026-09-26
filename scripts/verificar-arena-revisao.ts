import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createRayPointer } from "@pmndrs/pointer-events";
import { ORDEM_PONTEIRO_UI } from "../lib/botao3d-interacao.ts";

const cenario = new THREE.Group();
const corredor = new THREE.Box3(new THREE.Vector3(-1.4,.05,.6),new THREE.Vector3(1.4,2.1,4.1));
for (const [nome, tetoMalhas, tetoTris, tetoBytes] of [
  ["arena-medica-revisao", 13, 100_000, 9_000_000],
  ["piso-arena-revisao", 1, 2, 150_000],
] as const) {
  const dados = readFileSync(`public/models/props/${nome}.glb`);
  assert.equal(dados.toString("utf8",0,4), "glTF");
  assert.equal(dados.readUInt32LE(4), 2);
  assert.equal(dados.readUInt32LE(8), dados.length);
  const tamanho = dados.readUInt32LE(12);
  const json = JSON.parse(dados.toString("utf8",20,20+tamanho));
  const bin = dados.subarray(28+tamanho);
  assert.ok(dados.length <= tetoBytes);
  assert.ok(json.meshes.length <= tetoMalhas);
  assert.equal(json.animations?.length ?? 0, 0);
  assert.equal(json.cameras?.length ?? 0, 0);
  assert.ok(!json.extensionsUsed?.includes("KHR_lights_punctual"));
  assert.ok(!json.extensionsRequired?.includes("KHR_draco_mesh_compression"));
  assert.ok(json.buffers.every((b: { uri?: string }) => !b.uri), "buffers incorporados");
  const piso = nome.startsWith("piso-");
  let atlas = false;
  for (const img of json.images) {
    assert.equal(img.uri, undefined, "sem CDN ou textura externa");
    const view = json.bufferViews[img.bufferView];
    const png = bin.subarray(view.byteOffset,view.byteOffset+view.byteLength);
    assert.equal(png.subarray(1,4).toString(), "PNG");
    const w = png.readUInt32BE(16), h = png.readUInt32BE(20);
    assert.ok((piso && w === 512 && h === 512) || (!piso &&
      ((w === 256 && h === 256) || (w === 2048 && h === 1024))));
    atlas ||= w === 2048 && h === 1024;
  }
  if (!piso) {
    assert.ok(atlas, "inscrições locais com atlas limitado");
    assert.ok(json.materials.filter((m: { normalTexture?: unknown }) => m.normalTexture).length >= 2);
  }
  for (const mat of json.materials) {
    assert.equal(mat.alphaMode ?? "OPAQUE", "OPAQUE");
    assert.ok(!mat.extensions?.KHR_materials_unlit, "materiais recebem a luz do jogo");
  }
  // Node valida geometria e estrutura das imagens; a aparência é conferida no navegador.
  const loader = new GLTFLoader().register(() => ({ name: "ImagemTesteGeometrico",
    loadTexture: () => Promise.resolve(new THREE.Texture()) }));
  const { scene } = await loader.parseAsync(Uint8Array.from(dados).buffer, "");
  scene.updateMatrixWorld(true);
  if (!piso) {
    // Placa lateral: o eixo U deve acompanhar a largura, não a altura.
    const letras = scene.children.find(o => o instanceof THREE.Mesh &&
      !Array.isArray(o.material) && o.material.name.includes("Inscricoes"));
    assert.ok(letras);
    const amostrar = (y: number, z: number) => {
      const raio = new THREE.Raycaster(new THREE.Vector3(0,y,z),new THREE.Vector3(1,0,0));
      const hit = raio.intersectObject(letras,true)[0];
      assert.ok(hit?.uv && hit.point.x > 4.3 && hit.point.x < 4.34);
      return hit.uv;
    };
    const a = amostrar(2.32,2.1), b = amostrar(2.32,2.8), c = amostrar(2.4,2.1);
    assert.ok(b.x-a.x > .2 && Math.abs(b.y-a.y) < .001,"inscrição horizontal sem rotação de UV");
    assert.ok(Math.abs(c.x-a.x) < .001 && c.y < a.y,"altura correta da inscrição");
    const centroMonitor = new THREE.Raycaster(new THREE.Vector3(0,1.73,2.65),new THREE.Vector3(-1,0,0));
    const faceMonitor = centroMonitor.intersectObject(scene,true)[0];
    assert.ok(faceMonitor && faceMonitor.point.x < -3.98 && faceMonitor.point.x > -4.1,
      "braço não atravessa a face do monitor nem esconde a tela dinâmica");
  }
  let tris = 0;
  scene.traverse(obj => {
    if (!(obj instanceof THREE.Mesh)) return;
    assert.ok(obj.matrixWorld.determinant() > 0);
    const pos = obj.geometry.getAttribute("position"), norm = obj.geometry.getAttribute("normal");
    const uv = obj.geometry.getAttribute("uv"), cor = obj.geometry.getAttribute("color");
    const idx = obj.geometry.getIndex();
    assert.equal(norm.count,pos.count); assert.equal(uv.count,pos.count);
    if (!piso) assert.equal(cor.count,pos.count, "oclusão estática exportada");
    for (let i = 0; i < pos.count; i++) {
      const n = new THREE.Vector3().fromBufferAttribute(norm,i);
      assert.ok(Number.isFinite(n.lengthSq()) && Math.abs(n.lengthSq()-1) < .01);
      assert.ok(Number.isFinite(uv.getX(i)) && Number.isFinite(uv.getY(i)));
      if (cor) assert.ok(cor.getX(i) >= .32 && cor.getX(i) <= 1.001);
    }
    const tri = new THREE.Triangle();
    for (let i = 0; i < (idx?.count ?? pos.count); i += 3) {
      [tri.a,tri.b,tri.c].forEach((v,j) => {
        v.fromBufferAttribute(pos,idx?.getX(i+j) ?? i+j).applyMatrix4(obj.matrixWorld);
        assert.ok([v.x,v.y,v.z].every(Number.isFinite));
        assert.ok(Math.abs(v.x) <= 4.65 && Math.abs(v.z) <= 4.65 && v.y >= -.11 && v.y <= 3.65);
      });
      if (!piso) assert.ok(!corredor.intersectsTriangle(tri), `${nome}: corredor/posto do jogador livre`);
      tris++;
    }
    obj.raycast = () => null;
  });
  assert.ok(tris <= tetoTris);
  cenario.add(scene);
  console.log(`ok: ${nome} — ${tris} triângulos, ${json.meshes.length} malhas, ${dados.length} bytes`);
}

const cena = new THREE.Scene();
cenario.position.y = -1.3; cenario.pointerEvents = "none"; cena.add(cenario);
const painel = new THREE.Group();
painel.position.set(.85,.15,-.65); painel.rotation.y = -.14; cena.add(painel);
const alvos = Array.from({ length: 4 },(_,i) => {
  const alvo = new THREE.Mesh(new THREE.PlaneGeometry(1.55,.18),new THREE.MeshBasicMaterial());
  alvo.position.set(0,-.02-i*.21,.01); alvo.pointerEventsOrder = ORDEM_PONTEIRO_UI;
  alvo.addEventListener("click", () => undefined); painel.add(alvo); return alvo;
});
for (const lado of [-.2,.2]) {
  const controle = new THREE.Object3D(); controle.position.set(lado,-.05,2.45); cena.add(controle);
  const ponteiro = createRayPointer(() => new THREE.PerspectiveCamera(),{ current: controle },{});
  for (const alvo of alvos) for (const [dx,dy] of [[0,0],[-.75,-.08],[.75,.08]]) {
    cena.updateMatrixWorld(true);
    const ponto = alvo.localToWorld(new THREE.Vector3(dx,dy,0));
    controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position,ponto,new THREE.Vector3(0,1,0)));
    cena.updateMatrixWorld(true); ponteiro.move(cena,{ timeStamp: 1000 });
    assert.equal(ponteiro.getIntersection()?.object,alvo,"novo mobiliário não captura o laser");
  }
}
const fonte = readFileSync("components/duelo/ArenaMedicaRevisao.tsx","utf8");
assert.ok(fonte.includes('pointerEvents="none"') && fonte.includes('obj.raycast = () => null'));
assert.ok(fonte.includes('dispose={null}') && !/castShadow|onClick|onPointer/.test(fonte));
assert.ok(fonte.includes('<PalcoAnatomico />') && fonte.includes('<ConsoleArena />'));
const app = readFileSync("components/duelo/DueloApp.tsx","utf8");
assert.ok(app.includes('<ArenaMedicaRevisao />'),"nova Arena é o cenário padrão do hospital");
assert.ok(!app.includes('<AmbienteHospital />'),"a sala anterior não é montada junto da nova");
assert.ok(!app.includes('Arena: revisão experimental'),"comparador experimental não aparece em produção");
assert.ok(readFileSync("components/duelo/AmbienteHospital.tsx","utf8").includes('export function AmbienteHospital'),
  "implementação anterior preservada para recuperação");
assert.ok(app.includes('<AmbienteEscola detalhado='),"Escola preservada");
console.log("ok: nova Arena padrão, base preservada, anatomia central reutilizada, 24 alvos com dois raios e corredor livre");
