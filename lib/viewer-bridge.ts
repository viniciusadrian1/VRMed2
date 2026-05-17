import type { Vec3 } from "@/types";

/**
 * Ponte imperativa entre a UI React (toolbar, exportação) e o mundo 3D
 * dentro do <Canvas>. Componentes do canvas registram suas implementações;
 * a interface externa as invoca. Vale para a instância principal do visualizador.
 */
export interface ViewerBridge {
  /** Captura o canvas como dataURL PNG (ou null se indisponível). */
  capture: () => string | null;
  /** Reposiciona a câmera na vista padrão. */
  resetCamera: () => void;
  /** Anima a câmera até enquadrar um ponto do modelo. */
  frameTo: (point: Vec3) => void;
  /** Aproxima (fator < 1) ou afasta (fator > 1) a câmera. */
  zoom: (factor: number) => void;
  /** Solicita a entrada em modo VR (WebXR). */
  enterVR: () => void;
}

export const viewerBridge: ViewerBridge = {
  capture: () => null,
  resetCamera: () => {},
  frameTo: () => {},
  zoom: () => {},
  enterVR: () => {},
};
