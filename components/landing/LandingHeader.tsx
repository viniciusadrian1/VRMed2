"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/layout/Logo";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Button } from "@/components/ui/button";

const ANCHORS = [
  { href: "#recursos", label: "Recursos" },
  { href: "#catalogo", label: "Catálogo" },
  { href: "#fontes", label: "Fontes" },
  { href: "#pesquisa", label: "Pesquisa" },
];

/** Cabeçalho fixo da landing page, com leve elevação ao rolar. */
export function LandingHeader() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 transition-colors duration-300",
        scrolled
          ? "border-b border-border bg-background/80 backdrop-blur-xl"
          : "border-b border-transparent",
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-5 md:px-8">
        <Logo />
        <nav className="ml-6 hidden items-center gap-0.5 md:flex">
          {ANCHORS.map((anchor) => (
            <Button key={anchor.href} variant="ghost" size="sm" asChild>
              <Link href={anchor.href}>{anchor.label}</Link>
            </Button>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <Button asChild size="sm" className="shadow-sm">
            <Link href="/viewer">
              Iniciar estudo
              <ArrowRight />
            </Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
