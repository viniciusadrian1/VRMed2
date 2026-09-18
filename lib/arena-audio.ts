/**
 * Vocabulário sonoro da Arena e do Duelo, sintetizado no WebAudio — sem arquivo.
 *
 * O projeto não tem assets de áudio e, no evento, a rede pode cair — baixar som
 * seria mais uma dependência para falhar. Osciladores resolvem em algumas
 * linhas, tocam instantaneamente e funcionam offline.
 *
 * O áudio do headset é, aliás, o único canal sonoro que sobrevive ao barulho do
 * evento: os alto-falantes ficam junto ao ouvido. Por isso NENHUM ganho aqui
 * passa de 0.16 — o que num monitor de mesa é "presente", no Quest é grito.
 *
 * POR QUE VIROU UM VOCABULÁRIO, E NÃO MAIS BIPES
 *
 * O que separa som de jogo de som de aparelho médico é (1) cada evento ter
 * timbre próprio — o jogador aprende a ouvir a partida sem olhar o placar — e
 * (2) duas ocorrências do mesmo evento nunca saírem idênticas. Daí o detune de
 * ±25 cents por disparo e o offset aleatório no ruído: o cérebro perdoa o
 * sintetizado, mas reconhece na hora a repetição mecânica. O acerto sobe a
 * pentatônica de dó, então uma sequência de acertos vira melodia em vez de
 * bipe mais agudo.
 */

/** Meia-vida longa: o contexto e o mestre nascem uma vez e vivem a página. */
let contexto: AudioContext | null = null;
let mestre: GainNode | null = null;
/** Um único buffer de ruído de 1 s — gerar por disparo derrubaria o quadro. */
let ruidoBranco: AudioBuffer | null = null;

interface Global {
  AudioContext?: typeof AudioContext;
  webkitAudioContext?: typeof AudioContext;
}

/**
 * O contexto só pode nascer depois de um gesto do usuário. Olhamos o
 * `globalThis` (e não o `window`) para o módulo também ser inerte no SSR e
 * testável sem navegador.
 */
function audio(): { ctx: AudioContext; destino: AudioNode } | null {
  if (!contexto) {
    const escopo = globalThis as unknown as Global;
    const Ctor = escopo.AudioContext ?? escopo.webkitAudioContext;
    if (!Ctor) return null;
    contexto = new Ctor();
    // Um mestre único entre tudo e a saída: um lugar só para abaixar o volume
    // do jogo inteiro, e margem contra soma de vozes simultâneas estourando.
    mestre = contexto.createGain();
    mestre.gain.value = 0.9;
    mestre.connect(contexto.destination);
  }
  if (!mestre) return null;
  if (contexto.state === "suspended") void contexto.resume();
  return { ctx: contexto, destino: mestre };
}

function ruido(ctx: AudioContext): AudioBuffer {
  if (!ruidoBranco) {
    const amostras = Math.floor(ctx.sampleRate); // 1 s basta para todo transiente
    ruidoBranco = ctx.createBuffer(1, amostras, ctx.sampleRate);
    const dados = ruidoBranco.getChannelData(0);
    for (let i = 0; i < amostras; i += 1) dados[i] = Math.random() * 2 - 1;
  }
  return ruidoBranco;
}

interface Voz {
  /** Altura inicial em Hz. */
  de: number;
  /** Altura final; igual a `de` quando omitida (nota parada). */
  para?: number;
  dur: number;
  tipo?: OscillatorType;
  ganho?: number;
  /** Tempo de subida do envelope — curto ataca, longo "sopra". */
  ataque?: number;
  /** Atraso em segundos a partir de agora (acordes e arpejos). */
  em?: number;
  /** Lowpass opcional, em Hz: tira o serrilhado de sawtooth/square. */
  corte?: number;
  /** Panorâmica de -1 (esquerda) a 1 (direita). */
  pan?: number;
}

/** Uma nota com envelope, filtro e posição — o tijolo de tudo aqui embaixo. */
function voz({
  de,
  para = de,
  dur,
  tipo = "sine",
  ganho = 0.12,
  ataque = 0.012,
  em = 0,
  corte,
  pan,
}: Voz): void {
  const a = audio();
  if (!a) return;
  const { ctx, destino } = a;
  const t = ctx.currentTime + em;

  const osc = ctx.createOscillator();
  osc.type = tipo;
  osc.frequency.setValueAtTime(de, t);
  if (para !== de) osc.frequency.exponentialRampToValueAtTime(Math.max(para, 1), t + dur);
  // Desafinação mínima e sorteada a cada disparo: é o que impede o som de
  // soar "colado" quando dois acertos caem quase juntos.
  osc.detune.setValueAtTime((Math.random() * 2 - 1) * 25, t);

  const envelope = ctx.createGain();
  // Ataque rápido e queda exponencial — evita o "clique" do corte abrupto.
  envelope.gain.setValueAtTime(0.0001, t);
  envelope.gain.exponentialRampToValueAtTime(ganho, t + ataque);
  envelope.gain.exponentialRampToValueAtTime(0.0001, t + dur);

  let cadeia: AudioNode = envelope;
  osc.connect(envelope);
  if (corte !== undefined) {
    const filtro = ctx.createBiquadFilter();
    filtro.type = "lowpass";
    filtro.frequency.setValueAtTime(corte, t);
    cadeia = cadeia.connect(filtro);
  }
  if (pan !== undefined) {
    const panner = ctx.createStereoPanner();
    panner.pan.setValueAtTime(pan, t);
    cadeia = cadeia.connect(panner);
  }
  cadeia.connect(destino);

  osc.start(t);
  osc.stop(t + dur + 0.03);
}

