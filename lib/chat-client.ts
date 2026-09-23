import type { ChatApiMessage } from "@/types";
import { lerEventosTutor, type ContextoTutor, type ComandoTutor } from "./tutor-3d.ts";

interface ChatRequestPayload {
  messages: ChatApiMessage[];
  currentOrgan?: string;
  contexto3d?: ContextoTutor;
}

/**
 * Envia a conversa ao endpoint do tutor e encaminha a resposta em streaming.
 * Cada fragmento de texto recebido é repassado a `onChunk`.
 */
export async function streamChatResponse(
  payload: ChatRequestPayload,
  onChunk: (text: string) => void,
  signal?: AbortSignal,
  onCommand?: (comando: ComandoTutor) => void,
): Promise<void> {
  // O servidor aceita no máximo 40 mensagens não vazias (app/api/chat/route.ts).
  // Sem este corte, um chat longo persistido no localStorage deixava o tutor
  // em 400 para sempre; 20 mensagens (10 trocas) bastam de contexto.
  // Cada mensagem também tem teto de 8000 caracteres no mesmo schema: um texto
  // colado maior que isso ficava no histórico e travava todas as perguntas seguintes.
  const messages = payload.messages
    .filter((m) => m.content.trim())
    .slice(-20)
    .map((m) => ({ ...m, content: m.content.slice(0, 8000) }));

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, messages }),
      signal,
    });

    if (!response.ok || !response.body) {
      let message = "Não foi possível contatar o tutor de IA.";
      try {
        const data = (await response.json()) as { error?: string };
        if (data?.error) message = data.error;
      } catch {
        /* resposta sem corpo JSON — mantém a mensagem padrão */
      }
      throw new Error(message);
    }

    if (response.headers.get("Content-Type")?.includes("application/x-ndjson")) {
      await lerEventosTutor(response.body, (evento) => {
        if (evento.tipo === "texto") onChunk(evento.texto);
        if (evento.tipo === "comando") onCommand?.(evento.comando);
      }, signal);
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      onChunk(decoder.decode(value, { stream: true }));
    }
  } catch (e) {
    // Sem rede ou stream cortado, fetch/read rejeitam com TypeError em inglês
    // ("Failed to fetch", "network error"), que os chamadores mostram cru.
    // Abortos e as mensagens do servidor (Error comum) passam intactos.
    if (signal?.aborted || !(e instanceof TypeError)) throw e;
    throw new Error(
      "Não foi possível contatar o tutor de IA. Verifique sua conexão.",
    );
  }
}

/**
 * Classificação leve da pergunta — usada apenas para telemetria anônima
 * (nunca registramos o texto da pergunta, apenas a categoria e um hash).
 */
export function detectQuestionCategory(text: string): string {
  const value = text.toLowerCase();
  if (/(função|funciona|fisiolog|para que serve)/.test(value)) {
    return "fisiologia";
  }
  if (/(doença|patolog|lesão|sintoma|síndrome|câncer|inflamaç)/.test(value)) {
    return "patologia";
  }
  if (/(diferença|compar|versus| vs )/.test(value)) {
    return "comparacao";
  }
  if (/(onde|localiz|estrutura|o que é|quais|quantos)/.test(value)) {
    return "estrutura";
  }
  return "geral";
}
