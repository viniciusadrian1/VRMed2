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
/**
 * Limiares do gesto de pinça (metros, entre as pontas do polegar e do
 * indicador). Fechar e abrir têm valores diferentes de propósito: sem essa
 * histerese a pegada ficaria piscando quando os dedos param perto do limiar.
 */
const PINCH_CLOSE = 0.025;
const PINCH_OPEN = 0.045;

type Controller = ReturnType<typeof useXRInputSourceState<"controller">>;
type Hand = ReturnType<typeof useXRInputSourceState<"hand">>;

/** Verifica se um botão do controle está pressionado. */
function isPressed(controller: Controller, id: string): boolean {
  return controller?.gamepad?.[id]?.state === "pressed";
}

/**
 * Detecta a pinça (polegar encostando no indicador) lendo as articulações
 * da mão rastreada. A distância entre juntas é a mesma no espaço de
 * referência e no mundo — a transformação entre eles é rígida —, então dá
 * para comparar direto, sem conversão.
 */
function isPinching(
  hand: Hand,
  frame: XRFrame | undefined,
  referenceSpace: XRReferenceSpace | null,
  wasPinching: boolean,
): boolean {
  const joints = hand?.inputSource?.hand;
  if (!joints || !frame?.getJointPose || !referenceSpace) return false;

  const thumb = joints.get("thumb-tip");
  const index = joints.get("index-finger-tip");
  if (!thumb || !index) return false;

  const a = frame.getJointPose(thumb, referenceSpace);
  const b = frame.getJointPose(index, referenceSpace);
  if (!a || !b) return false;

  const dx = a.transform.position.x - b.transform.position.x;
  const dy = a.transform.position.y - b.transform.position.y;
  const dz = a.transform.position.z - b.transform.position.z;
  const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);

  // Já pegando: só solta ao abrir bem os dedos.
  return wasPinching ? distance < PINCH_OPEN : distance < PINCH_CLOSE;
}

interface Snapshot {
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
  scale: THREE.Vector3;
}

/**
 * Manipulação do modelo em VR, funcionando tanto com os controles quanto
 * apenas com as mãos rastreadas (hand tracking) — o gesto de pegar é o
 * gatilho lateral no controle ou a pinça (polegar + indicador) na mão:
 *
 *  - **Pegar com uma mão** — o órgão acompanha a mão, movendo e girando junto,
 *    mantendo a posição relativa de onde foi agarrado.
 *  - **Pegar com as duas** — afastar/aproximar aumenta e diminui;
 *    mover as duas juntas arrasta o modelo.
 *  - **Analógico (frente/trás)** — aumenta e diminui (só nos controles).
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
  const leftController = useXRInputSourceState("controller", "left");
  const rightController = useXRInputSourceState("controller", "right");
  const leftHandInput = useXRInputSourceState("hand", "left");
  const rightHandInput = useXRInputSourceState("hand", "right");

  /** Transformação original, para o botão de reset. */
  const home = useRef<Snapshot | null>(null);
  /** Deslocamento entre a mão e o modelo, no momento em que foi agarrado. */
  const grabOffset = useRef<THREE.Matrix4 | null>(null);
  /** Estado do gesto de duas mãos (distância e ponto médio anteriores). */
  const pinch = useRef<{ distance: number; middle: THREE.Vector3 } | null>(null);
  /** Pinça ativa em cada mão, para aplicar a histerese. */
  const pinching = useRef({ left: false, right: false });

  useFrame((state, delta, frame) => {
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
    if (
      isPressed(rightController, "a-button") ||
      isPressed(leftController, "x-button")
    ) {
      model.position.copy(home.current.position);
      model.quaternion.copy(home.current.quaternion);
      model.scale.copy(home.current.scale);
      grabOffset.current = null;
      pinch.current = null;
      return;
    }

    // Cada lado pode vir de um controle (gatilho lateral) ou de uma mão
    // rastreada (pinça). O resto da lógica não precisa saber a diferença.
    const referenceSpace = state.gl.xr.getReferenceSpace();

    pinching.current.left = isPinching(
      leftHandInput,
      frame,
      referenceSpace,
      pinching.current.left,
    );
    pinching.current.right = isPinching(
      rightHandInput,
      frame,
      referenceSpace,
      pinching.current.right,
    );

    const leftHeld =
      isPressed(leftController, "xr-standard-squeeze") || pinching.current.left;
    const rightHeld =
      isPressed(rightController, "xr-standard-squeeze") ||
      pinching.current.right;
    const leftHand = leftController?.object ?? leftHandInput?.object;
    const rightHand = rightController?.object ?? rightHandInput?.object;

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
    // Só existe em controles; com as mãos, usa-se o gesto de duas pinças.
    const stick =
      rightController?.gamepad?.["xr-standard-thumbstick"]?.yAxis ??
      leftController?.gamepad?.["xr-standard-thumbstick"]?.yAxis ??
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
