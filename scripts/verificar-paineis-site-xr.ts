import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as THREE from "three";
import { raioPlacaXR } from "../lib/raio-placa-xr.ts";
import { createRayPointer } from "@pmndrs/pointer-events";
import { alvoAindaValido, alvoNoPixel, colherAlvosDOM, contemPonto, intersecaoRetangulos, PAINEL_SITE_XR, pixelNoPainel, valorFaixaXR, type AlvoDOMXR } from "../lib/painel-dom-xr.ts";
import { deveAcionarBotao3D } from "../lib/botao3d-interacao.ts";
import "./registrar-componentes-teste.mjs";

const { ConteudoSiteXR } = await import("../components/viewer/PainelSiteXR.tsx");
const { ToolsPanelContent } = await import("../components/viewer/ToolsPanel.tsx");
const { ChatPanelContent } = await import("../components/chat/ChatPanel.tsx");
const { TooltipProvider } = await import("../components/ui/tooltip.tsx");
const { useVRMedStore } = await import("../lib/store.ts");
// Zustand usa o snapshot inicial durante SSR, não o estado corrente do cliente.
const inicial = useVRMedStore.getInitialState(), original = { ...inicial };
const loja = useVRMedStore.getState;
loja().setCurrentOrgan("larynx");
loja().setLayers([{ name: "Epiglottis", label: "Epiglote", visible: true, opacity: 0.65, depth: "internal", color: null }]);
const mensagens = [
  { id: "u", role: "user" as const, content: "Onde fica a traqueia?", createdAt: 1 },
  { id: "a", role: "assistant" as const, content: "A **traqueia** conduz o ar.\n\n- Abaixo da laringe.\n- Liga-se aos brônquios.\n\n[Fonte: Anatomia de referência]", createdAt: 2 },
];
function normalizar(html: string) {
  // React/Radix geram IDs diferentes por raiz; classes, SVGs, conteúdo e controles devem coincidir.
  return html.replace(/\s(id|for|aria-controls|aria-labelledby|aria-describedby)="[^"]*"/g, ' $1="normalizado"');
}
for (const chat of [[], mensagens]) {
  loja().setChat(chat);
  Object.assign(inicial, loja());
  for (const id of ["ferramentas", "tutor"] as const) {
    const componente = id === "ferramentas" ? ToolsPanelContent : ChatPanelContent;
    const site = renderToStaticMarkup(h(TooltipProvider, null, h(componente, { onClose: () => {} })));
    const xr = renderToStaticMarkup(h(ConteudoSiteXR, { id, aoFechar: () => {} }));
    assert.equal(normalizar(xr), normalizar(site), `o HTML de ${id} deve ser o do site, não uma versão aproximada`);
    assert.ok(xr.includes("<svg"), "ícones originais presentes");
    if (id === "ferramentas") assert.ok(xr.includes("Epiglote") && xr.includes("65") && xr.includes('data-slot="slider"'));
    if (id === "tutor" && chat.length) assert.ok(xr.includes("traqueia") && xr.includes("Esta resposta foi útil?") && xr.includes("<strong"));
  }
}
Object.assign(inicial, original);

assert.deepEqual(intersecaoRetangulos({ x: 10, y: 10, largura: 30, altura: 40 }, { x: 20, y: 0, largura: 40, altura: 30 }), { x: 20, y: 10, largura: 20, altura: 20 });
assert.equal(intersecaoRetangulos({ x: 0, y: 0, largura: 10, altura: 10 }, { x: 20, y: 20, largura: 10, altura: 10 }), null);
assert.equal(valorFaixaXR(0.5, -100, 100, 1), 0);
assert.equal(valorFaixaXR(0.49, 0.5, 2, 0.25), 1.25);
assert.equal(valorFaixaXR(-1, 0, 100, 1), 0);
assert.equal(valorFaixaXR(2, 0, 100, 1), 100);