/**
 * Transiente de ruído: o "toque" percussivo que faz a nota soar tocada e não
 * ligada. Sem ele todo evento vira apito de forno.
 */
function estalo(em = 0, agudo = 2600, ganho = 0.12, dur = 0.03): void {
  const a = audio();
  if (!a) return;
  const { ctx, destino } = a;
  const t = ctx.currentTime + em;

  const fonte = ctx.createBufferSource();
  fonte.buffer = ruido(ctx);
  // Velocidade e ponto de leitura sorteados: o mesmo buffer nunca devolve a
  // mesma fatia de 30 ms duas vezes seguidas.
  fonte.playbackRate.setValueAtTime(0.8 + Math.random() * 0.4, t);

  const filtro = ctx.createBiquadFilter();
  filtro.type = "highpass";
  filtro.frequency.setValueAtTime(agudo, t);

  const envelope = ctx.createGain();
  envelope.gain.setValueAtTime(ganho, t);
  envelope.gain.exponentialRampToValueAtTime(0.0001, t + dur);

  fonte.connect(filtro).connect(envelope).connect(destino);
  fonte.start(t, Math.random() * 0.9, dur);
  fonte.stop(t + dur + 0.01);
}

/** Vento curto para transições: ruído passando de grave a agudo. */
function whoosh(em = 0, dur = 0.3, ganho = 0.09): void {
  const a = audio();
  if (!a) return;
  const { ctx, destino } = a;
  const t = ctx.currentTime + em;

  const fonte = ctx.createBufferSource();
  fonte.buffer = ruido(ctx);

  const filtro = ctx.createBiquadFilter();
  filtro.type = "bandpass";
  filtro.Q.setValueAtTime(1.2, t);
  filtro.frequency.setValueAtTime(300, t);
  filtro.frequency.exponentialRampToValueAtTime(3000, t + dur);

  const envelope = ctx.createGain();
  envelope.gain.setValueAtTime(0.0001, t);
  envelope.gain.exponentialRampToValueAtTime(ganho, t + dur * 0.35);
  envelope.gain.exponentialRampToValueAtTime(0.0001, t + dur);

  fonte.connect(filtro).connect(envelope).connect(destino);
  fonte.start(t, 0, dur + 0.02);
  fonte.stop(t + dur + 0.02);
}

// --------------------------------------------------------------- eventos

/** Pentatônica de dó: qualquer ordem dessas notas soa consonante. */
const PENTATONICA = [0, 2, 4, 7, 9, 12, 16];
const DO5 = 523.25;

/**
 * Acerto DO JOGADOR. A sequência sobe a escala: o combo vira melodia, e o
 * teto no fim do array impede o som de virar assobio de chaleira.
 */
export function playHit(sequencia = 1): void {
  const passo = Math.min(Math.max(Math.round(sequencia), 1), PENTATONICA.length) - 1;
  const nota = DO5 * Math.pow(2, PENTATONICA[passo] / 12);
  estalo(0, 3200, 0.07, 0.02);
  voz({ de: nota, dur: 0.18, tipo: "triangle", ganho: 0.12, ataque: 0.006 });
  // A oitava acima, baixinha e um piscar atrasada, dá brilho sem dobrar o volume.
  voz({ de: nota * 2, dur: 0.14, tipo: "sine", ganho: 0.05, em: 0.012 });
}

/** Erro DO JOGADOR: grave e curto, sem punir o ouvido. */
export function playMiss(): void {
  voz({ de: 200, para: 120, dur: 0.2, tipo: "sawtooth", ganho: 0.1, corte: 900 });
}

/**
 * O OPONENTE pontuou. Antes isso tocava playMiss, e o jogador não tinha como
 * distinguir "errei" de "levei ponto" — dois fatos opostos com o mesmo som.
 * Fica à direita, longe do jogador, porque a ameaça vem do outro lado.
 */
export function playOponentePontuou(): void {
  voz({ de: 392, para: 330, dur: 0.26, tipo: "square", ganho: 0.12, corte: 1400, pan: 0.45 });
}

