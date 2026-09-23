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
