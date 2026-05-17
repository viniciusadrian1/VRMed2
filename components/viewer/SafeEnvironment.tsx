"use client";

import { Suspense } from "react";
import { Environment } from "@react-three/drei";
import { ErrorBoundary } from "@/components/ErrorBoundary";

/**
 * Iluminação por ambiente (preset "studio" do drei).
 * O preset busca um HDR pela rede; caso falhe (uso offline), o limite de erro
 * o descarta silenciosamente — as luzes explícitas da cena mantêm o modelo
 * sempre iluminado.
 */
export function SafeEnvironment() {
  return (
    <ErrorBoundary fallback={null}>
      <Suspense fallback={null}>
        <Environment preset="studio" />
      </Suspense>
    </ErrorBoundary>
  );
}
