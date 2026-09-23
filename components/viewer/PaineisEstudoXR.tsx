"use client";

import { useEffect, useRef, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { useXRInputSourceState } from "@react-three/xr";
import { Group } from "three";
import { JanelaMovelXR } from "./JanelaMovelXR";
import { useJanelasEstudoXR } from "@/lib/janelas-estudo-xr";
import { PAINEIS_XR } from "@/lib/painel-estudo-xr";
import { useVRMedStore } from "@/lib/store";
import { FerramentasPainelXR } from "./FerramentasPainelXR";
import { TutorPainelVR } from "./TutorPainelVR";
import { poseDaCabeca } from "./XRManipulation";

/** Inspeção desktop só montada em desenvolvimento; não simula hardware WebXR. */
export type InspecaoPaineis = "paineis" | "ferramentas" | "tutor";

/** Fixo no mundo após entrar/recentrar, nunca preso ao movimento da cabeça. */
export function PaineisEstudoXR({ inspecao, saidaRef }: { inspecao?: InspecaoPaineis; saidaRef?: RefObject<Group | null> }) {
  const grupo = useRef<Group>(null);
  const reposicionar = useRef(true);
  const botaoAnterior = useRef(false);
  const esquerdo = useXRInputSourceState("controller", "left");
  const direito = useXRInputSourceState("controller", "right");
  useEffect(() => () => useVRMedStore.getState().setAnnotationMode(false), []);

  useFrame(({ gl }, _, frame) => {
    if (inspecao || !grupo.current) return;
    const pressionado = esquerdo?.gamepad?.["y-button"]?.state === "pressed" || direito?.gamepad?.["b-button"]?.state === "pressed";
    if (pressionado && !botaoAnterior.current) {
      reposicionar.current = true;
      useJanelasEstudoXR.getState().restaurarLayout();
      useJanelasEstudoXR.getState().abrir("ferramentas", true);
      useJanelasEstudoXR.getState().abrir("tutor", true);
    }
    botaoAnterior.current = pressionado;
    if (!reposicionar.current) return;
    const pose = poseDaCabeca(gl, frame);
    if (!pose) return;
    grupo.current.position.copy(pose.cabeca);
    grupo.current.position.y -= PAINEIS_XR.abaixoDosOlhos;
    grupo.current.rotation.set(0, Math.atan2(-pose.frente.x, -pose.frente.z), 0);
    // Saída montada permanentemente em Scene, para preservar o ciclo WebXR.
    if (saidaRef?.current) {
      saidaRef.current.position.copy(grupo.current.position);
      saidaRef.current.rotation.copy(grupo.current.rotation);
    }
    grupo.current.visible = true;
    grupo.current.pointerEvents = "auto";
    reposicionar.current = false;
  });

  if (inspecao === "ferramentas") return <JanelaMovelXR id="ferramentas" posicao={[0, 0, -0.55]} rotacao={0}><FerramentasPainelXR /></JanelaMovelXR>;
  if (inspecao === "tutor") return <JanelaMovelXR id="tutor" posicao={[0, 0, -0.55]} rotacao={0}><TutorPainelVR /></JanelaMovelXR>;
  return <group ref={grupo} visible={Boolean(inspecao)} pointerEvents={inspecao ? "auto" : "none"} name="paineis-estudo-xr">
    <JanelaMovelXR id="ferramentas" posicao={[-PAINEIS_XR.lateral, 0, -PAINEIS_XR.distancia]} rotacao={PAINEIS_XR.inclinacao}>
      <FerramentasPainelXR />
    </JanelaMovelXR>
    <JanelaMovelXR id="tutor" posicao={[PAINEIS_XR.lateral, 0, -PAINEIS_XR.distancia]} rotacao={-PAINEIS_XR.inclinacao}>
      <TutorPainelVR />
    </JanelaMovelXR>
  </group>;
}
