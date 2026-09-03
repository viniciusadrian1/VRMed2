import { z } from "zod";
import { appendFeedback } from "@/lib/feedback-store";

/** Validação do payload de feedback (Zod). */
const feedbackSchema = z.object({
  messageId: z.string().min(1).max(120),
  userPrompt: z.string().max(8000),
  aiResponse: z.string().max(20000),
  rating: z.enum(["up", "down"]),
  tags: z
    .array(
      z.enum(["incorreta", "fonte_nao_confiavel", "incompleta", "fora_escopo"]),
    )
    .max(4),
  comment: z.string().max(2000),
  currentOrgan: z.string().max(80),
});

// ponytail: limite em memória por instância; trocar por store compartilhado se houver mais de uma réplica
const hits = new Map<string, number[]>();

export async function POST(request: Request) {
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "local";
  const now = Date.now();
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < 60_000);
  if (recent.length >= 10) {
    return Response.json(
      { error: "Muitos envios; aguarde um minuto." },
      { status: 429 },
    );
  }
  recent.push(now);
  hits.set(ip, recent);

  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return Response.json(
      { error: "Corpo da requisição inválido." },
      { status: 400 },
    );
  }

  const parsed = feedbackSchema.safeParse(rawBody);
  if (!parsed.success) {
    return Response.json(
      { error: "Payload de feedback inválido." },
      { status: 400 },
    );
  }

  try {
    await appendFeedback({ ...parsed.data, timestamp: new Date().toISOString() });
  } catch {
    return Response.json(
      { error: "Não foi possível registrar o feedback." },
      { status: 500 },
    );
  }

  return Response.json({ ok: true });
}
