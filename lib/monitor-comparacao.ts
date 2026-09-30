/** Controles independentes da câmera do headset; só o modelo da tela gira. */
export type VistaMonitor = { horizontal: number; vertical: number; zoom: number };
export type ComandoVista = "esquerda" | "direita" | "cima" | "baixo" | "aproximar" | "afastar" | "restaurar";
export const VISTA_MONITOR_INICIAL: VistaMonitor = { horizontal: .4, vertical: .15, zoom: 1 };
export function ajustarVistaMonitor(vista: VistaMonitor, comando: ComandoVista): VistaMonitor {
  switch (comando) {
    case "esquerda": return { ...vista, horizontal: vista.horizontal - Math.PI / 12 };
    case "direita": return { ...vista, horizontal: vista.horizontal + Math.PI / 12 };
    case "cima": return { ...vista, vertical: Math.min(Math.PI / 2, vista.vertical + Math.PI / 12) };
    case "baixo": return { ...vista, vertical: Math.max(-Math.PI / 2, vista.vertical - Math.PI / 12) };
    case "aproximar": return { ...vista, zoom: Math.min(1.6, vista.zoom + .15) };
    case "afastar": return { ...vista, zoom: Math.max(.65, vista.zoom - .15) };
    case "restaurar": return { ...VISTA_MONITOR_INICIAL };
  }
}

/** O monitor usa orçamento fixo, independente do DPR da sessão ou do desktop. */
export const RESOLUCAO_MODELO_MONITOR = [640, 320] as const;
