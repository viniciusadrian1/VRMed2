import type { ChatApiMessage } from "@/types";

interface ChatRequestPayload {
  messages: ChatApiMessage[];
  currentOrgan?: string;
}

/**
 * Envia a conversa ao endpoint do tutor e encaminha a resposta em streaming.
 * Cada fragmento de texto recebido é repassado a `onChunk`.
 */
export async function streamChatResponse(
  payload: ChatRequestPayload,
  onChunk: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
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

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    onChunk(decoder.decode(value, { stream: true }));
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
