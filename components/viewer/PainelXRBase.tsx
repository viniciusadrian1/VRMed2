"use client";

import type { ReactNode } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import { DoubleSide } from "three";
import { ocuparPonteiroUI, liberarPonteiroUI } from "@/lib/xr-foco-interface";
import { editarTextoXR, paginasXR, PAINEIS_XR, TECLAS_XR } from "@/lib/painel-estudo-xr";
import { useJanelasEstudoXR, LIMITES_JANELA_XR } from "@/lib/janelas-estudo-xr";
import { useJanelaXR } from "./ContextoJanelaXR";
import { BotaoEstudoXR, TextoPainelXR as Text3D, SuperficieXR, useTemaPainelXR } from "./EstiloPainelXR";

export const BotaoXR = BotaoEstudoXR;

export function PainelXRBase({ titulo, aberto, aoAlternar, children }: {
  titulo: string; aberto: boolean; aoAlternar: () => void; children: ReactNode;
}) {
  const escudo = useRef({}), janela = useJanelaXR(), tema = useTemaPainelXR();
  useEffect(() => {
    const dono = escudo.current;
    return () => liberarPonteiroUI(dono);
  }, [aberto]);
  const bloquear = (e: ThreeEvent<PointerEvent | MouseEvent>) => e.stopPropagation();
  const focar = (e: ThreeEvent<PointerEvent>) => { bloquear(e); if (janela.id) useJanelasEstudoXR.getState().focar(janela.id); };
  return <group>
    {/* Barra exclusiva de manipulação: não disputa gestos com as ferramentas. */}
    <SuperficieXR largura={1.04} altura={0.085} y={0.622} cor={janela.arrastando ? tema.accent : tema.muted} borda />
    <Text3D position={[0, 0.622, 0.025]} size={0.024} color="primary">
      {janela.arrastando ? "Solte o gatilho para posicionar" : "Mover janela · segure o gatilho e arraste"}
    </Text3D>
    <mesh name="Mover janela" position={[0, 0.622, 0.035]} pointerEventsOrder={janela.ordem + 2}
      userData={{ ordemJanelaXR: janela.ordem + 2 }}
      onPointerDown={janela.aoApertar} onPointerMove={janela.aoMover} onPointerUp={janela.aoSoltar} onPointerCancel={janela.aoSoltar}
      onClick={bloquear} onPointerOver={(e) => { bloquear(e); ocuparPonteiroUI(escudo.current, e); }}
      onPointerOut={(e) => liberarPonteiroUI(escudo.current, e.pointerId)}>
      <planeGeometry args={[1.04, 0.085]} /><meshBasicMaterial colorWrite={false} depthWrite={false} side={DoubleSide} />
    </mesh>
    {/* Ocultar sem desmontar preserva aba, rascunho, teclado e resposta em curso. */}
    <group visible={aberto} pointerEvents={aberto ? "auto" : "none"}>
      <SuperficieXR largura={PAINEIS_XR.largura} altura={PAINEIS_XR.altura} borda nivel={0} />
      <mesh name="escudo-painel-xr" position={[0, 0, 0.005]} pointerEventsOrder={janela.ordem}
        onClick={bloquear} onPointerDown={focar} onPointerUp={bloquear}
        onPointerOver={(e) => { bloquear(e); ocuparPonteiroUI(escudo.current, e); }}
        onPointerOut={(e) => liberarPonteiroUI(escudo.current, e.pointerId)}
        onPointerCancel={(e) => liberarPonteiroUI(escudo.current, e.pointerId)}>
        <planeGeometry args={[PAINEIS_XR.largura, PAINEIS_XR.altura]} />
        <meshBasicMaterial colorWrite={false} depthWrite={false} side={DoubleSide} />
      </mesh>
      <Text3D position={[-0.475, 0.482, 0.02]} anchorX="left" size={0.032} maxWidth={0.75}>{titulo}</Text3D>
      <BotaoXR label="−" x={0.44} y={0.482} largura={0.09} onClick={aoAlternar} variante="ghost" />
      <SuperficieXR largura={1.036} altura={0.002} y={0.422} cor={tema.border} />
      {children}
      <SuperficieXR largura={1.04} altura={0.083} y={-0.621} cor={tema.muted} borda />
      <BotaoXR label="−" x={-0.463} y={-0.621} largura={0.08} onClick={janela.diminuir} desabilitado={janela.escala <= LIMITES_JANELA_XR.escalaMin} />
      <Text3D position={[-0.352, -0.621, 0.03]} size={0.023}>{Math.round(janela.escala * 100) + "%"}</Text3D>
      <BotaoXR label="+" x={-0.242} y={-0.621} largura={0.08} onClick={janela.aumentar} desabilitado={janela.escala >= LIMITES_JANELA_XR.escalaMax} />
      <BotaoXR label="Mais perto" x={-0.075} y={-0.621} largura={0.225} tamanho={0.022} onClick={janela.aproximar} />
      <BotaoXR label="Mais longe" x={0.164} y={-0.621} largura={0.225} tamanho={0.022} onClick={janela.afastar} />
      <BotaoXR label="Restaurar" x={0.397} y={-0.621} largura={0.22} tamanho={0.022} onClick={janela.restaurar} />
    </group>
    {!aberto && <BotaoXR label={titulo + " · Abrir"} largura={1.04} altura={0.095} y={0.482} onClick={aoAlternar} />}
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
export function TecladoXR({ texto, aoMudar, aoConfirmar, aoCancelar, limite = 500, confirmar = "Enviar" }: {
  texto: string; aoMudar: (texto: string) => void; aoConfirmar: () => void; aoCancelar: () => void;
  limite?: number; confirmar?: string;
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
    <BotaoXR label={confirmar} x={0.31} largura={0.28} y={-0.43} ativo desabilitado={!texto.trim()} onClick={aoConfirmar} />
  </group>;
}
