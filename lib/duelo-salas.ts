/**
 * Duelo 1×1 entre duas pessoas: as salas e as regras, sem rede.
 *
 * O servidor (`app/api/duelo/route.ts`) é o árbitro. Os dois óculos só
 * mostram o que ele manda e avisam quando alguém clica. Assim o relógio, o
 * placar e "quem acertou primeiro" são um só para os dois, e ninguém depende
 * do relógio do outro aparelho.
 *
 * Tudo aqui é puro — recebe `agora` em vez de ler o relógio — para dar para
 * testar a partida inteira sem esperar (`scripts/verificar-duelo-salas.ts`).
 */

export const VERSAO_PROTOCOLO = 2;
export const TOTAL_RODADAS = 8;
export const CONTAGEM_MS = 3000;
export const RODADA_MS = 18000;
export const FEEDBACK_MS = 2400;
/**
 * Espera entre o primeiro acerto que chega e a decisão (ms).
 *
 * O servidor fica fora do Brasil e cada óculos tem a própria rede: um clique
 * feito antes pode chegar depois. Nessa janela os acertos que chegam entram na
 * disputa, e ganha o menor tempo de reação MEDIDO NO ÓCULOS (do instante em
 * que a pergunta apareceu na tela dele até o clique). Sem a janela, ganharia
 * quem tem a internet mais rápida, não quem sabe mais rápido.
 */
export const JANELA_DECISAO_MS = 600;
/** Sem conexão por mais que isso durante a partida conta como abandono. */
export const ABANDONO_MS = 30_000;
/** Sala sem ninguém conectado há mais que isso é apagada. */
export const SALA_ORFA_MS = 10 * 60_000;
/**
 * Sala esperando adversário e sem ninguém ouvindo é apagada antes (ms): quem
 * cria abre a conexão logo em seguida, então sala assim foi abandonada — ou
 * criada em série por alguém tentando lotar o servidor.
 */
export const SALA_ESPERA_ORFA_MS = 2 * 60_000;

export interface RodadaOnline {
  tipo: "orgao" | "estrutura" | "conhecimento";
  pontos: 100 | 200;
  alvo: string;
  opcoes: string[];
  modelo?: string;
  marcador?: [number, number, number];
  perguntaId?: string;
  pergunta?: string;
  explicacao?: string;
}

export type FaseSala =
  | "aguardando"
  | "contagem"
  | "rodada"
  | "feedback"
  | "fim"
  | "encerrada";

interface Jogador {
  id: string;
  pontos: number;
  conectado: boolean;
  desconectadoEm: number | null;
  querRevanche: boolean;
}

type Evento =
  | { seq: number; tipo: "ponto"; jogador: number; alvo: string; pontos: number }
  | { seq: number; tipo: "tempo"; alvo: string };

export interface Sala {
  codigo: string;
  jogadores: Jogador[];
  rodadas: RodadaOnline[];
  /** Muda a cada nova lista de rodadas (partida nova ou revanche). */
  partida: number;
  proximasRodadas: RodadaOnline[] | null;
  fase: FaseSala;
  indice: number;
  /** Instante em que a fase atual termina (0 = fase sem prazo). */
  prazo: number;
  candidatos: { jogador: number; reacaoMs: number }[];
  /** Instante da decisão entre acertos (0 = nenhum acerto pendente). */
  decidirEm: number;
  ultimo: Evento | null;
  /** Quem saiu, quando a sala foi encerrada por saída ou abandono. */
  saiu: number | null;
  seq: number;
  tocadaEm: number;
}

/** O que um jogador recebe: a sala vista do lado dele. */
export interface VisaoSala {
  v: number;
  seq: number;
  codigo: string;
  fase: FaseSala;
  partida: number;
  indice: number;
  total: number;
  restanteMs: number;
  rodadas: RodadaOnline[];
  eu: { pontos: number; querRevanche: boolean };
  outro: { pontos: number; conectado: boolean; querRevanche: boolean } | null;
  ultimo:
    | { seq: number; tipo: "ponto"; quem: "eu" | "outro"; alvo: string; pontos: number }
    | { seq: number; tipo: "tempo"; alvo: string }
    | null;
  saiu: "eu" | "outro" | null;
}

