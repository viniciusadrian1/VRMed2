import { cn } from "@/lib/utils";

interface CrosshairFrameProps {
  children: React.ReactNode;
  className?: string;
  /** Rótulo de instrumento no canto superior esquerdo (ex.: "AX · COR · SAG"). */
  label?: string;
  /** Leitura no canto inferior direito (ex.: "z = 0.00 mm"). */
  coord?: string;
  /** Desenha a mira central fina (cruz). */
  crosshair?: boolean;
}

/**
 * Moldura de atlas/visualizador médico: colchetes nos quatro cantos, mira
 * central opcional e rótulos de instrumento em fonte monoespaçada. Puramente
 * decorativa (aria-hidden) — o conteúdo real vai em `children`.
 *
 * O pai criado aqui é `relative`; a moldura se sobrepõe sem capturar cliques.
 */
export function CrosshairFrame({
  children,
  className,
  label,
  coord,
  crosshair = false,
}: CrosshairFrameProps) {
  const canto =
    "pointer-events-none absolute size-4 border-primary/60";
  return (
    <div className={cn("relative", className)}>
      {children}

      {/* Colchetes dos cantos */}
      <span aria-hidden className={cn(canto, "left-2 top-2 border-l border-t")} />
      <span aria-hidden className={cn(canto, "right-2 top-2 border-r border-t")} />
      <span aria-hidden className={cn(canto, "bottom-2 left-2 border-b border-l")} />
      <span aria-hidden className={cn(canto, "bottom-2 right-2 border-b border-r")} />

      {/* Mira central */}
      {crosshair && (
        <>
          <span
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-1/2 h-5 w-px -translate-x-1/2 -translate-y-1/2 bg-primary/30"
          />
          <span
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-1/2 h-px w-5 -translate-x-1/2 -translate-y-1/2 bg-primary/30"
          />
        </>
      )}

      {/* Rótulos de instrumento */}
      {label && (
        <span
          aria-hidden
          className="pointer-events-none absolute left-4 top-4 font-mono text-[10px] uppercase tracking-[0.2em] text-primary/70"
        >
          {label}
        </span>
      )}
      {coord && (
        <span
          aria-hidden
          className="pointer-events-none absolute bottom-4 right-4 font-mono text-[10px] tracking-wider text-primary/60"
        >
          {coord}
        </span>
      )}
    </div>
  );
}
