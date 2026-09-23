import { create } from "zustand";
import { Matrix4, Object3D, Plane, Ray, Vector3 } from "three";

export type JanelaXR = "ferramentas" | "tutor";
export const LIMITES_JANELA_XR = { escalaMin: 0.65, escalaMax: 1.55, x: 2.2, yMin: -0.65, yMax: 0.75, zPerto: -0.55, zLonge: -2.4 } as const;
export const useJanelasEstudoXR = create<{
  abertas: Record<JanelaXR, boolean>; frente: JanelaXR; revisao: number;
  abrir: (id: JanelaXR, aberto: boolean) => void; focar: (id: JanelaXR) => void; restaurarLayout: () => void;
}>((set) => ({
  abertas: { ferramentas: true, tutor: true }, frente: "tutor", revisao: 0,
  abrir: (id, aberto) => set((s) => ({ abertas: { ...s.abertas, [id]: aberto }, frente: id })),
  focar: (id) => set((s) => s.frente === id ? s : { frente: id }),
  restaurarLayout: () => set((s) => ({ revisao: s.revisao + 1 })),
}));

export function escalaPainelXR(escala: number) {
  if (!Number.isFinite(escala)) return 1;
  return Math.max(LIMITES_JANELA_XR.escalaMin, Math.min(LIMITES_JANELA_XR.escalaMax, Math.round(escala * 100) / 100));
}
/** Interseção com o plano atual, inclusive quando o raio sai da área de toque. */
export function opacidadePeloRaio(raio: Ray, matriz: Matrix4, largura: number): number | null {
  const plano = new Plane(new Vector3(0, 0, 1), 0).applyMatrix4(matriz);
  const ponto = raio.intersectPlane(plano, new Vector3());
  if (!ponto || largura <= 0) return null;
  const local = ponto.applyMatrix4(matriz.clone().invert());
  return Math.max(0, Math.min(1, Math.round((local.x / largura + 0.5) * 100) / 100));
}
export function limitarPosicaoPainel(ponto: Vector3) {
  const l = LIMITES_JANELA_XR;
  ponto.x = Math.max(-l.x, Math.min(l.x, ponto.x));
  ponto.y = Math.max(l.yMin, Math.min(l.yMax, ponto.y));
  ponto.z = Math.max(l.zLonge, Math.min(l.zPerto, ponto.z));
  return ponto;
}
export function iniciarArrastePainel(painel: Object3D, ponto: Vector3, raio: Ray) {
  return { distancia: Math.max(0.1, raio.origin.distanceTo(ponto)), deslocamento: painel.getWorldPosition(new Vector3()).sub(ponto) };
}
/** Distância fixa ao raio capturado: sair da barra não interrompe o arraste. */
export function posicaoArrastadaPainel(raio: Ray, inicio: ReturnType<typeof iniciarArrastePainel>, matrizDoPai: Matrix4) {
  const mundo = raio.at(inicio.distancia, new Vector3()).add(inicio.deslocamento);
  return limitarPosicaoPainel(mundo.applyMatrix4(matrizDoPai.clone().invert()));
}
/** No desktop, a ordem dos alvos acompanha a ordem visual das janelas XR. */
export function ordenarAlvosPaineis<T extends { object: Object3D; distance: number }>(itens: T[]): T[] {
  const ordem = (o: Object3D) => {
    let valor = 0;
    for (let atual: Object3D | null = o; atual; atual = atual.parent) {
      if (!atual.visible) return -1;
      valor = Math.max(valor, Number(atual.userData.ordemJanelaXR) || 0);
    }
    return valor;
  };
  return itens.filter((i) => ordem(i.object) >= 0).sort((a, b) => ordem(b.object) - ordem(a.object) || a.distance - b.distance);
}
