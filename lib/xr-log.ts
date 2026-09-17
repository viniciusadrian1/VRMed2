/**
 * Registro de diagnóstico do ciclo de vida WebXR, para ler NO Quest 3.
 *
 * Existe para confirmar ou derrubar, no aparelho, o diagnóstico da tarja
 * "rodando em segundo plano" (ver lib/xr-sessao.ts): quem pediu e quem
 * encerrou cada sessão, se o navegador ainda tinha oferta ou sessão viva ao
 * voltar para o 2D, e se algum elemento da página cobria o topo.
 *
 * Desligado por padrão — sem a flag, nada é interceptado nem gravado.
 *  - Ligar:    abrir uma rota com cena XR com `?debug=xrlog` — /viewer, /sala,
 *              /duelo, /clinica ou /arena (fica gravado). Nas outras páginas
 *              este módulo não carrega e a flag não é lida.
 *  - Desligar: botão "Desligar" do painel, ou uma dessas rotas com
 *              `?debug=off` (apaga a flag e o registro).
 *  - Ler:      painel recolhido no canto inferior esquerdo (botão "Registro"),
 *              ou pelo `chrome://inspect` com o Quest no cabo, filtrando `[xrlog]`.
 *  - Remover do projeto: apagar este arquivo e o import dele em
 *    components/xr/SairDoVR.tsx (o único arquivo que o importa).
 *
 * Grava no localStorage porque "Sair do VR" navega e a página recarrega.
 */

const CHAVE = "vrmed:xrlog";
const LIGADO = "vrmed:xrlog:on";
const MAX_LINHAS = 500;

function armazenamento(): Storage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

/** Lê a flag da URL (e grava), sem efeito colateral fora do navegador. */
function lerFlag(): boolean {
  const loja = armazenamento();
  if (!loja || typeof location === "undefined") return false;
  try {
    const flag = new URLSearchParams(location.search).get("debug");
    if (flag === "xrlog") loja.setItem(LIGADO, "1");
    if (flag === "off") {
      loja.removeItem(LIGADO);
      loja.removeItem(CHAVE);
    }
    return loja.getItem(LIGADO) === "1";
  } catch {
    return false;
  }
}

export const XR_LOG_LIGADO = lerFlag();
/** Cai para false no botão "Desligar"; os interceptadores passam a só repassar. */
let gravando = XR_LOG_LIGADO;

const vivas = new Set<XRSession>();
const ids = new WeakMap<XRSession, number>();
const endPedidoPelaPagina = new WeakSet<XRSession>();
let proximoId = 1;
let ofertasPendentes = 0;
let ultimoQuadroXR = 0;

const descreverErro = (e: unknown) =>
  e instanceof Error ? `${e.name}: ${e.message}` : String(e);

export function lerRegistro(): string[] {
  try {
    return JSON.parse(armazenamento()?.getItem(CHAVE) ?? "[]") as string[];
  } catch {
    return [];
  }
}

function estadoAtual(): string {
  const sessoes =
    [...vivas].map((s) => `#${ids.get(s)}:${s.visibilityState}`).join(",") || "nenhuma";
  const quadro = ultimoQuadroXR
    ? `${((performance.now() - ultimoQuadroXR) / 1000).toFixed(1)}s`
    : "-";
  const doc =
    typeof document === "undefined"
      ? "?"
      : `${document.visibilityState} foco=${document.hasFocus()}`;
  return `doc=${doc} sessões=${sessoes} ofertas=${ofertasPendentes} últimoQuadroXR=${quadro}`;
}

/** Registra um evento. Sem a flag, não faz nada. */
export function xrLog(evento: string): void {
  if (!gravando) return;
  const rota = typeof location === "undefined" ? "?" : location.pathname;
  const linha = `${new Date().toISOString().slice(11, 23)} ${rota} ${evento} | ${estadoAtual()}`;
  console.info("[xrlog]", linha);
  try {
    armazenamento()?.setItem(CHAVE, JSON.stringify([...lerRegistro(), linha].slice(-MAX_LINHAS)));
  } catch {
    /* cota cheia: o console ainda tem a linha */
  }
}

