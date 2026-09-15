"use client";

import { useRef, useState, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { useXRInputSourceState } from "@react-three/xr";
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
export function shapedAxis(value: number): number {
  const magnitude = Math.abs(value);
  if (magnitude < STICK_DEADZONE) return 0;
  const t = (magnitude - STICK_DEADZONE) / (1 - STICK_DEADZONE);
  return Math.sign(value) * t * t;
}
/** Giro pelo analógico (rad/s com o eixo no máximo). */
export const SPIN_SPEED = 3.2;
/** Tombamento (pitch) pelo analógico esquerdo (rad/s no máximo). */
export const PITCH_SPEED = 2.4;
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
  aoResetar,
}: {
  target: RefObject<THREE.Group | null>;
  /**
   * O que A/X faz com a POSIÇÃO. Sem isto, volta ao instantâneo inicial — o
   * certo nas cenas com lugar fixo (clínica, arena, mapa de achados). O
   * visualizador passa "trazer para a frente de quem olha agora".
   * A escala volta ao valor inicial nos dois casos.
   */
  aoResetar?: (
    model: THREE.Group,
    gl: THREE.WebGLRenderer,
    frame: XRFrame | undefined,
  ) => void;
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
      model.scale.copy(home.current.scale);
      if (aoResetar) {
        aoResetar(model, state.gl, frame);
      } else {
        model.position.copy(home.current.position);
        model.quaternion.copy(home.current.quaternion);
      }
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
      // Analógico para a direita traz para a frente o lado que estava à
      // direita de quem joga — como puxar a borda direita de uma vitrine
      // giratória em sua direção. O duelo usa o mesmo sentido.
      model.rotateOnWorldAxis(WORLD_Y, -spin * delta * SPIN_SPEED);
    }

    if (pitch !== 0) {
      // Tomba em torno do eixo "direita da câmera" projetado na horizontal:
      // o movimento acompanha o ponto de vista do jogador, de onde quer que
      // ele esteja olhando. Empurrar para frente tomba o topo para longe.
      //
      // O sinal estava invertido em relação a este comentário: com o eixo
      // "direita da câmera" e yAxis negativo para a frente, `-pitch` dava
      // ângulo positivo e trazia o topo PARA PERTO. Corrigido junto com o
      // duelo, que agora usa o analógico do mesmo jeito — os dois modos
      // tinham de responder igual ao mesmo gesto.
      TMP_DIR.setFromMatrixColumn(state.camera.matrixWorld, 0);
      TMP_DIR.y = 0;
      if (TMP_DIR.lengthSq() > 0.0001) {
        TMP_DIR.normalize();
        model.rotateOnWorldAxis(TMP_DIR, pitch * delta * PITCH_SPEED);
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
/* Entrada num modo imersivo: pose de partida à frente de quem olha            */
/* ------------------------------------------------------------------------- */

/**
 * Acima desta altura real o modelo deixa de flutuar e passa a apoiar no chão.
 *
 * Um corpo inteiro de 1,70 m não tem como ficar suspenso à frente do rosto: ou
 * some do campo de visão, ou atravessa o chão. A partir de 1 m a leitura certa
 * é a de uma pessoa em pé na sala, que é o que ela é.
 */
const ALTURA_PARA_APOIAR_NO_CHAO = 1.0;
/**
 * Quanto o centro do modelo flutuante fica abaixo da linha dos olhos.
 *
 * Cinco centímetros a meio metro de distância são ~6° para baixo: o olhar
 * desce um pouco, como quem observa algo na mão.
 */
const ABAIXO_DOS_OLHOS = 0.05;
/** Distância do modelo flutuante: proporcional ao tamanho, com piso e teto. */
const FLUTUANTE_DISTANCIA_POR_ALTURA = 2.2;
const FLUTUANTE_DISTANCIA_MIN = 0.45;
const FLUTUANTE_DISTANCIA_MAX = 1.1;
/** Distância do modelo apoiado: longe o bastante para caber no campo de visão. */
const CHAO_DISTANCIA_POR_ALTURA = 1.3;
const CHAO_DISTANCIA_MIN = 1.2;
const CHAO_DISTANCIA_MAX = 2.5;
/**
 * Quadros de tolerância esperando o rastreio reportar a cabeça. Passado esse
 * limite o modelo é colocado assim mesmo, supondo alguém de pé olhando para a
 * frente da sessão — e a manipulação é liberada. Melhor um órgão no lugar
 * aproximado do que um órgão que ninguém consegue agarrar.
 */
const QUADROS_DE_ESPERA = 90;
/** Altura dos olhos suposta quando o rastreio nunca responde (pessoa de pé). */
const OLHOS_SUPOSTOS = 1.55;
/**
 * Depois da primeira pose REAL, por quanto tempo o modelo continua sendo
 * recolocado na linha dos olhos antes de parar (s).
 *
 * Colocar uma vez só, no primeiro quadro, confiava num único número. Logo ao
 * entrar no modo imersivo o rastreio ainda está se acomodando e a altura pode
 * pular. Três quartos de segundo cobrem isso e passam despercebidos: a pessoa
 * vê o órgão já parado à frente dela.
 */
const ACOMODACAO_S = 0.75;

/**
 * Marca da versão desta lógica de pose, exibida no painel de diagnóstico.
 * Serve para uma pergunta só: "o óculos está rodando o código novo?". O cache
 * do Turbopack e o do navegador do Quest já serviram código velho mais de uma
 * vez neste projeto. Aumente o número a cada mudança nesta seção.
 */
export const VERSAO_POSE = "pose-4";

/**
 * O que a última colocação decidiu, para o painel `?debug=xr` ler.
 * Mutável e fora do React de propósito: é escrito dentro do `useFrame`, onde
 * um setState por quadro seria desperdício.
 */
export const diagnosticoPose = {
  /** De onde veio a altura dos olhos usada: pose real, estimada ou suposta. */
  fonte: "—" as "real" | "estimada" | "suposta" | "—",
  /** Poses descartadas por serem estimadas (`emulatedPosition`). */
  posesEstimadasDescartadas: 0,
  olhosAcimaDoChao: NaN,
  alturaModelo: NaN,
  distancia: NaN,
  apoiado: false,
  /** O objeto posicionado, para o painel medir a altura dele ao vivo. */
  modelo: null as THREE.Object3D | null,
};

// Reutilizados: a colocação roda uma vez, mas o reset pode rodar a cada A/X.
const TMP_CABECA = new THREE.Vector3();
const TMP_FRENTE = new THREE.Vector3();
const TMP_CHAO = new THREE.Vector3();

interface PoseDaCabeca {
  /** Posição dos olhos, em coordenadas de MUNDO. */
  cabeca: THREE.Vector3;
  /** Direção horizontal do olhar, normalizada, em MUNDO. */
  frente: THREE.Vector3;
  /** Y de mundo do chão da sessão. */
  chaoY: number;
}

/**
 * Onde está a cabeça de quem usa o headset, em coordenadas de MUNDO.
 *
 * POR QUE A CÂMERA DE XR, E NÃO `getViewerPose` + A ORIGEM DA SESSÃO
 *
 * A primeira versão lia a pose do `XRFrame` e a convertia para o mundo com a
 * matriz do `XROrigin`, obtida por `useXR((s) => s.origin)`. Esse valor só é
 * gravado no store no PRIMEIRO quadro de XR, e o componente só o enxerga no
 * render seguinte. O posicionamento rodava justamente nesse primeiro quadro,
 * com o valor antigo — a própria cena, de matriz identidade, que é o que a
 * origem vale fora da sessão. Na prática a conversão não fazia nada:
 *
 *   - em AR a origem fica em y=0, então pular não mudava nada — e o bug não
 *     aparecia nos testes de AR;
 *   - em VR a origem fica no chão da grade, 1,30 m abaixo. Sem a conversão, o
 *     órgão flutuante nascia ~1,25 m acima dos olhos, alto demais para ser
 *     encontrado, e o corpo inteiro, que deveria apoiar no chão, flutuava
 *     1,30 m acima dele.
 *
 * A câmera de XR resolve as duas coisas de uma vez. O `@react-three/xr` a
 * pendura como filha do `XROrigin`, e o three grava nela a pose deste quadro
 * ANTES de chamar o `useFrame`. `getWorldPosition` já devolve a pose composta
 * com a origem, sem conversão manual e sem depender de estado do React. O chão
 * sai do mesmo lugar: o pai dela é a própria origem.
 *
 * `getViewerPose` continua, mas só como sinal de que o rastreio está valendo
 * neste quadro; sem ele a câmera poderia guardar uma pose velha ou nula.
 */
function poseDaCabeca(
  gl: THREE.WebGLRenderer,
  frame: XRFrame | undefined,
  aceitarEstimada = false,
): PoseDaCabeca | null {
  const espaco = gl.xr.getReferenceSpace();
  const viewer = frame && espaco ? frame.getViewerPose(espaco) : null;
  if (!viewer) return null;
  // `emulatedPosition` quer dizer que o headset NÃO sabe onde a cabeça está e
  // devolveu uma estimativa. Isso acontece justamente nos primeiros quadros
  // depois de entrar no modo imersivo, antes do rastreio se firmar. Nem o
  // three nem o @react-three/xr filtram: a câmera recebe a estimativa como se
  // fosse real. Colocar o órgão nessa altura e congelar era o que o deixava
  // alto demais para quem está sentado — a estimativa não sabe disso.
  if (viewer.emulatedPosition && !aceitarEstimada) {
    diagnosticoPose.posesEstimadasDescartadas += 1;
    return null;
  }

  const camera = gl.xr.getCamera();
  const origem = camera.parent;
  if (!origem) return null;

  const cabeca = camera.getWorldPosition(TMP_CABECA);
  const frente = camera.getWorldDirection(TMP_FRENTE);
  frente.y = 0;
  // Olhando quase reto para cima ou para baixo: sem direção horizontal
  // confiável. Quem chamou tenta de novo no próximo quadro.
  if (frente.lengthSq() < 1e-4) return null;
  frente.normalize();

  return { cabeca, frente, chaoY: origem.getWorldPosition(TMP_CHAO).y };
}

/**
 * Coloca o modelo à frente da cabeça: flutuando na linha dos olhos se for
 * pequeno, apoiado no chão se for do tamanho de uma pessoa, e virado de frente
 * para quem olha.
 *
 * Só a componente HORIZONTAL do olhar é usada. Quem entra olhando para o chão
 * continua recebendo o modelo à frente e na altura certa — com a direção crua
 * ele seria enterrado no piso.
 */
function colocarAFrente(model: THREE.Object3D, pose: PoseDaCabeca): boolean {
  // Zera a rotação ANTES de medir. A altura que decide entre flutuar e apoiar
  // é a do modelo em pé; um modelo tombado no 2D (pelo gizmo de rotação, que
  // não é prop e atravessa a entrada na sessão) ou girado pelas mãos antes de
  // um reset mediria outra coisa. A rotação final é reaplicada logo abaixo.
  model.rotation.set(0, 0, 0);
  // A altura é MEDIDA no objeto como ele está, com a escala real já aplicada.
  const caixa = new THREE.Box3().setFromObject(model);
  const alturaReal = caixa.max.y - caixa.min.y;
  if (!Number.isFinite(alturaReal) || alturaReal <= 0) return false;

  const apoiado = alturaReal >= ALTURA_PARA_APOIAR_NO_CHAO;
  const distancia = apoiado
    ? THREE.MathUtils.clamp(
        alturaReal * CHAO_DISTANCIA_POR_ALTURA,
        CHAO_DISTANCIA_MIN,
        CHAO_DISTANCIA_MAX,
      )
    : THREE.MathUtils.clamp(
        alturaReal * FLUTUANTE_DISTANCIA_POR_ALTURA,
        FLUTUANTE_DISTANCIA_MIN,
        FLUTUANTE_DISTANCIA_MAX,
      );

  const alvo = pose.cabeca.clone().addScaledVector(pose.frente, distancia);
  // O modelo é normalizado com o centro na origem do grupo, então apoiar no
  // chão é pôr o CENTRO a meia altura acima dele.
  alvo.y = apoiado
    ? pose.chaoY + alturaReal / 2
    : pose.cabeca.y - ABAIXO_DOS_OLHOS;

  diagnosticoPose.olhosAcimaDoChao = pose.cabeca.y - pose.chaoY;
  diagnosticoPose.alturaModelo = alturaReal;
  diagnosticoPose.distancia = distancia;
  diagnosticoPose.apoiado = apoiado;
  diagnosticoPose.modelo = model;

  if (model.parent) model.parent.worldToLocal(alvo);
  model.position.copy(alvo);
  // O +Z do modelo aponta de volta para a cabeça: a pessoa começa vendo a
  // frente do órgão, não as costas.
  model.rotation.set(0, Math.atan2(-pose.frente.x, -pose.frente.z), 0);
  return true;
}

/** Pose suposta para quando o rastreio nunca responde: de pé, olhando para −Z. */
function poseSuposta(gl: THREE.WebGLRenderer): PoseDaCabeca {
  const origem = gl.xr.getCamera().parent;
  const base = origem
    ? origem.getWorldPosition(new THREE.Vector3())
    : new THREE.Vector3();
  return {
    cabeca: new THREE.Vector3(base.x, base.y + OLHOS_SUPOSTOS, base.z),
    frente: new THREE.Vector3(0, 0, -1),
    chaoY: base.y,
  };
}

/** Coloca o modelo uma vez, no início da sessão, e avisa quando terminou. */
function PoseDeEntrada({
  target,
  onPronto,
}: {
  target: RefObject<THREE.Group | null>;
  onPronto: () => void;
}) {
  const quadros = useRef(0);
  const feito = useRef(false);
  /** Instante da primeira colocação com pose REAL; abre a janela de acomodação. */
  const primeiraReal = useRef<number | null>(null);

  useFrame((state, _delta, frame) => {
    if (feito.current) return;
    const model = target.current;
    if (!model) return;

    quadros.current += 1;
    const encerrar = () => {
      feito.current = true;
      onPronto();
    };

    // Com pose real: recoloca a cada quadro durante a acomodação, e só então
    // para. A última colocação é a que fica.
    const real = poseDaCabeca(state.gl, frame);
    if (real && colocarAFrente(model, real)) {
      diagnosticoPose.fonte = "real";
      const agora = state.clock.elapsedTime;
      primeiraReal.current ??= agora;
      if (agora - primeiraReal.current >= ACOMODACAO_S) encerrar();
      return;
    }

    // Já houve pose real e ela sumiu no meio da acomodação: fica com a última.
    if (primeiraReal.current !== null) {
      if (quadros.current > QUADROS_DE_ESPERA) encerrar();
      return;
    }

    // Nunca veio pose real. Depois da espera, a estimativa do headset ainda é
    // melhor que uma altura inventada; sem nem ela, supõe alguém de pé.
    if (quadros.current > QUADROS_DE_ESPERA) {
      const estimada = poseDaCabeca(state.gl, frame, true);
      const colocou = estimada
        ? colocarAFrente(model, estimada)
        : colocarAFrente(model, poseSuposta(state.gl));
      diagnosticoPose.fonte = estimada ? "estimada" : "suposta";
      // Mesmo sem conseguir colocar (caixa ainda vazia), libera a manipulação
      // depois de um tempo: travar o controle seria pior que o lugar errado.
      if (colocou || quadros.current > QUADROS_DE_ESPERA * 2) encerrar();
    }
  });

  return null;
}

/**
 * Entrada num modo imersivo: posiciona o modelo e só então libera a
 * manipulação.
 *
 * A ordem importa. O `XRManipulation` guarda a escala inicial no primeiro
 * quadro em que roda; se montasse antes do posicionamento, guardaria a pose
 * provisória.
 *
 * O botão A/X, aqui, TRAZ O MODELO PARA A FRENTE DE QUEM ESTÁ USANDO AGORA,
 * em vez de devolvê-lo a um instantâneo. Num estande é isso que "a próxima
 * pessoa começa do mesmo jeito" quer dizer: a pessoa seguinte pode estar
 * sentada, ou de pé, ou virada para outro lado. Um instantâneo medido na
 * cabeça de quem veio antes deixaria o órgão no lugar certo para outra pessoa.
 */
export function EntradaXR({
  target,
}: {
  target: RefObject<THREE.Group | null>;
}) {
  const [posicionado, setPosicionado] = useState(false);

  return (
    <>
      {!posicionado && (
        <PoseDeEntrada target={target} onPronto={() => setPosicionado(true)} />
      )}
      {posicionado && (
        <XRManipulation
          target={target}
          aoResetar={(model, gl, frame) => {
            colocarAFrente(
              model,
              poseDaCabeca(gl, frame) ??
                poseDaCabeca(gl, frame, true) ??
                poseSuposta(gl),
            );
          }}
        />
      )}
    </>
  );
}
