"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface ShowItem {
  indice: string;
  eyebrow: string;
  titulo: string;
  descricao: string;
  bullets: string[];
  cta: { href: string; label: string };
  visual: React.ReactNode;
}

/** Marcador de bullet positivo — mesmo padrão do FeatureShowcase. */
function Check() {
  return (
    <span
      className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-accent text-accent-foreground"
      aria-hidden
    >
      <svg
        viewBox="0 0 12 12"
        className="size-3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M2.5 6.5 5 9l4.5-5.5" />
      </svg>
    </span>
  );
}

/** Bloco textual de um recurso (índice, eyebrow, título, descrição, bullets, CTA). */
function Texto({ item }: { item: ShowItem }) {
  return (
    <>
      <span className="font-mono text-xs tracking-widest text-muted-foreground">
        {item.indice}
      </span>
      <span className="mt-3 block text-xs font-medium uppercase tracking-wider text-primary">
        {item.eyebrow}
      </span>
      <h3 className="mt-2 text-balance font-serif text-3xl font-medium tracking-tight md:text-4xl">
        {item.titulo}
      </h3>
      <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
        {item.descricao}
      </p>
      <ul className="mt-5 flex flex-col gap-2.5">
        {item.bullets.map((bullet) => (
          <li key={bullet} className="flex items-start gap-2.5 text-sm">
            <Check />
            <span className="text-foreground/90">{bullet}</span>
          </li>
        ))}
      </ul>
      <Link
        href={item.cta.href}
        className="group mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary"
      >
        {item.cta.label}
        <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
      </Link>
    </>
  );
}

/** Envelope do visual: centralizado e limitado em largura. */
function Visual({ children }: { children: React.ReactNode }) {
  return <div className="grid w-full max-w-md place-items-center">{children}</div>;
}

export function StickyShowcase({ items }: { items: ShowItem[] }) {
  const reduzido = useReducedMotion();
  const [active, setActive] = useState(0);
  const blocosRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    // Movimento reduzido não renderiza a coluna sticky — nada para observar.
    if (reduzido) return;
    const blocos = blocosRef.current.filter(
      (b): b is HTMLDivElement => b !== null
    );
    if (blocos.length === 0) return;

    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting) continue;
          const i = Number((e.target as HTMLElement).dataset.index);
          if (!Number.isNaN(i)) setActive(i);
        }
      },
      // Ativa o bloco que cruza a faixa central da viewport.
      { rootMargin: "-45% 0px -45% 0px", threshold: 0 }
    );
    blocos.forEach((b) => obs.observe(b));
    return () => obs.disconnect();
  }, [reduzido, items.length]);

  // Layout empilhado (mobile e movimento reduzido): texto + visual em fluxo normal.
  const empilhado = (
    <div className="flex flex-col gap-16">
      {items.map((item) => (
        <div key={item.indice}>
          <Texto item={item} />
          <div className="mt-8 grid place-items-center">
            <Visual>{item.visual}</Visual>
          </div>
        </div>
      ))}
    </div>
  );

  if (reduzido) return empilhado;

  const total = String(items.length).padStart(2, "0");

  return (
    <>
      {/* Fallback empilhado abaixo de lg */}
      <div className="lg:hidden">{empilhado}</div>

      {/* Vitrine com scroll fixo em lg+ */}
      <div className="hidden lg:grid lg:grid-cols-2 lg:gap-16">
        {/* Coluna esquerda: blocos de texto empilhados */}
        <div>
          {items.map((item, i) => (
            <div
              key={item.indice}
              data-index={i}
              ref={(el) => {
                blocosRef.current[i] = el;
              }}
              className="flex min-h-[78vh] flex-col justify-center"
            >
              <Texto item={item} />
            </div>
          ))}
        </div>

        {/* Coluna direita: container sticky com todos os visuais sobrepostos */}
        <div className="relative">
          <div className="sticky top-24 flex h-[min(80vh,42rem)] flex-col">
            {/* Indicador de progresso em mono */}
            <div
              className="mb-4 font-mono text-xs tracking-widest text-muted-foreground"
              aria-hidden
            >
              {items[active]?.indice ?? "00"} / {total}
            </div>
            <div className="relative flex-1">
              {items.map((item, i) => (
                <div
                  key={item.indice}
                  aria-hidden={i !== active}
                  className={cn(
                    "absolute inset-0 grid place-items-center transition-opacity duration-500 ease-out",
                    i === active ? "opacity-100" : "pointer-events-none opacity-0"
                  )}
                >
                  <Visual>{item.visual}</Visual>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
