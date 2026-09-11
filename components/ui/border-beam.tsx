"use client";

// Feixe de luz que percorre a borda do elemento pai.
// O pai precisa ser position:relative, overflow:hidden e ter cantos arredondados
// (o rounded-[inherit] herda o raio dele). Um único feixe, lento e discreto.

import { motion, useReducedMotion } from "framer-motion";
import type { CSSProperties } from "react";

import { cn } from "@/lib/utils";

interface BorderBeamProps {
  /** Lado do quadrado luminoso que viaja pela borda, em px. */
  size?: number;
  /** Duração de uma volta completa, em segundos. Longo = discreto. */
  duration?: number;
  /** Atraso antes de começar, em segundos. */
  delay?: number;
  /** Cor inicial do gradiente. Padrão: azul clínico da paleta. */
  colorFrom?: string;
  /** Cor final do gradiente. Padrão: âmbar (cor de acento). */
  colorTo?: string;
  className?: string;
}

export function BorderBeam({
  size = 60,
  duration = 10,
  delay = 0,
  colorFrom = "var(--primary)",
  colorTo = "#c8935a",
  className,
}: BorderBeamProps) {
  const movimentoReduzido = useReducedMotion();

  // Preferência por menos movimento: não renderiza o feixe.
  // A borda estática do pai já cumpre o papel visual.
  if (movimentoReduzido) return null;

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 rounded-[inherit] border border-transparent [mask-clip:padding-box,border-box] [mask-composite:intersect] [mask:linear-gradient(transparent,transparent),linear-gradient(#fff,#fff)]"
    >
      <motion.div
        className={cn(
          "absolute aspect-square bg-gradient-to-l from-[var(--beam-from)] via-[var(--beam-to)] to-transparent",
          className,
        )}
        style={
          {
            width: size,
            // offset-path desenha o retângulo da borda com o mesmo raio do feixe.
            offsetPath: `rect(0 auto auto 0 round ${size}px)`,
            "--beam-from": colorFrom,
            "--beam-to": colorTo,
          } as CSSProperties
        }
        initial={{ offsetDistance: "0%" }}
        animate={{ offsetDistance: "100%" }}
        transition={{ repeat: Infinity, ease: "linear", duration, delay }}
      />
    </div>
  );
}
