"use client";

import { motion, useReducedMotion } from "framer-motion";

import { cn } from "@/lib/utils";

interface ScanBeamProps {
  className?: string;
  /** Duração de uma varredura completa, em segundos. */
  duration?: number;
}

/**
 * Faixa de varredura (motivo de tomografia) que desliza de cima a baixo do
 * elemento pai — que precisa ser `relative` e `overflow-hidden`. Discreta e
 * lenta. Com "reduzir movimento" ativo, não renderiza nada.
 */
export function ScanBeam({ className, duration = 4.5 }: ScanBeamProps) {
  const reduzido = useReducedMotion();
  if (reduzido) return null;

  return (
    <motion.div
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-x-0 h-24 bg-[linear-gradient(to_bottom,transparent,color-mix(in_srgb,var(--primary)_16%,transparent),transparent)]",
        className,
      )}
      initial={{ top: "-10%" }}
      animate={{ top: "110%" }}
      transition={{ duration, repeat: Infinity, ease: "easeInOut", repeatDelay: 1.2 }}
    />
  );
}
