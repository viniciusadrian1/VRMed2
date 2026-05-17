import { readAllFeedback } from "@/lib/feedback-store";
import { FeedbackExport } from "@/components/admin/FeedbackExport";
import { Badge } from "@/components/ui/badge";
import type { FeedbackTag } from "@/types";

export const dynamic = "force-dynamic";

const TAG_LABELS: Record<FeedbackTag, string> = {
  incorreta: "Informação incorreta",
  fonte_nao_confiavel: "Fonte não confiável",
  incompleta: "Resposta incompleta",
  fora_escopo: "Fora do escopo",
};

export default async function AdminFeedbackPage() {
  const feedback = await readAllFeedback();

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-serif text-2xl font-medium">
            Avaliações do tutor de IA
          </h1>
          <p className="text-sm text-muted-foreground">
            {feedback.length} registro{feedback.length === 1 ? "" : "s"} de
            avaliação.
          </p>
        </div>
        <FeedbackExport data={feedback} />
      </div>

      {feedback.length === 0 ? (
        <p className="mt-10 text-center text-sm text-muted-foreground">
          Nenhuma avaliação registrada ainda. As avaliações feitas pelos
          estudantes no chat aparecerão aqui.
        </p>
      ) : (
        <div className="mt-6 flex flex-col gap-3">
          {feedback.map((entry, index) => (
            <article
              key={`${entry.messageId}-${index}`}
              className="rounded-xl border border-border bg-card p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant={entry.rating === "up" ? "success" : "destructive"}
                >
                  {entry.rating === "up" ? "Positivo" : "Negativo"}
                </Badge>
                {entry.currentOrgan && (
                  <Badge variant="secondary">{entry.currentOrgan}</Badge>
                )}
                <span className="ml-auto text-xs text-muted-foreground">
                  {new Date(entry.timestamp).toLocaleString("pt-BR")}
                </span>
              </div>

              {entry.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {entry.tags.map((tag) => (
                    <Badge key={tag} variant="outline">
                      {TAG_LABELS[tag]}
                    </Badge>
                  ))}
                </div>
              )}

              {entry.comment && (
                <p className="mt-2 text-sm">{entry.comment}</p>
              )}

              <div className="mt-3 flex flex-col gap-2 rounded-lg bg-muted p-3 text-sm">
                <p>
                  <span className="font-medium">Pergunta: </span>
                  <span className="text-muted-foreground">
                    {entry.userPrompt || "—"}
                  </span>
                </p>
                <p>
                  <span className="font-medium">Resposta: </span>
                  <span className="text-muted-foreground">
                    {entry.aiResponse || "—"}
                  </span>
                </p>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
