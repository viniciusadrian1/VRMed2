/**
 * Vibração do controle (háptica) no WebXR.
 *
 * É o terceiro canal de resposta do duelo, junto com som e imagem: acertar e
 * sentir o controle responder é o que faz o toque parecer ter "peso". Vale um
 * arquivo próprio porque a API é frágil de três jeitos diferentes:
 *
 *  1. `hapticActuators` é experimental — existe no navegador da Meta, some no
 *     Chrome do desktop e não existe nenhum no SSR;
 *  2. o `gamepad` de um XRInputSource é opcional (mãos rastreadas não têm);
 *  3. alguns runtimes LANÇAM em vez de devolver undefined quando o controle
 *     acabou de desconectar — daí o try/catch por cima do optional chaining.
 *
 * O tipo já vem de @types/webxr (que declara `Gamepad.hapticActuators` e o
 * `pulse()` que falta na Gamepad API padrão), então não há `any` nenhum aqui.
 */

/** Pulsa o controle. Vibrar é enfeite: falhar aqui nunca derruba o jogo. */
/**
 * Trava de 60 ms, no módulo: com o laser parado na borda entre duas
 * alternativas, o tremor da mão faz o R3F alternar sair/entrar a cada quadro —
 * o booleano de hover não segura isso, e 90 pulsos por segundo esquentam o
 * motor e viram ruído branco na mão. O som do hover tem trava própria.
 */
let ultimoPulso = 0;

export function pulsar(
  fonte: XRInputSource | null | undefined,
  forca = 0.4,
  ms = 35,
): void {
  const agora = typeof performance === "undefined" ? 0 : performance.now();
  // Só os pulsos fracos (hover) são engolidos pela trava. Clique, acerto e
  // erro são eventos do jogo e podem cair no mesmo quadro — o acerto vem logo
  // depois do clique, e perder justamente esse seria o oposto do objetivo.
  if (forca <= 0.2 && agora - ultimoPulso < 60) return;
  ultimoPulso = agora;
  try {
    fonte?.gamepad?.hapticActuators?.[0]?.pulse?.(forca, ms)?.catch(() => {
      // Promessa rejeitada (controle sumiu no meio do pulso) não é problema nosso.
    });
  } catch {
    // Runtime sem háptica: segue o jogo, em silêncio.
  }
}
