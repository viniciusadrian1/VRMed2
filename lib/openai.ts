import OpenAI from "openai";

/**
 * Modelo de chat do tutor de IA (ChatGPT da OpenAI).
 *
 * `gpt-4o` é um modelo estável, com suporte a streaming e boa relação
 * custo/qualidade para um tutor de anatomia. Para usar outro modelo da
 * OpenAI, basta alterar esta constante.
 */
export const CHAT_MODEL = "gpt-4o";

let cachedClient: OpenAI | null = null;

/**
 * Retorna o cliente OpenAI (instanciado sob demanda).
 * Executado apenas no servidor — a chave de API nunca é exposta ao cliente.
 */
export function getOpenAIClient(): OpenAI {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OPENAI_API_KEY não configurada no ambiente.");
  }
  if (!cachedClient) {
    cachedClient = new OpenAI({ apiKey });
  }
  return cachedClient;
}