function acompanhar(sessao: XRSession, origem: string) {
  if (ids.has(sessao)) return;
  const id = proximoId++;
  ids.set(sessao, id);
  vivas.add(sessao);
  xrLog(
    `sessão #${id} criada via ${origem} (blend=${sessao.environmentBlendMode ?? "?"}, visibility=${sessao.visibilityState})`,
  );
  sessao.addEventListener("visibilitychange", () =>
    xrLog(`sessão #${id} visibilitychange → ${sessao.visibilityState}`),
  );
  sessao.addEventListener("inputsourceschange", () =>
    xrLog(`sessão #${id} inputsourceschange (${sessao.inputSources.length} fontes)`),
  );
  sessao.addEventListener("end", () => {
    vivas.delete(sessao);
    xrLog(
      `sessão #${id} evento 'end' ${
        endPedidoPelaPagina.has(sessao)
          ? "(a página chamou end)"
          : "(SEM end da página: botão do sistema, Sair da tarja ou navegador)"
      }`,
    );
    // Depois que o navegador volta ao 2D: algo da página cobre o topo?
    setTimeout(() => xrLog(`topo da página após sair: ${inspecionarTopo()}`), 1500);
  });
}

/** Elementos da página sob pontos do topo da tela (a tarja nativa não aparece aqui). */
function inspecionarTopo(): string {
  if (typeof document === "undefined") return "?";
  const w = window.innerWidth;
  const pontos: [number, number][] = [
    [w * 0.1, 10],
    [w * 0.5, 10],
    [w * 0.9, 10],
    [w * 0.5, 60],
  ];
  return pontos
    .map(([x, y]) => {
      const el = document.elementFromPoint(x, y);
      if (!el) return `(${Math.round(x)},${y}) vazio`;
      const estilo = getComputedStyle(el);
      const nome = `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ""}`;
      return `(${Math.round(x)},${y}) ${nome} pos=${estilo.position} z=${estilo.zIndex} pe=${estilo.pointerEvents}`;
    })
    .join(" ; ");
}

type SistemaComOferta = XRSystem & {
  offerSession?: XRSystem["requestSession"];
};

/**
 * Intercepta o `navigator.xr` e o protótipo de `XRSession`. Todas as stores
 * do @react-three/xr passam por aqui, então nenhuma chamada fica de fora.
 * Exportado para o teste; em produção só roda com a flag.
 */
export function instalarRegistroXR(
  xr: SistemaComOferta,
  prototipoDaSessao: XRSession,
): void {
  const pedir = xr.requestSession.bind(xr);
  xr.requestSession = (modo, init) => {
    xrLog(`requestSession(${modo})`);
    const pedido = pedir(modo, init);
    pedido.then(
      (s) => acompanhar(s, `requestSession(${modo})`),
      (e) => xrLog(`requestSession(${modo}) REJEITADA ${descreverErro(e)}`),
    );
    return pedido;
  };

  if (xr.offerSession) {
    const ofertar = xr.offerSession.bind(xr);
    xr.offerSession = (modo, init) => {
      ofertasPendentes += 1;
      xrLog(`offerSession(${modo})`);
      const oferta = ofertar(modo, init);
      oferta.then(
        (s) => {
          ofertasPendentes -= 1;
          acompanhar(s, `offerSession(${modo}) ACEITA`);
        },
        (e) => {
          ofertasPendentes -= 1;
          xrLog(`offerSession(${modo}) rejeitada ${descreverErro(e)}`);
        },
      );
      return oferta;
    };
  } else {
    xrLog("offerSession não existe neste navegador");
  }
  xr.addEventListener("sessiongranted", () => xrLog("evento sessiongranted"));

  const encerrar = prototipoDaSessao.end;
  prototipoDaSessao.end = function (this: XRSession) {
    endPedidoPelaPagina.add(this);
    const id = ids.get(this);
    xrLog(`end() chamado na sessão #${id}`);
    const fim = encerrar.call(this);
    fim.then(
      () => xrLog(`end() resolveu (#${id})`),
      (e) => xrLog(`end() REJEITOU (#${id}) ${descreverErro(e)}`),
    );
    return fim;
  };

  const pedirQuadro = prototipoDaSessao.requestAnimationFrame;
  prototipoDaSessao.requestAnimationFrame = function (
    this: XRSession,
    callback: XRFrameRequestCallback,
  ) {
    return pedirQuadro.call(this, (tempo, quadro) => {
      ultimoQuadroXR = performance.now();
      callback(tempo, quadro);
    });
  };
}

