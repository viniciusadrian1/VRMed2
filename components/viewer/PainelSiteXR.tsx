"use client";

import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { useXR } from "@react-three/xr";
import { CanvasTexture, DoubleSide, LinearFilter, SRGBColorSpace, type Mesh } from "three";
import { ToolsPanelContent } from "./ToolsPanel";
import { ChatPanelContent } from "@/components/chat/ChatPanel";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ContextoDOMXR, ContextoPortalDOMXR } from "./ContextoDOMXR";
import { ContextoJanelaXR, useJanelaXR } from "./ContextoJanelaXR";
import { PainelXRBase, BotaoXR, TecladoXR } from "./PainelXRBase";
import { TextoPainelXR, SuperficieXR } from "./EstiloPainelXR";
import { useJanelasEstudoXR, type JanelaXR } from "@/lib/janelas-estudo-xr";
import { renderizarPainelDOM, type QuadroPainelDOM } from "@/lib/renderizar-painel-dom";
import { acionarAlvoDOM, alvoAindaValido, alvoNoPixel, atualizarEntradaDOM, faixasDOMXR, PAINEL_SITE_XR, pixelNoPainel, retanguloDOM, valorFaixaXR, type AlvoDOMXR } from "@/lib/painel-dom-xr";
import { deveAcionarBotao3D, fonteDoPonteiro } from "@/lib/botao3d-interacao";
import { liberarPonteiroUI, ocuparPonteiroUI } from "@/lib/xr-foco-interface";
import { pulsar } from "@/lib/xr-haptica";
import { playClique } from "@/lib/arena-audio";
import { useVRMedStore } from "@/lib/store";
import { getOrganById } from "@/lib/organs";
import { cancelarConversaTutor, useConversaTutor } from "@/lib/tutor-conversa";

function AcoesModeloXR() {
  const malha = useVRMedStore((s) => s.wireframe), abertura = useVRMedStore((s) => s.explosao);
  const explodivel = useVRMedStore((s) => Boolean(getOrganById(s.currentOrganId)?.explosao));
  return <>
    <BotaoXR label={malha ? "Malha: ligada" : "Ver malha"} x={explodivel ? -0.34 : 0} y={0} largura={0.30} ativo={malha} onClick={() => useVRMedStore.getState().toggleWireframe()} />
    {explodivel && <>
      <BotaoXR label="Fechar ossos" y={0} largura={0.30} desabilitado={abertura === 0} onClick={() => useVRMedStore.getState().setExplosao(abertura - 0.1)} />
      <BotaoXR label="Abrir ossos" x={0.34} y={0} largura={0.30} desabilitado={abertura === 1} onClick={() => useVRMedStore.getState().setExplosao(abertura + 0.1)} />
    </>}
  </>;
}

type Evento = ThreeEvent<PointerEvent>;
type Entrada = { elemento: HTMLInputElement | HTMLTextAreaElement; texto: string; cor: boolean };
type Gesto = { id: number; alvo: AlvoDOMXR; captura: { releasePointerCapture: (id: number) => void }; ultimoY: number };

export function ConteudoSiteXR({ id, aoFechar, portal = null }: { id: JanelaXR; aoFechar: () => void; portal?: HTMLElement | null }) {
  return <TooltipProvider><ContextoDOMXR.Provider value={true}><ContextoPortalDOMXR.Provider value={portal}>
    {id === "ferramentas" ? <ToolsPanelContent onClose={aoFechar} /> : <ChatPanelContent onClose={aoFechar} />}
  </ContextoPortalDOMXR.Provider></ContextoDOMXR.Provider></TooltipProvider>;
}

