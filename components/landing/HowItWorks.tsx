import { cn } from "@/lib/utils";
import { Reveal } from "./Reveal";

interface Passo {
  titulo: string;
  descricao: string;
}

/**
 * Protocolo em passos numerados, disposto como um eixo/régua de instrumento:
 * horizontal no desktop (colunas iguais ligadas por uma hairline contínua),
 * empilhado no mobile com a linha vertical à esquerda ligando os marcadores.
 */
export function HowItWorks({ steps }: { steps: Passo[] }) {
  const ultimo = steps.length - 1;

  return (
    <Reveal>
      <ol className="flex flex-col md:flex-row">
        {steps.map((passo, i) => {
          const indice = String(i + 1).padStart(2, "0");
          const primeiro = i === 0;
          const derradeiro = i === ultimo;

          return (
            <li
              key={indice}
              className="relative flex gap-5 pb-10 last:pb-0 md:flex-1 md:flex-col md:gap-0 md:px-5 md:pb-0 md:text-center"
            >
              {/* Eixo para frente: vertical no mobile (liga ao próximo
                  marcador), meia-linha à direita no desktop. O primeiro começa
                  no centro (marcador); os demais atravessam a coluna inteira. */}
              {!derradeiro && (
                <span
                  aria-hidden
                  className={cn(
                    "absolute left-5 top-5 h-full w-px -translate-x-1/2 bg-border",
                    "md:right-0 md:top-5 md:h-px md:w-auto md:translate-x-0",
                    primeiro ? "md:left-1/2" : "md:left-0",
                  )}
                />
              )}
              {/* Meia-linha à esquerda no último passo fecha o eixo no marcador
                  final (só desktop; no mobile a linha não passa do último). */}
              {derradeiro && !primeiro && (
                <span
                  aria-hidden
                  className="absolute left-0 right-1/2 top-5 hidden h-px bg-border md:block"
                />
              )}

              <span className="relative z-10 grid size-10 shrink-0 place-items-center rounded-full border border-border bg-card md:mx-auto">
                <span className="size-2.5 rounded-full bg-primary" />
              </span>

              <div className="md:mt-5">
                <span className="block font-mono text-2xl leading-none text-muted-foreground/60 tabular-nums">
                  {indice}
                </span>
                <h3 className="mt-2 font-serif text-xl">{passo.titulo}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  {passo.descricao}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </Reveal>
  );
}
