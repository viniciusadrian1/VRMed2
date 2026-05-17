import { promises as fs } from "fs";
import path from "path";
import type { FeedbackPayload } from "@/types";

/**
 * Armazenamento de feedback das respostas do tutor.
 *
 * Para a fase de Iniciação Científica, os registros são gravados em
 * `feedback.jsonl` na raiz do projeto (um JSON por linha). A interface foi
 * mantida simples para facilitar a migração futura a Supabase/Postgres:
 * basta substituir as duas funções abaixo.
 */
const FEEDBACK_FILE = path.join(process.cwd(), "feedback.jsonl");

/** Acrescenta um registro de feedback ao arquivo. */
export async function appendFeedback(entry: FeedbackPayload): Promise<void> {
  await fs.appendFile(FEEDBACK_FILE, `${JSON.stringify(entry)}\n`, "utf8");
}

/** Lê todos os registros de feedback (mais recentes primeiro). */
export async function readAllFeedback(): Promise<FeedbackPayload[]> {
  try {
    const content = await fs.readFile(FEEDBACK_FILE, "utf8");
    return content
      .split("\n")
      .filter((line) => line.trim().length > 0)
      .map((line) => JSON.parse(line) as FeedbackPayload)
      .reverse();
  } catch (error) {
    // O arquivo ainda não existe — nenhum feedback registrado.
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw error;
  }
}
