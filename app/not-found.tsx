import Link from "next/link";
import { Home, Compass } from "lucide-react";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="vrmed-radial grid min-h-dvh place-items-center px-5">
      <div className="flex max-w-md flex-col items-center gap-6 text-center">
        <Logo />
        <div className="flex flex-col items-center gap-2">
          <p className="font-serif text-6xl font-medium text-primary">404</p>
          <h1 className="font-serif text-2xl font-medium tracking-tight">
            Página não encontrada
          </h1>
          <p className="text-pretty text-sm text-muted-foreground">
            O endereço que você procurou não existe ou foi movido. Volte ao
            início ou abra o visualizador para continuar estudando.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button asChild>
            <Link href="/">
              <Home />
              Página inicial
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/viewer">
              <Compass />
              Abrir visualizador
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
