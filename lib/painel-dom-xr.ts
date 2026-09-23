import { Matrix4, Plane, Ray, Vector3 } from "three";

export const PAINEL_SITE_XR = { ferramentas: { largura: 340, altura: 740 }, tutor: { largura: 400, altura: 740 }, alturaMetros: 1.4, resolucao: 2 } as const;
export type RetanguloXR = { x: number; y: number; largura: number; altura: number };
export function intersecaoRetangulos(a: RetanguloXR, b: RetanguloXR): RetanguloXR | null {
  const x = Math.max(a.x, b.x), y = Math.max(a.y, b.y);
  const largura = Math.min(a.x + a.largura, b.x + b.largura) - x, altura = Math.min(a.y + a.altura, b.y + b.altura) - y;
  return largura > 0 && altura > 0 ? { x, y, largura, altura } : null;
}
export function contemPonto(r: RetanguloXR, x: number, y: number) {
  return x >= r.x && y >= r.y && x <= r.x + r.largura && y <= r.y + r.altura;
}
/** A mesma geometria que mostra o HTML recebe o raio, inclusive após mover/escalar. */
export function pixelNoPainel(raio: Ray, matriz: Matrix4, larguraM: number, alturaM: number, larguraPx: number, alturaPx: number) {
  const p = raio.intersectPlane(new Plane(new Vector3(0, 0, 1), 0).applyMatrix4(matriz), new Vector3());
  if (!p) return null;
  p.applyMatrix4(matriz.clone().invert());
  return { x: (p.x / larguraM + 0.5) * larguraPx, y: (0.5 - p.y / alturaM) * alturaPx };
}
export function valorFaixaXR(fracao: number, minimo: number, maximo: number, passo: number) {
  const valor = minimo + Math.round(Math.max(0, Math.min(1, fracao)) * (maximo - minimo) / passo) * passo;
  return Math.max(minimo, Math.min(maximo, Number(valor.toFixed(6))));
}
type FaixaDOM = { min: number; max: number; step: number; disabled?: boolean; mudar: (valor: number) => void };
export const faixasDOMXR = new WeakMap<HTMLElement, FaixaDOM>();
export type AlvoDOMXR = {
  elemento: HTMLElement; retangulo: RetanguloXR; tipo: "botao" | "entrada" | "cor" | "slider" | "rolagem";
  assinatura: string;
};
export function assinaturaDOM(elemento: HTMLElement) {
  return [elemento.tagName, elemento.getAttribute("aria-label"), elemento.getAttribute("aria-checked"), elemento.getAttribute("data-state"),
    elemento.matches("input,textarea,[data-xr-scroll]") ? "" : elemento.textContent, elemento.hasAttribute("disabled")].join("|");
}
export function retanguloDOM(elemento: Element, raiz: HTMLElement): RetanguloXR {
  const a = elemento.getBoundingClientRect(), b = raiz.getBoundingClientRect();
  return { x: a.left - b.left, y: a.top - b.top, largura: a.width, altura: a.height };
}
function retanguloInterativo(elemento: HTMLElement, raiz: HTMLElement): RetanguloXR {
  const r = retanguloDOM(elemento, raiz);
  // O polegar do slider é mais alto que a trilha: sua área visível também recebe o raio.
  if (elemento.dataset.slot === "slider") for (const polegar of elemento.querySelectorAll('[role="slider"]')) {
    const p = retanguloDOM(polegar, raiz), direita = Math.max(r.x + r.largura, p.x + p.largura), baixo = Math.max(r.y + r.altura, p.y + p.altura);
    r.x = Math.min(r.x, p.x); r.y = Math.min(r.y, p.y); r.largura = direita - r.x; r.altura = baixo - r.y;
  }
  return r;
}
export function colherAlvosDOM(raiz: HTMLElement): AlvoDOMXR[] {
  const limites = { x: 0, y: 0, largura: raiz.clientWidth, altura: raiz.clientHeight };
  const modal = raiz.querySelector<HTMLElement>("[data-xr-modal]");
  const escopo = modal ?? raiz;
  const alvos: AlvoDOMXR[] = [];
  const elementos = [...escopo.querySelectorAll<HTMLElement>('button,input:not([type="hidden"]),textarea,[data-slot="slider"],label,a[href],[data-xr-scroll]')];
  if (modal?.hasAttribute("data-xr-scroll")) elementos.unshift(modal);
  for (const elemento of elementos) {
    const estilo = getComputedStyle(elemento);
    if (estilo.display === "none" || estilo.visibility === "hidden" || estilo.pointerEvents === "none" || elemento.closest('[hidden],[data-state="inactive"][role="tabpanel"]')) continue;
    let retangulo = intersecaoRetangulos(retanguloInterativo(elemento, raiz), limites);
    for (let pai = elemento.parentElement; retangulo && pai && pai !== raiz; pai = pai.parentElement) {
      const css = getComputedStyle(pai);
      if (/(hidden|auto|scroll|clip)/.test(css.overflow + css.overflowY + css.overflowX)) retangulo = intersecaoRetangulos(retangulo, retanguloDOM(pai, raiz));
    }
    if (!retangulo) continue;
    const tipo = elemento.hasAttribute("data-xr-scroll") ? "rolagem" : elemento.dataset.slot === "slider" ? "slider" :
      elemento instanceof HTMLInputElement && elemento.type === "color" ? "cor" :
      elemento instanceof HTMLTextAreaElement || elemento instanceof HTMLInputElement && !["checkbox", "radio"].includes(elemento.type) ? "entrada" : "botao";
    alvos.push({ elemento, retangulo, tipo, assinatura: assinaturaDOM(elemento) });
  }
  return alvos;
}
export function alvoNoPixel(alvos: AlvoDOMXR[], x: number, y: number, rolagem = false) {
  return alvos.findLast((a) => (rolagem ? a.tipo === "rolagem" : a.tipo !== "rolagem") && contemPonto(a.retangulo, x, y)) ?? null;
}
/** Não envia o clique a um controle deslocado/trocado desde o quadro exibido. */
export function alvoAindaValido(alvo: AlvoDOMXR, raiz: HTMLElement, x: number, y: number) {
  if (!raiz.contains(alvo.elemento) || alvo.assinatura !== assinaturaDOM(alvo.elemento) ||
    alvo.elemento.matches(":disabled,[aria-disabled=true],[data-disabled]")) return false;
  if (alvo.elemento.closest('[hidden],[data-state="inactive"][role="tabpanel"]')) return false;
  const css = getComputedStyle(alvo.elemento);
  if (css.visibility === "hidden" || css.display === "none" || css.pointerEvents === "none") return false;
  const modal = raiz.querySelector("[data-xr-modal]");
  if (modal && !modal.contains(alvo.elemento)) return false;
  const atual = retanguloInterativo(alvo.elemento, raiz);
  // O ponto precisa continuar na mesma região visível, não apenas na caixa não recortada.
  if (!contemPonto(atual, x, y) || !contemPonto(alvo.retangulo, x, y)) return false;
  for (let pai = alvo.elemento.parentElement; pai && pai !== raiz; pai = pai.parentElement) {
    const estilo = getComputedStyle(pai);
    if (/(hidden|auto|scroll|clip)/.test(estilo.overflow + estilo.overflowY + estilo.overflowX) && !contemPonto(retanguloDOM(pai, raiz), x, y)) return false;
  }
  return true;
}
export function atualizarEntradaDOM(elemento: HTMLInputElement | HTMLTextAreaElement, valor: string) {
  const proto = elemento instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, "value")?.set?.call(elemento, valor);
  elemento.dispatchEvent(new Event("input", { bubbles: true }));
  elemento.dispatchEvent(new Event("change", { bubbles: true }));
}
export function acionarAlvoDOM(alvo: AlvoDOMXR) {
  // Tabs do Radix ativam no mousedown; os demais controles no click.
  if (alvo.elemento.getAttribute("role") === "tab") alvo.elemento.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, button: 0 }));
  else alvo.elemento.click();
}
