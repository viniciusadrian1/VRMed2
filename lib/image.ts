/**
 * Reduz um dataURL de imagem a um JPEG compacto.
 * Usado para os thumbnails das sessões salvas — mantém o uso de localStorage
 * sob controle, já que screenshots PNG do canvas WebGL podem ser grandes.
 */
export function downscaleDataUrl(
  dataUrl: string,
  maxWidth = 900,
  quality = 0.82,
): Promise<string> {
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => {
      const scale = Math.min(1, maxWidth / image.width);
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(image.width * scale);
      canvas.height = Math.round(image.height * scale);
      const context = canvas.getContext("2d");
      if (!context) {
        resolve(dataUrl);
        return;
      }
      // O canvas WebGL é transparente — preenche um fundo branco antes.
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL("image/jpeg", quality));
    };
    image.onerror = () => resolve(dataUrl);
    image.src = dataUrl;
  });
}
