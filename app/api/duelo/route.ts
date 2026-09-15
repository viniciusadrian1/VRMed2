import { z } from "zod";
import * as Salas from "@/lib/duelo-salas";

/**
 * Duelo 1×1 online: o servidor é o árbitro das salas.
 *
 *  - GET  `?sala=4821&jogador=<id>` abre um fluxo Server-Sent Events: a cada
 *    mudança, o jogador recebe a sala vista do lado dele (`visao`).
 *  - POST `{ acao, ... }` cria, entra, responde, pede revanche ou sai.
 *
 * POR QUE SSE E NÃO WEBSOCKET: no Next 16 uma rota do app não aceita upgrade
 * de WebSocket — seria preciso um servidor à parte, que muda o jeito de
 * publicar no Render. Uma partida troca umas 40 mensagens; SSE + POST cabem
 * numa rota comum, e o `EventSource` do navegador já reconecta sozinho.
 *
 * ESTADO EM MEMÓRIA: as salas vivem neste processo. Vale enquanto o Render
 * rodar UMA instância; um deploy apaga as salas abertas (quem estiver
 * jogando vê "partida interrompida"). Fica em `globalThis` para sobreviver
 * ao recarregamento de módulo do `next dev`.
 */

export const dynamic = "force-dynamic";

/** Limite de salas abertas: a rota é pública, a memória não é infinita. */
const MAX_SALAS = 500;
/** Comentário SSE periódico: evita que proxies derrubem a conexão ociosa. */
const PING_MS = 15_000;
/**
 * Limites por IP, numa janela de 10 minutos. O código de 4 dígitos é a única
 * chave da sala: sem limite, um script acha uma sala em espera varrendo os
 * 9000 códigos e entra antes do amigo, ou cria salas até lotar o servidor.
 * Folgados de propósito: numa escola ou num evento todo mundo sai pelo mesmo
 * IP.
 */
const JANELA_LIMITE_MS = 10 * 60_000;
const MAX_SALAS_CRIADAS_POR_IP = 30;
const MAX_CODIGOS_ERRADOS_POR_IP = 20;

interface Ouvinte {
  jogador: string;
  enviar: (texto: string) => void;
}

interface Estado {
  salas: Map<string, Salas.Sala>;
  ouvintes: Map<string, Set<Ouvinte>>;
  timers: Map<string, ReturnType<typeof setTimeout>>;
  /** `${tipo}:${ip}` → instantes das tentativas dentro da janela. */
  tentativas: Map<string, number[]>;
}

const global = globalThis as typeof globalThis & { __dueloOnline?: Estado };
const estado: Estado = (global.__dueloOnline ??= {
  salas: new Map(),
  ouvintes: new Map(),
  timers: new Map(),
  tentativas: new Map(),
});
estado.tentativas ??= new Map(); // estado criado por uma versão anterior no dev

function ipDe(request: Request): string {
  return (
    request.headers.get("cf-connecting-ip") ??
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    "local"
  );
}

/** Quantas tentativas deste tipo o IP fez na janela (já descartando as velhas). */
function contar(chave: string, agora: number): number[] {
  const lista = (estado.tentativas.get(chave) ?? []).filter(
    (t) => agora - t < JANELA_LIMITE_MS,
  );
  estado.tentativas.set(chave, lista);
  return lista;
}

const muitasTentativas = () =>
  Response.json(
    { erro: "Muitas tentativas. Espere alguns minutos e tente de novo." },
    { status: 429 },
  );

function emitir(sala: Salas.Sala) {
  const agora = Date.now();
  for (const ouvinte of estado.ouvintes.get(sala.codigo) ?? []) {
    ouvinte.enviar(
      `data: ${JSON.stringify(Salas.visao(sala, ouvinte.jogador, agora))}\n\n`,
    );
  }
}

/** Um único timer por sala, sempre para o próximo prazo. */
function agendar(sala: Salas.Sala) {
  clearTimeout(estado.timers.get(sala.codigo));
  estado.timers.delete(sala.codigo);
  const prazo = Salas.proximoPrazo(sala);
  if (prazo === null) return;
  const timer = setTimeout(() => {
    estado.timers.delete(sala.codigo);
    if (estado.salas.get(sala.codigo) !== sala) return;
    if (Salas.avancar(sala, Date.now())) emitir(sala);
    agendar(sala);
  }, Math.max(0, prazo - Date.now()) + 5);
  estado.timers.set(sala.codigo, timer);
}