export function gerarCodigo(
  ocupados: { has(codigo: string): boolean },
  aleatorio: () => number = Math.random,
): string {
  // ponytail: sorteio com nova tentativa; com 9000 códigos e poucas salas
  // abertas, colisão é rara. Se um dia houver milhares de salas, trocar por
  // uma lista embaralhada.
  for (let i = 0; i < 50; i += 1) {
    const codigo = String(1000 + Math.floor(aleatorio() * 9000));
    if (!ocupados.has(codigo)) return codigo;
  }
  throw new Error("sem código livre");
}

export function criarSala(
  codigo: string,
  jogadorId: string,
  rodadas: RodadaOnline[],
  agora: number,
): Sala {
  return {
    codigo,
    jogadores: [novoJogador(jogadorId, agora)],
    rodadas,
    partida: 1,
    proximasRodadas: null,
    fase: "aguardando",
    indice: 0,
    prazo: 0,
    candidatos: [],
    decidirEm: 0,
    ultimo: null,
    saiu: null,
    seq: 1,
    tocadaEm: agora,
  };
}

/**
 * Nasce DESCONECTADO desde agora: quem entra e nunca abre a conexão (resposta
 * perdida no Wi-Fi, ou alguém que só mandou o POST) conta como ausente e cai
 * no limite de abandono, em vez de deixar o outro jogando contra ninguém.
 */
function novoJogador(id: string, agora: number): Jogador {
  return { id, pontos: 0, conectado: false, desconectadoEm: agora, querRevanche: false };
}

/**
 * A contagem começa: a tolerância de abandono passa a contar daqui. Uma queda
 * na tela de espera ou de fim, que não contam abandono, não pode encerrar a
 * partida no instante em que ela começa.
 */
function comecarContagem(sala: Sala, agora: number) {
  sala.fase = "contagem";
  sala.prazo = agora + CONTAGEM_MS;
  for (const j of sala.jogadores) {
    if (!j.conectado) j.desconectadoEm = agora;
  }
}

function mudou(sala: Sala, agora: number) {
  sala.seq += 1;
  sala.tocadaEm = agora;
}

export function indiceDe(sala: Sala, jogadorId: string): number {
  return sala.jogadores.findIndex((j) => j.id === jogadorId);
}

/** Segundo jogador entra (ou o mesmo volta). A partida começa ao completar. */
export function entrar(
  sala: Sala,
  jogadorId: string,
  agora: number,
): "ok" | "cheia" | "encerrada" {
  if (indiceDe(sala, jogadorId) >= 0) return "ok";
  if (sala.fase === "encerrada") return "encerrada";
  if (sala.jogadores.length >= 2) return "cheia";
  sala.jogadores.push(novoJogador(jogadorId, agora));
  comecarContagem(sala, agora);
  mudou(sala, agora);
  return "ok";
}

export function conectar(sala: Sala, jogadorId: string, agora: number) {
  const j = sala.jogadores[indiceDe(sala, jogadorId)];
  if (!j || j.conectado) return;
  j.conectado = true;
  j.desconectadoEm = null;
  mudou(sala, agora);
}

export function desconectar(sala: Sala, jogadorId: string, agora: number) {
  const j = sala.jogadores[indiceDe(sala, jogadorId)];
  if (!j || !j.conectado) return;
  j.conectado = false;
  j.desconectadoEm = agora;
  mudou(sala, agora);
}