/** O relógio venceu a rodada. Mais pesado e mais longo que um erro qualquer. */
export function playTempoEsgotado(): void {
  voz({ de: 220, para: 165, dur: 0.45, tipo: "square", ganho: 0.13, corte: 1100 });
}

/** Contagem regressiva 3-2-1: sobe de tom a cada passo. */
const CONTAGEM = [440, 554.4, 659.3];

export function playTick(passo = 0): void {
  const altura = CONTAGEM[Math.min(Math.max(Math.round(passo), 0), CONTAGEM.length - 1)];
  estalo(0, 3000, 0.06, 0.018);
  voz({ de: altura, dur: 0.08, tipo: "triangle", ganho: 0.1, ataque: 0.005 });
}

/** Largada: lá maior cheio, com vento por cima. */
export function playStart(): void {
  whoosh(0, 0.32, 0.08);
  [440, 554.4, 659.3, 880].forEach((altura, i) => {
    voz({ de: altura, dur: 0.5, tipo: "triangle", ganho: 0.075, em: i * 0.035 });
  });
}

/** Resposta enviada: confirmação seca enquanto o servidor não respondeu. */
export function playEnviado(): void {
  voz({ de: 900, para: 700, dur: 0.06, ganho: 0.07, ataque: 0.004 });
}

/**
 * Batida do relógio nos últimos 5 segundos: sobe de altura e de volume
 * conforme o tempo acaba. Fora dessa janela não toca nada — tensão constante
 * deixa de ser tensão.
 */
export function playTensao(restante: number): void {
  if (!(restante > 0 && restante <= 5)) return;
  const avanco = 5 - restante;
  voz({
    de: 700 + avanco * 55,
    dur: 0.07,
    tipo: "square",
    ganho: 0.09 + avanco * 0.0125,
    ataque: 0.004,
    corte: 2200,
  });
}

export function playClique(): void {
  estalo(0, 3400, 0.05, 0.015);
  voz({ de: 520, para: 700, dur: 0.05, tipo: "square", ganho: 0.06, ataque: 0.004, corte: 2600 });
}

/** O laser varre o menu inteiro em um gesto: sem trava viraria metralhadora. */
let ultimoHover = 0;

export function playHover(): void {
  const agora = Date.now();
  if (agora - ultimoHover < 70) return;
  ultimoHover = agora;
  voz({ de: 1200, dur: 0.035, ganho: 0.045, ataque: 0.004 });
}

export function playVoltar(): void {
  voz({ de: 520, para: 380, dur: 0.09, tipo: "triangle", ganho: 0.07 });
}

/** Vitória: arpejo de dó maior subindo. */
export function playVitoria(): void {
  whoosh(0, 0.3, 0.06);
  [523.25, 659.25, 783.99, 1046.5].forEach((altura, i) => {
    voz({ de: altura, dur: i === 3 ? 0.7 : 0.3, tipo: "triangle", ganho: 0.11, em: i * 0.09 });
  });
}

/** Derrota: a mesma ideia descendo, e com o timbre mais fosco. */
export function playDerrota(): void {
  [392, 330, 262, 196].forEach((altura, i) => {
    voz({
      de: altura,
      dur: i === 3 ? 0.7 : 0.3,
      tipo: "sawtooth",
      ganho: 0.1,
      em: i * 0.11,
      corte: 1200,
    });
  });
}

/** Empate: a mesma nota duas vezes — nem sobe nem desce. */
export function playEmpate(): void {
  voz({ de: 440, dur: 0.22, tipo: "triangle", ganho: 0.1 });
  voz({ de: 440, dur: 0.4, tipo: "triangle", ganho: 0.1, em: 0.16 });
}

/**
 * Fim de partida. A Arena chama sem argumento (ela não tem placar de dois
 * lados), então o padrão precisa continuar valendo.
 */
export function playEnd(resultado: "vitoria" | "derrota" | "empate" = "empate"): void {
  if (resultado === "vitoria") playVitoria();
  else if (resultado === "derrota") playDerrota();
  else playEmpate();
}

/** Troca de tela: mascara o corte entre uma cena e outra. */
export function playTransicao(): void {
  whoosh(0, 0.26, 0.07);
}

/**
 * Destrava o contexto dentro de um handler de clique. Um buffer de 1 amostra
 * é o suficiente para o navegador considerar que houve gesto do usuário.
 */
export function desbloquearAudio(): void {
  const a = audio();
  if (!a) return;
  const { ctx } = a;
  const fonte = ctx.createBufferSource();
  fonte.buffer = ctx.createBuffer(1, 1, ctx.sampleRate);
  fonte.connect(ctx.destination);
  fonte.start(0);
}

// Tirar o óculos da cabeça (ou trocar de aba) suspende o contexto, e ele não
// volta sozinho: sem isto, quem dá uma pausa no meio do duelo volta para um
// jogo mudo até recarregar a página.
if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && contexto?.state === "suspended") {
      void contexto.resume();
    }
  });
}
