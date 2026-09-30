import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { BoxGeometry, Mesh, MeshBasicMaterial, Object3D, PerspectiveCamera, PlaneGeometry, Scene, Vector3, Matrix4 } from "three";
import { CombinedPointer, createGrabPointer, createRayPointer } from "@pmndrs/pointer-events";
import { updatePointerCursorModel, updatePointerRayModel } from "@pmndrs/xr/internals";
import { COMPRIMENTO_MIRA_XR, CONTROLE_XR, MIRA_XR, MaterialCursorXR, MaterialRaioXR, ORDEM_MIRA_XR } from "../lib/xr-mira.ts";
import { CAMADAS_UI3D, ORDEM_PONTEIRO_UI, deveAcionarBotao3D } from "../lib/botao3d-interacao.ts";

// Interseções, seleção e atualização visual são as da biblioteca instalada.
const cena = new Scene();
const camera = new PerspectiveCamera();
const alvo = new Mesh(new PlaneGeometry(0.6, 0.4), new MeshBasicMaterial());
alvo.pointerEventsOrder = ORDEM_PONTEIRO_UI;
let escolhas = 0;
alvo.addEventListener("pointerdown", (e) => { if (deveAcionarBotao3D("pressionar", e)) escolhas++; });
alvo.addEventListener("click", (e) => { if (deveAcionarBotao3D("clicar", e)) escolhas++; });
cena.add(alvo);
const materialRaio = new MaterialRaioXR();
const materialCursor = new MaterialCursorXR();
const raio = new Mesh(new BoxGeometry(), materialRaio);
const cursor = new Mesh(new PlaneGeometry(), materialCursor);
const grupoCursor = new Object3D();
cena.add(grupoCursor);
let casos = 0;

for (const lado of ["left", "right"] as const) {
  const espaco = new Object3D();
  espaco.position.set(lado === "left" ? -0.2 : 0.2, 1.1, 0);
  cena.add(espaco);
  const ponteiro = createRayPointer(() => camera, { current: espaco }, { inputSource: { handedness: lado } }, MIRA_XR);
  const combinado = new CombinedPointer(false);
  combinado.register(ponteiro, true);
  function mover() {
    cena.updateMatrixWorld(true);
    combinado.move(cena, { timeStamp: 1000 });
    updatePointerRayModel(raio, materialRaio, ponteiro, MIRA_XR.rayModel);
    updatePointerCursorModel(grupoCursor, cursor, materialCursor, ponteiro, MIRA_XR.cursorModel);
  }
  for (const distancia of [0.08, 0.3, 1, 2.4, 5, 8]) {
    alvo.position.copy(espaco.position).add(new Vector3(0, 0, -distancia));
    mover();
    const hit = ponteiro.getIntersection()!;
    assert.equal(hit.object, alvo);
    assert.ok(raio.visible && cursor.visible);
    assert.ok(Math.abs(raio.scale.z - hit.distance) < 1e-6, "linha chega ao alvo, inclusive além de 1 m");
    assert.ok(Math.abs(-raio.position.z + raio.scale.z / 2 - hit.distance) < 1e-6);
    assert.ok(cursor.position.distanceTo(hit.pointOnFace) <= MIRA_XR.cursorModel.cursorOffset + 1e-6);
    assert.equal(materialRaio.color.getHexString(), "67e8f9");
    const antes = escolhas;
    ponteiro.down({ timeStamp: 1100, button: 0 });
    updatePointerRayModel(raio, materialRaio, ponteiro, MIRA_XR.rayModel);
    assert.equal(materialRaio.color.getHexString(), "fbbf24");
    ponteiro.up({ timeStamp: 1900, button: 0 });
    assert.equal(escolhas, antes + 1, "800 ms segurando gatilho: uma ação no alvo indicado");
    casos++;
  }
  // Painel deslocado e inclinado: cursor preserva o ponto real, não o centro.
  alvo.position.set(0.65, 1.3, -2.8);
  alvo.rotation.y = -0.35;
  cena.updateMatrixWorld(true);
  const ponto = alvo.localToWorld(new Vector3(0.12, -0.06, 0));
  espaco.quaternion.setFromRotationMatrix(new Matrix4().lookAt(espaco.position, ponto, new Vector3(0, 1, 0)));
  mover();
  assert.ok(ponteiro.getIntersection()!.point.distanceTo(ponto) < 1e-6);
  assert.ok(cursor.position.distanceTo(ponto) < 0.002);

  // Reprodução da disputa antiga: grab perto da mão vence e desativa o raio.
  const proximo = new Mesh(new BoxGeometry(0.04, 0.04, 0.04), new MeshBasicMaterial());
  proximo.position.copy(espaco.position);
  proximo.addEventListener("click", () => { throw new Error("objeto próximo não deve receber seleção do painel"); });
  cena.add(proximo);
  const grab = createGrabPointer(() => camera, { current: espaco }, {});
  const retirarGrab = combinado.register(grab);
  mover();
  assert.equal(ponteiro.getEnabled(), false, "reproduz o raio desativado pelo grab padrão");
  assert.equal(raio.visible, false);
  retirarGrab();
  assert.equal(CONTROLE_XR.grabPointer, false);
  mover();
  assert.equal(ponteiro.getEnabled(), true);
  assert.equal(ponteiro.getIntersection()?.object, alvo, "prioridade da UI preservada diante do órgão");
  assert.equal(cursor.visible, true);
  cena.remove(proximo);
  proximo.geometry.dispose(); proximo.material.dispose();

  // Um enfeite sem interação não encurta o raio.
  const enfeite = new Mesh(new BoxGeometry(5, 5, 0.05), new MeshBasicMaterial());
  enfeite.position.set(0, 1, -0.5); enfeite.pointerEvents = "none";
  cena.add(enfeite); mover();
  assert.equal(ponteiro.getIntersection()?.object, alvo);
  cena.remove(enfeite); enfeite.geometry.dispose(); enfeite.material.dispose();

  cena.remove(alvo); mover();
  assert.ok(ponteiro.getIntersection()?.object.isVoidObject);
  assert.equal(cursor.visible, false, "não promete clique no vazio");
  assert.equal(raio.scale.z, COMPRIMENTO_MIRA_XR);
  assert.equal(materialRaio.opacity, 0.3, "linha discreta enquanto procura um alvo");
  combinado.setEnabled(false, { timeStamp: 2000 });
  updatePointerRayModel(raio, materialRaio, ponteiro, MIRA_XR.rayModel);
  updatePointerCursorModel(grupoCursor, cursor, materialCursor, ponteiro, MIRA_XR.cursorModel);
  assert.ok(!raio.visible && !cursor.visible, "ponteiro inativo não deixa mira fantasma");
  ponteiro.exit({ timeStamp: 2100 });
  cena.remove(espaco); alvo.rotation.set(0, 0, 0); cena.add(alvo);
}

