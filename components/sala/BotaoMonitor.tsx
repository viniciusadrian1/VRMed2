"use client";

import { useRef, useState } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { Text3D } from "@/components/arena/ui3d";
import { deveAcionarBotao3D, fonteDoPonteiro } from "@/lib/botao3d-interacao";
import { raioMonitorEstudos } from "@/lib/sala-monitor-interacao";
import { pulsar } from "@/lib/xr-haptica";
import { useAcaoMonitor } from "./MonitorAcessivel";

/** Mesmo alvo no mouse e nos dois controles; sem ampliar a área sob a mira. */
export function BotaoMonitor({ titulo, detalhe, largura, altura, position, onClick, desabilitado = false, selecionado = false, tamanho = .029, rotuloAcessivel }: {
  titulo: string; detalhe?: string; largura: number; altura: number;
  position: [number, number, number]; onClick: () => void;
  desabilitado?: boolean; selecionado?: boolean; tamanho?: number; rotuloAcessivel?: string;
}) {
  const ponteiros = useRef(new Set<number>());
  const [foco, setFoco] = useState(false);
  useAcaoMonitor(rotuloAcessivel ?? titulo, onClick, desabilitado, position);
  const acionar = (etapa: "clicar" | "pressionar", event: ThreeEvent<MouseEvent | PointerEvent>) => {
    event.stopPropagation();
    if (desabilitado || !deveAcionarBotao3D(etapa, event)) return;
    pulsar(fonteDoPonteiro(event), .3, 25); onClick();
  };
  const sair = (event: ThreeEvent<PointerEvent>) => {
    ponteiros.current.delete(event.pointerId); setFoco(ponteiros.current.size > 0);
  };
  return <group position={position}>
    <mesh raycast={raioMonitorEstudos}
      onClick={(e) => acionar("clicar", e)} onPointerDown={(e) => acionar("pressionar", e)}
      onPointerOver={(e) => { e.stopPropagation(); ponteiros.current.add(e.pointerId); setFoco(true); }}
      onPointerOut={sair} onPointerCancel={sair}>
      <planeGeometry args={[largura, altura]} />
      <meshBasicMaterial color={desabilitado ? "#273339" : foco ? "#296467" : selecionado ? "#315e62" : "#233e44"} toneMapped={false} />
    </mesh>
    <group pointerEvents="none">
      <mesh position={[-largura / 2 + .003, 0, .0004]}>
        <planeGeometry args={[.006, altura]} />
        <meshBasicMaterial color={foco || selecionado ? "#8df2d8" : "#c6ae79"} toneMapped={false} />
      </mesh>
      <Text3D tratamento="tela" position={[-largura / 2 + .015, detalhe ? .015 : 0, .0008]}
        anchorX="left" align="left" size={tamanho} maxWidth={largura - .026} color={desabilitado ? "#8c9b9e" : "#f4f1e8"}>{titulo}</Text3D>
      {detalhe && <Text3D tratamento="tela" position={[-largura / 2 + .026, -.022, .0008]}
        anchorX="left" align="left" size={.019} maxWidth={largura - .04} color="#c1d5d4">{detalhe}</Text3D>}
    </group>
  </group>;
}
