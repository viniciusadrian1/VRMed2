"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Text } from "@react-three/drei";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { useXR } from "@react-three/xr";
import { useTheme } from "next-themes";
import { DoubleSide, MeshBasicMaterial, Shape, type Mesh } from "three";
import { ARENA_FONT } from "@/components/arena/ui3d";
import { deveAcionarBotao3D, fonteDoPonteiro } from "@/lib/botao3d-interacao";
import { ocuparPonteiroUI, liberarPonteiroUI } from "@/lib/xr-foco-interface";
import { pulsar } from "@/lib/xr-haptica";
import { playClique } from "@/lib/arena-audio";
import { TEMA_PAINEL_CLARO, TEMA_PAINEL_ESCURO } from "@/lib/tema-paineis-xr";
import { opacidadePeloRaio, useJanelasEstudoXR } from "@/lib/janelas-estudo-xr";
import { useJanelaXR } from "./ContextoJanelaXR";

export function useTemaPainelXR() {
  const { resolvedTheme } = useTheme();
  return resolvedTheme === "dark" ? TEMA_PAINEL_ESCURO : TEMA_PAINEL_CLARO;
}

const materialTexto = new MeshBasicMaterial({ transparent: true, depthTest: false, depthWrite: false, toneMapped: false, side: DoubleSide });
type Ponto = [number, number, number];

/** Mesma fonte e cores do site, sem contorno de jogo nem iluminação sobre a UI. */
export function TextoPainelXR({ children, position, size = 0.026, color, maxWidth, anchorY = "middle", anchorX = "center" }: {
  children: ReactNode; position?: Ponto; size?: number; color?: string; maxWidth?: number;
  anchorY?: "top" | "middle" | "bottom"; anchorX?: "left" | "center" | "right";
}) {
  const tema = useTemaPainelXR(), { ordem } = useJanelaXR();
  const cor = color === "muted" ? tema.mutedForeground : color === "danger" ? tema.danger : color === "primary" ? tema.primary : color ?? tema.foreground;
  return <Text font={ARENA_FONT} fontSize={size} color={cor} position={position} maxWidth={maxWidth}
    anchorX={anchorX} anchorY={anchorY} textAlign={anchorX} lineHeight={1.4}
    material={materialTexto} renderOrder={ordem + 8} raycast={() => null}>{children}</Text>;
}

/** Placas vetoriais leves: cantos suaves, borda e preenchimento chapado do site. */
export function SuperficieXR({ largura, altura, x = 0, y = 0, cor, borda, nivel = 1 }: {
  largura: number; altura: number; x?: number; y?: number; cor?: string; borda?: boolean; nivel?: number;
}) {
  const tema = useTemaPainelXR(), { ordem } = useJanelaXR();
  const forma = useMemo(() => {
    const w = largura / 2, h = altura / 2, r = Math.min(0.022, h * 0.45, w * 0.45), s = new Shape();
    s.moveTo(-w + r, -h); s.lineTo(w - r, -h); s.quadraticCurveTo(w, -h, w, -h + r);
    s.lineTo(w, h - r); s.quadraticCurveTo(w, h, w - r, h); s.lineTo(-w + r, h);
    s.quadraticCurveTo(-w, h, -w, h - r); s.lineTo(-w, -h + r); s.quadraticCurveTo(-w, -h, -w + r, -h);
    return s;
  }, [largura, altura]);
  return <group position={[x, y, 0]}>
    {borda && <mesh renderOrder={ordem + nivel} raycast={() => null}>
      <shapeGeometry args={[forma, 5]} />
      <meshBasicMaterial color={tema.border} transparent depthTest={false} depthWrite={false} toneMapped={false} side={DoubleSide} />
    </mesh>}
    <mesh scale={borda ? [(largura - 0.004) / largura, (altura - 0.004) / altura, 1] : 1}
      renderOrder={ordem + nivel + (borda ? 1 : 0)} raycast={() => null}>
      <shapeGeometry args={[forma, 5]} />
      <meshBasicMaterial color={cor ?? tema.card} transparent depthTest={false} depthWrite={false} toneMapped={false} side={DoubleSide} />
    </mesh>
  </group>;
}

