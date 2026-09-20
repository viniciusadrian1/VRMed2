/**
 * Checagem do vocabulário sonoro do duelo sem placa de som (ver lib/arena-audio.ts).
 *
 * O que pode quebrar sem ninguém notar até o evento:
 *  1. dois eventos opostos tocando o mesmo som (era o caso de "errei" e "o
 *     oponente pontuou", ambos em playMiss);
 *  2. o combo parar de subir a escala;
 *  3. a batida de tensão tocando fora da janela dos últimos 5 s;
 *  4. o hover virando metralhadora quando o laser varre o menu;
 *  5. o módulo explodir onde não existe AudioContext (SSR, teste, Safari velho).
 *
 * Um AudioContext falso registra tudo o que foi agendado; a assinatura de cada
 * evento é essa lista, menos o que é aleatório de propósito.
 *
 * Rodar: npm run verify:audio (Node 22+)
 */

const falhas: string[] = [];
const conferir = (ok: boolean, msg: string) => {
  if (!ok) falhas.push(msg);
  console.log(ok ? "  ok:" : "  FALHA:", msg);
};

// -------------------------------------------------------- AudioContext falso

let agendado: string[] = [];
const num = (v: number) => (Math.round(v * 1000) / 1000).toString();

function param(rotulo: string) {
  const p = {
    value: 0,
    setValueAtTime(v: number, t: number) {
      agendado.push(`${rotulo}=${num(v)}@${num(t)}`);
      return p;
    },
    linearRampToValueAtTime(v: number, t: number) {
      agendado.push(`${rotulo}~${num(v)}@${num(t)}`);
      return p;
    },
    exponentialRampToValueAtTime(v: number, t: number) {
      agendado.push(`${rotulo}^${num(v)}@${num(t)}`);
      return p;
    },
    cancelScheduledValues() {
      return p;
    },
  };
  return p;
}

/** Base comum: `connect` devolve o destino para o encadeamento do módulo. */
function no(rotulo: string) {
  return {
    connect<T>(destino: T): T {
      return destino;
    },
    disconnect() {},
    start(quando = 0) {
      agendado.push(`${rotulo}.start@${num(quando)}`);
    },
    stop(quando = 0) {
      agendado.push(`${rotulo}.stop@${num(quando)}`);
    },
  };
}

class ContextoFalso {
  currentTime = 0;
  sampleRate = 48000;
  state = "running";
  destination = { rotulo: "saida" };
  /** Quantos buffers foram criados — o ruído tem de ser um só. */
  static buffers = 0;

  resume() {
    return Promise.resolve();
  }
  createGain() {
    return { ...no("ganho"), gain: param("ganho.gain") };
  }
  createOscillator() {
    return {
      ...no("osc"),
      set type(v: string) {
        agendado.push(`osc.type=${v}`);
      },
      frequency: param("osc.frequency"),
      detune: param("osc.detune"),
    };
  }
  createBiquadFilter() {
    return {
      ...no("filtro"),
      set type(v: string) {
        agendado.push(`filtro.type=${v}`);
      },
      frequency: param("filtro.frequency"),
      Q: param("filtro.Q"),
    };
  }
  createStereoPanner() {
    return { ...no("pan"), pan: param("pan.pan") };
  }
  createBufferSource() {
    return {
      ...no("ruido"),
      buffer: null as unknown,
      playbackRate: param("ruido.playbackRate"),
    };
  }
  createBuffer(canais: number, amostras: number) {
    ContextoFalso.buffers += 1;
    return { getChannelData: () => new Float32Array(amostras * canais) };
  }
}

type Escopo = { AudioContext?: unknown };
const escopo = globalThis as Escopo;

