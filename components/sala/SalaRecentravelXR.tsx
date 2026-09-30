"use client";

import { useCallback, useRef, useState, type ReactNode } from "react";
import { useFrame } from "@react-three/fiber";
import { useXR, useXRInputSourceState } from "@react-three/xr";
import { Group, Quaternion, Vector3 } from "three";
import { Button3D, Panel, Text3D } from "@/components/arena/ui3d";
import { SairDoVR } from "@/components/xr/SairDoVR";
import { apertouRecentralizarSala, calcularRecentralizacaoSala, type EstadoAtalhoSala } from "@/lib/sala-recentrar";

const INSTRUCAO = "Olhe para a frente · Y (esquerdo) ou B (direito)";

/** Move a sala inteira uma única vez por pedido, nunca acompanha a cabeça. */
export function SalaRecentravelXR({ children }: { children: ReactNode }) {
  const sala = useRef<Group>(null);
  const controles = useRef<Group>(null);
  const session = useXR((state) => state.session);
  const esquerdo = useXRInputSourceState("controller", "left");
  const direito = useXRInputSourceState("controller", "right");
  const [aviso, setAviso] = useState(INSTRUCAO);
  const estado = useRef({
    session: undefined as XRSession | undefined,
    prazo: 0,
    esquerdo: { fonte: undefined, pressionado: false } as EstadoAtalhoSala,
    direito: { fonte: undefined, pressionado: false } as EstadoAtalhoSala,
    cabeca: new Vector3(), frente: new Vector3(), chao: new Vector3(), orientacao: new Quaternion(),
  });
  const solicitar = useCallback(() => {
    if (!session || session.visibilityState !== "visible") return;
    estado.current.prazo = performance.now() + 3000;
    setAviso("Ajustando à sua posição… olhe para a frente");
  }, [session]);

  useFrame(({ gl }, _, frame) => {
    const atual = estado.current;
    if (!sala.current || !controles.current) return;
    if (atual.session !== session) {
      atual.session = session;
      atual.esquerdo = { fonte: undefined, pressionado: false };
      atual.direito = { fonte: undefined, pressionado: false };
      // Reentrar começa limpo; uma pose real acomoda a mesa ao assento atual.
      sala.current.position.set(0, 0, 0);
      sala.current.rotation.set(0, 0, 0);
      controles.current.position.y = 0.9;
      atual.prazo = session ? performance.now() + 3000 : 0;
      setAviso(INSTRUCAO);
    }
    if (!session) return;

    // Atualizar as duas bordas mesmo quando ambos os botões estão pressionados.
    const y = apertouRecentralizarSala(atual.esquerdo, esquerdo?.inputSource, esquerdo?.gamepad?.["y-button"]?.state === "pressed");
    const b = apertouRecentralizarSala(atual.direito, direito?.inputSource, direito?.gamepad?.["b-button"]?.state === "pressed");
    if (session.visibilityState !== "visible" || gl.xr.getSession() !== session) {
      atual.prazo = 0; // Não guardar um salto para quando a pessoa voltar do menu Meta.
      return;
    }
    if (y || b) solicitar();
    if (!atual.prazo) return;
    if (performance.now() > atual.prazo) {
      atual.prazo = 0;
      setAviso("Olhe à frente e tente de novo quando o rastreio voltar");
      return;
    }
    const espaco = gl.xr.getReferenceSpace();
    const pose = frame && espaco ? frame.getViewerPose(espaco) : null;
    const origem = gl.xr.getCamera().parent;
    if (!pose || pose.emulatedPosition || !origem) return;

    // Ponto entre os olhos, não a câmera do olho esquerdo. A origem é a mesma
    // usada pelo renderer neste quadro; não dependemos de estado atrasado do XR.
    origem.updateWorldMatrix(true, false);
    const p = pose.transform.position;
    const q = pose.transform.orientation;
    atual.cabeca.set(p.x, p.y, p.z).applyMatrix4(origem.matrixWorld);
    atual.orientacao.set(q.x, q.y, q.z, q.w);
    atual.frente.set(0, 0, -1).applyQuaternion(atual.orientacao).transformDirection(origem.matrixWorld);
    origem.getWorldPosition(atual.chao);
    const ajuste = calcularRecentralizacaoSala(atual.cabeca, atual.frente, atual.chao.y);
    if (!ajuste) return;

    sala.current.position.fromArray(ajuste.posicao);
    sala.current.rotation.set(0, ajuste.rotacaoY, 0);
    controles.current.position.y = ajuste.alturaControles;
    sala.current.updateWorldMatrix(true, true);
    atual.prazo = 0;
    setAviso("Sala recentralizada · repetir: Y ou B");
  });

  return (
    <group ref={sala} name="sala-recentravel">
      {children}
      {/* Fora do ErrorBoundary da cena. SairDoVR permanece montado também no
          desktop, preservando a limpeza da sessão ao navegar para outra rota. */}
      <group ref={controles} position={[0, 0.9, -1.95]} visible={Boolean(session)}>
        <SairDoVR position={[0.3, 0, 0.01]} rotationY={0} />
        {session && (
          <Panel width={1.08} height={0.24} color="#34291f">
            <Button3D label="Recentralizar" width={0.52} height={0.11}
              position={[-0.23, 0, 0.01]} color="#73502c" onClick={solicitar} />
            <Text3D position={[0, 0.09, 0.01]} size={0.027}>Ajustar o assento</Text3D>
            <Text3D position={[0, -0.086, 0.01]} size={0.023} maxWidth={1.01}>{aviso}</Text3D>
          </Panel>
        )}
      </group>
    </group>
  );
}
