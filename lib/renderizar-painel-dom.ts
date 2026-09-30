import { colherAlvosDOM, type AlvoDOMXR } from "./painel-dom-xr";
import { ESTILOS_CAPTURA, estiloRaizCapturada, itemForaDaCaptura, validarPixelsPainel } from "./painel-captura-xr";

export type QuadroPainelDOM = { canvas: HTMLCanvasElement; alvos: AlvoDOMXR[] };
let fonteLocal: Promise<string> | undefined;
let fila: Promise<unknown> = Promise.resolve();
const buffers = new WeakMap<HTMLElement, { frente?: HTMLCanvasElement; verso?: HTMLCanvasElement }>();
type Estilos = { classes: Map<string, string>; janela: DOMRect; nos: number };
function fonteEmbutida() {
  return fonteLocal ??= fetch("/fonts/inter-600.woff").then((r) => {
    if (!r.ok) throw new Error("Fonte local indisponível");
    return r.blob();
  }).then((blob) => new Promise<string>((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(String(reader.result)); reader.onerror = reject; reader.readAsDataURL(blob);
  })).catch((erro) => { fonteLocal = undefined; throw erro; });
}

/** Clona só o painel. CSS real é rasterizado pelo navegador, não reinterpretado em 3D. */
function clonarComEstilos(original: Element, estilos: Estilos): Element {
  const copia = original.cloneNode(false) as HTMLElement | SVGElement, estilo = getComputedStyle(original);
  estilos.nos++;
  // Abas ocultas (incluindo Áudio forceMount) não precisam de cópia dos descendentes.
  if (estilo.display === "none") { copia.style.cssText = "display:none"; return copia; }
  if (original.hasAttribute("data-xr-item")) {
    const caixa = original.getBoundingClientRect();
    const rolagem = original.closest("[data-xr-scroll]")?.getBoundingClientRect() ?? estilos.janela;
    const janela = { top: Math.max(estilos.janela.top, rolagem.top), bottom: Math.min(estilos.janela.bottom, rolagem.bottom) };
    if (itemForaDaCaptura(caixa, janela)) {
      // Medida real mantém posição, rolagem e alvos. O item reaparece ao entrar no recorte.
      copia.style.cssText = `box-sizing:border-box;flex-shrink:0;height:${caixa.height}px;min-height:${caixa.height}px;width:${caixa.width}px;margin:${estilo.margin};visibility:hidden`;
      return copia;
    }
  }
  const regras: string[] = [];
  for (const propriedade of ESTILOS_CAPTURA) {
    const valor = estilo.getPropertyValue(propriedade);
    if (valor) regras.push(`${propriedade}:${valor}`);
  }
  const css = regras.join(";");
  let classe = estilos.classes.get(css);
  if (!classe) { classe = "xr-c" + estilos.classes.size; estilos.classes.set(css, classe); }
  // Reutiliza estilos repetidos em vez de centenas de setProperty por elemento.
  copia.removeAttribute("style"); copia.setAttribute("class", classe);
  // Nenhuma imagem externa é solicitada ao transformar o conteúdo em textura.
  if (copia instanceof HTMLImageElement && !copia.src.startsWith("data:")) copia.removeAttribute("src");
  for (const filho of original.childNodes) {
    if (filho instanceof Element) {
      if (!["SCRIPT", "STYLE", "IFRAME"].includes(filho.tagName.toUpperCase())) copia.appendChild(clonarComEstilos(filho, estilos));
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
async function desenharPainel(raiz: HTMLElement, escala: number, ativo: () => boolean): Promise<QuadroPainelDOM | null> {
  if (!ativo()) return null;
  await document.fonts.ready;
  const fonte = await fonteEmbutida();
  if (!ativo()) return null;
  const largura = raiz.clientWidth, altura = raiz.clientHeight;
  if (!largura || !altura || !raiz.isConnected) throw new Error("Painel não está montado");
  // Geometria de interação e imagem são capturadas no mesmo instante de layout.
  const inicio = performance.now();
  const estilos: Estilos = { classes: new Map(), janela: raiz.getBoundingClientRect(), nos: 0 };
  const alvos = colherAlvosDOM(raiz), copia = clonarComEstilos(raiz, estilos) as HTMLElement;
  // Também existem inset-inline-start/inset-block-start no estilo computado.
  // Trocar só left/top preservava aliases de -10000px: a imagem podia ficar vazia.
  const estiloOriginal = getComputedStyle(raiz);
  copia.style.cssText = "";
  for (const [nome, valor] of Object.entries(estiloRaizCapturada(largura, altura, (nome) => estiloOriginal.getPropertyValue(nome)))) copia.style.setProperty(nome, valor);
  copia.removeAttribute("aria-hidden");
  const style = document.createElement("style");
  const placeholder = getComputedStyle(raiz.querySelector("textarea,input") ?? raiz, "::placeholder").color;
  style.textContent = `@font-face{font-family:"VRmed Inter";src:url("${fonte}") format("woff");font-weight:600;font-style:normal}*{animation:none!important;transition:none!important;caret-color:transparent}textarea::placeholder,input::placeholder{color:${placeholder}}` +
    [...estilos.classes].map(([css, classe]) => `.${classe}{${css}}`).join("");
  copia.prepend(style);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(largura * escala)); svg.setAttribute("height", String(altura * escala));
  svg.setAttribute("viewBox", `0 0 ${largura} ${altura}`);
  const objeto = document.createElementNS(svg.namespaceURI, "foreignObject");
  objeto.setAttribute("x", "0"); objeto.setAttribute("y", "0");
  objeto.setAttribute("width", String(largura)); objeto.setAttribute("height", String(altura)); objeto.appendChild(copia); svg.appendChild(objeto);
  const endereco = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(svg));
  const preparado = performance.now();
  const imagem = await new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image(), timer = window.setTimeout(() => reject(new Error("Tempo esgotado ao renderizar painel")), 5000);
    img.onload = () => { clearTimeout(timer); resolve(img); };
    img.onerror = () => { clearTimeout(timer); reject(new Error("O navegador não conseguiu renderizar o painel HTML")); };
    img.src = endereco;
  });
  if (!ativo()) return null;
  let dupla = buffers.get(raiz);
  if (!dupla) { dupla = {}; buffers.set(raiz, dupla); }
  const canvas = dupla.verso ?? document.createElement("canvas");
  if (canvas.width !== largura * escala) canvas.width = largura * escala;
  if (canvas.height !== altura * escala) canvas.height = altura * escala;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D indisponível");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(imagem, 0, 0);
  // Ambos os painéis sempre têm título/ícones no cabeçalho. Transparência ou
  // fundo uniforme NÃO é uma captura bem-sucedida, mesmo sem erro do canvas.
  if (!validarPixelsPainel(ctx.getImageData(0, 0, canvas.width, Math.min(canvas.height, Math.ceil(120 * escala))).data)) {
    throw new Error("PAINEL_SEM_CONTEUDO: o navegador não desenhou o cabeçalho HTML");
  }
  if (process.env.NODE_ENV === "development" || new URLSearchParams(location.search).get("debug") === "paineis") {
    const nome = "vrmed:painel:" + raiz.dataset.painelSiteXr;
    if (performance.getEntriesByName(nome).length >= 32) performance.clearMeasures(nome);
    const medida = performance.measure(nome, { start: inicio, end: performance.now(), detail: {
      preparacaoMs: preparado - inicio, bytesSvg: endereco.length, elementos: raiz.querySelectorAll("*").length, copiados: estilos.nos,
    } });
    if (new URLSearchParams(location.search).get("debug") === "paineis") console.debug("[VRmed/Painel]", nome, JSON.stringify({ ms: medida.duration, ...medida.detail }));
  }
  dupla.verso = dupla.frente; dupla.frente = canvas;
  return { canvas, alvos };
}
export function renderizarPainelDOM(raiz: HTMLElement, escala = 2, ativo = () => raiz.isConnected) {
  // Duas telas não clonam/rasterizam simultaneamente no Quest.
  const pedido = fila.then(() => desenharPainel(raiz, escala, ativo));
  fila = pedido.catch(() => {});
  return pedido;
}
