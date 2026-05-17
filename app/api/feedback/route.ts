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
  timestamp: z.string().max(40),
});

export async function POST(request: Request) {
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
    await appendFeedback(parsed.data);
  } catch {
    return Response.json(
      { error: "Não foi possível registrar o feedback." },
      { status: 500 },
    );
  }

  return Response.json({ ok: true });
}