/** O HTML/CSS do site é a única fonte de desenho e de áreas interativas. */
export function PainelSiteXR({ id }: { id: JanelaXR }) {
  const janela = useJanelaXR(), aberto = useJanelasEstudoXR((s) => s.abertas[id]);
  const dimensao = PAINEL_SITE_XR[id], altura = PAINEL_SITE_XR.alturaMetros, largura = altura * dimensao.largura / dimensao.altura;
  const raiz = useRef<HTMLDivElement | null>(null), quadro = useRef<QuadroPainelDOM | null>(null);
  const plano = useRef<Mesh>(null), realce = useRef<Mesh>(null), dono = useRef({}), gesto = useRef<Gesto | null>(null);
  const solicitar = useRef<(urgente?: boolean) => void>(() => {}), sobre = useRef<AlvoDOMXR | null>(null);
  const cancelarInteracao = useRef(() => {});
  const [textura, setTextura] = useState<CanvasTexture | null>(null), [erro, setErro] = useState(false);
  const [entrada, setEntrada] = useState<Entrada | null>(null), [rotulo, setRotulo] = useState("");
  const { invalidate, gl } = useThree(), sessao = useXR((s) => s.session);
  const ocupado = useConversaTutor((s) => s.ocupado);
  const alternar = () => useJanelasEstudoXR.getState().abrir(id, !aberto);

  useEffect(() => {
    const host = document.createElement("div");
    host.setAttribute("aria-hidden", "true"); host.dataset.painelSiteXr = id;
    Object.assign(host.style, { position: "fixed", left: "-10000px", top: "0", width: dimensao.largura + "px", height: dimensao.altura + "px",
      overflow: "hidden", background: "var(--card)", color: "var(--foreground)", fontFamily: getComputedStyle(document.body).fontFamily,
      fontSize: "16px", lineHeight: "1.5", isolation: "isolate" });
    document.body.appendChild(host); raiz.current = host;
    // Captura estados finais, sem congelar a cor no meio de uma transição CSS.
    const css = document.createElement("style");
    css.textContent = `[data-painel-site-xr="${id}"] *,[data-painel-site-xr="${id}"] *::before,[data-painel-site-xr="${id}"] *::after{transition:none!important;animation:none!important}`;
    document.head.appendChild(css);
    // Comparação manual de desenvolvimento: HTML original ao lado da cena, nunca em produção.
    if (process.env.NODE_ENV === "development" && !gl.xr.isPresenting && new URLSearchParams(location.search).get("compararPainel") === id) {
      Object.assign(host.style, { left: "auto", right: "12px", top: "70px", zIndex: "9999" });
      host.removeAttribute("aria-hidden");
    }
    const dom = createRoot(host, { identifierPrefix: "xr-" + id + "-" });
    const fecharJanela = () => useJanelasEstudoXR.getState().abrir(id, false);
    dom.render(<ConteudoSiteXR id={id} aoFechar={fecharJanela} portal={host} />);
    let fim = false, ocupado = false, sujo = true, urgente = false, timer = 0, ultimo = 0;
    let mapa: CanvasTexture | null = null;
    const atualizar = (prioritario = false) => {
      sujo = true; urgente ||= prioritario;
      if (fim || ocupado || !useJanelasEstudoXR.getState().abertas[id]) return;
      if (timer && !urgente) return;
      if (timer) clearTimeout(timer);
      timer = window.setTimeout(async () => {
        timer = 0; ocupado = true; sujo = false; urgente = false; ultimo = performance.now();
        try {
          // O DOM auxiliar não entra na navegação Tab do site; a inspeção visível continua acessível.
          if (host.getAttribute("aria-hidden") === "true") for (const foco of host.querySelectorAll<HTMLElement>("button,input,textarea,a[href],[tabindex]")) {
            if (foco.tabIndex !== -1) foco.tabIndex = -1;
          }
          const proximo = await renderizarPainelDOM(host, PAINEL_SITE_XR.resolucao);
          if (fim) return;
          if (!mapa) {
            mapa = new CanvasTexture(proximo.canvas); mapa.colorSpace = SRGBColorSpace;
            mapa.minFilter = LinearFilter; mapa.magFilter = LinearFilter; mapa.generateMipmaps = false;
            setTextura(mapa);
          } else { mapa.image = proximo.canvas; mapa.needsUpdate = true; }
          quadro.current = proximo; setErro(false); invalidate();
        } catch {
          if (!fim) {
            quadro.current = null; cancelarInteracao.current();
            setErro(true); invalidate();
          }
        } finally { ocupado = false; if (sujo && !fim) atualizar(); }
      }, Math.max(0, (urgente ? 80 : 250) - (performance.now() - ultimo)));
    };
    solicitar.current = atualizar;
    const mudanca = () => atualizar();
    const observer = new MutationObserver(mudanca);
    observer.observe(host, { subtree: true, childList: true, attributes: true, characterData: true });
    const tema = new MutationObserver(mudanca); tema.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    host.addEventListener("scroll", mudanca, true); host.addEventListener("input", mudanca, true);
    const remover = useJanelasEstudoXR.subscribe((atual, anterior) => { if (atual.abertas[id] && !anterior.abertas[id]) atualizar(); });
    atualizar();
    return () => {
      fim = true; clearTimeout(timer); observer.disconnect(); tema.disconnect(); remover();
      host.removeEventListener("scroll", mudanca, true); host.removeEventListener("input", mudanca, true); css.remove();
      raiz.current = null; quadro.current = null; solicitar.current = () => {}; mapa?.dispose();
      // Raiz DOM independente: desmontar após o commit do reconciliador 3D.
      queueMicrotask(() => { dom.unmount(); host.remove(); });
      useVRMedStore.getState().setAnnotationMode(false);
    };
  }, [id, dimensao.largura, dimensao.altura, invalidate, gl]);

  useEffect(() => {
    const d = dono.current;
    const cancelar = () => {
      const atual = gesto.current; gesto.current = null; sobre.current = null;
      if (atual) { try { atual.captura.releasePointerCapture(atual.id); } catch { /* Controle removido. */ } }
      liberarPonteiroUI(d);
      if (realce.current) realce.current.visible = false;
    };
    cancelarInteracao.current = cancelar;
    const remover = useJanelasEstudoXR.subscribe((atual, anterior) => {
      if (!atual.abertas[id] || atual.revisao !== anterior.revisao) cancelar();
      if (id === "ferramentas" && !atual.abertas[id]) useVRMedStore.getState().setAnnotationMode(false);
    });
    const perdeu = (e: PointerEvent) => { if (gesto.current?.id === e.pointerId) cancelar(); };
    gl.domElement.addEventListener("lostpointercapture", perdeu);
    sessao?.addEventListener("inputsourceschange", cancelar); sessao?.addEventListener("visibilitychange", cancelar);
    return () => {
      cancelar(); cancelarInteracao.current = () => {}; remover(); gl.domElement.removeEventListener("lostpointercapture", perdeu);
      sessao?.removeEventListener("inputsourceschange", cancelar); sessao?.removeEventListener("visibilitychange", cancelar);
    };
  }, [id, sessao, gl]);

  const pixel = (e: ThreeEvent<PointerEvent | MouseEvent | WheelEvent>) => {
    if (!plano.current) return null;
    plano.current.updateWorldMatrix(true, false);
    return pixelNoPainel(e.ray, plano.current.matrixWorld, largura, altura, dimensao.largura, dimensao.altura);
  };
  const rolar = (delta: number, alvo = sobre.current) => {
    const host = raiz.current; if (!host) return;
    const modal = host.querySelector<HTMLElement>("[data-xr-modal]");
    const scroller = modal ?? (alvo && host.contains(alvo.elemento) ? alvo.elemento.closest<HTMLElement>("[data-xr-scroll]") : null) ?? host.querySelector<HTMLElement>("[data-xr-scroll]");
    if (scroller) { scroller.scrollTop += delta; solicitar.current(true); }
  };
  const slider = (alvo: AlvoDOMXR, x: number) => {
    if (!raiz.current) return;
    const faixa = faixasDOMXR.get(alvo.elemento), r = retanguloDOM(alvo.elemento, raiz.current);
    if (faixa && !faixa.disabled) faixa.mudar(valorFaixaXR((x - r.x) / r.largura, faixa.min, faixa.max, faixa.step));
    solicitar.current(true);
  };
  const apontar = (e: Evento) => {
    e.stopPropagation(); ocuparPonteiroUI(dono.current, e);
    const p = pixel(e), host = raiz.current, atual = gesto.current;
    if (!p || !host || !quadro.current) return;
    if (atual?.id === e.pointerId) {
      if (atual.alvo.tipo === "slider") slider(atual.alvo, p.x);
      else { atual.alvo.elemento.scrollTop -= p.y - atual.ultimoY; atual.ultimoY = p.y; solicitar.current(true); }
      return;
    }
    const alvo = alvoNoPixel(quadro.current.alvos, p.x, p.y);
    sobre.current = alvo;
    const valido = alvo && alvoAindaValido(alvo, host, p.x, p.y);
    if (realce.current) {
      realce.current.visible = Boolean(valido);
      if (valido) {
        const r = alvo.retangulo;
        realce.current.position.set(((r.x + r.largura / 2) / dimensao.largura - 0.5) * largura, (0.5 - (r.y + r.altura / 2) / dimensao.altura) * altura, 0.011);
        realce.current.scale.set(r.largura / dimensao.largura * largura, r.altura / dimensao.altura * altura, 1);
      }
    }
    const nome = valido ? alvo.elemento.getAttribute("aria-label") || alvo.elemento.getAttribute("title") || alvo.elemento.textContent?.trim().slice(0, 60) || "Editar" : "";
    setRotulo(nome);
  };
  const pressionar = (e: Evento) => {
    e.stopPropagation(); if (e.button !== 0 || gesto.current) return;
    useJanelasEstudoXR.getState().focar(id);
    const p = pixel(e), host = raiz.current, imagem = quadro.current;
    if (!p || !host || !imagem) return;
    const alvo = alvoNoPixel(imagem.alvos, p.x, p.y) ?? alvoNoPixel(imagem.alvos, p.x, p.y, true);
    if (!alvo || !alvoAindaValido(alvo, host, p.x, p.y)) { solicitar.current(true); return; }
    if (alvo.tipo === "slider" || alvo.tipo === "rolagem") {
      const captura = e.target as unknown as Gesto["captura"] & { setPointerCapture: (id: number) => void };
      gesto.current = { id: e.pointerId, alvo, captura, ultimoY: p.y }; captura.setPointerCapture(e.pointerId);
      if (alvo.tipo === "slider") slider(alvo, p.x);
    } else if (deveAcionarBotao3D("pressionar", e)) acionar(alvo, e);
  };
  const acionar = (alvo: AlvoDOMXR, e: ThreeEvent<PointerEvent | MouseEvent>) => {
    if (alvo.tipo === "entrada" || alvo.tipo === "cor") {
      const elemento = alvo.elemento as HTMLInputElement | HTMLTextAreaElement;
      setEntrada({ elemento, texto: elemento.value, cor: alvo.tipo === "cor" });
    } else acionarAlvoDOM(alvo);
    pulsar(fonteDoPonteiro(e), 0.3, 25); playClique(); solicitar.current(true);
  };
  const soltar = (e: Evento) => {
    e.stopPropagation();
    if (gesto.current?.id === e.pointerId) {
      const captura = gesto.current.captura; gesto.current = null;
      try { captura.releasePointerCapture(e.pointerId); } catch { /* Sessão encerrada. */ }
    }
    liberarPonteiroUI(dono.current, e.pointerId);
  };
  const aplicar = (texto: string) => {
    if (entrada?.elemento.isConnected) atualizarEntradaDOM(entrada.elemento, texto);
    setEntrada(null); solicitar.current(true);
  };

  return <PainelXRBase titulo={id === "tutor" ? "Tutor de IA" : "Ferramentas do modelo"} aberto={aberto} aoAlternar={alternar}
    conteudoSite largura={largura} altura={altura}>
    {textura && !erro ? <mesh ref={plano} name={"Site: " + id} position={[0, 0, 0.01]}
      renderOrder={janela.ordem + 3} pointerEventsOrder={janela.ordem + 1} userData={{ ordemJanelaXR: janela.ordem + 1 }}
      onPointerMove={apontar} onPointerOver={apontar} onPointerDown={pressionar} onPointerUp={soltar} onPointerCancel={soltar}
      onPointerOut={(e) => { if (gesto.current?.id !== e.pointerId) { liberarPonteiroUI(dono.current, e.pointerId); sobre.current = null; setRotulo(""); if (realce.current) realce.current.visible = false; } }}
      onClick={(e) => {
        e.stopPropagation(); if (!deveAcionarBotao3D("clicar", e)) return;
        const p = pixel(e), host = raiz.current; if (!p || !host || !quadro.current) return;
        const alvo = alvoNoPixel(quadro.current.alvos, p.x, p.y);
        if (alvo && alvo.tipo !== "slider" && alvoAindaValido(alvo, host, p.x, p.y)) acionar(alvo, e);
      }}
      onWheel={(e) => { e.stopPropagation(); rolar(e.deltaY); }}>
      <planeGeometry args={[largura, altura]} />
      <meshBasicMaterial map={textura} transparent depthTest={false} depthWrite={false} toneMapped={false} side={DoubleSide} />
    </mesh> : <TextoPainelXR size={0.03} maxWidth={largura - 0.05}>{erro ? "Não foi possível mostrar o painel do site." : "Carregando o painel do site..."}</TextoPainelXR>}
    {erro && <BotaoXR label="Tentar novamente" largura={0.45} y={-0.15} onClick={() => solicitar.current(true)} />}
    <mesh ref={realce} visible={false} renderOrder={janela.ordem + 4} raycast={() => null}>
      <planeGeometry args={[1, 1]} /><meshBasicMaterial color="#5896c8" opacity={0.16} transparent depthTest={false} depthWrite={false} toneMapped={false} side={DoubleSide} />
    </mesh>
    <group position={[0, -altura / 2 - 0.145, 0.03]}>
      <BotaoXR label="Subir" x={-0.36} y={0} largura={0.24} onClick={() => rolar(-210)} />
        <TextoPainelXR position={[0, 0, 0.02]} size={0.02} maxWidth={0.42}>{erro ? "Painel indisponível" : rotulo || "Arraste o texto para rolar"}</TextoPainelXR>
      <BotaoXR label="Descer" x={0.36} y={0} largura={0.24} onClick={() => rolar(210)} />
    </group>
    <group position={[0, -altura / 2 - 0.235, 0.03]}>
      {id === "ferramentas" ? <AcoesModeloXR /> : ocupado && <BotaoXR label="Parar resposta" y={0} largura={0.55} onClick={cancelarConversaTutor} />}
    </group>
    {entrada && <ContextoJanelaXR.Provider value={{ ...janela, ordem: janela.ordem + 20 }}>
      <group position={[0, 0, 0.08]} userData={{ ordemJanelaXR: janela.ordem + 20 }} pointerEventsOrder={janela.ordem + 20}>
        <SuperficieXR largura={1.04} altura={1.12} borda nivel={0} />
        <mesh onPointerDown={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()}>
          <planeGeometry args={[1.04, 1.12]} /><meshBasicMaterial colorWrite={false} depthWrite={false} side={DoubleSide} />
        </mesh>
        <TextoPainelXR position={[0, 0.48, 0.02]} size={0.03}>{entrada.cor ? "Cor de destaque" : "Editar texto"}</TextoPainelXR>
        {entrada.cor ? <>
          {["#5896c8", "#ffc166", "#71e0b2", "#ed8a7b", "#ffffff", "#9e72d1", "#0f4c81", "#15724f", "#b42318"].map((cor, i) =>
            <BotaoXR key={cor} label={cor} x={(i % 3 - 1) * 0.31} y={0.28 - Math.floor(i / 3) * 0.16} largura={0.28} cor={cor} onClick={() => aplicar(cor)} />)}
          <BotaoXR label="Cancelar" y={-0.43} largura={0.4} onClick={() => setEntrada(null)} />
        </> : <TecladoXR texto={entrada.texto} limite={entrada.elemento.maxLength > 0 ? entrada.elemento.maxLength : Math.max(500, entrada.texto.length)}
          permitirVazio aoMudar={(texto) => setEntrada({ ...entrada, texto })} confirmar="Aplicar" aoConfirmar={() => aplicar(entrada.texto)} aoCancelar={() => setEntrada(null)} />}
      </group>
    </ContextoJanelaXR.Provider>}
  </PainelXRBase>;
}