/** Um clique numa alternativa. Só acerto conta: erro é resolvido no óculos. */
export function responder(
  sala: Sala,
  jogadorId: string,
  indice: number,
  opcao: string,
  reacaoMs: number,
  agora: number,
): "certo" | "errado" | "tarde" {
  const jogador = indiceDe(sala, jogadorId);
  if (jogador < 0) return "tarde";
  if (sala.fase !== "rodada" || indice !== sala.indice) return "tarde";
  // Depois do prazo só vale se já houver disputa aberta (o outro acertou a
  // tempo e a janela ainda não fechou).
  if (agora >= sala.prazo && sala.decidirEm === 0) return "tarde";
  if (sala.decidirEm !== 0 && agora >= sala.decidirEm) return "tarde";
  if (opcao !== sala.rodadas[sala.indice]?.alvo) return "errado";
  if (sala.candidatos.some((c) => c.jogador === jogador)) return "certo";

  // O tempo de reação vem do óculos. Limitado ao que o servidor viu passar
  // desde o início da rodada: ninguém reage antes de a pergunta existir.
  const decorridoMs = agora - (sala.prazo - RODADA_MS);
  const reacao = Math.min(Math.max(0, reacaoMs), Math.max(0, decorridoMs));
  sala.candidatos.push({ jogador, reacaoMs: reacao });
  if (sala.decidirEm === 0) sala.decidirEm = agora + JANELA_DECISAO_MS;
  sala.tocadaEm = agora;
  return "certo";
}

/**
 * Aplica o que o tempo decidiu: fim da janela de acertos, fim da rodada,
 * troca de fase, abandono. Devolve se algo mudou.
 */
export function avancar(sala: Sala, agora: number): boolean {
  const seqAntes = sala.seq;

  for (let passos = 0; passos < 20; passos += 1) {
    if (verificarAbandono(sala, agora)) break;

    if (sala.fase === "contagem" && agora >= sala.prazo) {
      iniciarRodada(sala, sala.indice, agora);
      continue;
    }

    if (sala.fase === "rodada") {
      if (sala.decidirEm !== 0 && agora >= sala.decidirEm) {
        // Menor reação vence; empate exato fica com quem chegou primeiro.
        const vencedor = sala.candidatos.reduce((a, b) =>
          b.reacaoMs < a.reacaoMs ? b : a,
        );
        const rodada = sala.rodadas[sala.indice];
        sala.jogadores[vencedor.jogador].pontos += rodada.pontos;
        sala.ultimo = {
          seq: sala.seq + 1,
          tipo: "ponto",
          jogador: vencedor.jogador,
          alvo: rodada.alvo,
          pontos: rodada.pontos,
        };
        irParaFeedback(sala, agora);
        continue;
      }
      if (sala.decidirEm === 0 && agora >= sala.prazo) {
        sala.ultimo = { seq: sala.seq + 1, tipo: "tempo", alvo: sala.rodadas[sala.indice].alvo };
        irParaFeedback(sala, agora);
        continue;
      }
    }

    if (sala.fase === "feedback" && agora >= sala.prazo) {
      if (sala.indice + 1 >= sala.rodadas.length) {
        sala.fase = "fim";
        sala.prazo = 0;
        mudou(sala, agora);
      } else {
        iniciarRodada(sala, sala.indice + 1, agora);
      }
      continue;
    }
    break;
  }

  return sala.seq !== seqAntes;
}

function iniciarRodada(sala: Sala, indice: number, agora: number) {
  sala.fase = "rodada";
  sala.indice = indice;
  sala.prazo = agora + RODADA_MS;
  sala.candidatos = [];
  sala.decidirEm = 0;
  mudou(sala, agora);
}

function irParaFeedback(sala: Sala, agora: number) {
  sala.fase = "feedback";
  sala.prazo = agora + FEEDBACK_MS;
  sala.candidatos = [];
  sala.decidirEm = 0;
  mudou(sala, agora);
}

