/**
 * Rádio lo-fi da Sala de Estudos.
 *
 * Duas fontes, na ordem:
 *  1. Faixas locais em `/public/audio/lofi/` listadas num `manifest.json`
 *     (`{ "tracks": [{ "title": "...", "file": "nome.mp3" }] }`) — para quando
 *     o grupo baixar músicas royalty-free (Pixabay, YouTube Audio Library).
 *  2. Sem manifest, um GERADOR procedural por WebAudio: acordes suaves, baixo,
 *     batida leve e chiado de vinil. 100%% livre de direitos (é síntese nossa),
 *     zero download, funciona offline — mesma filosofia do áudio da Arena.
 *
 * Regra do projeto: nenhuma faixa com copyright entra no repositório.
 */

interface Estacao {
  nome: string;
  bpm: number;
  /** Progressão em semitons MIDI (acordes de 3–4 notas). */
  acordes: number[][];
}

// Progressões clássicas de lo-fi (ii–V–I–vi e variações), em tons calmos.
const ESTACOES: Estacao[] = [
  {
    nome: "Estação Foco",
    bpm: 72,
    acordes: [
      [57, 60, 64, 67], // Am7
      [53, 57, 60, 64], // Fmaj7
      [55, 59, 62, 65], // G7
      [48, 52, 55, 59], // Cmaj7
    ],
  },
  {
    nome: "Estação Madrugada",
    bpm: 64,
    acordes: [
      [50, 53, 57, 60], // Dm7
      [55, 59, 62, 65], // G7
      [48, 52, 55, 59], // Cmaj7
      [45, 48, 52, 55], // Am7
    ],
  },
  {
    nome: "Estação Chuva",
    bpm: 80,
    acordes: [
      [52, 55, 59, 62], // Em7
      [57, 60, 64, 67], // Am7
      [50, 53, 57, 60], // Dm7
      [55, 59, 62, 66], // G7(13)
    ],
  },
];

const midiParaHz = (nota: number) => 440 * 2 ** ((nota - 69) / 12);

interface EstadoRadio {
  tocando: boolean;
  nome: string;
  indice: number;
}

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let timer: ReturnType<typeof setInterval> | null = null;
let vinil: AudioBufferSourceNode | null = null;
let audioEl: HTMLAudioElement | null = null;
let faixasLocais: { title: string; file: string }[] | null = null;
let estadoAtual: EstadoRadio = { tocando: false, nome: "", indice: -1 };

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
    master = ctx.createGain();
    master.gain.value = 0.5;
    // Filtro geral abafado — o "calor" do lo-fi.
    const filtro = ctx.createBiquadFilter();
    filtro.type = "lowpass";
    filtro.frequency.value = 2400;
    master.connect(filtro).connect(ctx.destination);
  }
  if (ctx.state === "suspended") void ctx.resume();
  return ctx;
}

function nota(
  freq: number,
  inicio: number,
  duracao: number,
  ganho: number,
  tipo: OscillatorType = "triangle",
) {
  if (!ctx || !master) return;
  const osc = ctx.createOscillator();
  const vol = ctx.createGain();
  osc.type = tipo;
  osc.frequency.value = freq;
  // Ataque lento e cauda longa: pad, não piano.
  vol.gain.setValueAtTime(0.0001, inicio);
  vol.gain.linearRampToValueAtTime(ganho, inicio + duracao * 0.25);
  vol.gain.exponentialRampToValueAtTime(0.0001, inicio + duracao);
  osc.connect(vol).connect(master);
  osc.start(inicio);
  osc.stop(inicio + duracao + 0.05);
}

function baque(inicio: number) {
  if (!ctx || !master) return;
  const osc = ctx.createOscillator();
  const vol = ctx.createGain();
  osc.type = "sine";
  osc.frequency.setValueAtTime(120, inicio);
  osc.frequency.exponentialRampToValueAtTime(50, inicio + 0.12);
  vol.gain.setValueAtTime(0.16, inicio);
  vol.gain.exponentialRampToValueAtTime(0.0001, inicio + 0.16);
  osc.connect(vol).connect(master);
  osc.start(inicio);
  osc.stop(inicio + 0.2);
}

