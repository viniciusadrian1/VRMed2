"use client";

import { useRef } from "react";
import dynamic from "next/dynamic";
import { useInView, useReducedMotion } from "framer-motion";
import { Skeleton } from "@/components/ui/skeleton";

// Carrega o three.js/R3F sob demanda: mantém a landing leve no primeiro carregamento.
const HeroCanvas = dynamic(
  () => import("./HeroCanvas").then((m) => m.HeroCanvas),
  { ssr: false, loading: () => <Skeleton className="size-full rounded-2xl" /> },
);

/**
 * Demonstração 3D exibida na seção hero da landing page. Só anima quando está
 * na viewport e respeita prefers-reduced-motion — fora disso a cena fica
 * estática (frameloop "demand"), sem queimar GPU ociosa.
 */
export function HeroScene() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.2 });
  const reduce = useReducedMotion();

  return (
    <div ref={ref} className="size-full">
      <HeroCanvas active={inView && !reduce} />
    </div>
  );
}
