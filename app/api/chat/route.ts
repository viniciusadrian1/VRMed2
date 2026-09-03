import type OpenAI from "openai";
import { z } from "zod";
import {
  MEDICAL_SYSTEM_PROMPT,
  buildOrganContextNote,
} from "@/lib/medical-system-prompt";
import { CHAT_MODEL, getOpenAIClient } from "@/lib/openai";

/** Validação do payload de chat (Zod). */
const chatRequestSchema = z.object({
  messages: z
    .array(
      z.object({
        role: z.enum(["user", "assistant"]),
        content: z.string().min(1).max(8000),
      }),
    )
    .min(1)
    .max(40),
  currentOrgan: z.string().max(80).optional(),
});

export async function POST(request: Request) {
  // 1. Lê e valida o corpo da requisição.
  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return Response.json(
      { error: "Corpo da requisição inválido." },
      { status: 400 },
    );
  }

  const parsed = chatRequestSchema.safeParse(rawBody);
  if (!parsed.success) {
    return Response.json(
      { error: "Payload de chat inválido." },
      { status: 400 },
    );
  }

  // 2. Garante que o tutor está configurado (chave de API no servidor).
  let client: OpenAI;
  try {
    client = getOpenAIClient();
  } catch {
    // O detalhe (chave ausente) fica só no log do servidor.
    console.error("[api/chat] OPENAI_API_KEY ausente");
    return Response.json(
      { error: "O tutor de IA está indisponível neste servidor." },
      { status: 503 },
    );
  }

  const { messages, currentOrgan } = parsed.data;

  // O system prompt reúne as diretrizes estáveis e o contexto do órgão atual.
  const systemPrompt = `${MEDICAL_SYSTEM_PROMPT}\n\n${buildOrganContextNote(
    currentOrgan,
  )}`;

  // 3. Inicia a resposta em streaming (Chat Completions da OpenAI).
  let erro: unknown;
  const completion = await client.chat.completions
    .create({
      model: CHAT_MODEL,
      max_completion_tokens: 700,
      stream: true,
      messages: [{ role: "system", content: systemPrompt }, ...messages],
    },
    // Cliente abortou (fechou a gaveta/saiu da Sala): não pagar o resto.
    { signal: request.signal })
    .catch((error: unknown) => {
      erro = error;
      // Aborto pelo cliente não é falha do servidor — não polui o log.
      if (!request.signal.aborted) {
        console.error("[api/chat] falha ao iniciar a resposta", error);
      }
      return null;
    });

  if (!completion) {
    // Erros do SDK da OpenAI carregam .status (429 = ocupado/rate limit).
    const status = (erro as { status?: number } | undefined)?.status;
    if (status === 429) {
      return Response.json(
        {
          error:
            "O tutor está ocupado no momento. Tente de novo em instantes.",
        },
        { status: 429 },
      );
    }
    return Response.json(
      { error: "Não foi possível contatar o tutor de IA." },
      { status: 502 },
    );
  }

  // 4. Encaminha apenas o texto da resposta como um fluxo de bytes.
  const encoder = new TextEncoder();
  const readable = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        for await (const chunk of completion) {
          const delta = chunk.choices[0]?.delta?.content;
          if (delta) controller.enqueue(encoder.encode(delta));
        }
        controller.close();
      } catch (error) {
        // Aborto do cliente (cancel → completion.controller.abort) não é erro.
        if (!request.signal.aborted) {
          console.error("[api/chat] erro no meio do stream", error);
        }
        controller.error(error);
      }
    },
    cancel() {
      completion.controller.abort();
    },
  });

  return new Response(readable, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
