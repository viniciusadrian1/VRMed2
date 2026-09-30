import { getOpenAIClient } from "@/lib/openai";
import { criarHandlerTranscricao } from "@/lib/transcricao-servidor";

export const runtime = "nodejs";
export const maxDuration = 60;

export const POST = criarHandlerTranscricao(async (arquivo, signal) => {
  const resposta = await getOpenAIClient().audio.transcriptions.create({
    file: arquivo,
    model: "gpt-4o-mini-transcribe",
    language: "pt",
    response_format: "json",
  }, { signal, timeout: 45_000, maxRetries: 0 });
  return resposta.text;
});
