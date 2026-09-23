import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { raioPlacaXR } from "../lib/raio-placa-xr.ts";
import { createRayPointer } from "@pmndrs/pointer-events";
import { estiloRaizCapturada, validarPixelsPainel } from "../lib/painel-captura-xr.ts";
import { analogicosEstudoXR, transladarModeloXR } from "../lib/controles-modelo-xr.ts";
import { alcaJanelaXR, iniciarTamanhoPainel, tamanhoPeloRaio, zonasBordaXR } from "../lib/gestos-janelas-xr.ts";
import { PAINEL_SITE_XR } from "../lib/painel-dom-xr.ts";
import { liberarPonteiroUI, maoNaInterface, ocuparPonteiroUI, bloquearPincaUI } from "../lib/xr-foco-interface.ts";

// Regressão da captura: aliases lógicos e coordenadas do host oculto não atravessam.
const computado: Record<string, string> = { left: "-10000px", "inset-inline-start": "-10000px", right: "9000px",
  transform: "matrix(1, 0, 0, 1, -10000, 0)", opacity: "0", "background-color": "rgb(27,26,24)", color: "rgb(234,232,227)", "font-family": "VRmed Inter" };
const estilo = estiloRaizCapturada(400, 740, (p) => computado[p] ?? "");
assert.equal(estilo.left, "0px"); assert.equal(estilo.position, "relative"); assert.equal(estilo.width, "400px");
assert.equal(estilo["background-color"], computado["background-color"]);
assert.ok(!JSON.stringify(estilo).includes("-10000")); assert.equal(estilo["inset-inline-start"], undefined);
assert.equal(estilo.transform, undefined); assert.equal(estilo.opacity, "1");
const pixels = new Uint8ClampedArray(400 * 120 * 4);
assert.equal(validarPixelsPainel(pixels), false, "imagem transparente era aceita como sucesso");
for (let i = 0; i < pixels.length; i += 4) { pixels[i] = 27; pixels[i + 1] = 26; pixels[i + 2] = 24; pixels[i + 3] = 255; }
assert.equal(validarPixelsPainel(pixels), false, "somente fundo escuro também é inválido");
for (let i = 0; i < 1600; i += 4) { pixels[i] = 234; pixels[i + 1] = 232; pixels[i + 2] = 227; }
assert.equal(validarPixelsPainel(pixels), true, "contraste de conteúdo no cabeçalho");
pixels.fill(255); assert.equal(validarPixelsPainel(pixels), false, "fundo branco vazio também é inválido");