function chiadoDeVinil() {
  if (!ctx || !master) return;
  const dur = 2;
  const buffer = ctx.createBuffer(1, ctx.sampleRate * dur, ctx.sampleRate);
  const dados = buffer.getChannelData(0);
  for (let i = 0; i < dados.length; i += 1) {
    // Ruído esparso: estalos ocasionais sobre um chão baixo.
    dados[i] = (Math.random() * 2 - 1) * (Math.random() < 0.001 ? 0.5 : 0.015);
  }
  vinil = ctx.createBufferSource();
  vinil.buffer = buffer;
  vinil.loop = true;
  const filtro = ctx.createBiquadFilter();
  filtro.type = "highpass";
  filtro.frequency.value = 1800;
  const vol = ctx.createGain();
  vol.gain.value = 0.5;
  vinil.connect(filtro).connect(vol).connect(master);
  vinil.start();
}

function tocarProcedural(indice: number) {
  const contexto = getCtx();
  if (!contexto) return;
  const estacao = ESTACOES[indice % ESTACOES.length];
  const batida = 60 / estacao.bpm;
  const compasso = batida * 4;
  let compassoN = 0;
  let proximo = contexto.currentTime + 0.1;

  chiadoDeVinil();
  const agendar = () => {
    // Agenda um compasso à frente; setInterval só dispara o agendamento.
    while (proximo < contexto.currentTime + compasso * 1.5) {
      const acorde = estacao.acordes[compassoN % estacao.acordes.length];
      for (const n of acorde) {
        nota(midiParaHz(n), proximo, compasso * 1.05, 0.05);
      }
      nota(midiParaHz(acorde[0] - 12), proximo, compasso, 0.09, "sine"); // baixo
      baque(proximo);
      baque(proximo + batida * 2);
      compassoN += 1;
      proximo += compasso;
    }
  };
  agendar();
  timer = setInterval(agendar, compasso * 500);
}

async function carregarManifest(): Promise<typeof faixasLocais> {
  if (faixasLocais !== null) return faixasLocais;
  try {
    const res = await fetch("/audio/lofi/manifest.json");
    faixasLocais = res.ok ? (await res.json()).tracks ?? [] : [];
  } catch {
    faixasLocais = [];
  }
  return faixasLocais;
}

/** Para tudo (procedural e arquivo). */
export function pararRadio(): void {
  if (timer) clearInterval(timer);
  timer = null;
  vinil?.stop();
  vinil = null;
  audioEl?.pause();
  audioEl = null;
  estadoAtual = { tocando: false, nome: "", indice: estadoAtual.indice };
}

/**
 * Avança para a próxima estação/faixa (ou liga, se desligado).
 * Devolve o estado novo — a UI 3D mostra o nome.
 */
export async function proximaEstacao(): Promise<EstadoRadio> {
  const indice = estadoAtual.indice + 1;
  pararRadio();

  const faixas = await carregarManifest();
  if (faixas && faixas.length > 0) {
    if (indice >= faixas.length) {
      estadoAtual = { tocando: false, nome: "Desligado", indice: -1 };
      return estadoAtual;
    }
    const faixa = faixas[indice];
    audioEl = new Audio(`/audio/lofi/${faixa.file}`);
    audioEl.loop = true;
    void audioEl.play();
    estadoAtual = { tocando: true, nome: faixa.title, indice };
    return estadoAtual;
  }

  if (indice >= ESTACOES.length) {
    estadoAtual = { tocando: false, nome: "Desligado", indice: -1 };
    return estadoAtual;
  }
  tocarProcedural(indice);
  estadoAtual = { tocando: true, nome: ESTACOES[indice].nome, indice };
  return estadoAtual;
}

export function estadoRadio(): EstadoRadio {
  return estadoAtual;
}
