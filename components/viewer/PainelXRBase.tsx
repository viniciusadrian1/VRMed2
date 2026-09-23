"use client";

import type { ReactNode } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import { DoubleSide } from "three";
import { ocuparPonteiroUI, liberarPonteiroUI } from "@/lib/xr-foco-interface";
import { editarTextoXR, paginasXR, PAINEIS_XR, TECLAS_XR } from "@/lib/painel-estudo-xr";
import { useJanelasEstudoXR } from "@/lib/janelas-estudo-xr";
import { useJanelaXR } from "./ContextoJanelaXR";
import { raioPlacaXR } from "@/lib/raio-placa-xr";
import { alcaJanelaXR, zonasBordaXR } from "@/lib/gestos-janelas-xr";
import { BotaoEstudoXR, TextoPainelXR as Text3D, SuperficieXR, useTemaPainelXR } from "./EstiloPainelXR";

export const BotaoXR = BotaoEstudoXR;

function BordaJanela({ zona, largura, altura }: { zona: ReturnType<typeof zonasBordaXR>[number]; largura: number; altura: number }) {
  const janela = useJanelaXR(), tema = useTemaPainelXR(), dono = useRef({});
  const [sobre, setSobre] = useState(false);
  useEffect(() => { const d = dono.current; return () => liberarPonteiroUI(d); }, []);
  return <group position={[zona.x, zona.y, 0.025]}>
    {/* Alvo na margem extrema: não invade o X ou os botões do site. */}
    <mesh raycast={raioPlacaXR} name="Redimensionar pela borda" pointerEventsOrder={janela.ordem + 2} userData={{ ordemJanelaXR: janela.ordem + 2 }}
      onPointerDown={(e) => janela.aoRedimensionar(e, zona.borda, largura, altura)}
      onPointerMove={janela.aoMover} onPointerUp={janela.aoSoltar} onPointerCancel={janela.aoSoltar}
      onClick={(e) => e.stopPropagation()}
      onPointerOver={(e) => { e.stopPropagation(); ocuparPonteiroUI(dono.current, e); setSobre(true); }}
      onPointerOut={(e) => { liberarPonteiroUI(dono.current, e.pointerId); setSobre(false); }}>
      <planeGeometry args={[zona.largura, zona.altura]} /><meshBasicMaterial colorWrite={false} depthWrite={false} side={DoubleSide} />
    </mesh>
    {sobre && <SuperficieXR largura={zona.borda.x ? 0.004 : 0.12} altura={zona.borda.y ? 0.004 : 0.12} cor={tema.primary} nivel={5} />}
    {sobre && zona.borda.x !== 0 && zona.borda.y !== 0 && <>
      <SuperficieXR largura={0.045} altura={0.004} cor={tema.primary} nivel={5} />
      <SuperficieXR largura={0.004} altura={0.045} cor={tema.primary} nivel={5} />
    </>}
  </group>;
}

/** Conteúdo original, uma alça inferior e bordas de tamanho. Sem barras de comandos extras. */
export function PainelXRBase({ titulo, aberto, aoAlternar, children, largura = PAINEIS_XR.largura, altura = PAINEIS_XR.altura }: {
  titulo: string; aberto: boolean; aoAlternar: () => void; children: ReactNode;
  largura?: number; altura?: number;
}) {
  const escudo = useRef({}), janela = useJanelaXR(), tema = useTemaPainelXR();
  const [sobreAlca, setSobreAlca] = useState(false);
  const alca = alcaJanelaXR(altura, aberto);
  useEffect(() => { const dono = escudo.current; return () => liberarPonteiroUI(dono); }, [aberto]);
  const bloquear = (e: ThreeEvent<PointerEvent | MouseEvent>) => e.stopPropagation();
  const focar = (e: ThreeEvent<PointerEvent>) => { bloquear(e); if (janela.id) useJanelasEstudoXR.getState().focar(janela.id); };
  return <group>
    {/* Ocultar sem desmontar preserva aba, rascunho, teclado e resposta em curso. */}
    <group visible={aberto} pointerEvents={aberto ? "auto" : "none"}>
      <SuperficieXR largura={largura} altura={altura} borda nivel={0} />
      <mesh raycast={raioPlacaXR} name="escudo-painel-xr" position={[0, 0, 0.005]} pointerEventsOrder={janela.ordem}
        onClick={bloquear} onPointerDown={focar} onPointerUp={bloquear}
        onPointerOver={(e) => { bloquear(e); ocuparPonteiroUI(escudo.current, e); }}
        onPointerOut={(e) => liberarPonteiroUI(escudo.current, e.pointerId)}
        onPointerCancel={(e) => liberarPonteiroUI(escudo.current, e.pointerId)}>
        <planeGeometry args={[largura, altura]} />
        <meshBasicMaterial colorWrite={false} depthWrite={false} side={DoubleSide} />
      </mesh>
      {children}
      {aberto && zonasBordaXR(largura, altura).map((zona) => <BordaJanela key={zona.borda.x + ":" + zona.borda.y} zona={zona} largura={largura} altura={altura} />)}
    </group>
    <group position={[alca.x, alca.y, 0.03]}>
      <SuperficieXR largura={sobreAlca || janela.arrastando ? 0.24 : 0.20} altura={0.008} cor={sobreAlca || janela.arrastando ? tema.primary : tema.mutedForeground} nivel={5} />
      <mesh raycast={raioPlacaXR} name="Mover janela pela alça inferior" pointerEventsOrder={janela.ordem + 2} userData={{ ordemJanelaXR: janela.ordem + 2 }}
        onPointerDown={janela.aoApertar} onPointerMove={janela.aoMover} onPointerUp={janela.aoSoltar} onPointerCancel={janela.aoSoltar}
        onClick={bloquear}
        onPointerOver={(e) => { bloquear(e); ocuparPonteiroUI(escudo.current, e); setSobreAlca(true); }}
        onPointerOut={(e) => { liberarPonteiroUI(escudo.current, e.pointerId); setSobreAlca(false); }}>
        <planeGeometry args={[alca.largura, alca.altura]} /><meshBasicMaterial colorWrite={false} depthWrite={false} side={DoubleSide} />
      </mesh>
    </group>
    {!aberto && <BotaoXR label={titulo} largura={Math.max(largura, 0.5)} altura={0.085} y={0} onClick={aoAlternar} />}
  </group>;
}

