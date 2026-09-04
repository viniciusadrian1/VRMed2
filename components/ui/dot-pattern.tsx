import { useId } from "react";

import { cn } from "@/lib/utils";

/** Props do padrão de pontos decorativo (fundo em SVG estático). */
interface DotPatternProps {
  /** Largura da célula do padrão, em px. */
  width?: number;
  /** Altura da célula do padrão, em px. */
  height?: number;
  /** Posição X do centro do ponto dentro da célula. */
  cx?: number;
  /** Posição Y do centro do ponto dentro da célula. */
  cy?: number;
  /** Raio do ponto. */
  cr?: number;
  className?: string;
}

/**
 * Padrão de pontos em SVG para fundo decorativo.
 *
 * Estático (já é reduced-motion-safe) e sem interação. Preenche o container pai
 * (que precisa ter `position: relative`). Os pontos herdam `currentColor`, então
 * quem usa define a cor pela paleta — ex.: `className="text-primary/20"`.
 */
export function DotPattern({
  width = 16,
  height = 16,
  cx = 1,
  cy = 1,
  cr = 1,
  className,
}: DotPatternProps) {
  // id único e estável entre servidor/cliente para referenciar o <pattern>
  const id = useId();

  return (
    <svg
      aria-hidden="true"
      className={cn(
        "pointer-events-none absolute inset-0 h-full w-full fill-current",
        className,
      )}
    >
      <pattern
        id={id}
        width={width}
        height={height}
        patternUnits="userSpaceOnUse"
        patternContentUnits="userSpaceOnUse"
      >
        <circle cx={cx} cy={cy} r={cr} />
      </pattern>
      <rect width="100%" height="100%" strokeWidth={0} fill={`url(#${id})`} />
    </svg>
  );
}
