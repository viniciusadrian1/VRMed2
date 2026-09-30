import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DoubleSide, Group, Matrix4, Mesh, MeshBasicMaterial, PerspectiveCamera, PlaneGeometry, Quaternion, Raycaster, Scene, Vector3 } from "three";
import { createRayPointer } from "@pmndrs/pointer-events";
import { ASSENTO_SALA, CONTROLES_SALA, apertouRecentralizarSala, calcularRecentralizacaoSala, type EstadoAtalhoSala } from "../lib/sala-recentrar.ts";
import { ORDEM_PONTEIRO_UI, deveAcionarBotao3D } from "../lib/botao3d-interacao.ts";
import { raioPlacaXR } from "../lib/raio-placa-xr.ts";

function perto(a: number, b: number, descricao: string) {
  assert.ok(Math.abs(a - b) < 1e-8, `${descricao}: ${a} != ${b}`);
}

// Poses centrais sintéticas: validam matemática/raycast, não simulam um Quest.
let poses = 0;
for (const altura of [0.95, 1.2, 1.75]) {
  for (const angulo of [0, Math.PI / 2, -Math.PI / 2, Math.PI, 0.37]) {
    for (const piso of [0, 0.25]) {
      const cena = new Scene();
      const sala = new Group();
      cena.add(sala);
      const cabeca = new Vector3(1.8, piso + altura, -0.35);
      const frente = new Vector3(-Math.sin(angulo), -0.25, -Math.cos(angulo)).normalize();
      const ajuste = calcularRecentralizacaoSala(cabeca, frente, piso);
      assert.ok(ajuste);
      // Substitui qualquer transformação anterior, sem acumular deslocamento.
      sala.position.set(10, 0, -7);
      sala.rotation.y = 2.1;
      sala.position.fromArray(ajuste.posicao);
      sala.rotation.set(0, ajuste.rotacaoY, 0);
      sala.updateWorldMatrix(true, true);
      const assento = sala.localToWorld(new Vector3(...ASSENTO_SALA));
      perto(assento.x, cabeca.x, "assento sob a cabeça (x)");
      perto(assento.z, cabeca.z, "assento sob a cabeça (z)");
      perto(assento.y, piso, "piso sem altura artificial");
      perto(cabeca.y - assento.y, altura, "altura real preservada");
      const mesa = sala.localToWorld(new Vector3(0, 0.765, -1.9));
      const direcaoMesa = mesa.clone().sub(assento).setY(0).normalize();
      perto(direcaoMesa.dot(frente.clone().setY(0).normalize()), 1, "mesa à frente");
      perto(mesa.y - piso, 0.765, "móveis continuam no mesmo nível");
      assert.deepEqual(sala.scale.toArray(), [1, 1, 1]);
      assert.equal(sala.rotation.x, 0);
      assert.equal(sala.rotation.z, 0);
      assert.deepEqual(calcularRecentralizacaoSala(cabeca, frente, piso), ajuste, "repetir não acumula deriva");

      // O alvo via Button3D continua clicável para ambas as mãos após a rotação.
      const controles = new Group();
      controles.position.set(CONTROLES_SALA.x, ajuste.alturaControles, CONTROLES_SALA.z);
      controles.rotation.y = CONTROLES_SALA.rotacaoY;
      sala.add(controles);
      let cliques = 0;
      const botao = new Mesh(new PlaneGeometry(0.52, 0.11), new MeshBasicMaterial({ side: DoubleSide }));
      botao.raycast = raioPlacaXR;
      botao.position.fromArray(CONTROLES_SALA.recentralizar);
      botao.pointerEventsOrder = ORDEM_PONTEIRO_UI;
      botao.addEventListener("pointerdown", (evento) => {
        if (deveAcionarBotao3D("pressionar", evento)) cliques++;
      });
      controles.add(botao);
      for (const posicao of [CONTROLES_SALA.recentralizar, CONTROLES_SALA.sair]) for (const mao of [-1, 1]) {
        botao.position.fromArray(posicao);
        const controle = new Group();
        controle.position.copy(cabeca).add(new Vector3(mao * 0.22, -0.25, 0.05));
        cena.add(controle);
        cena.updateMatrixWorld(true);
        const alvo = botao.getWorldPosition(new Vector3());
        controle.quaternion.setFromRotationMatrix(new Matrix4().lookAt(controle.position, alvo, new Vector3(0, 1, 0)));
        cena.updateMatrixWorld(true);
        const raio = createRayPointer(() => new PerspectiveCamera(), { current: controle }, {});
        raio.move(cena, { timeStamp: 1 });
        assert.ok(raio.getIntersection()?.object === botao, `mira: altura=${altura}, giro=${angulo}, piso=${piso}, mão=${mao}, botão=${posicao}`);
        raio.down({ timeStamp: 2, button: 0 });
        raio.up({ timeStamp: 702, button: 0 });
      }
      assert.equal(cliques, 4, "os dois botões respondem às duas mãos, inclusive com gatilho longo");
      poses++;
    }
  }
}

