"use client";

import { useEffect, useRef, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { useXRInputSourceState } from "@react-three/xr";
import { Group } from "three";
import { Text3D } from "@/components/arena/ui3d";
import { PAINEIS_XR } from "@/lib/painel-estudo-xr";
import { useVRMedStore } from "@/lib/store";
import { FerramentasPainelXR } from "./FerramentasPainelXR";
import { TutorPainelVR } from "./TutorPainelVR";
import { BotaoXR } from "./PainelXRBase";
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
    if (pressionado && !botaoAnterior.current) reposicionar.current = true;
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
    reposicionar.current = false;
  });

  if (inspecao === "ferramentas") return <FerramentasPainelXR />;
  if (inspecao === "tutor") return <TutorPainelVR />;
  return <group ref={grupo} visible={Boolean(inspecao)} name="paineis-estudo-xr">
    <group position={[-PAINEIS_XR.lateral, 0, -PAINEIS_XR.distancia]} rotation={[0, PAINEIS_XR.inclinacao, 0]}>
      <FerramentasPainelXR />
    </group>
    <group position={[PAINEIS_XR.lateral, 0, -PAINEIS_XR.distancia]} rotation={[0, -PAINEIS_XR.inclinacao, 0]}>
      <TutorPainelVR />
    </group>
    <group position={[-0.27, -0.66, -1.12]}>
      <BotaoXR label="Reposicionar painéis" largura={0.48} y={0} onClick={() => { reposicionar.current = true; }} />
      <Text3D position={[0, -0.065, 0]} size={0.02} maxWidth={0.55}>B/Y também traz os painéis para a frente</Text3D>
    </group>
  </group>;
}