// Contrato DOM com retângulos/estilos controlados, sem emular renderização de navegador.
// Exercita o coletor usado em produção: recortes, polegar, modais e quadros obsoletos.
class NoRetangular {
  parentElement: NoRetangular | null = null;
  filhos: NoRetangular[] = [];
  attrs: Record<string, string> = {};
  dataset: Record<string, string> = {};
  estilo = { display: "block", visibility: "visible", pointerEvents: "auto", overflow: "visible", overflowX: "visible", overflowY: "visible" };
  textContent = "Controle";
  tagName: string; x: number; y: number; clientWidth: number; clientHeight: number;
  constructor(tagName: string, x: number, y: number, clientWidth: number, clientHeight: number) {
    this.tagName = tagName; this.x = x; this.y = y; this.clientWidth = clientWidth; this.clientHeight = clientHeight;
  }
  getBoundingClientRect() { return { left: this.x - 10000, top: this.y, width: this.clientWidth, height: this.clientHeight }; }
  getAttribute(n: string) { return this.attrs[n] ?? null; }
  hasAttribute(n: string) { return n in this.attrs; }
  matches(seletor: string) {
    return seletor.split(",").some((s) => s === this.tagName.toLowerCase() ||
      s === ":disabled" && this.hasAttribute("disabled") || s === "[aria-disabled=true]" && this.attrs["aria-disabled"] === "true" ||
      s === "[data-disabled]" && this.hasAttribute("data-disabled") || s === "[data-xr-scroll]" && this.hasAttribute("data-xr-scroll"));
  }
  closest(): NoRetangular | null { return this.hasAttribute("hidden") ? this : this.parentElement?.closest() ?? null; }
  contains(n: NoRetangular): boolean { return n === this || this.filhos.some((f) => f.contains(n)); }
  anexar(n: NoRetangular) { this.filhos.push(n); n.parentElement = this; return n; }
  descendentes(): NoRetangular[] { return this.filhos.flatMap((f) => [f, ...f.descendentes()]); }
  querySelector(s: string) { return this.descendentes().find((n) => s === "[data-xr-modal]" && n.hasAttribute("data-xr-modal")) ?? null; }
  querySelectorAll(s: string) { return this.descendentes().filter((n) => s === '[role="slider"]' ? n.attrs.role === "slider" :
    n.tagName === "BUTTON" || n.dataset.slot === "slider" || n.hasAttribute("data-xr-scroll")); }
}
const globais = ["getComputedStyle", "HTMLInputElement", "HTMLTextAreaElement"];
const descritores = globais.map((chave) => Object.getOwnPropertyDescriptor(globalThis, chave));
Object.defineProperties(globalThis, {
  getComputedStyle: { configurable: true, value: (n: NoRetangular) => n.estilo },
  HTMLInputElement: { configurable: true, value: class {} },
  HTMLTextAreaElement: { configurable: true, value: class {} },
});
try {
  const raiz = new NoRetangular("DIV", 0, 0, 400, 740), dom = raiz as unknown as HTMLElement;
  const scroll = raiz.anexar(new NoRetangular("DIV", 0, 60, 400, 400));
  scroll.attrs["data-xr-scroll"] = ""; scroll.estilo.overflowY = "auto";
  const cortado = scroll.anexar(new NoRetangular("BUTTON", 12, 40, 150, 40));
  const escondido = scroll.anexar(new NoRetangular("BUTTON", 12, 200, 150, 40)); escondido.estilo.display = "none";
  const faixa = scroll.anexar(new NoRetangular("SPAN", 20, 150, 180, 6)); faixa.dataset.slot = "slider";
  const polegar = faixa.anexar(new NoRetangular("SPAN", 100, 145, 16, 16)); polegar.attrs.role = "slider";
  const mapa = colherAlvosDOM(dom), a = mapa.find((m) => m.elemento === cortado as unknown as HTMLElement)!;
  assert.deepEqual(a.retangulo, { x: 12, y: 60, largura: 150, altura: 20 });
  assert.equal(alvoNoPixel(mapa, 40, 50), null);
  assert.equal(alvoNoPixel(mapa, 40, 70), a);
  assert.equal(alvoNoPixel(mapa, 108, 146)?.tipo, "slider", "polegar visível fora da altura da trilha é clicável");
  assert.equal(alvoNoPixel(mapa, 40, 220), null, "controle oculto não recebe o raio");
  assert.equal(alvoAindaValido(a, dom, 40, 70), true);
  cortado.attrs.disabled = ""; assert.equal(alvoAindaValido(a, dom, 40, 70), false); delete cortado.attrs.disabled;
  cortado.textContent = "Outro controle"; assert.equal(alvoAindaValido(a, dom, 40, 70), false); cortado.textContent = "Controle";
  cortado.y = 100; assert.equal(alvoAindaValido(a, dom, 40, 70), false); cortado.y = 40;
  const ler = mapa.find((m) => m.tipo === "rolagem")!;
  scroll.textContent = "Resposta recebendo novos tokens";
  assert.equal(alvoAindaValido(ler, dom, 200, 250), true, "streaming não bloqueia o início de rolagem");
  const modal = raiz.anexar(new NoRetangular("DIV", 10, 500, 380, 210));
  modal.attrs["data-xr-modal"] = ""; modal.attrs["data-xr-scroll"] = "";
  modal.anexar(new NoRetangular("BUTTON", 25, 550, 100, 30));
  assert.equal(alvoAindaValido(a, dom, 40, 70), false, "modal novo bloqueia ações do quadro anterior");
  const sobreposto = colherAlvosDOM(dom);
  assert.equal(sobreposto.length, 2); assert.equal(alvoNoPixel(sobreposto, 40, 70), null);
  assert.equal(alvoNoPixel(sobreposto, 40, 560)?.tipo, "botao");
  assert.equal(alvoNoPixel(sobreposto, 200, 650, true)?.tipo, "rolagem");
} finally {
  globais.forEach((chave, i) => { const d = descritores[i]; if (d) Object.defineProperty(globalThis, chave, d); else Reflect.deleteProperty(globalThis, chave); });
}

