import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { createRayPointer } from "@pmndrs/pointer-events";
import { escalaPainelXR, iniciarArrastePainel, limitarPosicaoPainel, opacidadePeloRaio, ordenarAlvosPaineis, posicaoArrastadaPainel, useJanelasEstudoXR } from "../lib/janelas-estudo-xr.ts";
import { TEMA_PAINEL_CLARO, TEMA_PAINEL_ESCURO } from "../lib/tema-paineis-xr.ts";
import { deveAcionarBotao3D } from "../lib/botao3d-interacao.ts";

// Tokens reais do site: mudanças em CSS precisam chegar às janelas imersivas.
const css = readFileSync("app/globals.css", "utf8");
const tokens = { card: "card", foreground: "foreground", primary: "primary", primaryForeground: "primary-foreground", muted: "muted", mutedForeground: "muted-foreground", accent: "accent", accentForeground: "accent-foreground", border: "border", danger: "destructive" };
for (const [seletor, tema] of [[":root", TEMA_PAINEL_CLARO], [".dark", TEMA_PAINEL_ESCURO]] as const) {
  const bloco = css.slice(css.indexOf(seletor + " {")).split("}")[0];
  for (const chave of Object.keys(tokens) as (keyof typeof tokens)[]) {
    assert.ok(bloco.includes(`--${tokens[chave]}: ${tema[chave]};`), `cor ${chave} divergiu do site em ${seletor}`);
  }
}
assert.ok(css.includes('url("/fonts/inter-600.woff")'));
const estilo = readFileSync("components/viewer/EstiloPainelXR.tsx", "utf8");
assert.match(estilo, /font=\{ARENA_FONT\}/);
assert.ok(!estilo.includes("outlineWidth="), "texto de estudo não usa contorno da arena");
assert.match(estilo, /resolvedTheme === "dark"/);

assert.equal(escalaPainelXR(-100), 0.65);
assert.equal(escalaPainelXR(100), 1.55);
assert.equal(escalaPainelXR(0.65 + 0.1), 0.75);
assert.equal(escalaPainelXR(NaN), 1);
assert.deepEqual(limitarPosicaoPainel(new THREE.Vector3(9, -9, 9)).toArray(), [2.2, -0.65, -0.55]);
assert.deepEqual(limitarPosicaoPainel(new THREE.Vector3(-9, 9, -9)).toArray(), [-2.2, 0.75, -2.4]);

// Reabertura independente, foco e reset não alteram a escolha de visibilidade.
const loja = useJanelasEstudoXR.getState;
loja().abrir("ferramentas", false);
assert.equal(loja().abertas.tutor, true);
loja().abrir("tutor", false); loja().abrir("ferramentas", true);
assert.equal(loja().abertas.ferramentas, true);
assert.equal(loja().abertas.tutor, false);
const revisao = loja().revisao;
loja().restaurarLayout(); assert.equal(loja().revisao, revisao + 1);
assert.equal(loja().abertas.tutor, false, "restaurar não abre a janela que a pessoa minimizou");
loja().abrir("tutor", true); assert.equal(loja().frente, "tutor");
loja().focar("ferramentas"); assert.equal(loja().frente, "ferramentas");

