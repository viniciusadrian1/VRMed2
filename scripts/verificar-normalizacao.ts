/**
 * Confere que `normalizeContent` não depende da pose do pai.
 *
 * Em AR/VR o pai do conteúdo (o root do OrganModel) já está escalado para o
 * tamanho real e posto à frente dos olhos. Se a normalização rodar nesse
 * momento — GLB terminando de carregar com a sessão aberta — e medir em mundo,
 * todo órgão vira 2 m e sai descentrado. Este script monta exatamente isso e
 * reprova se acontecer.
 *
 * Rodar: npx -y tsx scripts/verificar-normalizacao.ts
 */
import * as THREE from "three";
import { normalizeContent } from "../lib/model-utils";

const pai = new THREE.Group();
pai.scale.setScalar(14 / 100 / 2); // coração, 14 cm
pai.position.set(0.3, 1.25, -0.4);
pai.rotation.set(0.4, 1.1, -0.2);

// Nó girado fora dos eixos, como o do rim: a caixa rápida incharia.
const conteudo = new THREE.Group();
const no = new THREE.Group();
no.rotation.set(0.6, 0.3, 0.9);
no.position.set(5, -3, 2);
// Tetraedro esticado, e não caixa: os vértices de uma BoxGeometry são os
// cantos da própria caixa, e aí a medida rápida empata com a precisa — o teste
// passaria mesmo sem `precise`.
const malha = new THREE.Mesh(new THREE.TetrahedronGeometry(3));
malha.scale.set(1, 2, 0.7);
no.add(malha);
conteudo.add(no);
pai.add(conteudo);
pai.updateMatrixWorld(true);

normalizeContent(conteudo);

// Medida de referência no espaço do pai, vértice a vértice.
const noPai = new THREE.Box3();
const v = new THREE.Vector3();
const pos = (no.children[0] as THREE.Mesh).geometry.getAttribute("position");
const matriz = new THREE.Matrix4()
  .copy(conteudo.matrix)
  .multiply(no.matrix)
  .multiply(malha.matrix);
for (let i = 0; i < pos.count; i++) {
  noPai.expandByPoint(v.fromBufferAttribute(pos, i).applyMatrix4(matriz));
}
const tam = noPai.getSize(new THREE.Vector3());
const centro = noPai.getCenter(new THREE.Vector3());
const maior = Math.max(tam.x, tam.y, tam.z);

const falhas: string[] = [];
if (Math.abs(maior - 2) > 1e-6) falhas.push(`maior eixo ${maior}, esperado 2`);
if (centro.length() > 1e-6) falhas.push(`centro ${centro.toArray()}, esperado origem`);
// A matriz de mundo do pai tem de voltar intacta.
const esperado = new THREE.Matrix4().compose(pai.position, pai.quaternion, pai.scale);
if (!pai.matrixWorld.equals(esperado)) falhas.push("matriz de mundo do pai alterada");

if (falhas.length) {
  console.error("FALHA:\n  " + falhas.join("\n  "));
  process.exit(1);
}
console.log("ok: normalização independe da pose do pai e mede por vértice");