let verificacoes = 0;
for (const id of ["ferramentas", "tutor"] as const) {
  const d = PAINEL_SITE_XR[id], altura = PAINEL_SITE_XR.alturaMetros, largura = altura * d.largura / d.altura;
  // Alvos em coordenadas CSS, incluindo cantos e campo de pergunta junto ao rodapé.
  const alvos = [
    { x: d.largura - 43, y: 10, largura: 28, altura: 28 },
    { x: 12, y: 82, largura: d.largura - 24, altura: 32 },
    { x: 12, y: d.altura - 65, largura: d.largura - 70, altura: 36 },
  ].map((retangulo, i) => ({ retangulo, tipo: "botao" as const, assinatura: String(i), elemento: {} as HTMLElement }));
  for (const escala of [0.65, 1, 1.55]) for (const giro of [-0.9, 0, 0.9]) for (const mao of [-0.2, 0.2]) {
    const cena = new THREE.Scene(), pai = new THREE.Group(), janela = new THREE.Group(), controle = new THREE.Object3D(), camera = new THREE.PerspectiveCamera();
    pai.position.set(1.2, 0.8, -0.4); pai.rotation.y = 0.3; cena.add(pai);
    janela.position.set(0.5, 0.2, -1.4); janela.rotation.y = giro; janela.scale.setScalar(escala); pai.add(janela);
    const plano = new THREE.Mesh(new THREE.PlaneGeometry(largura, altura), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide })); janela.add(plano);
    plano.raycast = raioPlacaXR; plano.pointerEventsOrder = 1201; controle.position.set(mao, 1, 0.5); cena.add(controle);
    let selecionado: AlvoDOMXR | null = null, cliques = 0;
    plano.addEventListener("pointerdown", (e) => {
      if (!deveAcionarBotao3D("pressionar", e)) return;
      const p = pixelNoPainel(e.ray, plano.matrixWorld, largura, altura, d.largura, d.altura);
      selecionado = p ? alvoNoPixel(alvos, p.x, p.y) : null; cliques++;
    });
    plano.addEventListener("click", (e) => { if (deveAcionarBotao3D("clicar", e)) cliques++; });
    const raio = createRayPointer(() => camera, { current: controle }, {});
    for (const alvo of alvos) for (const [u, v] of [[0.5, 0.5], [0.05, 0.05], [0.95, 0.95]]) {
      const r = alvo.retangulo, x = r.x + r.largura * u, y = r.y + r.altura * v;
      cena.updateMatrixWorld(true);
      const ponto = plano.localToWorld(new THREE.Vector3((x / d.largura - 0.5) * largura, (0.5 - y / d.altura) * altura, 0));
      controle.quaternion.setFromRotationMatrix(new THREE.Matrix4().lookAt(controle.position, ponto, new THREE.Vector3(0, 1, 0)));
      cena.updateMatrixWorld(true); raio.move(cena, { timeStamp: verificacoes * 1000 });
      assert.equal(raio.getIntersection()?.object, plano);
      const antes = cliques;
      raio.down({ timeStamp: verificacoes * 1000 + 1, button: 0 }); raio.up({ timeStamp: verificacoes * 1000 + 850, button: 0 });
      assert.equal(selecionado, alvo); assert.equal(cliques, antes + 1); verificacoes++;
    }
    // Espaço em branco não aciona outro controle.
    assert.equal(alvoNoPixel(alvos, d.largura / 2, d.altura / 2), null);
    raio.exit({ timeStamp: verificacoes * 1000 });
    plano.geometry.dispose(); (plano.material as THREE.Material).dispose();
  }
}
assert.equal(contemPonto({ x: 0, y: 50, largura: 340, altura: 400 }, 170, 25), false, "conteúdo acima do recorte não recebe clique");
const implementacao = readFileSync("components/viewer/PainelSiteXR.tsx", "utf8");
assert.match(implementacao, /renderizarPainelDOM\(host, PAINEL_SITE_XR.resolucao\)/);
assert.match(implementacao, /alvoAindaValido/);
assert.match(implementacao, /pointerEventsOrder=\{janela.ordem \+ 1\}/);
assert.match(implementacao, /process.env.NODE_ENV === "development"/);
assert.ok(!readFileSync("components/viewer/TutorPainelVR.tsx", "utf8").includes("paginasXR"), "chat não é reformatado em outra UI");
console.log(`ok: painéis do site — HTML original idêntico (vazio/conversa), ícones/Markdown/feedback preservados e ${verificacoes} cliques por pixel com escala, rotação e dois controles`);
console.log("limite: teste estrutural e geométrico; rasterização SVG/CSS e desempenho exigem navegador/Quest");
