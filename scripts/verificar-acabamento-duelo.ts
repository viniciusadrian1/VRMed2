import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createRayPointer } from "@pmndrs/pointer-events";
import { ORDEM_PONTEIRO_UI } from "../lib/botao3d-interacao.ts";
import { ESCOLA } from "../lib/escola-apresentacao.ts";
import { ARENA_INICIAL } from "../lib/duelo-apresentacao.ts";
import { monitorDoAmbiente } from "../lib/monitor-ambiente.ts";

assert.equal(monitorDoAmbiente(ARENA_INICIAL).texto, "Em espera");
assert.equal(monitorDoAmbiente({ ...ARENA_INICIAL, fase: "rodada", combo: 3 }).texto, "Sequência ×3");
assert.equal(monitorDoAmbiente({ ...ARENA_INICIAL, fase: "rodada", combo: 3, tempo: 5 }).texto, "Tempo final");
assert.equal(monitorDoAmbiente({ ...ARENA_INICIAL, fase: "feedback", resultado: "voce" }).texto, "Acerto");
assert.equal(monitorDoAmbiente({ ...ARENA_INICIAL, fase: "fim", meus: 400, outros: 200 }).texto, "Vitória");
assert.equal(monitorDoAmbiente({ ...ARENA_INICIAL, fase: "encerrada" }).texto, "Encerrado");

const casos = [
  { nome: "entorno-arena-direcao", sala: "hospital", malhas: 8, tris: 33000, bytes: 2_500_000, imagens: 0 },
  { nome: "retaguarda-arena-acabada", sala: "hospital", malhas: 8, tris: 22000, bytes: 2_200_000, imagens: 0 },
  { nome: "escola-medicina-direcao", sala: "escola", malhas: 11, tris: 40000, bytes: 3_400_000, imagens: 1 },
  { nome: "piso-hospital-direcao", sala: "hospital", malhas: 1, tris: 2, bytes: 150_000, imagens: 1 },
  { nome: "piso-escola-direcao", sala: "escola", malhas: 1, tris: 2, bytes: 150_000, imagens: 1 },
];
const cenarios = { hospital: new THREE.Group(), escola: new THREE.Group() };
const corredor = new THREE.Box3(new THREE.Vector3(-1.4,.05,.6), new THREE.Vector3(1.4,2.1,4.1));
const postos = [ESCOLA.jogadorX, ESCOLA.adversarioX].map(x =>
  new THREE.Box3(new THREE.Vector3(x-.3,.05,ESCOLA.postoZ-.3), new THREE.Vector3(x+.3,2.05,ESCOLA.postoZ+.3)));

for (const caso of casos) {
  const dados = readFileSync(`public/models/props/${caso.nome}.glb`);
  const tamanho = dados.readUInt32LE(12);
  const json = JSON.parse(dados.toString("utf8",20,20+tamanho));
  const bin = dados.subarray(28+tamanho);
  assert.equal(json.meshes.length, caso.malhas);
  assert.equal(json.images?.length ?? 0, caso.imagens);
  assert.equal(json.animations?.length ?? 0, 0);
  assert.equal(json.cameras?.length ?? 0, 0);
  assert.ok(dados.length < caso.bytes);
  assert.ok(!json.extensionsUsed?.includes("KHR_lights_punctual"), "nenhuma luz extra no GLB");
  assert.ok(!json.extensionsRequired?.includes("KHR_draco_mesh_compression"));
  for (const img of json.images ?? []) {
    assert.equal(img.uri, undefined, "imagem local incorporada, sem CDN");
    const view = json.bufferViews[img.bufferView];
    const png = bin.subarray(view.byteOffset, view.byteOffset+view.byteLength);
    assert.equal(png.subarray(1,4).toString(), "PNG");
    const dim = caso.nome.startsWith("piso-") ? 512 : 128;
    assert.equal(png.readUInt32BE(16), dim); assert.equal(png.readUInt32BE(20), dim);
  }
  for (const mat of json.materials) {
    assert.equal(mat.alphaMode ?? "OPAQUE", "OPAQUE");
    assert.ok(!mat.extensions?.KHR_materials_unlit, "PBR continua recebendo luz do jogo");
  }
  // Imagens são verificadas estruturalmente aqui e visualmente no navegador.
  // O substituto evita fingir que Node tem um decodificador de imagem WebGL.
  const loader = new GLTFLoader().register(() => ({ name: "ImagemTesteGeometrico",
    loadTexture: () => Promise.resolve(new THREE.Texture()) }));
  const { scene } = await loader.parseAsync(Uint8Array.from(dados).buffer, "");
  scene.updateMatrixWorld(true);
  let tris = 0, menorCor = 1, maiorCor = 0;
  const piso = caso.nome.startsWith("piso-");
  scene.traverse(obj => {
    if (!(obj instanceof THREE.Mesh)) return;
    assert.ok(obj.matrixWorld.determinant() > 0);
    const pos = obj.geometry.getAttribute("position"), norm = obj.geometry.getAttribute("normal");
    const cor = obj.geometry.getAttribute("color"), idx = obj.geometry.getIndex();
    assert.equal(norm.count, pos.count);
    if (!piso) assert.equal(cor.count, pos.count, "oclusão exportada em COLOR_0");
    for (let i = 0; i < pos.count; i++) {
      const n = new THREE.Vector3().fromBufferAttribute(norm, i);
      assert.ok(Number.isFinite(n.lengthSq()) && Math.abs(n.lengthSq()-1) < .01);
      if (cor) {
        const v = cor.getX(i);
        assert.ok(v >= .32 && v <= 1.001, "contato sem preto absoluto");
        menorCor = Math.min(menorCor,v); maiorCor = Math.max(maiorCor,v);
      }
    }
    const tri = new THREE.Triangle();
    for (let i = 0; i < (idx?.count ?? pos.count); i += 3) {
      [tri.a,tri.b,tri.c].forEach((v,j) => {
        v.fromBufferAttribute(pos, idx?.getX(i+j) ?? i+j).applyMatrix4(obj.matrixWorld);
        assert.ok([v.x,v.y,v.z].every(Number.isFinite));
        assert.ok(Math.abs(v.x) <= (caso.sala === "escola" ? 3.61 : 4.65)
          && Math.abs(v.z) <= (caso.sala === "escola" ? 4.01 : 4.65)
          && v.y >= -.11 && v.y <= (caso.sala === "escola" ? 3.30 : 3.61));
      });
      if (!piso) {
        const livres = caso.sala === "hospital" ? [corredor] : postos;
        for (const livre of livres) assert.ok(!livre.intersectsTriangle(tri), `${caso.nome}: passagem livre`);
      }
      tris++;
    }
    obj.raycast = () => null;
  });
  assert.ok(tris <= caso.tris);
  if (!piso) assert.ok(maiorCor-menorCor > .05, "bake não pode ser uma cor uniforme");
  cenarios[caso.sala as keyof typeof cenarios].add(scene);
  console.log(`ok: ${caso.nome} — ${tris} triângulos, ${dados.length} bytes, ${caso.malhas} malhas`);
}

