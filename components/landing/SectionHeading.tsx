import { Reveal } from "./Reveal";
import { cn } from "@/lib/utils";

interface SectionHeadingProps {
  eyebrow: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  align?: "left" | "center";
  className?: string;
}

/**
 * Cabeçalho de seção reutilizável: eyebrow (rótulo curto), título em serifa e
 * descrição opcional. Mantém o ritmo tipográfico consistente em toda a landing.
 */
export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
  className,
}: SectionHeadingProps) {
  return (
    <Reveal
      className={cn(
        "max-w-2xl",
        align === "center" && "mx-auto text-center",
        className,
      )}
    >
      <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.14em] text-primary">
        {align === "center" && (
          <span className="h-px w-6 bg-primary/40" aria-hidden />
        )}
        {eyebrow}
        {align === "center" && (
          <span className="h-px w-6 bg-primary/40" aria-hidden />
        )}
      </p>
      <h2 className="mt-3 text-balance font-serif text-3xl font-medium tracking-tight md:text-[2.5rem] md:leading-[1.1]">
        {title}
      </h2>
      {description && (
        <p className="mt-4 text-pretty text-base leading-relaxed text-muted-foreground">
          {description}
        </p>
      )}
    </Reveal>
  );
}
