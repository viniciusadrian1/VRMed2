/** Conteúdo do monitor é uma única superfície opaca, não letras soltas no ar. */
export const RESOLUCAO_TELAO = [1024, 320] as const;

export function pintarTelao(ctx: CanvasRenderingContext2D, texto: string, cor: string, fonte: string) {
  const [w, h] = RESOLUCAO_TELAO;
  const fundo = ctx.createLinearGradient(0, 0, 0, h);
  fundo.addColorStop(0, "#17303a"); fundo.addColorStop(1, "#0b1b23");
  ctx.fillStyle = fundo; ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = "#33505a"; ctx.lineWidth = 2;
  ctx.strokeRect(14, 14, w-28, h-28);
  ctx.fillStyle = cor;
  ctx.fillRect(44, 34, 24, 6); ctx.fillRect(w-68, 34, 24, 6);
  ctx.fillRect(44, h-40, w-88, 3);
  const titulo = texto === "DUELO 1×1" ? "Duelo 1×1" : texto;
  let tamanho = /^\d+$/.test(titulo) ? 208 : 154;
  ctx.font = `600 ${tamanho}px ${fonte}`;
  tamanho *= Math.min(1, (w-144) / Math.max(1, ctx.measureText(titulo).width));
  ctx.font = `600 ${tamanho}px ${fonte}`;
  ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
  const medida = ctx.measureText(titulo);
  const y = h/2 + (medida.actualBoundingBoxAscent-medida.actualBoundingBoxDescent)/2;
  // Título neutro no menu; tempo/placar preservam as cores de estado da partida.
  ctx.fillStyle = texto === "DUELO 1×1" ? "#e2ebe8" : cor;
  ctx.fillText(titulo, w/2, y);
}