for (const sala of ["hospital", "escola"] as const) {
  const escola = sala === "escola";
  const cena = new THREE.Scene(), grupo = cenarios[sala];
  grupo.position.y = -1.3; grupo.pointerEvents = "none"; cena.add(grupo);
  const painel = new THREE.Group();
  painel.position.set(escola ? .36 : .85, escola ? 0 : .15, escola ? -1.06 : -.65);
  painel.rotation.y = escola ? 0 : -.14; cena.add(painel);
  const w = escola ? 1.1 : 1.55, h = escola ? .094 : .18;
  const alvos = Array.from({length:4}, (_,i) => {
    const alvo = new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial());
    alvo.position.set(0, escola ? -.055-i*.115 : -.02-i*.21,.01);
    alvo.pointerEventsOrder = ORDEM_PONTEIRO_UI; alvo.addEventListener("click", () => undefined);
    painel.add(alvo); return alvo;
  });
  for (const lado of [-.2,.2]) {
    const controle = new THREE.Object3D();
    controle.position.set((escola ? ESCOLA.jogadorX : 0)+lado,-.05,escola ? ESCOLA.postoZ-.1 : 2.45);
    cena.add(controle);
    const camera = new THREE.PerspectiveCamera();
    const ponteiro = createRayPointer(() => camera,{current:controle},{});
    for (const alvo of alvos) for (const [dx,dy] of [[0,0],[-w*.49,-h*.45],[w*.49,h*.45]]) {
      cena.updateMatrixWorld(true);
      const ponto = alvo.localToWorld(new THREE.Vector3(dx,dy,0));
      controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position,ponto,new THREE.Vector3(0,1,0)));
      cena.updateMatrixWorld(true); ponteiro.move(cena,{timeStamp:1000});
      assert.equal(ponteiro.getIntersection()?.object,alvo,"cenário não captura o laser");
    }
  }
}
for (const [arquivo, asset] of [["EntornoHospital", "entorno-arena-direcao"],
  ["RetaguardaHospital", "retaguarda-arena-acabada"], ["AmbienteEscola", "escola-medicina-direcao"]]) {
  const fonte = readFileSync(`components/duelo/${arquivo}.tsx`,"utf8");
  assert.ok(fonte.includes(`${asset}.glb`), "o runtime usa o asset testado");
  assert.ok(fonte.includes('pointerEvents="none"'));
}
const fonte = readFileSync("components/duelo/PisoCenario.tsx","utf8");
assert.ok(!/useFrame|castShadow|transparent|CanvasTexture/.test(fonte));
assert.ok(fonte.includes('dispose={null}'), "cache GLTF não é destruído pela troca de sala");
assert.ok(fonte.includes('piso-hospital-direcao.glb'), "piso recalculado para os novos equipamentos");
assert.ok(fonte.includes('piso-escola-direcao.glb'), "piso recalculado para a nova Escola");
const reflexos = readFileSync("components/duelo/useReflexosCenario.ts", "utf8");
assert.ok(!/scene\.environment\s*=|useFrame|useEffect/.test(reflexos), "reflexo local e estático, sem mudar anatomia");
assert.ok(reflexos.includes("size: 128"), "resolução limitada do mapa compartilhado");
assert.ok(reflexos.includes("mat.clone()") && reflexos.includes("entrada.alvo.dispose()"));
console.log("ok: acabamento — normais, cores, texturas locais, limites, postos livres e 48 alvos com dois raios");
