import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { Reveal } from "./Reveal";

interface SectionIntroProps {
  index: string;
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  align?: "left" | "center";
  className?: string;
}

/**
 * Cabeçalho de seção no estilo "prancha de atlas": numeração técnica,
 * rótulo em versalete e título sóbrio. O movimento fica a cargo do Reveal.
 */
export function SectionIntro({
  index,
  eyebrow,
  title,
  description,
  align = "left",
  className,
}: SectionIntroProps) {
  const centered = align === "center";

  return (
    <Reveal className={className}>
      <div className={cn("max-w-2xl", centered && "mx-auto text-center")}>
        {/* Linha superior: índice de prancha + hairline + rótulo técnico */}
        <div className={cn("flex items-center gap-3", centered && "justify-center")}>
          <span className="font-mono text-xs text-primary">{index}</span>
          <span className="h-px w-8 bg-border" aria-hidden />
          <span className="text-sm font-medium uppercase tracking-[0.14em] text-primary">
            {eyebrow}
          </span>
          {centered && <span className="h-px w-8 bg-border" aria-hidden />}
        </div>

        <h2 className="mt-4 text-balance font-serif text-3xl font-medium tracking-tight md:text-[2.6rem] md:leading-[1.08]">
          {title}
        </h2>

        {description && (
          <p
            className={cn(
              "mt-4 max-w-2xl text-pretty leading-relaxed text-muted-foreground",
              centered && "mx-auto",
            )}
          >
            {description}
          </p>
        )}
      </div>
    </Reveal>
  );
}