const cabeca = new Vector3(0, 1.2, -1.15);
// A faixa inteira fica fora da projeção do monitor e do eixo central da mesa.
const xMin = CONTROLES_SALA.x - Math.abs(Math.cos(CONTROLES_SALA.rotacaoY)) * CONTROLES_SALA.largura / 2;
assert.ok(xMin > 0.78, "borda interna não invade a área central de trabalho");
const painelLateral = new Group();
painelLateral.position.set(CONTROLES_SALA.x, 0.9, CONTROLES_SALA.z);
painelLateral.rotation.y = CONTROLES_SALA.rotacaoY;
painelLateral.updateMatrixWorld(true);
const normal = new Vector3(0, 0, 1).transformDirection(painelLateral.matrixWorld);
const paraAluno = new Vector3(0, 0.9, ASSENTO_SALA[2]).sub(painelLateral.position).normalize();
perto(normal.dot(paraAluno), 1, "painel lateral voltado ao assento");
// Linhas de visão para a frente da mesa em três alturas sentadas/em pé.
// A posição lateral não basta: um painel muito à frente ainda encobre o rádio.
const superficie = new Mesh(new PlaneGeometry(CONTROLES_SALA.largura, CONTROLES_SALA.altura), new MeshBasicMaterial({ side: DoubleSide }));
superficie.raycast = raioPlacaXR;
painelLateral.add(superficie);
for (const altura of [0.95, 1.2, 1.75]) {
  painelLateral.position.y = Math.max(0.5, altura - 0.38);
  painelLateral.updateMatrixWorld(true);
  const olho = new Vector3(0, altura, ASSENTO_SALA[2]);
  for (const [nome, pontos] of [
    ["monitor", [[-0.52, 1, -2.046], [0.52, 1, -2.046], [-0.52, 1.7, -2.046], [0.52, 1.7, -2.046]]],
    ["rádio", [[0.7, 0.77, -2.01], [1.16, 0.77, -2.01], [0.7, 1, -2.01], [1.16, 1, -2.01]]],
    ["livro", [[-0.75, 0.82, -1.85], [-0.22, 0.82, -1.85]]],
  ] as const) for (const ponto of pontos) {
    const direcao = new Vector3(...ponto).sub(olho);
    const raio = new Raycaster(olho, direcao.clone().normalize(), 0, direcao.length());
    assert.equal(raio.intersectObject(superficie).length, 0, `painel não encobre ${nome} na altura ${altura}`);
  }
}
superficie.geometry.dispose();
superficie.material.dispose();
assert.equal(calcularRecentralizacaoSala(cabeca, new Vector3(0, 1, 0), 0), null);
assert.equal(calcularRecentralizacaoSala(new Vector3(NaN, 1, 0), new Vector3(0, 0, -1), 0), null);
assert.equal(calcularRecentralizacaoSala(cabeca, new Vector3(0, 0, -1), Infinity), null);
// Aplicar a origem à pose central não introduz o deslocamento de um dos olhos.
const origem = new Matrix4().compose(new Vector3(2, 0, -3), new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), 0.6), new Vector3(1, 1, 1));
const central = new Vector3(0.2, 1.15, 0.1).applyMatrix4(origem);
const direcao = new Vector3(0, 0, -1).transformDirection(origem);
assert.ok(calcularRecentralizacaoSala(central, direcao, 0));

const estado: EstadoAtalhoSala = { fonte: undefined, pressionado: false };
const controle = {};
assert.equal(apertouRecentralizarSala(estado, controle, true), false, "conectar segurando não dispara");
assert.equal(apertouRecentralizarSala(estado, controle, false), false);
assert.equal(apertouRecentralizarSala(estado, controle, true), true);
assert.equal(apertouRecentralizarSala(estado, controle, true), false, "segurar não repete");
assert.equal(apertouRecentralizarSala(estado, undefined, false), false);
assert.equal(apertouRecentralizarSala(estado, {}, true), false, "reconectar não dispara");

const componente = readFileSync("components/sala/SalaRecentravelXR.tsx", "utf8");
assert.match(readFileSync("components/arena/ui3d.tsx", "utf8"), /name=\{`alvo-botao-\$\{selo \?\? label\}`\} raycast=\{raioPlacaXR\}/);
const app = readFileSync("components/sala/SalaApp.tsx", "utf8");
assert.match(componente, /pose\.emulatedPosition/);
assert.match(componente, /session\.visibilityState !== "visible"/);
assert.match(componente, /if \(!session\) return/);
assert.match(componente, /performance\.now\(\) > atual\.prazo/);
assert.match(componente, /"y-button"/);
assert.match(componente, /"b-button"/);
assert.match(componente, /label="Recentralizar"/);
assert.match(componente, /<SairDoVR[^>]+\/>\s*\{session &&/);
assert.match(app, /<SalaRecentravelXR>[\s\S]*<ErrorBoundary[\s\S]*<CenaSala[\s\S]*<\/ErrorBoundary>[\s\S]*<\/SalaRecentravelXR>/);
assert.doesNotMatch(componente, /camera\.(position|rotation|quaternion)\.(set|copy)|key=\{|enterVR\(/);
console.log(`Sala: ${poses} poses, alturas, orientação, dois raios, rastreio e atalhos verificados. Validação no Quest físico pendente.`);