export function PaginacaoXR({ pagina, total, aoMudar, y = -0.46 }: {
  pagina: number; total: number; aoMudar: (pagina: number) => void; y?: number;
}) {
  return <group>
    <BotaoXR label="Anterior" x={-0.34} y={y} largura={0.22} desabilitado={pagina === 0} onClick={() => aoMudar(pagina - 1)} />
    <Text3D position={[0, y, 0.025]} size={0.025}>{`${pagina + 1} / ${Math.max(1, total)}`}</Text3D>
    <BotaoXR label="Próxima" x={0.34} y={y} largura={0.22} desabilitado={pagina + 1 >= total} onClick={() => aoMudar(pagina + 1)} />
  </group>;
}

/** Teclado renderizado na própria placa, sem DOM, teclado do sistema ou microfone. */
export function TecladoXR({ texto, aoMudar, aoConfirmar, aoCancelar, limite = 500, confirmar = "Enviar", permitirVazio = false }: {
  texto: string; aoMudar: (texto: string) => void; aoConfirmar: () => void; aoCancelar: () => void;
  limite?: number; confirmar?: string; permitirVazio?: boolean;
}) {
  const [maiusculas, setMaiusculas] = useState(false);
  const digitar = (tecla: string) => aoMudar(editarTextoXR(texto, tecla, limite));
  return <group>
    <Text3D position={[0, 0.33, 0.025]} size={0.025} maxWidth={0.92}>{texto ? paginasXR(texto.slice(-60), 30, 2).at(-1) : "Escreva usando o laser e o gatilho"}</Text3D>
    <Text3D position={[0, 0.235, 0.025]} size={0.021} color="muted">{`${texto.length}/${limite} caracteres`}</Text3D>
    {TECLAS_XR.map((linha, i) => [...linha].map((letra, j) => <BotaoXR
      key={letra} label={maiusculas ? letra.toUpperCase() : letra} largura={0.085}
      x={(j - (linha.length - 1) / 2) * 0.098} y={0.15 - i * 0.076}
      onClick={() => digitar(maiusculas ? letra.toUpperCase() : letra)} />))}
    <BotaoXR label="Maiúsculas" ativo={maiusculas} x={-0.35} largura={0.24} y={-0.24} onClick={() => setMaiusculas((s) => !s)} />
    <BotaoXR label="Espaço" largura={0.31} y={-0.24} onClick={() => digitar("Espaço")} />
    <BotaoXR label="Apagar" x={0.35} largura={0.24} y={-0.24} onClick={() => digitar("Apagar")} />
    <BotaoXR label="Cancelar" x={-0.31} largura={0.28} y={-0.43} onClick={aoCancelar} />
    <BotaoXR label="Limpar" largura={0.24} y={-0.43} onClick={() => digitar("Limpar")} />
    <BotaoXR label={confirmar} x={0.31} largura={0.28} y={-0.43} ativo desabilitado={!permitirVazio && !texto.trim()} onClick={aoConfirmar} />
  </group>;
}
