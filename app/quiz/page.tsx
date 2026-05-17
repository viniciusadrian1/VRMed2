"use client";

import { AppShell } from "@/components/layout/AppShell";
import { QuizMode } from "@/components/quiz/QuizMode";

export default function QuizPage() {
  return (
    <AppShell
      title="Modo Quiz"
      description="Teste seu conhecimento sobre as estruturas anotadas"
      fullBleed
    >
      <QuizMode />
    </AppShell>
  );
}
