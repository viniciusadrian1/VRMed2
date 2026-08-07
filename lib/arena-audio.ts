/**
 * Sons da Arena gerados por síntese (WebAudio), sem nenhum arquivo.
 *
 * O projeto não tem assets de áudio e, no evento, a rede pode cair — baixar
 * som seria mais uma dependência para falhar. Osciladores resolvem em algumas
 * linhas, tocam instantaneamente e funcionam offline.
 *
 * O áudio do headset é, aliás, o único canal sonoro que sobrevive ao barulho
 * do evento: os alto-falantes ficam junto ao ouvido.
 */

let context: AudioContext | null = null;

/** O contexto só pode ser criado depois de um gesto do usuário. */
function getContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!context) {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!Ctor) return null;
    context = new Ctor();
  }
  if (context.state === "suspended") void context.resume();
  return context;
}

interface ToneOptions {
  from: number;
  to: number;
  duration: number;
  type?: OscillatorType;
  gain?: number;
}

/** Toca uma nota curta com variação de altura. */
function tone({ from, to, duration, type = "sine", gain = 0.18 }: ToneOptions) {
  const ctx = getContext();
  if (!ctx) return;

  const oscillator = ctx.createOscillator();
  const volume = ctx.createGain();
  const now = ctx.currentTime;

  oscillator.type = type;
  oscillator.frequency.setValueAtTime(from, now);
  oscillator.frequency.exponentialRampToValueAtTime(to, now + duration);

  // Ataque rápido e queda suave — evita o "clique" de corte abrupto.
  volume.gain.setValueAtTime(0.0001, now);
  volume.gain.exponentialRampToValueAtTime(gain, now + 0.01);
  volume.gain.exponentialRampToValueAtTime(0.0001, now + duration);

  oscillator.connect(volume).connect(ctx.destination);
  oscillator.start(now);
  oscillator.stop(now + duration + 0.02);
}

/** Acerto: nota ascendente e clara. */
export function playHit(combo = 1): void {
  // Cada acerto seguido sobe um pouco o tom — o combo vira som.
  const base = 520 + Math.min(combo, 6) * 60;
  tone({ from: base, to: base * 1.5, duration: 0.16, type: "triangle" });
}

/** Erro: nota grave e curta, sem punir o ouvido. */
export function playMiss(): void {
  tone({ from: 220, to: 130, duration: 0.22, type: "sawtooth", gain: 0.12 });
}

/** Passo da contagem regressiva. */
export function playTick(): void {
  tone({ from: 660, to: 660, duration: 0.07, gain: 0.1 });
}

/** Início da partida. */
export function playStart(): void {
  tone({ from: 440, to: 880, duration: 0.28, type: "triangle" });
}

/** Fim da partida. */
export function playEnd(): void {
  tone({ from: 700, to: 300, duration: 0.5, type: "triangle", gain: 0.16 });
}
