"use client";

import { Suspense, useMemo, useRef, useState } from "react";
import { useGLTF } from "@react-three/drei";
import { useXR } from "@react-three/xr";
import type { ThreeEvent } from "@react-three/fiber";
import { Text3D } from "@/components/arena/ui3d";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { deveAcionarBotao3D, fonteDoPonteiro } from "@/lib/botao3d-interacao";
import { raioMonitorEstudos } from "@/lib/sala-monitor-interacao";
import { pulsar } from "@/lib/xr-haptica";
import { sairENavegar } from "@/lib/xr-sessao";
import { MODOS_ESTUDO, TELA_ESTUDO, BOTAO_ESTUDO, posicaoModoEstudo } from "@/lib/sala-monitor";
import layout from "@/lib/sala-estudos-layout.json";

function Carcassa() {
  const { scene } = useGLTF(layout.monitor);
  const copia = useMemo(() => scene.clone(true), [scene]);
  return <primitive object={copia} />;
}

function CarcassaReserva() {
  return <mesh position={[0, 1.22, -2.10]}>
    <boxGeometry args={[1.12, .65, .095]} />
    <meshStandardMaterial color="#273234" roughness={.75} />
  </mesh>;
}

/** Alvo imóvel, sem zoom sob a mira e sem receber o clique outra vez na soltura. */
function BotaoTela({ titulo, detalhe, largura, altura, position, onClick }: {
  titulo: string; detalhe?: string; largura: number; altura: number;
  position: [number, number, number]; onClick: () => void;
}) {
  const ponteiros = useRef(new Set<number>());
  const [foco, setFoco] = useState(false);
  const acionar = (etapa: "clicar" | "pressionar", event: ThreeEvent<MouseEvent | PointerEvent>) => {
    event.stopPropagation();
    if (!deveAcionarBotao3D(etapa, event)) return;
    pulsar(fonteDoPonteiro(event), .3, 25);
    onClick();
  };
  const sair = (event: ThreeEvent<PointerEvent>) => {
    ponteiros.current.delete(event.pointerId);
    setFoco(ponteiros.current.size > 0);
  };
  return <group position={position}>
    <mesh raycast={raioMonitorEstudos}
      onClick={(e) => acionar("clicar", e)} onPointerDown={(e) => acionar("pressionar", e)}
      onPointerOver={(e) => { e.stopPropagation(); ponteiros.current.add(e.pointerId); setFoco(true); }}
      onPointerOut={sair} onPointerCancel={sair}>
      <planeGeometry args={[largura, altura]} />
      <meshBasicMaterial color={foco ? "#296467" : "#233e44"} toneMapped={false} />
    </mesh>
    <group pointerEvents="none">
      <mesh position={[-largura / 2 + .003, 0, .0004]}>
        <planeGeometry args={[.006, altura]} />
        <meshBasicMaterial color={foco ? "#8df2d8" : "#c6ae79"} toneMapped={false} />
      </mesh>
      <Text3D tratamento="tela" position={[-largura / 2 + .026, detalhe ? .015 : 0, .0008]}
        anchorX="left" align="left" size={.029} maxWidth={largura - .04} color="#f4f1e8">{titulo}</Text3D>
      {detalhe && <Text3D tratamento="tela" position={[-largura / 2 + .026, -.022, .0008]}
        anchorX="left" align="left" size={.019} maxWidth={largura - .04} color="#c1d5d4">{detalhe}</Text3D>}
    </group>
  </group>;
}

/** A tela é parte do monitor: respeita profundidade e perspectiva, sem HTML capturado. */
export function MonitorEstudos({ aberto, onAbrir, onFechar }: {
  aberto: boolean; onAbrir: () => void; onFechar: () => void;
}) {
  const session = useXR((s) => s.session);
  return <group>
    <group pointerEvents="none">
      <ErrorBoundary fallback={<CarcassaReserva />}>
        <Suspense fallback={<CarcassaReserva />}><Carcassa /></Suspense>
      </ErrorBoundary>
    </group>
    <group position={TELA_ESTUDO.posicao as [number, number, number]}>
      <mesh pointerEvents="none">
        <planeGeometry args={[TELA_ESTUDO.largura, TELA_ESTUDO.altura]} />
        <meshBasicMaterial color="#10292f" toneMapped={false} />
      </mesh>
      <Text3D tratamento="tela" position={[-.474, .234, .001]} anchorX="left" size={.021} color="#d8bf89">VRmed / SALA DE ESTUDOS</Text3D>
      {aberto ? <>
        <Text3D tratamento="tela" position={[-.474, .174, .001]} anchorX="left" size={.035}>O que vamos estudar?</Text3D>
        <BotaoTela titulo="Voltar" largura={.15} altura={.064} position={[.403, .179, .002]} onClick={onFechar} />
        {MODOS_ESTUDO.map((modo, i) => <BotaoTela key={modo.href} titulo={modo.rotulo} detalhe={modo.detalhe}
          largura={BOTAO_ESTUDO.largura} altura={BOTAO_ESTUDO.altura} position={posicaoModoEstudo(i)}
          onClick={() => sairENavegar(session, modo.href)} />)}
        <Text3D tratamento="tela" position={[0, -.246, .001]} size={.019} color="#c1d5d4" maxWidth={.96}>
          {session ? "Abrir um modo encerra o VR. Entre em VR novamente na próxima página." : "Escolha um modo. O livro abre o tutor; o rádio controla a música."}
        </Text3D>
      </> : <>
        <Text3D tratamento="tela" position={[0, .084, .001]} size={.056}>Seu espaço de estudo</Text3D>
        <Text3D tratamento="tela" position={[0, .002, .001]} size={.024} color="#c1d5d4">Anatomia, prática e descoberta.</Text3D>
        <BotaoTela titulo="Começar a estudar" largura={.57} altura={.106} position={[0, -.112, .002]} onClick={onAbrir} />
        <Text3D tratamento="tela" position={[0, -.239, .001]} size={.019} color="#c1d5d4">Aponte para a tela e pressione o gatilho.</Text3D>
        {/* Toda a área livre do monitor também abre o hub, sem cobrir o botão. */}
        <mesh position={[0, 0, .0002]} raycast={raioMonitorEstudos}
          onClick={(e) => { e.stopPropagation(); if (deveAcionarBotao3D("clicar", e)) onAbrir(); }}
          onPointerDown={(e) => { e.stopPropagation(); if (deveAcionarBotao3D("pressionar", e)) onAbrir(); }}>
          <planeGeometry args={[TELA_ESTUDO.largura, TELA_ESTUDO.altura]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      </>}
    </group>
  </group>;
}
