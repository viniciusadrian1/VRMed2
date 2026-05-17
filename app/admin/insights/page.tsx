import { BarChart3, ExternalLink } from "lucide-react";
import { readAllFeedback } from "@/lib/feedback-store";
import { Card } from "@/components/ui/card";
import type { FeedbackTag } from "@/types";

export const dynamic = "force-dynamic";

const TAG_LABELS: Record<FeedbackTag, string> = {
  incorreta: "Informação incorreta",
  fonte_nao_confiavel: "Fonte não confiável",
  incompleta: "Resposta incompleta",
  fora_escopo: "Fora do escopo",
};

/** Cartão de métrica resumida. */
function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <p className="font-serif text-3xl font-medium text-primary">{value}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
    </Card>
  );
}

export default async function AdminInsightsPage() {
  const feedback = await readAllFeedback();
  const total = feedback.length;
  const positive = feedback.filter((f) => f.rating === "up").length;
  const negative = total - positive;
  const approval = total ? Math.round((positive / total) * 100) : 0;

  const organMap = new Map<string, { up: number; down: number }>();
  for (const entry of feedback) {
    const key = entry.currentOrgan || "(não informado)";
    const current = organMap.get(key) ?? { up: 0, down: 0 };
    if (entry.rating === "up") current.up += 1;
    else current.down += 1;
    organMap.set(key, current);
  }
  const byOrgan = [...organMap.entries()].sort(
    (a, b) => b[1].up + b[1].down - (a[1].up + a[1].down),
  );

  const tagMap = new Map<FeedbackTag, number>();
  for (const entry of feedback) {
    for (const tag of entry.tags) {
      tagMap.set(tag, (tagMap.get(tag) ?? 0) + 1);
    }
  }
  const byTag = [...tagMap.entries()].sort((a, b) => b[1] - a[1]);

  return (
    <div>
      <h1 className="font-serif text-2xl font-medium">Insights da pesquisa</h1>
      <p className="text-sm text-muted-foreground">
        Síntese das avaliações do tutor de IA registradas no servidor.
      </p>

      <div className="mt-6 grid gap-3 sm:grid-cols-4">
        <Stat label="Avaliações" value={total} />
        <Stat label="Positivas" value={positive} />
        <Stat label="Negativas" value={negative} />
        <Stat label="Aprovação" value={`${approval}%`} />
      </div>

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <section>
          <h2 className="text-sm font-semibold">Avaliações por órgão</h2>
          {byOrgan.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">
              Sem dados ainda.
            </p>
          ) : (
            <ul className="mt-3 flex flex-col gap-2">
              {byOrgan.map(([organ, counts]) => {
                const sum = counts.up + counts.down;
                const ratio = sum ? (counts.up / sum) * 100 : 0;
                return (
                  <li key={organ}>
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{organ}</span>
                      <span className="text-muted-foreground">
                        {counts.up}↑ · {counts.down}↓
                      </span>
                    </div>
                    <div className="mt-1 h-2 overflow-hidden rounded-full bg-destructive/30">
                      <div
                        className="h-full bg-success"
                        style={{ width: `${ratio}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section>
          <h2 className="text-sm font-semibold">Problemas mais apontados</h2>
          {byTag.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">
              Nenhuma marcação de problema registrada.
            </p>
          ) : (
            <ul className="mt-3 flex flex-col gap-2">
              {byTag.map(([tag, count]) => (
                <li
                  key={tag}
                  className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm"
                >
                  <span>{TAG_LABELS[tag]}</span>
                  <span className="font-medium tabular-nums">{count}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <Card className="mt-8 flex items-start gap-3 p-4">
        <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent text-accent-foreground">
          <BarChart3 className="size-4.5" />
        </span>
        <div className="text-sm">
          <p className="font-medium">Métricas de uso detalhadas</p>
          <p className="mt-0.5 text-muted-foreground">
            Órgãos mais visualizados, ferramentas mais usadas e tempo de
            permanência são coletados de forma anônima e ficam disponíveis no
            painel do Umami configurado em{" "}
            <code className="text-xs">NEXT_PUBLIC_ANALYTICS_URL</code>.
          </p>
        </div>
        <ExternalLink className="size-4 shrink-0 text-muted-foreground" />
      </Card>
    </div>
  );
}
