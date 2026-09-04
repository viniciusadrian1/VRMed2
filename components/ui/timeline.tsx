"use client";

import { useRef } from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";

import { cn } from "@/lib/utils";

interface TimelineItem {
  titulo: string;
  conteudo: React.ReactNode;
}

interface TimelineProps {
  items: TimelineItem[];
  className?: string;
}

/**
 * Linha do tempo vertical, sóbria e editorial. A "beam" à esquerda se preenche
 * de var(--primary) para o âmbar (#c8935a) conforme o scroll passa pela seção.
 * Com "reduzir movimento" ativo, a linha aparece estática e totalmente preenchida.
 */
export function Timeline({ items, className }: TimelineProps) {
  const reduceMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);

  // Progresso do scroll enquanto a seção atravessa a viewport.
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 20%", "end 70%"],
  });
  const alturaBeam = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  // Gradiente do preenchimento: primário no topo, âmbar embaixo.
  const gradienteBeam =
    "linear-gradient(to bottom, var(--primary) 0%, #c8935a 100%)";

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {/* Trilho base (não preenchido) */}
      <div
        aria-hidden
        className="absolute left-[15px] top-2 bottom-2 w-px bg-border"
      />

      {/* Beam preenchida sobre o trilho */}
      {reduceMotion ? (
        <div
          aria-hidden
          className="absolute left-[15px] top-2 bottom-2 w-px rounded-full"
          style={{ background: gradienteBeam }}
        />
      ) : (
        <motion.div
          aria-hidden
          className="absolute left-[15px] top-2 w-px rounded-full"
          style={{ height: alturaBeam, maxHeight: "calc(100% - 1rem)", background: gradienteBeam }}
        />
      )}

      <ol className="space-y-12">
        {items.map((item, index) => (
          <li key={index} className="relative pl-12">
            {/* Marcador */}
            <span
              aria-hidden
              className="absolute left-0 top-1 flex h-8 w-8 items-center justify-center rounded-full bg-background ring-1 ring-border"
            >
              <span className="h-3 w-3 rounded-full bg-primary" />
            </span>

            <h3 className="text-lg font-semibold text-foreground">{item.titulo}</h3>
            <div className="mt-2 text-sm text-muted-foreground">{item.conteudo}</div>
          </li>
        ))}
      </ol>
    </div>
  );
}