// Arraste em coordenadas do mundo com pai rotacionado, deslocado e escalado.
for (const escala of [0.65, 1, 1.55]) {
  const pai = new THREE.Group(), janela = new THREE.Group();
  pai.position.set(3, 1.1, -2); pai.rotation.y = 0.73; pai.scale.setScalar(1.2); pai.add(janela);
  janela.position.set(-0.9, 0.1, -1.12); janela.rotation.y = 0.55; janela.scale.setScalar(escala);
  pai.updateMatrixWorld(true);
  const pegada = janela.localToWorld(new THREE.Vector3(0.21, 0.622, 0));
  const origem = pai.localToWorld(new THREE.Vector3(-0.2, -0.25, 0.1));
  const raio = new THREE.Ray(origem, pegada.clone().sub(origem).normalize());
  const inicio = iniciarArrastePainel(janela, pegada, raio);
  const inicial = posicaoArrastadaPainel(raio, inicio, pai.matrixWorld);
  assert.ok(inicial.distanceTo(janela.position) < 1e-6, "pressionar a barra não salta para o centro");
  const deltaLocal = new THREE.Vector3(0.3, -0.1, -0.2);
  const deltaMundo = deltaLocal.clone().multiplyScalar(1.2).applyQuaternion(pai.quaternion);
  const movido = posicaoArrastadaPainel(new THREE.Ray(origem.clone().add(deltaMundo), raio.direction), inicio, pai.matrixWorld);
  assert.ok(movido.distanceTo(janela.position.clone().add(deltaLocal)) < 1e-6, "acompanha controle sem drift no espaço do pai");
  const barra = new THREE.Object3D(); janela.add(barra); barra.position.set(-0.13, -0.049, 0.03); pai.updateMatrixWorld(true);
  for (const [x, valor] of [[-0.4, 0], [-0.3, 0], [0, 0.5], [0.3, 1], [0.4, 1]]) {
    const ponto = barra.localToWorld(new THREE.Vector3(x, 0, 0));
    assert.equal(opacidadePeloRaio(new THREE.Ray(origem, ponto.clone().sub(origem).normalize()), barra.matrixWorld, 0.6), valor);
  }
}
assert.equal(opacidadePeloRaio(new THREE.Ray(new THREE.Vector3(0, 0, 1), new THREE.Vector3(1, 0, 0)), new THREE.Matrix4(), 0.6), null);

// Captura da biblioteca instalada: ambos os controles podem sair da barra segurando.
for (const mao of [-0.2, 0.2]) {
  const cena = new THREE.Scene(), camera = new THREE.PerspectiveCamera();
  const janela = new THREE.Group(); janela.position.set(-0.8, 0, -1.12); janela.rotation.y = 0.55; cena.add(janela);
  const barra = new THREE.Mesh(new THREE.PlaneGeometry(1.04, 0.085), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
  barra.position.y = 0.622; barra.pointerEventsOrder = 1202; janela.add(barra);
  const orgao = new THREE.Object3D(); orgao.position.set(0, -0.1, -0.8); cena.add(orgao);
  const cameraAntes = camera.matrixWorld.clone(), orgaoAntes = orgao.position.clone();
  const controle = new THREE.Object3D(); controle.position.set(mao, -0.2, 0.1); cena.add(controle);
  const raio = createRayPointer(() => camera, { current: controle }, {});
  let inicio: ReturnType<typeof iniciarArrastePainel> | null = null, dono: number | null = null, movimentos = 0;
  barra.addEventListener("pointerdown", (e) => {
    e.stopPropagation(); if (dono != null) return;
    dono = e.pointerId; inicio = iniciarArrastePainel(janela, e.point, e.ray); e.target.setPointerCapture(e.pointerId);
  });
  barra.addEventListener("pointermove", (e) => {
    e.stopPropagation(); if (!inicio || dono !== e.pointerId) return;
    janela.position.copy(posicaoArrastadaPainel(e.ray, inicio, cena.matrixWorld)); movimentos++;
  });
  barra.addEventListener("pointerup", (e) => {
    e.stopPropagation(); if (dono !== e.pointerId) return;
    dono = null; inicio = null; e.target.releasePointerCapture(e.pointerId);
  });
  cena.updateMatrixWorld(true);
  const ponto = janela.localToWorld(barra.position.clone());
  controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position, ponto, new THREE.Vector3(0, 1, 0)));
  cena.updateMatrixWorld(true); raio.move(cena, { timeStamp: 0 }); raio.down({ timeStamp: 1, button: 0 });
  assert.equal(raio.getPointerCapture()?.object, barra);
  const posicaoAntes = janela.position.clone();
  controle.position.x += 0.35; controle.position.y -= 0.12; cena.updateMatrixWorld(true);
  raio.move(cena, { timeStamp: 500 });
  assert.ok(movimentos > 0);
  assert.ok(janela.position.distanceTo(posicaoAntes.clone().add(new THREE.Vector3(0.35, -0.12, 0))) < 1e-6);
  raio.up({ timeStamp: 900, button: 0 });
  assert.equal(raio.getPointerCapture(), undefined);
  const posicaoSolta = janela.position.clone();
  controle.position.x += 0.1; cena.updateMatrixWorld(true); raio.move(cena, { timeStamp: 1000 });
  assert.ok(janela.position.equals(posicaoSolta), "soltar encerra o arraste");
  assert.ok(camera.matrixWorld.equals(cameraAntes)); assert.ok(orgao.position.equals(orgaoAntes));
}

