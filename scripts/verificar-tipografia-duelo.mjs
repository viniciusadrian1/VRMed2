import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as THREE from "three";
import { criarMaterialTexto3D, layoutRotuloBotao, TIPOGRAFIA_3D } from "../lib/tipografia-3d.ts";
import { PERGUNTAS_DUELO, MODELOS_DUELO } from "../lib/duelo-perguntas.ts";
import { pintarTelao, RESOLUCAO_TELAO } from "../lib/telao-duelo.ts";

// O parser instalado do Troika permite medir a fonte real, sem navegador,
// rasterização, rede ou dependência nova. `self` é exigido pelo parser de fonte.
// Este acesso interno é restrito ao teste; não entra no bundle da aplicação.
globalThis.self = globalThis;
const { default: parse } = await import("troika-three-text/src/FontParser.js");
const bytes = readFileSync("public/fonts/inter-600.woff");
const fonte = await parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
const medir = (texto, tamanho) => fonte.forEachGlyph(texto, tamanho, 0, () => {});

function verificarLinha(texto, tamanho, largura, contexto) {
  assert.ok(medir(texto, tamanho) <= largura, `${contexto}: não pode quebrar linha — ${texto}`);
  for (const caractere of texto) {
    assert.ok(fonte.supportsCodePoint(caractere.codePointAt(0)), `glifo local ausente: ${caractere}`);
  }
}

for (const tratamento of Object.keys(TIPOGRAFIA_3D)) {
  const material = criarMaterialTexto3D(tratamento);
  const fisico = tratamento === "placa" || tratamento === "tela";
  assert.equal(material.depthTest, fisico, "só sinalização física respeita oclusão");
  assert.equal(material.depthWrite, false);
  assert.equal(material.transparent, true);
  assert.equal(material.side, fisico ? THREE.FrontSide : THREE.DoubleSide);
  assert.equal(material.toneMapped, tratamento === "placa");
  assert.equal(material instanceof THREE.MeshStandardMaterial, tratamento === "placa");
  assert.equal(TIPOGRAFIA_3D[tratamento].contorno, tratamento === "sobreposto" ? 0.05 : 0);
  material.dispose();
}

const opcoes = [...new Set([
  ...PERGUNTAS_DUELO.flatMap((p) => [p.resposta, ...p.distratores]),
  ...MODELOS_DUELO.map((m) => m.nome),
  "Epiglote", "Traqueia", "Cartilagem tireóidea", "Osso hioide",
])];

for (const [largura, altura] of [[1.55, 0.18], [1.1, 0.094]]) {
  const layout = layoutRotuloBotao(largura, altura, true, false);
  const direitaSelo = -largura / 2 + altura * (0.45 + 0.52 / 2);
  assert.ok(layout.x > direitaSelo, "o rótulo não invade o selo A–D");
  assert.ok(layout.x + layout.largura < largura / 2, "margem direita preservada");
  for (const opcao of opcoes) {
    const tamanho = largura === 1.55
      ? Math.min(0.069, 1.22 / Math.max(1, opcao.length * 0.55))
      : Math.min(0.05, altura * 0.5, largura * 0.86 / Math.max(1, opcao.length * 0.6));
    verificarLinha(opcao, tamanho, layout.largura, "alternativa");
    assert.ok(tamanho * TIPOGRAFIA_3D.interface.entrelinha < altura, "texto cabe na altura do alvo");
  }
}

const perguntas = PERGUNTAS_DUELO.map((p) => p.pergunta).concat(
  "Qual órgão é este?", "Qual estrutura está marcada em amarelo?",
);
const feedbacks = opcoes.flatMap((opcao) => [
  `Tempo esgotado — era: ${opcao}`, `Adversário pontuou: ${opcao}`,
]).concat("Você pontuou! +200 · combo x8");
for (const texto of [...perguntas, ...feedbacks]) {
  verificarLinha(texto, 0.036, 1.08, "enunciado da Escola");
  verificarLinha(texto, 0.058, 1.49, "enunciado do Hospital");
}

// As explicações podem ocupar duas linhas, mas permanecem na área de revisão.
for (const p of PERGUNTAS_DUELO) {
  for (const [tamanho, largura] of [[0.029, 1.08], [0.046, 1.49]]) {
    let linha = "", linhas = 1;
    for (const palavra of p.explicacao.split(" ")) {
      const candidata = linha ? `${linha} ${palavra}` : palavra;
      if (medir(candidata, tamanho) > largura) { linhas++; linha = palavra; }
      else linha = candidata;
    }
    assert.ok(linhas <= 2, `${p.id}: explicação cabe na área de revisão`);
  }
}

