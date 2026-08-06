"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Home, RotateCcw } from "lucide-react";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/button";

/** Limite de erro de rota: captura falhas de renderização e oferece recuperação. */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Em produção, este é o ponto para enviar o erro a um serviço de log.
    console.error(error);
  }, [error]);

  return (
    <div className="vrmed-radial grid min-h-dvh place-items-center px-5">
      <div className="flex max-w-md flex-col items-center gap-6 text-center">
        <Logo />
        <div className="flex flex-col items-center gap-2">
          <h1 className="font-serif text-2xl font-medium tracking-tight">
            Algo deu errado
          </h1>
          <p className="text-pretty text-sm text-muted-foreground">
            Ocorreu um erro inesperado ao carregar esta página. Você pode tentar
            novamente ou voltar ao início.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button onClick={reset}>
            <RotateCcw />
            Tentar novamente
          </Button>
          <Button asChild variant="outline">
            <Link href="/">
              <Home />
              Página inicial
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
