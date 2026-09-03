"use client";

import { useReducedMotion } from "framer-motion";

interface MarqueeProps {
  items: string[];
  /** Rótulo acessível para o grupo (ex.: "Fontes médicas"). */
  label: string;
}

/**
 * Faixa horizontal com rolagem contínua das fontes médicas. Respeita a
 * preferência de movimento reduzido — nesse caso, exibe os itens estáticos
 * em linhas quebradas, sem animação.
 */
export function Marquee({ items, label }: MarqueeProps) {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return (
      <ul
        aria-label={label}
        className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3"
      >
        {items.map((item) => (
          <li
            key={item}
            className="text-sm font-medium text-muted-foreground"
          >
            {item}
          </li>
        ))}
      </ul>
    );
  }

  // Repetido 4× para a rolagem parecer infinita: com poucas fontes, duas
  // cópias não preenchem a faixa e deixam um vão vazio; -50% equivale a
  // duas cópias, então o reset continua sem emenda visível.
  const loop = Array(4).fill(items).flat();

  return (
    <div
      className="group relative overflow-hidden [mask-image:linear-gradient(90deg,transparent,#000_8%,#000_92%,transparent)]"
      aria-label={label}
    >
      <ul className="flex w-max animate-[marquee_38s_linear_infinite] items-center gap-10 pr-10 group-hover:[animation-play-state:paused]">
        {loop.map((item, i) => (
          <li
            key={`${item}-${i}`}
            aria-hidden={i >= items.length}
            className="whitespace-nowrap text-sm font-medium text-muted-foreground"
          >
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