function ouvirPagina() {
  const nav = performance.getEntriesByType("navigation")[0] as
    | PerformanceNavigationTiming
    | undefined;
  xrLog(`página carregou (${nav?.type ?? "?"}) ${navigator.userAgent}`);
  document.addEventListener("visibilitychange", () => xrLog("document visibilitychange"));
  addEventListener("pagehide", (e) => xrLog(`pagehide persisted=${e.persisted}`));
  addEventListener("pageshow", (e) => xrLog(`pageshow persisted=${e.persisted}`));
  addEventListener("blur", () => xrLog("window blur"));
  addEventListener("focus", () => xrLog("window focus"));
  addEventListener("popstate", () => xrLog("popstate (voltar/avançar)"));
  addEventListener("unhandledrejection", (e) =>
    xrLog(`unhandledrejection ${descreverErro(e.reason)}`),
  );
  addEventListener("error", (e) => xrLog(`error ${e.message}`));
  // Mudanças silenciosas: rota SPA, sessão viva com a página 2D visível,
  // quadros de XR parados com a sessão ainda aberta.
  let anterior = "";
  setInterval(() => {
    const parado =
      vivas.size > 0 && performance.now() - ultimoQuadroXR > 1500 ? "quadros-parados" : "";
    const chave = `${location.pathname}|${document.visibilityState}|${[...vivas]
      .map((s) => s.visibilityState)
      .join(",")}|${ofertasPendentes}|${parado}`;
    if (chave !== anterior) {
      anterior = chave;
      xrLog(`estado mudou ${parado}`);
    }
  }, 1000);
}

function montarPainel() {
  const caixa = document.createElement("div");
  // No RODAPÉ: o topo é onde a tarja nativa aparece e não pode ser coberto.
  // Recolhido e só da largura dos botões, para não cobrir os "Entrar em VR"
  // do rodapé da Sala, Clínica e Arena nem o Tutor de IA à direita.
  caixa.style.cssText =
    "position:fixed;left:8px;right:auto;bottom:8px;z-index:2147483647;max-height:40vh;overflow:auto;background:#000d;color:#9f9;font:12px/1.3 monospace;padding:6px;border-radius:6px";
  const texto = document.createElement("pre");
  texto.style.cssText = "white-space:pre-wrap;margin:4px 0 0";
  texto.hidden = true;
  const mostrar = () => {
    texto.textContent = lerRegistro().slice(-80).reverse().join("\n");
  };
  const botao = (rotulo: string, acao: () => void) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = rotulo;
    b.style.cssText = "margin:2px;padding:8px 12px;font:inherit;color:#000;background:#9f9;border:0;border-radius:4px";
    b.onclick = () => {
      acao();
      mostrar();
    };
    caixa.append(b);
  };
  botao("Registro", () => {
    texto.hidden = !texto.hidden;
  });
  // O topo é inspecionado aqui também: no "Sair do VR" a página navega antes
  // do timer de 1,5 s do evento 'end', e esta é a página que a pessoa vê.
  botao("Marcar: tarja apareceu", () =>
    xrLog(`MARCA DO USUÁRIO: tarja visível agora | topo: ${inspecionarTopo()}`),
  );
  botao("Copiar", () => void navigator.clipboard?.writeText(lerRegistro().join("\n")));
  botao("Limpar", () => armazenamento()?.removeItem(CHAVE));
  botao("Desligar", () => {
    gravando = false;
    clearInterval(atualizar);
    armazenamento()?.removeItem(LIGADO);
    // Sem recarregar: com uma sessão pausada viva, navegar é o caminho da
    // tarja. Só tira o parâmetro para um F5 não religar.
    const url = new URL(location.href);
    url.searchParams.delete("debug");
    history.replaceState(history.state, "", url);
    caixa.remove();
  });
  caixa.append(texto);
  document.body.append(caixa);
  mostrar();
  const atualizar = setInterval(mostrar, 2000);
}

if (
  XR_LOG_LIGADO &&
  typeof window !== "undefined" &&
  !(window as Window & { __vrmedXrLog?: boolean }).__vrmedXrLog
) {
  (window as Window & { __vrmedXrLog?: boolean }).__vrmedXrLog = true;
  if (navigator.xr && typeof XRSession !== "undefined") {
    instalarRegistroXR(navigator.xr, XRSession.prototype);
  } else {
    xrLog("navigator.xr ausente (sem WebXR neste navegador ou sem HTTPS)");
  }
  ouvirPagina();
  if (document.body) montarPainel();
  else addEventListener("DOMContentLoaded", montarPainel);
}
