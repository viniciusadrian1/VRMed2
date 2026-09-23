"use client";

import type { ReactNode } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import { DoubleSide } from "three";
import { Panel, Button3D, Text3D } from "@/components/arena/ui3d";
import { ORDEM_PONTEIRO_UI } from "@/lib/botao3d-interacao";
import { ocuparPonteiroUI, liberarPonteiroUI } from "@/lib/xr-foco-interface";
import { editarTextoXR, paginasXR, PAINEIS_XR, TECLAS_XR } from "@/lib/painel-estudo-xr";

export function BotaoXR({ label, x = 0, y, largura = 0.28, onClick, desabilitado = false, ativo = false, cor }: {
  label: string; x?: number; y: number; largura?: number; onClick: () => void;
  desabilitado?: boolean; ativo?: boolean; cor?: string;
}) {
  return <Button3D label={label} position={[x, y, 0.025]} width={largura} height={PAINEIS_XR.alturaBotao}
    tamanhoTexto={0.025} color={cor ?? (ativo ? "#237b75" : "#365b78")} desabilitado={desabilitado} onClick={onClick} />;
}

export function PainelXRBase({ titulo, aberto, aoAlternar, children }: {
  titulo: string; aberto: boolean; aoAlternar: () => void; children: ReactNode;
}) {
  const escudo = useRef({});
  useEffect(() => {
    const dono = escudo.current;
    return () => liberarPonteiroUI(dono);
  }, [aberto]);
  if (!aberto) return <BotaoXR label={`Abrir ${titulo}`} largura={0.65} y={0} onClick={aoAlternar} />;
  const bloquear = (e: ThreeEvent<PointerEvent | MouseEvent>) => e.stopPropagation();
  return <Panel width={PAINEIS_XR.largura} height={PAINEIS_XR.altura} opacity={1}>
    {/* Intercepta vãos vazios: apontar para a placa não seleciona o órgão atrás. */}
    <mesh name="escudo-painel-xr" position={[0, 0, 0.005]} pointerEventsOrder={ORDEM_PONTEIRO_UI - 1}
      onClick={bloquear} onPointerDown={bloquear} onPointerUp={bloquear}
      onPointerOver={(e) => { bloquear(e); ocuparPonteiroUI(escudo.current, e); }}
      onPointerOut={(e) => liberarPonteiroUI(escudo.current, e.pointerId)}
      onPointerCancel={(e) => liberarPonteiroUI(escudo.current, e.pointerId)}>
      <planeGeometry args={[PAINEIS_XR.largura, PAINEIS_XR.altura]} />
      <meshBasicMaterial transparent opacity={0} depthWrite={false} colorWrite={false} side={DoubleSide} />
    </mesh>
    <Text3D position={[-0.09, 0.475, 0.02]} size={0.032} maxWidth={0.7}>{titulo}</Text3D>
    <BotaoXR label="Recolher" x={0.385} y={0.475} largura={0.21} onClick={aoAlternar} />
    {children}
  </Panel>;
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
    <Text3D position={[0, 0.235, 0.025]} size={0.021} color="#9fb3c4">{`${texto.length}/${limite} caracteres`}</Text3D>
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
