import { colherAlvosDOM, type AlvoDOMXR } from "./painel-dom-xr";

export type QuadroPainelDOM = { canvas: HTMLCanvasElement; alvos: AlvoDOMXR[] };
let fonteLocal: Promise<string> | undefined;
let fila: Promise<unknown> = Promise.resolve();
function fonteEmbutida() {
  return fonteLocal ??= fetch("/fonts/inter-600.woff").then((r) => {
    if (!r.ok) throw new Error("Fonte local indisponível");
    return r.blob();
  }).then((blob) => new Promise<string>((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = reject; reader.readAsDataURL(blob);
  })).catch((erro) => { fonteLocal = undefined; throw erro; });
}

/** Clona só o painel. CSS real é rasterizado pelo navegador, não reinterpretado em 3D. */
function clonarComEstilos(original: Element): Element {
  const copia = original.cloneNode(false) as HTMLElement | SVGElement, estilo = getComputedStyle(original);
  for (const propriedade of estilo) {
    if (!propriedade.startsWith("--")) copia.style.setProperty(propriedade, estilo.getPropertyValue(propriedade));
  }
  copia.style.animation = "none"; copia.style.transition = "none"; copia.style.caretColor = "transparent";
  // Nenhuma imagem externa é solicitada ao transformar o conteúdo em textura.
  if (copia instanceof HTMLImageElement && !copia.src.startsWith("data:")) copia.removeAttribute("src");
  for (const filho of original.childNodes) {
    if (filho instanceof Element) {
      if (!["SCRIPT", "STYLE", "IFRAME"].includes(filho.tagName.toUpperCase())) copia.appendChild(clonarComEstilos(filho));
    } else copia.appendChild(filho.cloneNode());
  }
  if (original instanceof HTMLTextAreaElement) copia.textContent = original.value;
  if (original instanceof HTMLInputElement) {
    copia.setAttribute("value", original.value);
    if (original.checked) copia.setAttribute("checked", "checked"); else copia.removeAttribute("checked");
  }
  // scrollTop não sobrevive à serialização SVG: transforma só o conteúdo, mantendo o recorte.
  if (original instanceof HTMLElement && original.hasAttribute("data-xr-scroll") && (original.scrollTop || original.scrollLeft)) {
    const conteudo = document.createElement("div");
    conteudo.style.transform = `translate(${-original.scrollLeft}px, ${-original.scrollTop}px)`;
    while (copia.firstChild) conteudo.appendChild(copia.firstChild);
    copia.appendChild(conteudo);
  }
  return copia;
}
async function desenharPainel(raiz: HTMLElement, escala: number): Promise<QuadroPainelDOM> {
  await document.fonts.ready;
  const fonte = await fonteEmbutida();
  const largura = raiz.clientWidth, altura = raiz.clientHeight;
  if (!largura || !altura || !raiz.isConnected) throw new Error("Painel não está montado");
  // Geometria de interação e imagem são capturadas no mesmo instante de layout.
  const alvos = colherAlvosDOM(raiz), copia = clonarComEstilos(raiz) as HTMLElement;
  copia.style.position = "relative"; copia.style.left = "0"; copia.style.top = "0"; copia.style.right = "auto"; copia.style.margin = "0";
  copia.style.width = largura + "px"; copia.style.height = altura + "px"; copia.removeAttribute("aria-hidden");
  const style = document.createElement("style");
  const placeholder = getComputedStyle(raiz.querySelector("textarea,input") ?? raiz, "::placeholder").color;
  style.textContent = `@font-face{font-family:"VRmed Inter";src:url("${fonte}") format("woff");font-weight:600;font-style:normal}textarea::placeholder,input::placeholder{color:${placeholder}}`;
  copia.prepend(style);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(largura * escala)); svg.setAttribute("height", String(altura * escala));
  svg.setAttribute("viewBox", `0 0 ${largura} ${altura}`);
  const objeto = document.createElementNS(svg.namespaceURI, "foreignObject");
  objeto.setAttribute("width", String(largura)); objeto.setAttribute("height", String(altura)); objeto.appendChild(copia); svg.appendChild(objeto);
  const endereco = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(svg));
  const imagem = await new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image(), timer = window.setTimeout(() => reject(new Error("Tempo esgotado ao renderizar painel")), 5000);
    img.onload = () => { clearTimeout(timer); resolve(img); };
    img.onerror = () => { clearTimeout(timer); reject(new Error("O navegador não conseguiu renderizar o painel HTML")); };
    img.src = endereco;
  });
  const canvas = document.createElement("canvas");
  canvas.width = largura * escala; canvas.height = altura * escala;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D indisponível");
  ctx.drawImage(imagem, 0, 0);
  // Detecta canvas contaminado/recusado antes de enviá-lo ao WebGL.
  ctx.getImageData(0, 0, 1, 1);
  return { canvas, alvos };
}
export function renderizarPainelDOM(raiz: HTMLElement, escala = 2) {
  // Duas telas não clonam/rasterizam simultaneamente no Quest.
  const pedido = fila.then(() => desenharPainel(raiz, escala));
  fila = pedido.catch(() => {});
  return pedido;
}
