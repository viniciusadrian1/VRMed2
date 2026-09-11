"use client";

import { useRef, useState, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { useXR, useXRInputSourceState } from "@react-three/xr";
import * as THREE from "three";

/** Limites de escala, relativos ao tamanho original do modelo. */
const MIN_SCALE = 0.2;
const MAX_SCALE = 6;
/** Zona morta do analógico — evita deriva com o polegar em repouso. */
const STICK_DEADZONE = 0.2;

/**
 * Resposta suavizada do analógico: zero dentro da zona morta e curva
 * quadrática fora dela. Sem isso o comando "liga de repente" quando o
 * polegar cruza a borda da zona morta — a sensação de travado/aos trancos —
 * e não há controle fino perto do centro.
 */
function shapedAxis(value: number): number {
  const magnitude = Math.abs(value);
  if (magnitude < STICK_DEADZONE) return 0;
  const t = (magnitude - STICK_DEADZONE) / (1 - STICK_DEADZONE);
  return Math.sign(value) * t * t;
}
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

    // Por analógico, age só o eixo DOMINANTE. Ninguém empurra o polegar
    // perfeitamente para o lado — sempre vai um resto de "frente" junto, e
    // com os eixos independentes tentar girar disparava o aproximar.
    const rightSpin = Math.abs(rx) >= Math.abs(ry) ? shapedAxis(rx) : 0;
    const approach = Math.abs(ry) > Math.abs(rx) ? shapedAxis(ry) : 0;
    const leftSpin = Math.abs(lx) >= Math.abs(ly) ? shapedAxis(lx) : 0;
    const pitch = Math.abs(ly) > Math.abs(lx) ? shapedAxis(ly) : 0;
    const spin =
      Math.abs(rightSpin) >= Math.abs(leftSpin) ? rightSpin : leftSpin;

    if (spin !== 0) {
      // Sinal invertido: analógico para a direita gira a face do modelo
      // para a direita do jogador (sentido natural de "girar a vitrine").
      model.rotateOnWorldAxis(WORLD_Y, -spin * delta * SPIN_SPEED);
    }

    if (pitch !== 0) {
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

    if (approach !== 0) {
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

/* ------------------------------------------------------------------------- */
/* Pose de entrada em AR                                                       */
/* ------------------------------------------------------------------------- */

/** Distância horizontal entre a cabeça e o centro do órgão, ao entrar em AR. */
const AR_DISTANCIA = 0.6;
/**
 * Quanto o centro do órgão fica ABAIXO da linha dos olhos.
 *
 * Com o órgão em ~44 cm, 0,18 m deixa o topo dele pouco acima do olhar e o
 * corpo logo abaixo — a pessoa baixa um pouco os olhos, que é como se olha
 * para algo na mão, em vez de erguer a cabeça.
 */
const AR_ABAIXO_DOS_OLHOS = 0.18;
/**
 * Quadros de tolerância esperando o rastreio reportar a cabeça. Passado esse
 * limite a manipulação é liberada assim mesmo, com a pose fixa que já estava
 * aplicada: melhor um órgão no lugar aproximado do que um órgão que ninguém
 * consegue agarrar porque o rastreio não respondeu.
 */
const AR_QUADROS_DE_ESPERA = 90;

/**
 * Coloca o órgão à frente de QUEM ESTÁ OLHANDO, no instante em que a sessão
 * de AR começa — uma vez só, não a cada quadro.
 *
 * O problema que isto resolve: a pose fixa supunha alguém de pé. Abrindo o
 * modo sentado, o órgão aparecia alto e distante, e a pessoa tinha de olhar
 * para cima. A altura dos olhos varia quase meio metro entre sentado e de pé,
 * e a direção para onde a pessoa começa virada é imprevisível num estande.
 *
 * A pose vem do `XRFrame`, não da câmera do three: a câmera só recebe a pose
 * do quadro ANTERIOR, e no primeiro quadro da sessão ela ainda está na
 * posição do modo 2D. `getViewerPose` é a fonte autoritativa e já vale no
 * primeiro quadro; enquanto ela não vier (rastreio ainda iniciando), espera.
 *
 * Só a componente HORIZONTAL do olhar é usada. Quem entra olhando para o chão
 * ou para o teto continua recebendo o órgão à sua frente, na altura certa —
 * usar a direção crua enterraria o modelo no piso.
 */
function PoseDeEntradaAR({
  target,
  onPronto,
}: {
  target: RefObject<THREE.Group | null>;
  onPronto: () => void;
}) {
  const origem = useXR((state) => state.origin);
  const quadros = useRef(0);
  const feito = useRef(false);

  useFrame((state, _delta, frame) => {
    if (feito.current) return;
    const model = target.current;
    if (!model) return;

    quadros.current += 1;
    const desistir = quadros.current > AR_QUADROS_DE_ESPERA;

    const espaco = state.gl.xr.getReferenceSpace();
    const pose = frame && espaco ? frame.getViewerPose(espaco) : null;
    if (!pose) {
      if (desistir) {
        feito.current = true;
        onPronto();
      }
      return;
    }

    const p = pose.transform.position;
    const o = pose.transform.orientation;
    const cabeca = new THREE.Vector3(p.x, p.y, p.z);
    const frente = new THREE.Vector3(0, 0, -1).applyQuaternion(
      new THREE.Quaternion(o.x, o.y, o.z, o.w),
    );

    // Do espaço de referência do WebXR para o mundo: o XROrigin pode estar
    // deslocado (em AR ele fica na origem, mas isto não é suposição daqui).
    if (origem) {
      cabeca.applyMatrix4(origem.matrixWorld);
      frente.transformDirection(origem.matrixWorld);
    }

    frente.y = 0;
    if (frente.lengthSq() < 1e-4) {
      // Olhando quase reto para cima ou para baixo: sem direção horizontal
      // confiável. Tenta no próximo quadro.
      if (desistir) {
        feito.current = true;
        onPronto();
      }
      return;
    }
    frente.normalize();

    const alvo = cabeca.clone().addScaledVector(frente, AR_DISTANCIA);
    alvo.y = cabeca.y - AR_ABAIXO_DOS_OLHOS;
    if (model.parent) model.parent.worldToLocal(alvo);
    model.position.copy(alvo);

    // Vira o órgão de frente para quem olha. Em VR o usuário nasce no +Z e vê
    // a face +Z do modelo; aqui o +Z tem de apontar de volta para a cabeça,
    // senão a pessoa pode começar olhando para as costas do órgão.
    model.rotation.set(0, Math.atan2(-frente.x, -frente.z), 0);

    feito.current = true;
    onPronto();
  });

  return null;
}

/**
 * Entrada num modo imersivo: coloca o órgão no lugar e só então libera a
 * manipulação.
 *
 * A ordem importa. O `XRManipulation` guarda a pose inicial no primeiro
 * quadro em que roda, para o botão de reset (A/X) poder devolver o modelo ao
 * ponto de partida. Se ele montasse antes do posicionamento de AR, o reset
 * levaria o órgão para a pose de VR — a que o estande não comporta.
 *
 * Em VR não há o que medir: a cena é nossa e a pose é fixa, então a
 * manipulação entra direto.
 */
export function EntradaXR({
  modo,
  target,
}: {
  modo: XRSessionMode | null;
  target: RefObject<THREE.Group | null>;
}) {
  const [posicionado, setPosicionado] = useState(modo !== "immersive-ar");

  return (
    <>
      {!posicionado && (
        <PoseDeEntradaAR target={target} onPronto={() => setPosicionado(true)} />
      )}
      {posicionado && <XRManipulation target={target} />}
    </>
  );
}