export function BotaoEstudoXR({ label, x = 0, y, largura = 0.28, altura = 0.065, onClick, desabilitado = false, ativo = false, cor, variante = "outline", alinhar = "center", tamanho = 0.025, manterCorNoHover = false }: {
  label: string; x?: number; y: number; largura?: number; altura?: number; onClick: () => void;
  desabilitado?: boolean; ativo?: boolean; cor?: string; variante?: "outline" | "ghost" | "primary" | "tab";
  alinhar?: "left" | "center"; tamanho?: number; manterCorNoHover?: boolean;
}) {
  const tema = useTemaPainelXR(), janela = useJanelaXR();
  const [sobre, setSobre] = useState(false);
  const dono = useRef({});
  useEffect(() => { const d = dono.current; return () => liberarPonteiroUI(d); }, []);
  const primaria = variante === "primary";
  const fundo = desabilitado ? tema.muted : sobre && !manterCorNoHover ? tema.accent : cor ?? (primaria ? tema.primary : variante === "tab" ? ativo ? tema.card : tema.muted : ativo ? tema.accent : tema.card);
  const acionar = (etapa: "pressionar" | "clicar", e: ThreeEvent<PointerEvent | MouseEvent>) => {
    e.stopPropagation();
    if (janela.id) useJanelasEstudoXR.getState().focar(janela.id);
    if (desabilitado || !deveAcionarBotao3D(etapa, e)) return;
    pulsar(fonteDoPonteiro(e), 0.3, 25); playClique(); onClick();
  };
  return <group position={[x, y, 0.025]} userData={{ ordemJanelaXR: janela.ordem + 2 }} pointerEventsOrder={janela.ordem + 2}>
    <SuperficieXR largura={largura} altura={altura} cor={fundo} borda={variante === "outline"} nivel={4} />
    <TextoPainelXR position={[alinhar === "left" ? -largura / 2 + 0.02 : 0, 0, 0.004]}
      size={tamanho} maxWidth={largura - 0.026} anchorX={alinhar}
      color={desabilitado ? tema.mutedForeground : primaria && !sobre ? tema.primaryForeground : ativo ? tema.primary : tema.foreground}>{label}</TextoPainelXR>
    <mesh name={label} onPointerDown={(e) => acionar("pressionar", e)} onClick={(e) => acionar("clicar", e)}
      onPointerUp={(e) => e.stopPropagation()}
      onPointerOver={(e) => { e.stopPropagation(); setSobre(true); ocuparPonteiroUI(dono.current, e); }}
      onPointerOut={(e) => { setSobre(false); liberarPonteiroUI(dono.current, e.pointerId); }}
      onPointerCancel={(e) => { setSobre(false); liberarPonteiroUI(dono.current, e.pointerId); }}>
      <planeGeometry args={[largura, altura]} />
      <meshBasicMaterial colorWrite={false} depthWrite={false} side={DoubleSide} />
    </mesh>
  </group>;
}

/** Caixa de seleção vetorial, sem glifos que dependam de fontes externas. */
export function CaixaSelecaoXR({ ativo, x, y, onClick }: { ativo: boolean; x: number; y: number; onClick: () => void }) {
  const tema = useTemaPainelXR(), { ordem } = useJanelaXR();
  return <group position={[x, y, 0]}>
    <BotaoEstudoXR label="" largura={0.065} y={0} ativo={ativo} manterCorNoHover={ativo} cor={ativo ? tema.primary : tema.card} onClick={onClick} />
    {ativo && <group>
      <mesh position={[-0.009, -0.003, 0.035]} rotation={[0, 0, -0.7]} renderOrder={ordem + 7} raycast={() => null}>
        <planeGeometry args={[0.018, 0.005]} /><meshBasicMaterial color={tema.primaryForeground} transparent depthTest={false} depthWrite={false} toneMapped={false} />
      </mesh>
      <mesh position={[0.007, 0.002, 0.035]} rotation={[0, 0, 0.85]} renderOrder={ordem + 7} raycast={() => null}>
        <planeGeometry args={[0.032, 0.005]} /><meshBasicMaterial color={tema.primaryForeground} transparent depthTest={false} depthWrite={false} toneMapped={false} />
      </mesh>
    </group>}
  </group>;
}

