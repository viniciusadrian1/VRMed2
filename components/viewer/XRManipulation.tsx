"use client";

import { useRef, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { useXRInputSourceState } from "@react-three/xr";
import * as THREE from "three";

/** Limites de escala, relativos ao tamanho original do modelo. */
const MIN_SCALE = 0.2;
const MAX_SCALE = 6;
/** Zona morta do analógico — evita deriva com o polegar em repouso. */
const STICK_DEADZONE = 0.15;
const STICK_SPEED = 1.4;

type Controller = ReturnType<typeof useXRInputSourceState<"controller">>;

/** Verifica se um botão do controle está pressionado. */
function isPressed(controller: Controller, id: string): boolean {
  return controller?.gamepad?.[id]?.state === "pressed";
}

/** Objeto 3D rastreado do controle (existe apenas durante a sessão). */
function objectOf(controller: Controller): THREE.Object3D | undefined {
  return controller?.object;
}

interface Snapshot {
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
  scale: THREE.Vector3;
}

/**
 * Manipulação do modelo em VR com os controles do headset:
 *
 *  - **Grip (uma mão)** — pega o órgão: ele acompanha a mão, movendo e girando
 *    junto, mantendo a posição relativa de onde foi agarrado.
 *  - **Grip (duas mãos)** — afastar/aproximar as mãos aumenta e diminui;
 *    mover as duas juntas arrasta o modelo.
 *  - **Analógico (frente/trás)** — aumenta e diminui, alternativa de uma mão só.
 *  - **Botão A ou X** — devolve o modelo à posição original (essencial num
 *    estande: a próxima pessoa sempre começa do mesmo jeito).
 *
 * A transformação é aplicada por matriz de mundo, sem reparentar o objeto —
 * assim o React Three Fiber continua dono da árvore da cena.
 */
export function XRManipulation({
  target,
}: {
  target: RefObject<THREE.Group | null>;
}) {
  const left = useXRInputSourceState("controller", "left");
  const right = useXRInputSourceState("controller", "right");

  /** Transformação original, para o botão de reset. */
  const home = useRef<Snapshot | null>(null);
  /** Deslocamento entre a mão e o modelo, no momento em que foi agarrado. */
  const grabOffset = useRef<THREE.Matrix4 | null>(null);
  /** Estado do gesto de duas mãos (distância e ponto médio anteriores). */
  const pinch = useRef<{ distance: number; middle: THREE.Vector3 } | null>(null);

  useFrame((_, delta) => {
    const model = target.current;
    if (!model) return;

    // Guarda a pose inicial na primeira vez que o modelo existe.
    if (!home.current) {
      home.current = {
        position: model.position.clone(),
        quaternion: model.quaternion.clone(),
        scale: model.scale.clone(),
      };
    }

    // --- Reset (A no controle direito, X no esquerdo) ---
    if (isPressed(right, "a-button") || isPressed(left, "x-button")) {
      model.position.copy(home.current.position);
      model.quaternion.copy(home.current.quaternion);
      model.scale.copy(home.current.scale);
      grabOffset.current = null;
      pinch.current = null;
      return;
    }

    const leftHeld = isPressed(left, "xr-standard-squeeze");
    const rightHeld = isPressed(right, "xr-standard-squeeze");
    const leftHand = objectOf(left);
    const rightHand = objectOf(right);

    const baseScale = home.current.scale.x || 1;
    const minScale = baseScale * MIN_SCALE;
    const maxScale = baseScale * MAX_SCALE;

    /* ---------------- Duas mãos: escalar e arrastar ---------------- */
    if (leftHeld && rightHeld && leftHand && rightHand) {
      grabOffset.current = null;

      const a = leftHand.getWorldPosition(new THREE.Vector3());
      const b = rightHand.getWorldPosition(new THREE.Vector3());
      const distance = a.distanceTo(b);
      const middle = a.clone().add(b).multiplyScalar(0.5);

      if (pinch.current && pinch.current.distance > 0.001) {
        // Escala proporcional à variação da distância entre as mãos.
        const ratio = distance / pinch.current.distance;
        const next = THREE.MathUtils.clamp(
          model.scale.x * ratio,
          minScale,
          maxScale,
        );
        model.scale.setScalar(next);
        // Arrasta acompanhando o deslocamento do ponto médio.
        model.position.add(middle.clone().sub(pinch.current.middle));
      }

      pinch.current = { distance, middle };
      return;
    }
    pinch.current = null;

    /* ---------------- Uma mão: pegar, mover e girar ---------------- */
    const held = rightHeld ? rightHand : leftHeld ? leftHand : undefined;
    if (held) {
      if (!grabOffset.current) {
        // Guarda a posição do modelo em relação à mão no instante da pegada.
        grabOffset.current = held.matrixWorld
          .clone()
          .invert()
          .multiply(model.matrixWorld);
      } else {
        const world = held.matrixWorld.clone().multiply(grabOffset.current);
        // Converte de volta para o espaço local do pai.
        const local = model.parent
          ? model.parent.matrixWorld.clone().invert().multiply(world)
          : world;
        local.decompose(model.position, model.quaternion, model.scale);
      }
      return;
    }
    grabOffset.current = null;

    /* ---------------- Analógico: aumentar / diminuir ---------------- */
    const stick =
      right?.gamepad?.["xr-standard-thumbstick"]?.yAxis ??
      left?.gamepad?.["xr-standard-thumbstick"]?.yAxis ??
      0;
    if (Math.abs(stick) > STICK_DEADZONE) {
      // Empurrar para frente (yAxis negativo) aumenta o modelo.
      const factor = 1 - stick * delta * STICK_SPEED;
      model.scale.setScalar(
        THREE.MathUtils.clamp(model.scale.x * factor, minScale, maxScale),
      );
    }
  });

  return null;
}
