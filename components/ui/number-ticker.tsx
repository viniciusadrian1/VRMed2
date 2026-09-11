"use client";

// Contador que anima de 0 ate `value` quando entra na viewport (framer-motion).
// Herda a cor do texto (currentColor) e respeita prefers-reduced-motion:
// se o movimento for reduzido, mostra o valor final formatado imediatamente.
import { useEffect, useRef } from "react";
import {
  useInView,
  useMotionValue,
  useReducedMotion,
  useSpring,
} from "framer-motion";

import { cn } from "@/lib/utils";

interface NumberTickerProps {
  value: number;
  className?: string;
  decimalPlaces?: number;
  delay?: number; // atraso em segundos antes de animar
  suffix?: string; // sufixo opcional, ex.: "%"
}

export function NumberTicker({
  value,
  className,
  decimalPlaces = 0,
  delay = 0,
  suffix = "",
}: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduzido = useReducedMotion();
  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, { damping: 60, stiffness: 100 });
  const isInView = useInView(ref, { once: true, margin: "0px" });

  // dispara a mola ao entrar na viewport, respeitando o delay
  useEffect(() => {
    if (reduzido || !isInView) return;
    const timer = setTimeout(() => motionValue.set(value), delay * 1000);
    return () => clearTimeout(timer);
  }, [motionValue, isInView, delay, value, reduzido]);

  // escreve o numero formatado a cada frame da animacao
  useEffect(() => {
    if (reduzido) return;
    return springValue.on("change", (atual) => {
      if (!ref.current) return;
      ref.current.textContent =
        Intl.NumberFormat("pt-BR", {
          minimumFractionDigits: decimalPlaces,
          maximumFractionDigits: decimalPlaces,
        }).format(Number(atual.toFixed(decimalPlaces))) + suffix;
    });
  }, [springValue, decimalPlaces, suffix, reduzido]);

  // valor do primeiro render: final se o movimento for reduzido, senao zero
  const inicial =
    Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: decimalPlaces,
      maximumFractionDigits: decimalPlaces,
    }).format(reduzido ? value : 0) + suffix;

  return (
    <span ref={ref} className={cn("inline-block tabular-nums", className)}>
      {inicial}
    </span>
  );
}
