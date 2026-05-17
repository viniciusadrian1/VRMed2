import Link from "next/link";
import { Logo } from "@/components/layout/Logo";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { buttonVariants } from "@/components/ui/button";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex h-16 max-w-5xl items-center gap-3 px-5">
          <Logo />
          <span className="hidden text-sm text-muted-foreground sm:inline">
            · Painel do pesquisador
          </span>
          <nav className="ml-4 flex gap-1">
            <Link
              href="/admin/feedback"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              Feedback
            </Link>
            <Link
              href="/admin/insights"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              Insights
            </Link>
          </nav>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-5 py-8">{children}</main>
    </div>
  );
}
