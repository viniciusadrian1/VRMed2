/** Raiz de captura independente das coordenadas usadas para esconder o DOM auxiliar. */
export function estiloRaizCapturada(largura: number, altura: number, ler: (nome: string) => string) {
  const estilo: Record<string, string> = {
    position: "relative", display: "block", left: "0px", top: "0px", width: largura + "px", height: altura + "px",
    margin: "0px", padding: "0px", overflow: "hidden", "box-sizing": "border-box", opacity: "1", visibility: "visible",
  };
  for (const nome of ["background-color", "color", "font-family", "font-size", "font-weight", "font-style", "line-height",
    "letter-spacing", "word-spacing", "text-align", "direction", "writing-mode", "color-scheme", "font-feature-settings", "font-variation-settings"]) {
    const valor = ler(nome); if (valor) estilo[nome] = valor;
  }
  return estilo;
}

/** Rejeita textura vazia/uniforme: getImageData sem exceção não prova que o HTML foi desenhado. */
export function validarPixelsPainel(pixels: Uint8ClampedArray) {
  let opacos = 0, contraste = 0, base: [number, number, number] | null = null;
  for (let i = 0; i < pixels.length; i += 4) {
    if (pixels[i + 3] < 230) continue;
    opacos++;
    if (!base) base = [pixels[i], pixels[i + 1], pixels[i + 2]];
    if (Math.max(Math.abs(pixels[i] - base[0]), Math.abs(pixels[i + 1] - base[1]), Math.abs(pixels[i + 2] - base[2])) > 24) contraste++;
  }
  return opacos >= pixels.length / 16 && contraste >= Math.max(24, opacos / 2000);
}
/** Propriedades visuais usadas pelos painéis. Não copiar os ~450 defaults do navegador por nó. */
export const ESTILOS_CAPTURA = [
  "display", "position", "top", "right", "bottom", "left", "z-index", "box-sizing",
  "width", "height", "min-width", "max-width", "min-height", "max-height", "aspect-ratio",
  "margin-top", "margin-right", "margin-bottom", "margin-left", "padding-top", "padding-right", "padding-bottom", "padding-left",
  "flex-direction", "flex-wrap", "flex-grow", "flex-shrink", "flex-basis", "order", "align-items", "align-self", "align-content", "justify-content", "justify-items", "justify-self", "gap",
  "grid-template-columns", "grid-template-rows", "grid-auto-flow", "grid-column", "grid-row",
  "overflow-x", "overflow-y", "scrollbar-width", "scrollbar-color", "visibility", "opacity", "clip", "clip-path",
  "background-color", "background-image", "background-size", "background-position", "background-repeat", "background-clip",
  "border-top", "border-right", "border-bottom", "border-left", "border-radius", "box-shadow", "outline", "outline-offset",
  "color", "font-family", "font-size", "font-weight", "font-style", "font-variant-numeric", "font-feature-settings", "font-variation-settings",
  "line-height", "letter-spacing", "word-spacing", "text-align", "text-indent", "text-transform", "text-decoration", "text-shadow", "text-overflow",
  "white-space", "overflow-wrap", "word-break", "vertical-align", "direction", "writing-mode", "tab-size", "text-rendering",
  "list-style-type", "list-style-position", "border-collapse", "border-spacing", "table-layout",
  "transform", "transform-origin", "translate", "rotate", "scale", "object-fit", "object-position", "filter",
  "fill", "fill-opacity", "fill-rule", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "vector-effect",
  "appearance", "accent-color", "color-scheme", "-webkit-text-fill-color", "-webkit-text-stroke-width", "-webkit-text-stroke-color",
] as const;

/** Retém o espaço de itens fora da janela de rolagem; não altera o DOM original. */
export function itemForaDaCaptura(item: { top: number; bottom: number }, janela: { top: number; bottom: number }) {
  return item.bottom < janela.top - 2 || item.top > janela.bottom + 2;
}
