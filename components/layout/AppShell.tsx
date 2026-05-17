import { cn } from "@/lib/utils";
import { MobileNav, SideRail } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

interface AppShellProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  /** Remove o espaçamento interno (usado pelo visualizador e comparação). */
  fullBleed?: boolean;
  children: React.ReactNode;
}

/**
 * Estrutura compartilhada das telas internas: trilho de navegação,
 * barra superior e área de conteúdo rolável. Ocupa exatamente a altura
 * da viewport para que o canvas 3D possa preenchê-la por completo.
 */
export function AppShell({
  title,
  description,
  actions,
  fullBleed = false,
  children,
}: AppShellProps) {
  return (
    <div className="flex h-dvh overflow-hidden">
      <SideRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar title={title} description={description} actions={actions} />
        <main
          id="conteudo-principal"
          className={cn(
            "min-h-0 flex-1",
            fullBleed ? "overflow-hidden" : "overflow-y-auto p-5 md:p-8",
          )}
        >
          {children}
        </main>
        <MobileNav />
      </div>
    </div>
  );
}