// Os quatro eixos têm papéis independentes e respeitam foco/zona morta.
assert.deepEqual(analogicosEstudoXR(1, 0, 0, 0), { giro: 1, aberturaOuTombo: 0, lateral: 0, profundidade: 0 });
assert.deepEqual(analogicosEstudoXR(0, 1, 0, 0), { giro: 0, aberturaOuTombo: 1, lateral: 0, profundidade: 0 });
assert.deepEqual(analogicosEstudoXR(0, 0, 1, -1), { giro: 0, aberturaOuTombo: 0, lateral: 1, profundidade: -1 });
assert.deepEqual(analogicosEstudoXR(0.15, -0.15, 0.1, -0.1), { giro: 0, aberturaOuTombo: 0, lateral: 0, profundidade: 0 });
assert.deepEqual(analogicosEstudoXR(1, 0, 1, 1, true, true), { giro: 0, aberturaOuTombo: 0, lateral: 0, profundidade: 0 });
assert.equal(analogicosEstudoXR(1, 0.3, 0, 0).aberturaOuTombo, 0, "giro não abre ossos por pequena diagonal");
const dono = {}, outro = {};
const controleUI = { pointerId: 20, pointerState: { inputSource: { handedness: "right" as const } } };
ocuparPonteiroUI(dono, controleUI); ocuparPonteiroUI(outro, controleUI);
assert.equal(maoNaInterface("right"), true, "controle, não somente mão, reserva a interface");
assert.equal(maoNaInterface("left"), false);
liberarPonteiroUI(dono, 20); assert.equal(maoNaInterface("right"), true, "outro alvo mantém seu foco");
assert.equal(bloquearPincaUI(true, false, false, maoNaInterface("right")), true);
liberarPonteiroUI(outro); assert.equal(maoNaInterface("right"), false);
assert.equal(bloquearPincaUI(true, true, true, false), true, "pegada iniciada na UI permanece bloqueada até soltar");
assert.equal(bloquearPincaUI(false, true, true, false), false);
for (const giro of [0, Math.PI / 2, -0.9]) {
  const cena = new THREE.Scene(), camera = new THREE.PerspectiveCamera(), pai = new THREE.Group(), modelo = new THREE.Group();
  camera.position.set(1, 1.6, 2); camera.rotation.y = giro; cena.add(camera, pai);
  pai.position.set(-0.3, 0.4, 0.6); pai.rotation.y = 0.55; pai.scale.setScalar(1.3); pai.add(modelo);
  cena.updateMatrixWorld(true);
  const frente = camera.getWorldDirection(new THREE.Vector3()), direita = new THREE.Vector3().crossVectors(frente, new THREE.Vector3(0, 1, 0));
  const inicio = camera.position.clone().addScaledVector(frente, 1.2); inicio.y = 1.2;
  modelo.position.copy(pai.worldToLocal(inicio.clone())); cena.updateMatrixWorld(true);
  const orientacao = modelo.quaternion.clone(), tamanho = modelo.scale.clone(), cameraAntes = camera.matrixWorld.clone();
  transladarModeloXR(modelo, camera, 1, 0, 1 / 60); cena.updateMatrixWorld(true);
  assert.ok(modelo.getWorldPosition(new THREE.Vector3()).distanceTo(inicio.clone().addScaledVector(direita, 0.7 / 60)) < 1e-6);
  modelo.position.copy(pai.worldToLocal(inicio.clone()));
  transladarModeloXR(modelo, camera, 0, -1, 1 / 60); cena.updateMatrixWorld(true);
  assert.ok(modelo.getWorldPosition(new THREE.Vector3()).distanceTo(inicio.clone().addScaledVector(frente, 0.7 / 60)) < 1e-6, "empurrar afasta no plano do olhar");
  assert.ok(modelo.quaternion.equals(orientacao)); assert.ok(modelo.scale.equals(tamanho)); assert.ok(camera.matrixWorld.equals(cameraAntes));
}
const camera = new THREE.PerspectiveCamera(), orgao = new THREE.Group();
camera.position.y = 1.6; orgao.position.set(0, 1.6, -0.28);
transladarModeloXR(orgao, camera, 0, 1, 1); assert.equal(orgao.position.z, -0.28, "não atravessa a cabeça");
orgao.position.z = -5; transladarModeloXR(orgao, camera, 0, -1, 1); assert.equal(orgao.position.z, -5);
orgao.position.z = -1; transladarModeloXR(orgao, camera, 1, 0, 30);
assert.ok(Math.abs(orgao.position.x - 0.7 / 30) < 1e-6, "retomar sessão não produz salto");