function verificarAbandono(sala: Sala, agora: number): boolean {
  if (sala.fase !== "contagem" && sala.fase !== "rodada" && sala.fase !== "feedback") {
    return false;
  }
  const i = sala.jogadores.findIndex(
    (j) => j.desconectadoEm !== null && agora - j.desconectadoEm >= ABANDONO_MS,
  );
  if (i < 0) return false;
  encerrar(sala, i, agora);
  return true;
}

function encerrar(sala: Sala, quemSaiu: number, agora: number) {
  sala.fase = "encerrada";
  sala.prazo = 0;
  sala.candidatos = [];
  sala.decidirEm = 0;
  sala.saiu = quemSaiu;
  mudou(sala, agora);
}

export function sair(sala: Sala, jogadorId: string, agora: number) {
  const i = indiceDe(sala, jogadorId);
  if (i < 0 || sala.fase === "encerrada") return;
  encerrar(sala, i, agora);
}

/** Revanche só começa quando os dois pedem. Quem pede primeiro manda as rodadas. */
export function pedirRevanche(
  sala: Sala,
  jogadorId: string,
  rodadas: RodadaOnline[],
  agora: number,
) {
  const i = indiceDe(sala, jogadorId);
  if (i < 0 || sala.fase !== "fim" || sala.jogadores.length < 2) return;
  sala.jogadores[i].querRevanche = true;
  sala.proximasRodadas ??= rodadas;
  if (sala.jogadores.every((j) => j.querRevanche)) {
    for (const j of sala.jogadores) {
      j.pontos = 0;
      j.querRevanche = false;
    }
    sala.rodadas = sala.proximasRodadas;
    sala.proximasRodadas = null;
    sala.partida += 1;
    sala.indice = 0;
    sala.ultimo = null;
    comecarContagem(sala, agora);
  }
  mudou(sala, agora);
}

/** Próximo instante em que `avancar` tem algo a fazer (null = nada agendado). */
export function proximoPrazo(sala: Sala): number | null {
  const tempos: number[] = [];
  if (sala.prazo) tempos.push(sala.prazo);
  if (sala.decidirEm) tempos.push(sala.decidirEm);
  if (sala.fase === "contagem" || sala.fase === "rodada" || sala.fase === "feedback") {
    for (const j of sala.jogadores) {
      if (j.desconectadoEm !== null) tempos.push(j.desconectadoEm + ABANDONO_MS);
    }
  }
  return tempos.length ? Math.min(...tempos) : null;
}

export function visao(sala: Sala, jogadorId: string, agora: number): VisaoSala {
  const i = indiceDe(sala, jogadorId);
  const eu = sala.jogadores[i];
  const outro = sala.jogadores[1 - i];
  const ultimo = sala.ultimo;
  return {
    v: VERSAO_PROTOCOLO,
    seq: sala.seq,
    codigo: sala.codigo,
    fase: sala.fase,
    partida: sala.partida,
    indice: sala.indice,
    total: sala.rodadas.length,
    restanteMs: sala.prazo ? Math.max(0, sala.prazo - agora) : 0,
    rodadas: sala.rodadas,
    eu: { pontos: eu?.pontos ?? 0, querRevanche: eu?.querRevanche ?? false },
    outro: outro
      ? { pontos: outro.pontos, conectado: outro.conectado, querRevanche: outro.querRevanche }
      : null,
    ultimo:
      ultimo?.tipo === "ponto"
        ? { ...ultimo, quem: ultimo.jogador === i ? "eu" : "outro" }
        : ultimo,
    saiu: sala.saiu === null ? null : sala.saiu === i ? "eu" : "outro",
  };
}

/** Sala pode ser apagada: encerrada ou esquecida, e sem ninguém ouvindo. */
export function descartavel(sala: Sala, ouvintes: number, agora: number): boolean {
  if (ouvintes > 0) return false;
  if (sala.fase === "encerrada") return true;
  const limite = sala.fase === "aguardando" ? SALA_ESPERA_ORFA_MS : SALA_ORFA_MS;
  return agora - sala.tocadaEm >= limite;
}