assert.equal(materialRaio.depthWrite, false);
assert.equal(materialCursor.depthTest, false);
assert.equal(materialCursor.depthWrite, false);
assert.ok(ORDEM_MIRA_XR > Math.max(...Object.values(CAMADAS_UI3D)));
assert.ok(MIRA_XR.cursorModel.renderOrder > MIRA_XR.rayModel.renderOrder);

// Todas as stores devem usar o contrato. Sem mexer em flags de sessão/performance.
for (const arquivo of ["lib/xr-store.ts", "components/arena/ArenaScene.tsx", "components/viewer/Scene.tsx"]) {
  const codigo = readFileSync(arquivo, "utf8");
  assert.match(codigo, /controller: CONTROLE_XR/);
  assert.match(codigo, /hand: \{[^}]*grabPointer: false[^}]*touchPointer: false[^}]*rayPointer: MIRA_XR/);
  assert.ok(codigo.includes("/webxr-profiles/"));
}
for (const arquivo of ["components/sala/SalaInterativos.tsx", "components/arena/ArenaModel.tsx", "components/clinica/ClinicaViewer.tsx", "components/clinica/MapaAchados.tsx"]) {
  const codigo = readFileSync(arquivo, "utf8");
  assert.match(codigo, /deveAcionarBotao3D\("pressionar", event\)/);
  assert.match(codigo, /deveAcionarBotao3D\("clicar", event\)/);
}
raio.geometry.dispose(); cursor.geometry.dispose(); alvo.geometry.dispose(); alvo.material.dispose();
materialRaio.dispose(); materialCursor.dispose();
console.log(`ok: mira dos dois controles em ${casos} distâncias (8 cm–8 m), painel inclinado, alcance visual, clique lento único, grab concorrente, cenário, cursor, vazio e ciclo de desligamento`);