/** Barra de opacidade com área de toque maior que o traço, como no site. */
export function OpacidadeXR({ valor, aoMudar, x, y, largura = 0.62 }: {
  valor: number; aoMudar: (valor: number) => void; x: number; y: number; largura?: number;
}) {
  const tema = useTemaPainelXR(), janela = useJanelaXR(), alvo = useRef<Mesh>(null);
  const sessao = useXR((s) => s.session), gl = useThree((s) => s.gl);
  const dono = useRef({}), ponteiro = useRef<number | null>(null);
  const captura = useRef<{ releasePointerCapture: (id: number) => void } | null>(null);
  useEffect(() => {
    const d = dono.current;
    const liberar = () => {
      const id = ponteiro.current; ponteiro.current = null;
      if (id != null) { try { captura.current?.releasePointerCapture(id); } catch { /* Controle desconectado. */ } }
      liberarPonteiroUI(d);
    };
    const remover = useJanelasEstudoXR.subscribe((atual, anterior) => {
      if (atual.revisao !== anterior.revisao || (janela.id && !atual.abertas[janela.id])) liberar();
    });
    const perdeuCaptura = (e: PointerEvent) => { if (e.pointerId === ponteiro.current) liberar(); };
    sessao?.addEventListener("inputsourceschange", liberar);
    sessao?.addEventListener("visibilitychange", liberar);
    gl.domElement.addEventListener("lostpointercapture", perdeuCaptura);
    return () => {
      remover(); liberar();
      sessao?.removeEventListener("inputsourceschange", liberar);
      sessao?.removeEventListener("visibilitychange", liberar);
      gl.domElement.removeEventListener("lostpointercapture", perdeuCaptura);
    };
  }, [janela.id, sessao, gl]);
  const mudar = (e: ThreeEvent<PointerEvent>) => {
    if (!alvo.current) return;
    alvo.current.updateWorldMatrix(true, false);
    const novoValor = opacidadePeloRaio(e.ray, alvo.current.matrixWorld, largura);
    if (novoValor != null && novoValor !== valor) aoMudar(novoValor);
  };
  const soltar = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    if (ponteiro.current !== e.pointerId) return;
    ponteiro.current = null;
    try { captura.current?.releasePointerCapture(e.pointerId); } catch { /* Controle desconectado. */ }
    liberarPonteiroUI(dono.current, e.pointerId);
  };
  return <group position={[x, y, 0.03]} userData={{ ordemJanelaXR: janela.ordem + 2 }} pointerEventsOrder={janela.ordem + 2}>
    <SuperficieXR largura={largura} altura={0.009} cor={tema.muted} nivel={4} />
    {valor > 0 && <SuperficieXR x={-(1 - valor) * largura / 2} largura={Math.max(0.001, largura * valor)} altura={0.009} cor={tema.primary} nivel={5} />}
    <mesh position={[(valor - 0.5) * largura, 0, 0]} renderOrder={janela.ordem + 6} raycast={() => null}>
      <circleGeometry args={[0.017, 20]} /><meshBasicMaterial color={tema.primary} transparent depthTest={false} depthWrite={false} toneMapped={false} />
    </mesh>
    <mesh position={[(valor - 0.5) * largura, 0, 0]} renderOrder={janela.ordem + 7} raycast={() => null}>
      <circleGeometry args={[0.011, 20]} /><meshBasicMaterial color={tema.card} transparent depthTest={false} depthWrite={false} toneMapped={false} />
    </mesh>
    <mesh ref={alvo} name="Opacidade da camada" onPointerDown={(e) => {
      e.stopPropagation(); if (e.button !== 0 || ponteiro.current != null) return;
      if (janela.id) useJanelasEstudoXR.getState().focar(janela.id);
      const destino = e.target as unknown as { setPointerCapture: (id: number) => void; releasePointerCapture: (id: number) => void };
      ponteiro.current = e.pointerId; captura.current = destino; destino.setPointerCapture(e.pointerId);
      ocuparPonteiroUI(dono.current, e); mudar(e);
    }} onPointerMove={(e) => { e.stopPropagation(); if (ponteiro.current === e.pointerId) mudar(e); }}
      onPointerUp={soltar} onPointerCancel={soltar} onClick={(e) => e.stopPropagation()}
      onPointerOver={(e) => { e.stopPropagation(); ocuparPonteiroUI(dono.current, e); }}
      onPointerOut={(e) => { if (ponteiro.current !== e.pointerId) liberarPonteiroUI(dono.current, e.pointerId); }}>
      <planeGeometry args={[largura + 0.034, 0.065]} /><meshBasicMaterial colorWrite={false} depthWrite={false} side={DoubleSide} />
    </mesh>
  </group>;
}
