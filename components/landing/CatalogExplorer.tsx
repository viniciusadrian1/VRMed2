"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface CatalogTier {
  label: string;
  caption: string;
  items: string[];
}

/**
 * Explorador de catálogo em abas (segmented control). O indicador do tab ativo
 * desliza com layout animation; o painel troca com fade/slide sutil. Respeita
 * prefers-reduced-motion (troca seca, sem animação de layout). Navegação por
 * teclado com roving tabindex (setas, Home/End).
 */
export function CatalogExplorer({ tiers }: { tiers: CatalogTier[] }) {
  const [active, setActive] = useState(0);
  const reduceMotion = useReducedMotion();
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const activeTier = tiers[active];
  if (!activeTier) return null;

  function handleKeyDown(event: React.KeyboardEvent<HTMLButtonElement>) {
    let next = active;
    if (event.key === "ArrowRight") next = (active + 1) % tiers.length;
    else if (event.key === "ArrowLeft")
      next = (active - 1 + tiers.length) % tiers.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tiers.length - 1;
    else return;
    event.preventDefault();
    setActive(next);
    tabRefs.current[next]?.focus();
  }

  const count = activeTier.items.length;
  const body = (
    <>
      <p className="text-pretty leading-relaxed text-muted-foreground">
        {activeTier.caption}
      </p>
      <p className="mt-3 font-mono text-xs uppercase tracking-wider text-muted-foreground">
        {String(count).padStart(2, "0")} {count === 1 ? "modelo" : "modelos"}
      </p>
      <ul className="mt-4 flex flex-wrap gap-2">
        {activeTier.items.map((item) => (
          <li
            key={item}
            className="rounded-lg border border-border bg-background px-2.5 py-1 text-xs text-foreground/90"
          >
            {item}
          </li>
        ))}
      </ul>
    </>
  );

  return (
    <div>
      <div
        role="tablist"
        aria-label="Camadas do catálogo"
        className="inline-flex max-w-full gap-1 overflow-x-auto rounded-xl border border-border bg-muted/50 p-1"
      >
        {tiers.map((tier, i) => {
          const selected = i === active;
          return (
            <button
              key={tier.label}
              ref={(el) => {
                tabRefs.current[i] = el;
              }}
              type="button"
              role="tab"
              id={`cat-tab-${i}`}
              aria-selected={selected}
              aria-controls="cat-panel"
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(i)}
              onKeyDown={handleKeyDown}
              className={cn(
                "relative shrink-0 whitespace-nowrap rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50",
                selected
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground",
                // Sob reduced-motion o fundo do ativo vem por classe (sem layout animation).
                selected && reduceMotion && "bg-card shadow-sm",
              )}
            >
              {selected && !reduceMotion && (
                <motion.span
                  layoutId="cat-indicator"
                  aria-hidden
                  className="absolute inset-0 rounded-lg bg-card shadow-sm"
                  transition={{ type: "spring", stiffness: 500, damping: 40 }}
                />
              )}
              <span className="relative z-10">{tier.label}</span>
            </button>
          );
        })}
      </div>

      <div
        id="cat-panel"
        role="tabpanel"
        aria-labelledby={`cat-tab-${active}`}
        className="mt-4 rounded-2xl border border-border bg-card p-6 md:p-8"
      >
        {reduceMotion ? (
          body
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={active}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
            >
              {body}
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
