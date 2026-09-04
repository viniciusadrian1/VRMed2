"use client";

import { Fragment } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

interface WordRevealProps {
  /** Texto a revelar; é dividido por espaços e cada palavra anima em sequência. */
  text: string;
  /** Classes tipográficas de quem usa (ex.: a serifada do H1) — preservadas no container. */
  className?: string;
  /** Atraso inicial em segundos antes da primeira palavra. */
  delay?: number;
  /** Tag do container. Padrão "span" (inline); passe "h1" etc. para bloco. */
  as?: React.ElementType;
}

/**
 * Revela um texto palavra a palavra com blur + slide ao entrar na tela.
 * Respeita prefers-reduced-motion: renderiza o texto final estático.
 */
export function WordReveal({
  text,
  className,
  delay = 0,
  as = "span",
}: WordRevealProps) {
  const reduceMotion = useReducedMotion();
  // React aceita tag em string; tipar como componente que recebe children
  // evita o erro do union React.ElementType (que inclui elementos sem filhos).
  const Tag = as as React.ComponentType<{
    className?: string;
    children?: React.ReactNode;
  }>;

  // Sem movimento: entrega o texto inteiro, sem animação. Preserva acentos pt-BR (texto cru).
  if (reduceMotion) {
    return <Tag className={cn(className)}>{text}</Tag>;
  }

  const words = text.split(" ");

  return (
    <Tag className={cn(className)}>
      {words.map((word, i) => (
        <Fragment key={`${word}-${i}`}>
          <motion.span
            // inline-block é necessário para que y/blur tenham efeito nas palavras.
            className="inline-block"
            initial={{ opacity: 0, y: 8, filter: "blur(6px)" }}
            whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{
              duration: 0.4,
              delay: delay + i * 0.06,
              ease: [0.22, 1, 0.36, 1],
            }}
          >
            {word}
          </motion.span>
          {/* Espaço real entre palavras: mantém a quebra de linha natural. */}
          {i < words.length - 1 ? " " : ""}
        </Fragment>
      ))}
    </Tag>
  );
}
