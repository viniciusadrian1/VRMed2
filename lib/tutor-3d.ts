import { z } from "zod";
import type { LayerState } from "../types/index.ts";

/** Sobreposição transitória: não modifica as camadas configuradas pelo aluno. */
export function camadasComFoco(layers: LayerState[], foco: { id: string; label: string } | null) {
  if (!foco || foco.id === "modelo") return layers;
  return layers.map((l) => ({
    ...l, visible: l.label === foco.label ? true : l.visible,
    opacity: l.label === foco.label ? 1 : Math.min(l.opacity, 0.16),
  }));
}

/** Só identificadores do modelo carregado; nunca código, URL ou coordenadas da IA. */
export const contextoTutorSchema = z.object({
  organId: z.string().min(1).max(80),
  revisao: z.number().int().nonnegative(),
  alvos: z.array(z.object({
    id: z.string().regex(/^(modelo|e\d{1,3})$/),
    label: z.string().min(1).max(160),
  }).strict()).min(1).max(101),
}).strict().refine((c) => c.alvos[0].id === "modelo" && new Set(c.alvos.map((a) => a.id)).size === c.alvos.length);

export type ContextoTutor = z.infer<typeof contextoTutorSchema>;
export const comandoTutorSchema = z.object({
  acao: z.enum(["focar", "restaurar"]),
  alvo: z.string().max(12),
}).strict();
export type ComandoTutor = z.infer<typeof comandoTutorSchema>;

export function validarComandoTutor(dado: unknown, contexto: ContextoTutor): ComandoTutor | null {
  const resultado = comandoTutorSchema.safeParse(dado);
  if (!resultado.success || !contexto.alvos.some((a) => a.id === resultado.data.alvo)) return null;
  return resultado.data;
}

export type EventoTutor =
  | { tipo: "texto"; texto: string }
  | { tipo: "comando"; comando: ComandoTutor }
  | { tipo: "erro"; erro: string }
  | { tipo: "fim" };

/** Decodificação incremental: uma linha JSON pode atravessar vários pacotes UTF-8. */
export async function lerEventosTutor(
  corpo: ReadableStream<Uint8Array>,
  receber: (evento: EventoTutor) => void,
  signal?: AbortSignal,
) {
  const leitor = corpo.getReader();
  // Encerra também uma leitura pendente, sem esperar o próximo fragmento.
  const cancelar = () => { void leitor.cancel().catch(() => {}); };
  signal?.addEventListener("abort", cancelar, { once: true });
  const decoder = new TextDecoder();
  let buffer = "";
  let terminou = false;
  const linha = (texto: string) => {
    if (!texto.trim()) return;
    if (signal?.aborted) throw new DOMException("Cancelado", "AbortError");
    const evento = JSON.parse(texto) as EventoTutor;
    if (terminou) throw new Error("Resposta do tutor inválida.");
    if (evento.tipo === "erro") throw new Error(evento.erro);
    if (evento.tipo === "fim") terminou = true;
    else if (evento.tipo === "texto" && typeof evento.texto === "string") receber(evento);
    else if (evento.tipo === "comando" && comandoTutorSchema.safeParse(evento.comando).success) receber(evento);
    else throw new Error("Resposta do tutor inválida.");
  };
  try {
    if (signal?.aborted) throw new DOMException("Cancelado", "AbortError");
    while (true) {
      const { value, done } = await leitor.read();
      if (signal?.aborted) throw new DOMException("Cancelado", "AbortError");
      buffer += decoder.decode(value, { stream: !done });
      if (buffer.length > 64_000) throw new Error("Resposta do tutor excedeu o limite.");
      let quebra: number;
      while ((quebra = buffer.indexOf("\n")) >= 0) {
        linha(buffer.slice(0, quebra));
        buffer = buffer.slice(quebra + 1);
      }
      if (done) break;
    }
    linha(buffer);
    if (!terminou) throw new Error("A resposta foi interrompida. Tente novamente.");
  } finally {
    signal?.removeEventListener("abort", cancelar);
    await leitor.cancel().catch(() => {});
    leitor.releaseLock();
  }
}
