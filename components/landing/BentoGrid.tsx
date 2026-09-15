import Link from "next/link";
import {
  type LucideIcon,
  FileText,
  Glasses,
  GraduationCap,
  Lamp,
  ScanLine,
  Swords,
  Volume2,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { MagicCard } from "@/components/ui/magic-card";
import { Reveal } from "./Reveal";

type BentoItem = {
  icon: LucideIcon;
  title: string;
  description: string;
  /** Quando presente, o cartão inteiro vira link para a rota e mostra "Abrir →". */
  href?: string;
  /** Rótulo mono no canto superior direito (ex.: "VR"). */
  tag?: string;
  /** Cartão em destaque: tipografia e respiro maiores. */
  featured?: boolean;
  /** Classes de span da célula do grid (ocupação assimétrica). */
  span?: string;
};

// Modos e recursos extras da plataforma — NÃO inclui Catálogo (seção própria).
// Ordem e spans compõem o bento: Sala em destaque (largo) abre a grade e
// Histórico fecha (largo), preenchendo 3×3 no lg sem buracos.
const cards: BentoItem[] = [
  {
    icon: Lamp,
    title: "Sala de estudos",
    href: "/sala",
    tag: "VR",
    featured: true,
    span: "sm:col-span-2 lg:col-span-2",
    description:
      "Quarto 3D com flashcards, rádio e tutor de IA; estuda no desktop ou no headset.",
  },
  {
    icon: ScanLine,
    title: "Clínica",
    href: "/clinica",
    tag: "VR",
    description:
      "Casos em 3D a partir de exames reais anonimizados. Visualização educacional, não substitui laudo.",
  },
  {
    icon: Swords,
    title: "Duelo 1×1",
    href: "/duelo",
    description:
      "Quiz de anatomia contra bot em três dificuldades ou 1×1 online, cada um no seu óculos, pelo código da sala.",
  },
  {
    icon: Glasses,
    title: "Arena VR",
    href: "/arena",
    tag: "VR",
    description:
      "Desafio de anatomia imersivo em qualquer headset WebXR, direto do navegador.",
  },
  {
    icon: GraduationCap,
    title: "Modo quiz",
    href: "/quiz",
    description:
      "Teste-se identificando estruturas marcadas sobre os próprios modelos 3D.",
  },
  {
    icon: Volume2,
    title: "Narração em áudio",
    description:
      "Ouça a descrição de cada estrutura com a voz do navegador, em português.",
  },
  {
    icon: FileText,
    title: "Histórico e PDF",
    href: "/history",
    span: "lg:col-span-2",
    description:
      "Salve sessões com anotações, conversas e capturas e exporte um relatório pronto para revisar.",
  },
];

/**
 * Seção "E ainda" — bento assimétrico com os modos e recursos extras da
 * plataforma. Cada cartão usa <MagicCard> por dentro (spotlight no hover);
 * os que têm `href` são clicáveis por inteiro, com foco visível.
 */
export function BentoGrid() {
  return (
    <div className="grid auto-rows-[1fr] gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((card, i) => (
        <Reveal key={card.title} delay={i * 0.05} className={card.span}>
          <BentoCard {...card} />
        </Reveal>
      ))}
    </div>
  );
}

function BentoCard({ icon: Icon, title, description, href, tag, featured }: BentoItem) {
  const shell =
    "block h-full rounded-2xl border border-border bg-card shadow-sm";

  const content = (
    <MagicCard className={cn("h-full rounded-[inherit]", featured ? "p-6 sm:p-8" : "p-6")}>
      <div className="flex items-start justify-between gap-3">
        <span className="grid size-11 place-items-center rounded-xl bg-accent text-accent-foreground">
          <Icon className="size-5" aria-hidden />
        </span>
        {tag ? (
          <span className="font-mono text-[10px] uppercase tracking-wider text-primary/70">
            {tag}
          </span>
        ) : null}
      </div>
      <h3 className={cn("mt-4 font-semibold", featured ? "text-xl sm:text-2xl" : "text-lg")}>
        {title}
      </h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>
      {href ? (
        <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary">
          Abrir <span aria-hidden>→</span>
        </span>
      ) : null}
    </MagicCard>
  );

  if (!href) {
    return <article className={shell}>{content}</article>;
  }

  return (
    <Link
      href={href}
      className={cn(
        shell,
        "transition-colors hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
      )}
    >
      {content}
    </Link>
  );
}