// A janela desenhada na frente vence mesmo se fisicamente estiver mais longe.
// Minimizar não deixa o painel invisível interceptar botões da outra janela.
const cena = new THREE.Scene(), camera = new THREE.PerspectiveCamera(), controle = new THREE.Object3D();
cena.add(controle);
const raio = createRayPointer(() => camera, { current: controle }, {});
const janelas: THREE.Group[] = [], escudos: THREE.Mesh[] = [];
let acionamentos = 0;
for (const [z, ordem] of [[-0.8, 1100], [-1.3, 1200]]) {
  const janela = new THREE.Group(); janela.position.z = z; janela.pointerEventsOrder = ordem; janela.userData.ordemJanelaXR = ordem; cena.add(janela);
  const escudo = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
  escudo.pointerEventsOrder = ordem; escudo.addEventListener("pointerdown", (e) => e.stopPropagation()); janela.add(escudo);
  const botao = new THREE.Mesh(new THREE.PlaneGeometry(0.25, 0.07), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
  botao.position.set(0, 0.2, 0.025); botao.pointerEventsOrder = ordem + 2; botao.userData.ordemJanelaXR = ordem + 2;
  botao.addEventListener("pointerdown", (e) => { e.stopPropagation(); if (deveAcionarBotao3D("pressionar", e)) acionamentos++; });
  botao.addEventListener("click", (e) => { e.stopPropagation(); if (deveAcionarBotao3D("clicar", e)) acionamentos++; }); janela.add(botao);
  janelas.push(janela); escudos.push(escudo);
}
cena.updateMatrixWorld(true); raio.move(cena, { timeStamp: 0 });
assert.equal(raio.getIntersection()?.object, escudos[1]);
const mouse = new THREE.Raycaster(controle.position, new THREE.Vector3(0, 0, -1));
assert.equal(ordenarAlvosPaineis(mouse.intersectObjects(janelas, true))[0].object, escudos[1]);
janelas[1].visible = false; janelas[1].pointerEvents = "none";
raio.move(cena, { timeStamp: 1 });
assert.equal(raio.getIntersection()?.object, escudos[0]);
assert.equal(ordenarAlvosPaineis(mouse.intersectObjects(janelas, true))[0].object, escudos[0]);
janelas[1].visible = true; janelas[1].pointerEvents = "auto";
controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position, new THREE.Vector3(0, 0.2, -1.275), new THREE.Vector3(0, 1, 0)));
cena.updateMatrixWorld(true); raio.move(cena, { timeStamp: 2 });
assert.equal(raio.getIntersection()?.object, janelas[1].children[1]);
raio.down({ timeStamp: 3, button: 0 }); raio.up({ timeStamp: 800, button: 0 });
assert.equal(acionamentos, 1, "gatilho demorado não duplica nem perde ação");

// Contratos de integração; complementam os testes de raios, não simulam headset.
const base = readFileSync("components/viewer/PainelXRBase.tsx", "utf8");
assert.match(base, /visible=\{aberto\} pointerEvents=\{aberto \? "auto" : "none"\}/);
assert.ok(!base.includes("if (!aberto) return"), "minimização não desmonta rascunhos");
const tutor = readFileSync("components/viewer/TutorPainelVR.tsx", "utf8");
assert.match(tutor, /aoAlternar=\{\(\) => useJanelasEstudoXR.getState\(\).abrir\("tutor", !aberto\)\}/);
const janela = readFileSync("components/viewer/JanelaMovelXR.tsx", "utf8");
assert.ok(!/camera\.position\.|camera\.lookAt\(/.test(janela), "não pode transformar a câmera");
assert.match(janela, /inputsourceschange/); assert.match(janela, /visibilitychange/);
assert.match(janela, /atual.ponteiro !== e.pointerId/);
console.log("ok: janelas XR — identidade claro/escuro, escala, arraste capturado em dois controles, opacidade, prioridade visual, minimização, reabertura e câmera preservada");
