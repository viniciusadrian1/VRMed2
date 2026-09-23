"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useThree } from "@react-three/fiber";
import { useXR } from "@react-three/xr";
import { Group, Vector3 } from "three";
import { escalaPainelXR, iniciarArrastePainel, limitarPosicaoPainel, posicaoArrastadaPainel, useJanelasEstudoXR, type JanelaXR } from "@/lib/janelas-estudo-xr";
import { liberarPonteiroUI, ocuparPonteiroUI } from "@/lib/xr-foco-interface";
import { ContextoJanelaXR, type EventoJanelaXR } from "./ContextoJanelaXR";

type Captura = { setPointerCapture: (id: number) => void; releasePointerCapture: (id: number) => void };
/** Só transforma a janela. Câmera e órgão nunca participam do arraste. */
export function JanelaMovelXR({ id, posicao, rotacao, children }: {
  id: JanelaXR; posicao: [number, number, number]; rotacao: number; children: ReactNode;
}) {
  const grupo = useRef<Group>(null);
  const dono = useRef({});
  const inicio = useRef<{ ponteiro: number; captura: Captura; dados: ReturnType<typeof iniciarArrastePainel> } | null>(null);
  const [escala, setEscala] = useState(1), [arrastando, setArrastando] = useState(false);
  const frente = useJanelasEstudoXR((s) => s.frente);
  const { camera, invalidate, gl } = useThree();
  const sessao = useXR((s) => s.session);
  const ordem = frente === id ? 1200 : 1100;
  const soltar = useCallback(() => {
    const atual = inicio.current; inicio.current = null;
    if (atual) { try { atual.captura.releasePointerCapture(atual.ponteiro); } catch { /* Controle desconectado. */ } }
    liberarPonteiroUI(dono.current); setArrastando(false); invalidate();
  }, [invalidate]);
  const [px, py, pz] = posicao;
  const restaurar = useCallback(() => {
    soltar();
    if (grupo.current) { grupo.current.position.set(px, py, pz); grupo.current.rotation.set(0, rotacao, 0); }
    setEscala(1); invalidate();
  }, [px, py, pz, rotacao, soltar, invalidate]);
  useEffect(() => useJanelasEstudoXR.subscribe((atual, anterior) => {
    if (atual.revisao !== anterior.revisao) restaurar();
    else if (atual.abertas[id] !== anterior.abertas[id]) soltar();
  }), [id, restaurar, soltar]);
  useEffect(() => {
    const d = dono.current;
    const desconectar = () => soltar();
    sessao?.addEventListener("inputsourceschange", desconectar);
    sessao?.addEventListener("visibilitychange", desconectar);
    const perdeuCaptura = (e: PointerEvent) => { if (e.pointerId === inicio.current?.ponteiro) soltar(); };
    gl.domElement.addEventListener("lostpointercapture", perdeuCaptura);
    return () => {
      sessao?.removeEventListener("inputsourceschange", desconectar);
      sessao?.removeEventListener("visibilitychange", desconectar);
      gl.domElement.removeEventListener("lostpointercapture", perdeuCaptura);
      const atual = inicio.current; inicio.current = null;
      if (atual) { try { atual.captura.releasePointerCapture(atual.ponteiro); } catch { /* Sessão encerrada. */ } }
      liberarPonteiroUI(d);
    };
  }, [gl, sessao, soltar]);
  const orientar = () => {
    const g = grupo.current; if (!g) return;
    const cabeca = (gl.xr.isPresenting ? gl.xr.getCamera() : camera).getWorldPosition(new Vector3()), centro = g.getWorldPosition(new Vector3());
    g.lookAt(cabeca.x, centro.y, cabeca.z);
  };
  const moverProfundidade = (delta: number) => {
    if (!grupo.current) return;
    soltar(); grupo.current.position.z += delta; limitarPosicaoPainel(grupo.current.position);
    orientar(); invalidate();
  };
  const aoApertar = (e: EventoJanelaXR) => {
    e.stopPropagation(); if (e.button !== 0 || inicio.current || !grupo.current) return;
    useJanelasEstudoXR.getState().focar(id);
    grupo.current.updateWorldMatrix(true, false);
    const captura = e.target as unknown as Captura;
    inicio.current = { ponteiro: e.pointerId, captura, dados: iniciarArrastePainel(grupo.current, e.point, e.ray) };
    captura.setPointerCapture(e.pointerId); ocuparPonteiroUI(dono.current, e); setArrastando(true);
  };
  const aoMover = (e: EventoJanelaXR) => {
    e.stopPropagation();
    const atual = inicio.current, g = grupo.current;
    if (!atual || atual.ponteiro !== e.pointerId || !g?.parent) return;
    g.parent.updateWorldMatrix(true, false);
    g.position.copy(posicaoArrastadaPainel(e.ray, atual.dados, g.parent.matrixWorld)); invalidate();
  };
  const aoSoltar = (e: EventoJanelaXR) => {
    e.stopPropagation();
    if (inicio.current?.ponteiro !== e.pointerId) return;
    orientar(); soltar();
  };
  return <ContextoJanelaXR.Provider value={{
    id, ordem, escala, arrastando,
    aumentar: () => { soltar(); setEscala((s) => escalaPainelXR(s + 0.1)); },
    diminuir: () => { soltar(); setEscala((s) => escalaPainelXR(s - 0.1)); },
    aproximar: () => moverProfundidade(0.15), afastar: () => moverProfundidade(-0.15), restaurar, aoApertar, aoMover, aoSoltar,
  }}>
    <group ref={grupo} position={[px, py, pz]} rotation={[0, rotacao, 0]} scale={escala} name={`janela-xr-${id}`} userData={{ ordemJanelaXR: ordem }} pointerEventsOrder={ordem}>
      {children}
    </group>
  </ContextoJanelaXR.Provider>;
}