function limpar() {
  const agora = Date.now();
  for (const [chave, lista] of estado.tentativas) {
    if (lista.every((t) => agora - t >= JANELA_LIMITE_MS)) estado.tentativas.delete(chave);
  }
  for (const [codigo, sala] of estado.salas) {
    const ouvintes = estado.ouvintes.get(codigo)?.size ?? 0;
    if (Salas.descartavel(sala, ouvintes, agora)) {
      clearTimeout(estado.timers.get(codigo));
      estado.timers.delete(codigo);
      estado.ouvintes.delete(codigo);
      estado.salas.delete(codigo);
    }
  }
}

/* ------------------------------------------------------------------ GET */

const idJogador = z.string().regex(/^[A-Za-z0-9-]{8,64}$/);
const codigoSala = z.string().regex(/^\d{4}$/);

export async function GET(request: Request) {
  limpar();
  const url = new URL(request.url);
  const codigo = codigoSala.safeParse(url.searchParams.get("sala"));
  const jogador = idJogador.safeParse(url.searchParams.get("jogador"));
  const sala = codigo.success ? estado.salas.get(codigo.data) : undefined;
  if (!sala || !jogador.success || Salas.indiceDe(sala, jogador.data) < 0) {
    // Status diferente de 200 faz o EventSource desistir de reconectar: é o
    // sinal, no óculos, de que a partida não existe mais.
    return Response.json({ erro: "Sala não encontrada." }, { status: 404 });
  }

  const encoder = new TextEncoder();
  let ouvinte: Ouvinte | null = null;
  let ping: ReturnType<typeof setInterval> | undefined;
  let fechado = false;

  const fechar = () => {
    if (fechado) return;
    fechado = true;
    clearInterval(ping);
    const lista = estado.ouvintes.get(sala.codigo);
    if (ouvinte) lista?.delete(ouvinte);
    // Uma aba recarregando pode abrir a conexão nova antes de a velha fechar:
    // só desconecta se não sobrou outra do mesmo jogador.
    const aindaConectado = [...(lista ?? [])].some((o) => o.jogador === jogador.data);
    if (!aindaConectado && estado.salas.get(sala.codigo) === sala) {
      Salas.desconectar(sala, jogador.data, Date.now());
      emitir(sala);
      agendar(sala);
    }
  };

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      ouvinte = {
        jogador: jogador.data,
        enviar: (texto) => {
          if (fechado) return;
          try {
            controller.enqueue(encoder.encode(texto));
          } catch {
            fechar();
          }
        },
      };
      let lista = estado.ouvintes.get(sala.codigo);
      if (!lista) {
        lista = new Set();
        estado.ouvintes.set(sala.codigo, lista);
      }
      lista.add(ouvinte);

      ouvinte.enviar("retry: 2000\n\n");
      Salas.conectar(sala, jogador.data, Date.now());
      emitir(sala);
      agendar(sala);
      ping = setInterval(() => ouvinte?.enviar(": p\n\n"), PING_MS);
      request.signal.addEventListener("abort", fechar);
    },
    cancel: fechar,
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      // no-transform: sem isso a compressão segura os eventos em buffer.
      "Cache-Control": "no-cache, no-store, no-transform",
      "X-Accel-Buffering": "no",
    },
  });
}

/* ----------------------------------------------------------------- POST */

const texto = z.string().min(1).max(80);

const rodadasSchema = z
  .array(
    z.object({
      tipo: z.enum(["orgao", "estrutura"]),
      pontos: z.union([z.literal(100), z.literal(200)]),
      alvo: texto,
      opcoes: z.array(texto).length(4),
      modelo: z.string().startsWith("/models/").max(120).optional(),
      marcador: z.tuple([z.number(), z.number(), z.number()]).optional(),
    }),
  )
  .length(Salas.TOTAL_RODADAS)
  .refine(
    (lista) =>
      lista.every(
        (r) =>
          r.pontos === (r.tipo === "orgao" ? 100 : 200) &&
          (r.tipo !== "orgao" || Boolean(r.modelo)) &&
          r.opcoes.includes(r.alvo) &&
          new Set(r.opcoes).size === 4 &&
          (r.marcador ?? []).every(Number.isFinite),
      ),
    "Rodadas inválidas.",
  );

