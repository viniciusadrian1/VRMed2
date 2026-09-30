"use client";

import { lazy, Suspense, useMemo, useState } from "react";
import { useGLTF } from "@react-three/drei";
import { useXR } from "@react-three/xr";
import { Text3D } from "@/components/arena/ui3d";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { deveAcionarBotao3D } from "@/lib/botao3d-interacao";
import { raioMonitorEstudos } from "@/lib/sala-monitor-interacao";
import { sairENavegar } from "@/lib/xr-sessao";
import { MODOS_ESTUDO, TELA_ESTUDO, BOTAO_ESTUDO, posicaoModoEstudo } from "@/lib/sala-monitor";
import layout from "@/lib/sala-estudos-layout.json";
import { BotaoMonitor as BotaoTela } from "./BotaoMonitor";

const CompararNoMonitor = lazy(() => import("./CompararNoMonitor").then((m) => ({ default: m.CompararNoMonitor })));
const QuizNoMonitor = lazy(() => import("./QuizNoMonitor").then((m) => ({ default: m.QuizNoMonitor })));

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


/** A tela é parte do monitor: respeita profundidade e perspectiva, sem HTML capturado. */
export function MonitorEstudos({ aberto, onAbrir, onFechar }: {
  aberto: boolean; onAbrir: () => void; onFechar: () => void;
}) {
  const session = useXR((s) => s.session);
  const [atividade, setAtividade] = useState<string | null>(null);
  const interna = atividade === "/compare" || atividade === "/quiz";
  const externa = MODOS_ESTUDO.find((modo) => modo.href === atividade && !interna);
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
      <Text3D tratamento="tela" position={[-.474, .244, .001]} anchorX="left" size={.021} color="#d8bf89">{interna && aberto ? `VRmed / ${atividade === "/quiz" ? "QUIZ" : "COMPARAR"}` : "VRmed / SALA DE ESTUDOS"}</Text3D>
      {aberto && atividade ? <>
        <BotaoTela titulo="Menu" largura={.15} altura={.053} tamanho={.024} position={[.403, .244, .003]} onClick={() => setAtividade(null)} />
        {interna ? <ErrorBoundary key={atividade} fallback={<Text3D tratamento="tela" size={.027} maxWidth={.88}>Não foi possível abrir a atividade. Volte ao menu para tentar novamente.</Text3D>}>
          <Suspense fallback={<Text3D tratamento="tela" size={.028}>Preparando atividade…</Text3D>}>
            {atividade === "/compare" ? <CompararNoMonitor /> : <QuizNoMonitor abrirEstudo={() => setAtividade("/viewer")} />}
          </Suspense>
        </ErrorBoundary> : externa && <>
          <Text3D tratamento="tela" position={[0, .115, .003]} size={.04}>{externa.rotulo}</Text3D>
          <Text3D tratamento="tela" position={[0, .015, .003]} size={.026} maxWidth={.88}>Esta atividade abre em sua própria página. Continuar sai da sala{session ? " e encerra o VR" : ""}.</Text3D>
          <BotaoTela titulo="Continuar na sala" largura={.4} altura={.08} position={[-.24, -.12, .003]} onClick={() => setAtividade(null)} />
          <BotaoTela titulo="Sair e abrir atividade" largura={.43} altura={.08} tamanho={.025} position={[.22, -.12, .003]} onClick={() => sairENavegar(session, externa.href)} />
        </>}
      </> : aberto ? <>
        <Text3D tratamento="tela" position={[-.474, .174, .001]} anchorX="left" size={.035}>O que vamos estudar?</Text3D>
        <BotaoTela titulo="Voltar" largura={.15} altura={.064} position={[.403, .179, .002]} onClick={onFechar} />
        {MODOS_ESTUDO.map((modo, i) => <BotaoTela key={modo.href} titulo={modo.rotulo} detalhe={modo.detalhe}
          largura={BOTAO_ESTUDO.largura} altura={BOTAO_ESTUDO.altura} position={posicaoModoEstudo(i)}
          onClick={() => setAtividade(modo.href)} />)}
        <Text3D tratamento="tela" position={[0, -.246, .001]} size={.019} color="#c1d5d4" maxWidth={.96}>
          Comparar e Quiz abrem aqui, sem sair da sala.
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