for (const texto of ["Últimos segundos · escolha na lousa", "Observe o órgão · responda na lousa"]) {
  verificarLinha(texto, 0.027, 0.88, "plaqueta do jogador");
}
verificarLinha("Sequência ×8 · continue assim", 0.034, 1.02, "placa abaixo da lousa");
verificarLinha("Ver esqueleto 3D", 0.14 * 0.42, 0.64 * 0.86, "vitrine");

// Cálculo de contraste das cores sRGB, não promessa de legibilidade no headset.
const luminancia = (cor) => 0.2126 * cor.r + 0.7152 * cor.g + 0.0722 * cor.b;
for (const cor of ["#5896c8", "#e06a5c", "#4fae89", "#31574d", "#3fd49a", "#f0796a"]) {
  const texto = luminancia(new THREE.Color("#f3f6f8"));
  const fundo = luminancia(new THREE.Color(cor).multiplyScalar(0.22));
  assert.ok((texto + 0.05) / (fundo + 0.05) >= 4.5, `contraste de rótulo ativo: ${cor}`);
}

const ui = readFileSync("components/arena/ui3d.tsx", "utf8");
const duelo = readFileSync("components/duelo/DueloGame.tsx", "utf8");
assert.match(ui, /tratamento = "sobreposto"/, "outros modos mantêm o padrão anterior");
assert.match(ui, /sombra\(corEstado, 0\.22\)/, "mesmo contraste medido neste teste");
assert.match(ui, /material=\{MATERIAIS_TEXTO\[tratamento\]\}/);
assert.match(ui, /raycast=\{\(\) => null\}/, "texto não vira novo alvo de laser");
assert.match(ui, /<group ref=\{group\} pointerEvents="none">/);
assert.match(duelo, /LOUSA_X - 0\.54, 0\.082, LOUSA_Z/, "aviso de erro fora da pergunta");
assert.match(duelo, /<TelaoDuelo position=\{HOSP_LED\}/, "letreiro integrado à superfície do monitor");
// Mede as linhas do monitor com a mesma fonte local. O desenho real é inspecionado
// no navegador; o contexto de teste apenas registra coordenadas e comandos.
assert.deepEqual(RESOLUCAO_TELAO, [1024, 320]);
for (const valor of ["DUELO 1×1", "0 × 0", "1600 × 1600", "3200 × 3200", ...Array.from({ length: 19 }, (_, i) => String(i))]) {
  const desenhos = [];
  const ctx = {
    font: "", textAlign: "", textBaseline: "",
    createLinearGradient: () => ({ addColorStop() {} }),
    fillRect() {}, strokeRect() {},
    measureText(texto) {
      const tamanho = Number(this.font.split(" ")[1].replace("px", ""));
      return { width: medir(texto, tamanho), actualBoundingBoxAscent: tamanho*.7, actualBoundingBoxDescent: tamanho*.2 };
    },
    fillText(texto, x, y) { desenhos.push({ texto, x, y, medida: this.measureText(texto) }); },
  };
  pintarTelao(ctx, valor, "#9ccdd4", "Inter");
  assert.equal(desenhos.length, 1, "uma inscrição por estado");
  const desenho = desenhos[0];
  assert.equal(desenho.x, 512); assert.equal(ctx.textAlign, "center");
  assert.ok(desenho.medida.width <= 881, `${valor}: respeita a margem do monitor`);
  assert.ok(Math.abs(desenho.y - (desenho.medida.actualBoundingBoxAscent-desenho.medida.actualBoundingBoxDescent)/2 - 160) < .001);
}
const telao = readFileSync("components/duelo/TelaoDuelo.tsx", "utf8");
assert.doesNotMatch(telao, /useFrame|setInterval|requestAnimationFrame/);
assert.match(telao, /textura\.dispose\(\)/);
assert.match(telao, /pointerEvents="none"/);
assert.match(telao, /emissiveIntensity=\{\.35\} depthTest depthWrite/);
console.log(`ok: materiais, oclusão, fonte local, ${opcoes.length} rótulos, 30 perguntas, feedbacks, margens e contraste`);