const base = { v: z.literal(Salas.VERSAO_PROTOCOLO), jogador: idJogador };

const acaoSchema = z.discriminatedUnion("acao", [
  z.object({ ...base, acao: z.literal("criar"), rodadas: rodadasSchema }),
  z.object({ ...base, acao: z.literal("entrar"), sala: codigoSala }),
  z.object({
    ...base,
    acao: z.literal("responder"),
    sala: codigoSala,
    indice: z.number().int().min(0).max(Salas.TOTAL_RODADAS - 1),
    opcao: texto,
    reacaoMs: z.number().finite(),
  }),
  z.object({ ...base, acao: z.literal("revanche"), sala: codigoSala, rodadas: rodadasSchema }),
  z.object({ ...base, acao: z.literal("sair"), sala: codigoSala }),
]);

export async function POST(request: Request) {
  limpar();
  let corpo: unknown;
  try {
    corpo = await request.json();
  } catch {
    return Response.json({ erro: "Corpo inválido." }, { status: 400 });
  }
  if (
    typeof corpo === "object" &&
    corpo !== null &&
    (corpo as { v?: unknown }).v !== Salas.VERSAO_PROTOCOLO
  ) {
    return Response.json(
      { erro: "O site foi atualizado. Recarregue a página nos dois óculos." },
      { status: 409 },
    );
  }
  const parsed = acaoSchema.safeParse(corpo);
  if (!parsed.success) {
    return Response.json({ erro: "Ação inválida." }, { status: 400 });
  }
  const acao = parsed.data;
  const agora = Date.now();
  const ip = ipDe(request);
  const naoEncontrada = () =>
    Response.json({ erro: "Sala não encontrada. Confira o código." }, { status: 404 });

  if (acao.acao === "criar") {
    const criadas = contar(`criar:${ip}`, agora);
    if (criadas.length >= MAX_SALAS_CRIADAS_POR_IP) return muitasTentativas();
    if (estado.salas.size >= MAX_SALAS) {
      return Response.json(
        { erro: "Muitas salas abertas agora. Tente de novo em alguns minutos." },
        { status: 503 },
      );
    }
    const codigo = Salas.gerarCodigo(estado.salas);
    const sala = Salas.criarSala(codigo, acao.jogador, acao.rodadas, agora);
    estado.salas.set(codigo, sala);
    criadas.push(agora);
    return Response.json({ sala: codigo });
  }

  const sala = estado.salas.get(acao.sala);

  if (acao.acao === "entrar") {
    const erros = contar(`codigo:${ip}`, agora);
    if (erros.length >= MAX_CODIGOS_ERRADOS_POR_IP) return muitasTentativas();
    if (!sala) {
      erros.push(agora);
      return naoEncontrada();
    }
    const r = Salas.entrar(sala, acao.jogador, agora);
    if (r === "cheia") {
      return Response.json({ erro: "Essa sala já tem dois jogadores." }, { status: 409 });
    }
    if (r === "encerrada") {
      return Response.json({ erro: "Essa partida já terminou." }, { status: 410 });
    }
    emitir(sala);
    agendar(sala);
    return Response.json({ sala: sala.codigo });
  }

  // Para quem não é da sala, a mesma resposta de sala inexistente: um 403
  // diria que o código existe, e daria para varrer códigos sem deixar rastro.
  if (!sala || Salas.indiceDe(sala, acao.jogador) < 0) return naoEncontrada();

  if (acao.acao === "responder") {
    const resultado = Salas.responder(
      sala,
      acao.jogador,
      acao.indice,
      acao.opcao,
      acao.reacaoMs,
      agora,
    );
    agendar(sala);
    return Response.json({ resultado });
  }

  if (acao.acao === "revanche") {
    Salas.pedirRevanche(sala, acao.jogador, acao.rodadas, agora);
  } else {
    Salas.sair(sala, acao.jogador, agora);
  }
  emitir(sala);
  agendar(sala);
  return Response.json({ ok: true });
}
