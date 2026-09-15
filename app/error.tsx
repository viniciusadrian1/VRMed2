"use client";

import { useEffect } from "react";
import { Home, RotateCcw } from "lucide-react";
import { BrandMark } from "@/components/layout/Logo";
import { Button } from "@/components/ui/button";

/** Limite de erro de rota: captura falhas de renderização e oferece recuperação. */
export default function Error({
  error,
}: {
  error: Error & { digest?: string };
}) {
  useEffect(() => {
    // Em produção, este é o ponto para enviar o erro a um serviço de log.
    console.error(error);
  }, [error]);

  return (
    <main
      id="conteudo-principal"
      className="vrmed-radial grid min-h-dvh place-items-center px-5"
    >
      <div className="flex max-w-md flex-col items-center gap-6 text-center">
        {/* Marca sem link: o <Logo> é um next/link, que teria o mesmo defeito
            das saídas abaixo; a volta ao início fica com "Página inicial". */}
        <span className="flex items-center gap-2.5">
          <BrandMark />
          <span className="font-serif text-xl font-medium tracking-tight">
            VRmed
          </span>
        </span>
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
          {/* Recarregamento completo nas duas saídas: o reset() do Next só
              remonta a árvore, e o useGLTF relança o erro guardado no cache
              do suspend-react (o mesmo vale para um lazy rejeitado). Em "/",
              um <Link> para o mesmo pathname nem tira o usuário desta tela. */}
          <Button onClick={() => window.location.reload()}>
            <RotateCcw />
            Tentar novamente
          </Button>
          <Button asChild variant="outline">
            {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- navegação completa de propósito, para descartar o cache com o erro */}
            <a href="/">
              <Home />
              Página inicial
            </a>
          </Button>
        </div>
      </div>
    </main>
  );
}
