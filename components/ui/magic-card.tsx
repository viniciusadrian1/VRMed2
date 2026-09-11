"use client";

import * as React from "react";
import { motion, useMotionTemplate, useMotionValue, useReducedMotion } from "framer-motion";

import { cn } from "@/lib/utils";

interface MagicCardProps {
  children?: React.ReactNode;
  className?: string;
  /** Diâmetro (px) do brilho radial que segue o cursor. */
  gradientSize?: number;
  /** Cor do preenchimento do spotlight (sutil, azul da paleta por padrão). */
  gradientColor?: string;
  /** Início do realce da borda no hover. */
  gradientFrom?: string;
  /** Fim do realce da borda no hover (âmbar de acento por padrão). */
  gradientTo?: string;
}

/**
 * Card com spotlight radial discreto que segue o cursor e realça a borda no hover.
 * Não aplica fundo próprio: preserva o estilo de quem envolve, só adiciona a camada de brilho.
 */
export function MagicCard({
  children,
  className,
  gradientSize = 200,
  gradientColor = "color-mix(in srgb, var(--primary) 12%, transparent)",
  gradientFrom = "color-mix(in srgb, var(--primary) 55%, transparent)",
  gradientTo = "color-mix(in srgb, #c8935a 45%, transparent)",
}: MagicCardProps) {
  const reduceMotion = useReducedMotion();

  // Posição do cursor relativa ao card; começa fora da área (sem realce em repouso).
  const mouseX = useMotionValue(-gradientSize);
  const mouseY = useMotionValue(-gradientSize);

  const handleMouseMove = React.useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      mouseX.set(e.clientX - rect.left);
      mouseY.set(e.clientY - rect.top);
    },
    [mouseX, mouseY],
  );

  // Templates de gradiente que acompanham o cursor (hooks sempre no topo).
  const spotlight = useMotionTemplate`radial-gradient(${gradientSize}px circle at ${mouseX}px ${mouseY}px, ${gradientColor}, transparent 80%)`;
  const borderSheen = useMotionTemplate`radial-gradient(${gradientSize}px circle at ${mouseX}px ${mouseY}px, ${gradientFrom}, ${gradientTo}, transparent 100%) border-box`;

  // Movimento reduzido: só o conteúdo, sem spotlight nem handlers.
  if (reduceMotion) {
    return <div className={cn("relative rounded-[inherit]", className)}>{children}</div>;
  }

  return (
    <div
      className={cn("group relative overflow-hidden rounded-[inherit]", className)}
      onMouseMove={handleMouseMove}
    >
      {/* Preenchimento do spotlight que segue o cursor. */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{ background: spotlight }}
      />
      {/* Realce só na borda (máscara mantém o interior transparente). */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-[inherit] border border-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: borderSheen,
          WebkitMask: "linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0)",
          WebkitMaskComposite: "xor",
          mask: "linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0)",
          maskComposite: "exclude",
        }}
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
}
