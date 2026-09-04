import { Reveal } from "./Reveal";

export interface SourceGroup {
  /** Disciplina do grupo (ex.: "ANATOMIA"). */
  label: string;
  /** Tratados/referências daquela disciplina. */
  items: string[];
}

/**
 * Painel editorial de fontes no estilo "ficha bibliográfica de atlas":
 * um único painel dividido em linhas por disciplina — rótulo técnico e índice
 * à esquerda, tratados como sumário à direita. Sóbrio; o movimento fica só
 * a cargo do Reveal.
 */
export function SourcesPanel({ groups }: { groups: SourceGroup[] }) {
  return (
    <Reveal>
      <div className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
        {groups.map((group, i) => (
          <section
            key={group.label}
            className="grid gap-4 px-6 py-8 md:grid-cols-[160px_1fr] md:gap-8 md:px-8 md:py-10"
          >
            {/* Rótulo da disciplina + índice da ficha */}
            <div className="flex items-baseline gap-3 md:flex-col md:items-start md:gap-2">
              <span className="font-mono text-xs tabular-nums text-muted-foreground">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="font-mono text-sm uppercase tracking-wider text-primary">
                {group.label}
              </h3>
            </div>

            {/* Tratados do grupo como sumário/ficha */}
            <ul className="space-y-3">
              {group.items.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  {/* Marcador hairline sutil */}
                  <span
                    className="mt-[0.6em] h-px w-4 shrink-0 bg-border"
                    aria-hidden
                  />
                  <span className="text-pretty font-medium leading-snug text-foreground">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </Reveal>
  );
}