async function principal() {
  // ------------------------------------------- 5. sem AudioContext (antes de tudo)
  delete escopo.AudioContext;
  const a = await import("../lib/arena-audio.ts");
  try {
    a.playHit(3);
    a.playMiss();
    a.playOponentePontuou();
    a.playTempoEsgotado();
    a.playTick(1);
    a.playStart();
    a.playEnviado();
    a.playTensao(2);
    a.playClique();
    a.playHover();
    a.playVoltar();
    a.playEnd("vitoria");
    a.playTransicao();
    a.desbloquearAudio();
    conferir(true, "sem AudioContext (SSR/Safari velho): nada quebra e nada toca");
  } catch (erro) {
    conferir(false, `sem AudioContext: lançou ${String(erro)}`);
  }

  // A partir daqui existe contexto — o módulo cria o dele no próximo disparo.
  escopo.AudioContext = ContextoFalso;

  const capturar = (tocar: () => void): string[] => {
    agendado = [];
    tocar();
    return agendado;
  };
  // detune (±25 cents) e playbackRate (0.8–1.2×) são sorteados de propósito e o
  // ruído é lido de um ponto aleatório: ficam fora da assinatura, senão dois
  // disparos do MESMO evento nunca bateriam.
  const assinar = (tocar: () => void) =>
    capturar(tocar)
      .filter((linha) => !/detune|playbackRate/.test(linha))
      .join("|");

  // --------------------------------------------- 1. cada evento soa diferente
  const eventos: Record<string, () => void> = {
    playHit: () => a.playHit(1),
    playMiss: () => a.playMiss(),
    playOponentePontuou: () => a.playOponentePontuou(),
    playTempoEsgotado: () => a.playTempoEsgotado(),
    playVitoria: () => a.playVitoria(),
    playDerrota: () => a.playDerrota(),
    playEmpate: () => a.playEmpate(),
  };
  const assinaturas = new Map(
    Object.entries(eventos).map(([nome, tocar]) => [nome, assinar(tocar)]),
  );
  for (const [nome, assinatura] of assinaturas) {
    conferir(assinatura.length > 0, `${nome} agenda som de verdade`);
  }
  conferir(
    new Set(assinaturas.values()).size === assinaturas.size,
    "os 7 eventos do duelo têm sons distintos entre si (erro meu ≠ ponto do oponente)",
  );
  conferir(
    assinaturas.get("playMiss") !== assinaturas.get("playOponentePontuou"),
    "playOponentePontuou não é mais um playMiss disfarçado",
  );

  // --------------------------------------------------- 2. combo sobe a escala
  const alturas = (sequencia: number) =>
    capturar(() => a.playHit(sequencia)).filter((l) => l.startsWith("osc.frequency"));
  conferir(alturas(1).length > 0, "playHit toca nota");
  conferir(alturas(1).join() !== alturas(4).join(), "playHit(1) e playHit(4) usam frequências diferentes");
  conferir(alturas(7).join() === alturas(99).join(), "o combo tem teto: a escala não vira assobio");
  conferir(
    assinar(() => a.playHit(1)) === assinar(() => a.playHit(1)),
    "o mesmo acerto é a mesma nota (só o detune varia)",
  );
  conferir(
    capturar(() => a.playHit(1)).filter((l) => l.startsWith("osc.detune")).join() !==
      capturar(() => a.playHit(1)).filter((l) => l.startsWith("osc.detune")).join(),
    "cada disparo desafina um pouco diferente (±25 cents)",
  );

  // -------------------------------------------------- 3. janela da tensão
  conferir(capturar(() => a.playTensao(6)).length === 0, "playTensao(6) fica calado (fora dos 5 s finais)");
  conferir(capturar(() => a.playTensao(0)).length === 0, "playTensao(0) fica calado (tempo já acabou)");
  conferir(capturar(() => a.playTensao(5)).length > 0, "playTensao(5) toca");
  conferir(
    assinar(() => a.playTensao(5)) !== assinar(() => a.playTensao(1)),
    "a batida aperta conforme o tempo acaba",
  );

  // ------------------------------------------------------ 4. trava do hover
  // O bloco sem AudioContext lá em cima já chamou playHover: espera a trava de
  // 70 ms abrir, senão o primeiro hover daqui cai dentro da anterior.
  await new Promise((r) => setTimeout(r, 90));
  const primeiro = capturar(() => a.playHover());
  const segundo = capturar(() => a.playHover());
  conferir(primeiro.length > 0 && segundo.length === 0, "dois hovers seguidos disparam um som só");

  // ------------------------------------------------- buffer de ruído reusado
  const antes = ContextoFalso.buffers;
  a.playHit(2);
  a.playTransicao();
  a.playStart();
  conferir(
    ContextoFalso.buffers === antes,
    "o buffer de ruído é criado uma vez só (nada de alocar por disparo)",
  );

  console.log(falhas.length ? `\n${falhas.length} falha(s)` : "\nok: vocabulário sonoro do duelo");
  process.exit(falhas.length ? 1 : 0);
}

void principal();
