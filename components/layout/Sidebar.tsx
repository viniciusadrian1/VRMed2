"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Box,
  GraduationCap,
  History,
  ScanLine,
  SplitSquareHorizontal,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/layout/Logo";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/viewer", label: "Visualizador", icon: Box },
  { href: "/compare", label: "Comparar", icon: SplitSquareHorizontal },
  { href: "/quiz", label: "Quiz", icon: GraduationCap },
  { href: "/clinica", label: "Clínica", icon: ScanLine },
  { href: "/history", label: "Histórico", icon: History },
];

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Trilho de navegação vertical (desktop). */
export function SideRail() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-[84px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex">
      <div className="flex h-16 items-center justify-center border-b border-sidebar-border">
        <Logo withText={false} />
      </div>
      <nav aria-label="Navegação principal" className="flex flex-col gap-1 p-2.5">
        {NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex flex-col items-center gap-1 rounded-lg px-2 py-2.5 text-[11px] font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
              )}
            >
              <item.icon className="size-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

/** Barra de navegação inferior (mobile). */
export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Navegação principal"
      className="flex shrink-0 items-stretch border-t border-sidebar-border bg-sidebar md:hidden"
    >
      {NAV_ITEMS.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition-colors",
              active ? "text-primary" : "text-muted-foreground",
            )}
          >
            <item.icon className="size-5" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