// Os alvos reais de borda não cruzam a alça e mantêm proporção/âncora oposta.
let redimensionamentos = 0;
for (const id of ["ferramentas", "tutor"] as const) {
  const d = PAINEL_SITE_XR[id], altura = PAINEL_SITE_XR.alturaMetros, largura = altura * d.largura / d.altura;
  const zonas = zonasBordaXR(largura, altura), alca = alcaJanelaXR(altura, true);
  assert.equal(zonas.length, 8);
  for (const z of zonas) {
    const cruza = Math.abs(z.x - alca.x) < (z.largura + alca.largura) / 2 && Math.abs(z.y - alca.y) < (z.altura + alca.altura) / 2;
    assert.equal(cruza, false, "mover e redimensionar não disputam o mesmo ponto");
    for (const mao of [-0.2, 0.2]) for (const escala of [0.65, 1, 1.55]) {
      const cena = new THREE.Scene(), pai = new THREE.Group(), painel = new THREE.Group(), camera = new THREE.PerspectiveCamera(), controle = new THREE.Object3D();
      cena.add(pai, controle); pai.position.set(1, 0.8, -1); pai.rotation.y = 0.35; pai.scale.setScalar(1.1);
      pai.add(painel); painel.position.set(0, 0, -1.3); painel.rotation.y = -0.4; painel.scale.setScalar(escala);
      controle.position.set(mao, 1, 1);
      const alvo = new THREE.Mesh(new THREE.PlaneGeometry(z.largura, z.altura), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
      alvo.raycast = raioPlacaXR; alvo.position.set(z.x, z.y, 0.025); alvo.pointerEventsOrder = 1202; painel.add(alvo);
      let inicio: ReturnType<typeof iniciarTamanhoPainel> | null = null;
      alvo.addEventListener("pointerdown", (e) => { inicio = iniciarTamanhoPainel(painel, e.point, z.borda, largura, altura); e.target.setPointerCapture(e.pointerId); });
      alvo.addEventListener("pointerup", (e) => { e.target.releasePointerCapture(e.pointerId); });
      cena.updateMatrixWorld(true);
      const ponto = alvo.getWorldPosition(new THREE.Vector3());
      // O raio dos controles segue -Z, como o ponteiro real do projeto.
      controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position, ponto, new THREE.Vector3(0, 1, 0)));
      cena.updateMatrixWorld(true);
      const ponteiro = createRayPointer(() => camera, { current: controle }, {});
      ponteiro.move(cena, { timeStamp: 0 });
      assert.ok(ponteiro.getIntersection()?.object === alvo, "o raio precisa atingir a borda renderizada");
      ponteiro.down({ timeStamp: 1, button: 0 }); assert.equal(ponteiro.getPointerCapture()?.object, alvo); assert.ok(inicio);
      const dados = inicio as ReturnType<typeof iniciarTamanhoPainel>;
      const mesmoRaio = new THREE.Ray(controle.position, ponto.clone().sub(controle.position).normalize());
      const primeiro = tamanhoPeloRaio(mesmoRaio, dados, pai.matrixWorld)!;
      assert.equal(primeiro.escala, escala); assert.ok(primeiro.posicao.distanceTo(painel.position) < 1e-6, "pressionar não causa salto");
      const destinoLocal = dados.ancoraLocal.clone().addScaledVector(dados.vetorInicial, 1.1); destinoLocal.z = 0.025;
      const destino = painel.localToWorld(destinoLocal);
      const novo = tamanhoPeloRaio(new THREE.Ray(controle.position, destino.sub(controle.position).normalize()), dados, pai.matrixWorld)!;
      assert.ok(novo.escala >= escala && novo.escala <= 1.55);
      painel.position.copy(novo.posicao); painel.scale.setScalar(novo.escala); cena.updateMatrixWorld(true);
      assert.ok(painel.localToWorld(dados.ancoraLocal.clone()).distanceTo(dados.ancoraMundo) < 1e-6, "canto/lado oposto fica parado");
      ponteiro.up({ timeStamp: 1000, button: 0 }); assert.equal(ponteiro.getPointerCapture(), undefined);
      ponteiro.exit({ timeStamp: 1100 }); alvo.geometry.dispose(); (alvo.material as THREE.Material).dispose(); redimensionamentos++;
    }
  }
}
// O plano contínuo aceita centro/cantos, mas não expande alvos para fora da placa.
const placa = new THREE.Mesh(new THREE.PlaneGeometry(0.7, 1.4), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
placa.raycast = raioPlacaXR; placa.position.set(0, 1, -2); placa.rotation.y = 0.4; placa.scale.setScalar(1.55); placa.updateMatrixWorld(true);
for (const [x, y, esperado] of [[0, 0, true], [-0.349, -0.699, true], [0.349, 0.699, true], [0.351, 0, false], [0, 0.701, false]] as const) {
  const destino = placa.localToWorld(new THREE.Vector3(x, y, 0)), origem = new THREE.Vector3(0.2, 1.6, 0);
  const raycaster = new THREE.Raycaster(origem, destino.sub(origem).normalize());
  const acertos = raycaster.intersectObject(placa);
  assert.equal(acertos.length, esperado ? 1 : 0);
  if (esperado) {
    assert.ok(Math.abs(acertos[0].uv!.x - (x / 0.7 + 0.5)) < 1e-6);
    raycaster.far = 0.1; assert.equal(raycaster.intersectObject(placa).length, 0);
    raycaster.far = Infinity; raycaster.near = 10; assert.equal(raycaster.intersectObject(placa).length, 0);
  }
}
placa.geometry.dispose(); placa.material.dispose();
const base = readFileSync("components/viewer/PainelXRBase.tsx", "utf8");
const painel = readFileSync("components/viewer/PainelSiteXR.tsx", "utf8");
for (const texto of ['label="Mais perto"', 'label="Mais longe"', 'label="Restaurar"', 'label="Subir"', 'label="Descer"', 'label="Abrir ossos"']) assert.ok(!(base + painel).includes(texto), "não reintroduzir fileiras extras");
assert.ok(base.includes('name="Mover janela pela alça inferior"') && base.includes("aoRedimensionar"));
assert.ok(readFileSync("lib/renderizar-painel-dom.ts", "utf8").includes("validarPixelsPainel"));
console.log(`ok: captura vazia recusada, estilo sem offsets ocultos, analógicos separados, câmera preservada e ${redimensionamentos} pegadas de borda sem salto`);
console.log("limite: pixels/estilos de teste e raios reais; rasterização final e headset ainda exigem inspeção visual");
