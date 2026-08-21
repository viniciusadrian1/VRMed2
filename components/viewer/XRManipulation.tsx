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
/** Giro pelo analógico (rad/s com o eixo no máximo). */
const SPIN_SPEED = 3.2;
/** Tombamento (pitch) pelo analógico esquerdo (rad/s no máximo). */
const PITCH_SPEED = 2.4;
/** Aproximar/afastar pelo analógico (m/s com o eixo no máximo). */
const APPROACH_SPEED = 1.3;
/** Distância cabeça→órgão permitida (m): nem dentro do rosto, nem longe demais. */
const MIN_HEAD_DISTANCE = 0.45;
const MAX_HEAD_DISTANCE = 5;

// Reutilizados a cada quadro para não alocar vetores a 72–90 Hz.
const WORLD_Y = new THREE.Vector3(0, 1, 0);
const TMP_HEAD = new THREE.Vector3();
const TMP_DIR = new THREE.Vector3();
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
 *  - **Analógico ⇄ (qualquer um)** — gira o órgão como um torno (yaw).
 *  - **Analógico direito ↕** — traz para perto do rosto / afasta.
 *  - **Analógico esquerdo ↕** — tomba o órgão (pitch), para alcançar
 *    estruturas no topo ou embaixo.
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

  useFrame((state, rawDelta, frame) => {
    const model = target.current;
    if (!model) return;

    // Limita o passo de tempo. Ao tirar o headset da cabeça a sessão pausa e,
    // ao voltar, o primeiro `delta` vem com dezenas de segundos acumulados —
    // sem esse teto, um polegar apenas encostado no analógico faria a escala
    // saltar direto para o limite.
    const delta = Math.min(rawDelta, 1 / 30);

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

    /* ------------- Analógicos: girar, tombar e aproximar ------------- */
    // Virar o modelo pela pegada 1:1 exige contorção do punho (180° de giro
    // = 180° de pulso). Os analógicos fazem isso sem esforço:
    //   direito  X → gira (yaw)      | direito  Y → aproxima/afasta
    //   esquerdo X → gira (yaw)      | esquerdo Y → TOMBA (pitch)
    // O tombamento é o que faltava: estrutura no topo ou embaixo do órgão
    // era inalcançável só com o giro horizontal.
    const leftPad = leftController?.gamepad?.["xr-standard-thumbstick"];
    const rightPad = rightController?.gamepad?.["xr-standard-thumbstick"];
    const lx = leftPad?.xAxis ?? 0;
    const rx = rightPad?.xAxis ?? 0;
    const ly = leftPad?.yAxis ?? 0;
    const ry = rightPad?.yAxis ?? 0;
    const spin = Math.abs(rx) >= Math.abs(lx) ? rx : lx;
    const pitch = ly;
    const approach = ry;

    if (Math.abs(spin) > STICK_DEADZONE) {
      // Sinal invertido: analógico para a direita gira a face do modelo
      // para a direita do jogador (sentido natural de "girar a vitrine").
      model.rotateOnWorldAxis(WORLD_Y, -spin * delta * SPIN_SPEED);
    }

    if (Math.abs(pitch) > STICK_DEADZONE) {
      // Tomba em torno do eixo "direita da câmera" projetado na horizontal:
      // o movimento acompanha o ponto de vista do jogador, de onde quer que
      // ele esteja olhando. Empurrar para frente tomba o topo para longe.
      TMP_DIR.setFromMatrixColumn(state.camera.matrixWorld, 0);
      TMP_DIR.y = 0;
      if (TMP_DIR.lengthSq() > 0.0001) {
        TMP_DIR.normalize();
        model.rotateOnWorldAxis(TMP_DIR, -pitch * delta * PITCH_SPEED);
      }
    }

    if (Math.abs(approach) > STICK_DEADZONE) {
      // Move ao longo da linha cabeça→órgão: ao aproximar, ele também sobe
      // até a altura do olhar — vem "para a mão" do jogador.
      const head = state.camera.getWorldPosition(TMP_HEAD);
      const direction = TMP_DIR.copy(model.position).sub(head);
      const distance = direction.length() || 1;
      direction.normalize();
      // yAxis é negativo com o analógico para frente → aproxima.
      const next = THREE.MathUtils.clamp(
        distance + approach * delta * APPROACH_SPEED,
        MIN_HEAD_DISTANCE,
        MAX_HEAD_DISTANCE,
      );
      model.position.copy(head).addScaledVector(direction, next);
    }
  });

  return null;
}
