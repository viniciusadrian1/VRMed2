import Link from "next/link";
import { HelpCircle } from "lucide-react";
import { Logo } from "@/components/layout/Logo";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Button } from "@/components/ui/button";

interface TopBarProps {
  title: string;
  description?: string;
  /** Conteúdo extra alinhado à direita (ações específicas da página). */
  actions?: React.ReactNode;
}

/** Barra superior das telas internas. */
export function TopBar({ title, description, actions }: TopBarProps) {
  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-card/80 px-4 backdrop-blur-sm md:px-6">
      {/* O logo aparece no topo apenas no mobile (no desktop fica no trilho lateral) */}
      <Logo withText={false} className="md:hidden" />

      <div className="min-w-0 flex-1">
        <h1 className="truncate font-serif text-lg font-medium leading-tight tracking-tight">
          {title}
        </h1>
        {description && (
          <p className="truncate text-xs text-muted-foreground">{description}</p>
        )}
      </div>

      <div className="flex items-center gap-1">
        {actions}
        <Button
          variant="ghost"
          size="icon"
          asChild
          aria-label="Sobre o projeto"
          title="Sobre o projeto"
        >
          <Link href="/#pesquisa">
            <HelpCircle />
          </Link>
        </Button>
        <ThemeToggle />
      </div>
    </header>
  );
}
