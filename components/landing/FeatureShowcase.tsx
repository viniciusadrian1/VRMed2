import Link from "next/link";
import {
  ArrowRight,
  type LucideIcon,
  Layers,
  Sparkles,
  SplitSquareHorizontal,
} from "lucide-react";
import { Reveal } from "./Reveal";
import { CompareMockup, TutorMockup, ViewerMockup } from "./mockups";
import { cn } from "@/lib/utils";

interface ShowcaseItem {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  description: string;
  bullets: string[];
  cta: { href: string; label: string };
  mockup: React.ReactNode;
}

const ITEMS: ShowcaseItem[] = [
  {
    icon: Layers,
    eyebrow: "Visualizador 3D",
    title: "Disseque sem bisturi.",
    description:
      "Gire, amplie e isole cada camada de um modelo anatômico. Clique numa estrutura e descubra na hora o que ela é — com pontos numerados sobre as principais estruturas.",
    bullets: [
      "Controle livre de câmera e manipulação direta",
      "Camadas com opacidade, cor e modo raio-X",
      "Identificação por clique e pontos numerados",
    ],
    cta: { href: "/viewer", label: "Abrir o visualizador" },
    mockup: <ViewerMockup />,
  },
  {
    icon: Sparkles,
    eyebrow: "Tutor de IA",
    title: "Uma dúvida, uma fonte confiável.",
    description:
      "Pergunte sobre a estrutura em foco e receba respostas curtas e diretas, fundamentadas nos tratados da graduação, nunca em achismos.",
    bullets: [
      "Contextualizado no órgão que você estuda",
      "Indica em qual tratado aprofundar",
      "Respostas avaliadas por especialistas",
    ],
    cta: { href: "/viewer", label: "Conversar com o tutor" },
    mockup: <TutorMockup />,
  },
  {
    icon: SplitSquareHorizontal,
    eyebrow: "Saudável × patológico",
    title: "Veja a doença, lado a lado.",
    description:
      "Compare a anatomia normal e a alterada com câmeras sincronizadas. Entenda visualmente o que a patologia transforma — como o fígado cirrótico ao lado do fígado saudável.",
    bullets: [
      "Câmeras espelhadas para comparação precisa",
      "Legendas com as diferenças anatômicas chave",
      "Fígado com par patológico real; coração e pulmão em preparação",
    ],
    cta: { href: "/compare", label: "Comparar modelos" },
    mockup: <CompareMockup />,
  },
];

/** Vitrine de funcionalidades em linhas alternadas (texto + mockup visual). */
export function FeatureShowcase() {
  return (
    <div className="flex flex-col gap-20 md:gap-28">
      {ITEMS.map((item, index) => {
        const reversed = index % 2 === 1;
        return (
          <div
            key={item.title}
            className="grid items-center gap-8 md:grid-cols-2 md:gap-14"
          >
            <Reveal className={cn(reversed && "md:order-2")}>
              <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium uppercase tracking-wider text-primary shadow-sm">
                <item.icon className="size-3.5" />
                {item.eyebrow}
              </span>
              <h3 className="mt-4 text-balance font-serif text-2xl font-medium tracking-tight md:text-3xl">
                {item.title}
              </h3>
              <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
                {item.description}
              </p>
              <ul className="mt-5 flex flex-col gap-2.5">
                {item.bullets.map((bullet) => (
                  <li key={bullet} className="flex items-start gap-2.5 text-sm">
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
            </Reveal>

            <Reveal
              delay={0.1}
              className={cn("min-w-0", reversed && "md:order-1")}
            >
              {item.mockup}
            </Reveal>
          </div>
        );
      })}
    </div>
  );
}
