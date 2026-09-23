import { Matrix4, Object3D, Plane, Ray, Vector3 } from "three";
import { escalaPainelXR, limitarPosicaoPainel } from "./janelas-estudo-xr.ts";

export type BordaPainelXR = { x: -1 | 0 | 1; y: -1 | 0 | 1 };
export function alcaJanelaXR(altura: number, aberto: boolean) {
  return { x: 0, y: aberto ? -altura / 2 - 0.10 : -0.075, largura: 0.29, altura: 0.055 };
}
export function zonasBordaXR(largura: number, altura: number) {
  const zonas: { borda: BordaPainelXR; x: number; y: number; largura: number; altura: number }[] = [];
  for (const x of [-1, 0, 1] as const) for (const y of [-1, 0, 1] as const) {
    if (!x && !y) continue;
    zonas.push({ borda: { x, y }, x: x * (largura / 2 + 0.024), y: y * (altura / 2 + 0.024),
      largura: x ? 0.05 : largura - 0.06, altura: y ? 0.05 : altura - 0.06 });
  }
  return zonas;
}

/** A borda oposta fica ancorada: puxar o canto não faz a janela deslizar pelo mundo. */
export function iniciarTamanhoPainel(painel: Object3D, ponto: Vector3, borda: BordaPainelXR, largura: number, altura: number) {
  painel.updateWorldMatrix(true, false);
  const inversa = painel.matrixWorld.clone().invert();
  const ancoraLocal = new Vector3(-borda.x * largura / 2, -borda.y * altura / 2, 0);
  const plano = new Plane(new Vector3(0, 0, 1), 0).applyMatrix4(painel.matrixWorld);
  plano.constant = -plano.normal.dot(ponto);
  const vetorInicial = ponto.clone().applyMatrix4(inversa).sub(ancoraLocal); vetorInicial.z = 0;
  return {
    borda, inversa, escala: painel.scale.x,
    plano, ancoraLocal, vetorInicial,
    ancoraMundo: ancoraLocal.clone().applyMatrix4(painel.matrixWorld),
    centroMundo: painel.getWorldPosition(new Vector3()),
  };
}
export function tamanhoPeloRaio(raio: Ray, inicio: ReturnType<typeof iniciarTamanhoPainel>, pai: Matrix4) {
  const p = raio.intersectPlane(inicio.plano, new Vector3());
  if (!p) return null;
  const vetor = p.applyMatrix4(inicio.inversa).sub(inicio.ancoraLocal), base = inicio.vetorInicial;
  vetor.z = 0;
  const fator = inicio.borda.x && inicio.borda.y ? vetor.dot(base) / base.lengthSq() :
    inicio.borda.x ? vetor.x / base.x : vetor.y / base.y;
  if (!Number.isFinite(fator)) return null;
  const escala = escalaPainelXR(inicio.escala * fator);
  const centro = inicio.centroMundo.clone().sub(inicio.ancoraMundo).multiplyScalar(escala / inicio.escala).add(inicio.ancoraMundo);
  return { escala, posicao: limitarPosicaoPainel(centro.applyMatrix4(pai.clone().invert())) };
}
