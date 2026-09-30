import { AUDIO_MAX_BYTES, formatoAudio, TRANSCRICAO_MAX_CARACTERES } from "./transcricao.ts";

type Transcrever = (arquivo: File, sinal: AbortSignal) => Promise<string>;
class ErroAudio extends Error {
  status: number;
  constructor(status: number, mensagem: string) { super(mensagem); this.status = status; }
}
const json = (dados: object, status = 200) => Response.json(dados, { status, headers: { "Cache-Control": "no-store" } });

/** Limita os bytes efetivamente lidos, inclusive sem Content-Length. */
async function lerAudio(request: Request, sinal: AbortSignal) {
  sinal.throwIfAborted();
  if (!request.body) throw new ErroAudio(400, "Gravação vazia. Grave novamente.");
  const leitor = request.body.getReader();
  const partes: Uint8Array<ArrayBuffer>[] = [];
  let tamanho = 0;
  const cancelar = () => { void leitor.cancel().catch(() => {}); };
  sinal.addEventListener("abort", cancelar, { once: true });
  try {
    while (true) {
      const { value, done } = await leitor.read();
      sinal.throwIfAborted();
      if (done) break;
      tamanho += value.byteLength;
      if (tamanho > AUDIO_MAX_BYTES) {
        cancelar();
        throw new ErroAudio(413, "Áudio muito grande. Grave uma pergunta mais curta.");
      }
      partes.push(new Uint8Array(value));
    }
  } finally { sinal.removeEventListener("abort", cancelar); leitor.releaseLock(); }
  if (tamanho < 100) throw new ErroAudio(400, "Gravação vazia ou curta demais. Grave novamente.");
  return partes;
}

/** Limites por instância; não substituem autenticação/WAF em uma implantação pública. */
export function criarHandlerTranscricao(transcrever: Transcrever, agora = Date.now, prazoMs = 45_000) {
  const uso = new Map<string, { inicio: number; quantidade: number }>();
  let simultaneos = 0;
  let janela = 0, total = 0;
  return async (request: Request) => {
    const origem = request.headers.get("origin");
    // Host é preservado pelo proxy. Não confiar em X-Forwarded-Host arbitrário.
    // No standalone, request.url pode conter o host interno do container.
    const url = new URL(request.url);
    const host = request.headers.get("host") ?? url.host;
    const protocolo = request.headers.get("x-forwarded-proto") ?? url.protocol.slice(0, -1);
    const origemEsperada = `${protocolo}://${host}`;
    if ((origem && origem !== origemEsperada) || request.headers.get("sec-fetch-site") === "cross-site") {
      return json({ error: "Origem da gravação não permitida." }, 403);
    }
    const formato = formatoAudio(request.headers.get("content-type") ?? "");
    if (!formato) return json({ error: "Formato de áudio não aceito. Grave pelo microfone do tutor." }, 415);
    const declarado = Number(request.headers.get("content-length") ?? 0);
    if (declarado > AUDIO_MAX_BYTES) return json({ error: "Áudio muito grande. Grave uma pergunta mais curta." }, 413);
    const t = agora();
    for (const [chave, item] of uso) if (t - item.inicio >= 60_000) uso.delete(chave);
    if (t - janela >= 60_000) { janela = t; total = 0; }
    const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim().slice(0, 100) || "local";
    const item = uso.get(ip) ?? { inicio: t, quantidade: 0 };
    if (item.quantidade >= 6 || total >= 60 || simultaneos >= 4 || (uso.size >= 1000 && !uso.has(ip))) {
      return json({ error: "Muitas gravações no momento. Aguarde um minuto." }, 429);
    }
    item.quantidade++; uso.set(ip, item); total++; simultaneos++;
    const prazo = new AbortController();
    const timer = setTimeout(() => prazo.abort(new DOMException("Prazo excedido", "TimeoutError")), prazoMs);
    const sinal = AbortSignal.any([request.signal, prazo.signal]);
    try {
      const partes = await lerAudio(request, sinal);
      sinal.throwIfAborted();
      const arquivo = new File(partes, `pergunta.${formato.extensao}`, { type: formato.mime });
      const texto = (await transcrever(arquivo, sinal)).trim();
      sinal.throwIfAborted();
      if (!texto) return json({ error: "Não foi possível identificar uma fala. Tente novamente." }, 422);
      if (texto.length > TRANSCRICAO_MAX_CARACTERES) return json({ error: "A transcrição ficou longa demais. Grave uma pergunta mais curta." }, 422);
      return json({ texto });
    } catch (erro) {
      if (erro instanceof ErroAudio) return json({ error: erro.message }, erro.status);
      if (request.signal.aborted) return json({ error: "Transcrição cancelada." }, 499);
      const falha = erro as { status?: number; code?: string; name?: string };
      if (prazo.signal.aborted || falha.name === "TimeoutError" || falha.name === "APIConnectionTimeoutError") return json({ error: "A transcrição demorou demais. Tente novamente." }, 504);
      if (falha.status === 429 && falha.code !== "insufficient_quota") return json({ error: "A transcrição está ocupada. Tente em instantes." }, 429);
      if (falha.status === 400) return json({ error: "Não foi possível ler o áudio. Grave novamente." }, 400);
      // Não registrar áudio, transcrição, cabeçalhos ou detalhes do provedor.
      return json({ error: "A transcrição está indisponível no momento. Você pode digitar a pergunta." }, 503);
    } finally { clearTimeout(timer); simultaneos--; }
  };
}
