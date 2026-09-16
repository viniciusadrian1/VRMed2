import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  Languages,
  type LucideIcon,
  MonitorSmartphone,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { BentoGrid } from "@/components/landing/BentoGrid";
import { CatalogExplorer } from "@/components/landing/CatalogExplorer";
import { HeroScene } from "@/components/landing/HeroScene";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { LandingHeader } from "@/components/landing/LandingHeader";
import { Marquee } from "@/components/landing/Marquee";
import { Reveal } from "@/components/landing/Reveal";
import { SectionIntro } from "@/components/landing/SectionIntro";
import { SourcesPanel } from "@/components/landing/SourcesPanel";
import { StickyShowcase, type ShowItem } from "@/components/landing/StickyShowcase";
import {
  CompareMockup,
  TutorMockup,
  ViewerMockup,
} from "@/components/landing/mockups";
import { Logo } from "@/components/layout/Logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CrosshairFrame } from "@/components/ui/crosshair-frame";
import { DotPattern } from "@/components/ui/dot-pattern";
import { NumberTicker } from "@/components/ui/number-ticker";
import { ScanBeam } from "@/components/ui/scan-beam";
import { WordReveal } from "@/components/ui/word-reveal";
import {
  ALL_MODELS,
  getComparableOrgans,
  ORGANS,
  REGIONS,
  SYSTEMS,
} from "@/lib/organs";

/* -------------------------------------------------------------------------- */
/* Dados estáticos da página                                                   */
/* -------------------------------------------------------------------------- */

const HERO_STATS: {
  icon: LucideIcon;
  label: string;
  value?: number;
  suffix?: string;
  text?: string;
}[] = [
  // Contado do catálogo: número escrito à mão ficava velho a cada modelo novo.
  { icon: Boxes, value: ALL_MODELS.length, label: "Modelos 3D" },
  { icon: Sparkles, text: "IA", label: "Tutor com fontes" },
  { icon: MonitorSmartphone, text: "VR", label: "No navegador" },
  { icon: Languages, value: 100, suffix: "%", label: "Em português" },
];

const SHOWCASE_ITEMS: ShowItem[] = [
  {
    indice: "01",
    eyebrow: "Visualizador 3D",
    titulo: "Disseque sem bisturi.",
    descricao:
      "Gire, amplie e isole cada camada de um modelo anatômico. Clique numa estrutura e descubra na hora o que ela é — com pontos numerados sobre as principais.",
    bullets: [
      "Controle livre de câmera e manipulação direta",
      "Camadas com opacidade, cor e modo raio-X",
      "Identificação por clique e pontos numerados",
    ],
    cta: { href: "/viewer", label: "Abrir o visualizador" },
    visual: <ViewerMockup />,
  },
  {
    indice: "02",
    eyebrow: "Tutor de IA",
    titulo: "Uma dúvida, uma fonte confiável.",
    descricao:
      "Pergunte sobre a estrutura em foco e receba respostas curtas e diretas, fundamentadas nos tratados da graduação, nunca em achismos.",
    bullets: [
      "Contextualizado no órgão que você estuda",
      "Indica em qual tratado aprofundar",
      "Avalie com 👍/👎 e alimente a validação da pesquisa",
    ],
    cta: { href: "/viewer", label: "Conversar com o tutor" },
    visual: <TutorMockup />,
  },
  {
    indice: "03",
    eyebrow: "Saudável × patológico",
    titulo: "Veja a doença, lado a lado.",
    descricao:
      "Compare a anatomia normal e a alterada com câmeras sincronizadas. Entenda visualmente o que a patologia transforma — como o fígado cirrótico ao lado do saudável.",
    bullets: [
      "Câmeras espelhadas para comparação precisa",
      "Legendas com as diferenças anatômicas chave",
      "Fígado e rim com par patológico real; coração em preparação",
    ],
    cta: { href: "/compare", label: "Comparar modelos" },
    visual: <CompareMockup />,
  },
];

const STEPS = [
  {
    title: "Escolha o que estudar",
    description:
      "Selecione um sistema, uma região ou um órgão no catálogo e abra-o no visualizador 3D.",
  },
  {
    title: "Explore livremente",
    description:
      "Gire, corte, isole camadas, ative o raio-X e clique para identificar cada estrutura.",
  },
  {
    title: "Aprofunde e revise",
    description:
      "Converse com o tutor de IA, teste-se no quiz e exporte a sessão em PDF para revisar depois.",
  },
];

const SOURCE_GROUPS: { label: string; items: string[] }[] = [
  {
    label: "Anatomia",
    items: [
      "Moore (Anatomia Orientada para a Clínica)",
      "Gray's Anatomy",
      "Netter",
      "Sobotta",
    ],
  },
  { label: "Fisiologia", items: ["Guyton & Hall"] },
  { label: "Patologia", items: ["Robbins"] },
];

const ALL_SOURCES = SOURCE_GROUPS.flatMap((group) => group.items);

const CATALOG_TIERS = [
  {
    label: "Sistemas",
    caption: "Corpo inteiro, organizado por sistema anatômico.",
    items: SYSTEMS.map((s) => s.name),
  },
  {
    label: "Regiões",
    caption: "Anatomia regional detalhada, com estruturas nomeadas.",
    items: REGIONS.map((r) => r.name),
  },
  {
    label: "Órgãos",
    caption: `Modelos individuais; ${getComparableOrgans().length} com par patológico.`,
    items: ORGANS.map((o) => o.name),
  },
];

/* -------------------------------------------------------------------------- */
/* Página                                                                      */
/* -------------------------------------------------------------------------- */

export default function LandingPage() {
  return (
    <div className="min-h-dvh">
      <LandingHeader />

      <main id="conteudo-principal">
        {/* ----------------------------- Hero ----------------------------- */}
        <section className="vrmed-radial relative overflow-hidden">
          <DotPattern className="text-primary/[0.07] [mask-image:radial-gradient(78%_65%_at_50%_22%,#000,transparent)]" />

          <div className="relative mx-auto flex min-h-[calc(100dvh-4rem)] max-w-6xl flex-col justify-center gap-14 px-5 py-16 md:px-8 lg:grid lg:grid-cols-[1.05fr_1fr] lg:items-center lg:gap-14 lg:py-20">
            <Reveal>
              <p className="mb-6 flex items-center gap-2.5 font-mono text-xs uppercase tracking-[0.28em] text-primary">
                <span className="relative flex size-2" aria-hidden>
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary/60" />
                  <span className="relative inline-flex size-2 rounded-full bg-primary" />
                </span>
                Atlas 3D · VR · pt-BR
              </p>

              <Badge variant="accent" className="mb-5">
                <Sparkles className="size-3" />
                Projeto de Iniciação Científica
              </Badge>

              <WordReveal
                as="h1"
                text="A anatomia humana, em 3D e ao seu alcance."
                className="text-balance font-serif text-[2.9rem] font-medium leading-[0.98] tracking-tight sm:text-6xl lg:text-7xl"
              />

              <p className="mt-6 max-w-md text-pretty text-base text-muted-foreground md:text-lg">
                O VRmed reúne modelos 3D interativos, cortes anatômicos,
                realidade virtual e um tutor de IA — feito para estudantes de
                medicina e das áreas da saúde.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Button asChild size="lg" className="shadow-md">
                  <Link href="/viewer">
                    Iniciar estudo
                    <ArrowRight />
                  </Link>
                </Button>
                <Button asChild size="lg" variant="outline">
                  <Link href="#recursos">Ver recursos</Link>
                </Button>
              </div>

              <p className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
                <ShieldCheck className="size-4 shrink-0 text-primary" />
                Respostas do tutor fundamentadas apenas em fontes médicas
                confiáveis.
              </p>
            </Reveal>

            <Reveal delay={0.15}>
              <div className="relative">
                <div
                  className="absolute inset-0 -z-10 bg-[radial-gradient(closest-side,color-mix(in_srgb,var(--primary)_20%,transparent),transparent)] blur-2xl"
                  aria-hidden
                />
                <CrosshairFrame
                  coord="arraste para girar"
                  className="h-[400px] w-full overflow-hidden rounded-3xl border border-border bg-card/30 shadow-2xl shadow-primary/10 backdrop-blur-sm md:h-[560px]"
                >
                  <HeroScene />
                  <ScanBeam />
                </CrosshairFrame>

                <div className="absolute -right-2 top-8 hidden rounded-xl border border-border bg-card px-3 py-2 shadow-lg md:block">
                  <p className="flex items-center gap-1.5 text-xs font-semibold text-primary">
                    <Sparkles className="size-3.5" />
                    Tutor de IA
                  </p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    Pergunte sobre a estrutura
                  </p>
                </div>
              </div>
            </Reveal>
          </div>

          {/* Faixa de estatísticas */}
          <div className="relative mx-auto max-w-6xl px-5 pb-16 pt-8 md:px-8">
            <Reveal>
              <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-4">
                {HERO_STATS.map((stat) => (
                  <div
                    key={stat.label}
                    className="flex flex-col items-center gap-1 bg-card px-4 py-6 text-center"
                  >
                    <stat.icon className="mb-1 size-5 text-primary" />
                    <dt className="order-2 text-xs text-muted-foreground">
                      {stat.label}
                    </dt>
                    <dd className="order-1 font-serif text-3xl font-medium md:text-4xl">
                      {stat.text ?? (
                        <NumberTicker value={stat.value ?? 0} suffix={stat.suffix} />
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            </Reveal>
          </div>
        </section>

        {/* --------------------------- Faixa de fontes -------------------- */}
        <section className="border-y border-border bg-card py-8">
          <div className="mx-auto max-w-6xl px-5 md:px-8">
            <p className="mb-5 text-center font-mono text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
              Fundamentado nos tratados da graduação
            </p>
            <Marquee items={ALL_SOURCES} label="Fontes médicas de referência" />
          </div>
        </section>

        {/* ----------------------------- Recursos ------------------------- */}
        <section
          id="recursos"
          className="mx-auto max-w-6xl scroll-mt-20 px-5 pt-20 md:px-8 md:pt-28"
        >
          <SectionIntro
            index="01"
            eyebrow="Recursos"
            title="Estude com a profundidade de uma dissecação."
            description="Cada ferramenta transforma a anatomia plana do papel numa experiência tridimensional, interativa e fundamentada. Role para percorrer as três principais."
            className="mb-4"
          />
          <StickyShowcase items={SHOWCASE_ITEMS} />
        </section>

        {/* ----------------------------- Catálogo ------------------------- */}
        <section className="border-y border-border bg-card">
          <div
            id="catalogo"
            className="mx-auto max-w-6xl scroll-mt-20 px-5 py-20 md:px-8 md:py-28"
          >
            <SectionIntro
              index="02"
              eyebrow="Catálogo"
              title="Três níveis de detalhe, um corpo inteiro para explorar."
              description="Comece pelo sistema completo, aprofunde numa região e termine no órgão — todos no mesmo ambiente."
              className="mb-10"
            />
            <Reveal>
              <CatalogExplorer tiers={CATALOG_TIERS} />
            </Reveal>
            <Reveal className="mt-10 flex justify-center">
              <Button asChild size="lg">
                <Link href="/viewer">
                  Explorar o catálogo
                  <ArrowRight />
                </Link>
              </Button>
            </Reveal>
          </div>
        </section>

        {/* ------------------------ Bento de capacidades ------------------ */}
        <section className="mx-auto max-w-6xl px-5 py-20 md:px-8 md:py-28">
          <SectionIntro
            index="03"
            eyebrow="E ainda"
            title="Tudo o que um plantão de estudos precisa."
            className="mb-12"
          />
          <BentoGrid />
        </section>

        {/* -------------------------- Como funciona ----------------------- */}
        <section className="border-y border-border bg-card">
          <div className="mx-auto max-w-6xl px-5 py-20 md:px-8 md:py-28">
            <SectionIntro
              index="04"
              eyebrow="Como funciona"
              title="Três passos, do primeiro acesso ao domínio do conteúdo."
              className="mb-12"
            />
            <HowItWorks
              steps={STEPS.map((step) => ({
                titulo: step.title,
                descricao: step.description,
              }))}
            />
          </div>
        </section>

        {/* ------------------------------ Fontes -------------------------- */}
        <section
          id="fontes"
          className="mx-auto max-w-6xl scroll-mt-20 px-5 py-20 md:px-8 md:py-28"
        >
          <SectionIntro
            index="05"
            eyebrow="Fontes"
            title="Confiança que você pode citar."
            description="O tutor de IA é instruído a ensinar só o que está consolidado nos tratados usados na graduação e a indicar, no fim da resposta, onde aprofundar:"
            className="mb-12"
          />
          <SourcesPanel groups={SOURCE_GROUPS} />
        </section>

        {/* --------------------------- Pesquisa --------------------------- */}
        <section
          id="pesquisa"
          className="mx-auto max-w-6xl scroll-mt-20 px-5 pb-20 md:px-8 md:pb-28"
        >
          <Reveal>
            <div className="relative overflow-hidden rounded-3xl border border-border bg-card shadow-sm">
              <div className="grid gap-8 p-8 md:grid-cols-[1.4fr_1fr] md:p-12">
                <div>
                  <p className="font-mono text-xs font-medium uppercase tracking-[0.2em] text-primary">
                    Para pesquisadores
                  </p>
                  <h2 className="mt-3 font-serif text-3xl font-medium tracking-tight md:text-4xl">
                    Construído como pesquisa, aberto à pesquisa.
                  </h2>
                  <p className="mt-4 text-pretty text-sm leading-relaxed text-muted-foreground md:text-base">
                    O VRmed é desenvolvido como projeto de Iniciação Científica.
                    Com consentimento explícito, a aplicação coleta dados de uso{" "}
                    <strong className="font-medium text-foreground">
                      anônimos e sem informação pessoal
                    </strong>{" "}
                    — quais órgãos são mais estudados, quais ferramentas são mais
                    usadas e como o tutor de IA é avaliado — para gerar
                    evidências sobre o aprendizado imersivo.
                  </p>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <Button asChild variant="outline">
                      <Link href="/privacidade">Política de privacidade</Link>
                    </Button>
                    <Button asChild>
                      <Link href="/viewer">
                        Explorar a plataforma
                        <ArrowRight />
                      </Link>
                    </Button>
                  </div>
                </div>
                <ul className="flex flex-col justify-center gap-4 rounded-2xl bg-accent/50 p-6 text-sm">
                  {[
                    "Consentimento solicitado antes de qualquer coleta.",
                    "Dados anônimos, sem identificação dos estudantes.",
                    "Respostas avaliadas pelos estudantes são revisadas pela equipe da pesquisa.",
                  ].map((point) => (
                    <li key={point} className="flex gap-3">
                      <ShieldCheck className="size-5 shrink-0 text-primary" />
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Reveal>
        </section>

        {/* ------------------------------ CTA final ----------------------- */}
        <section className="px-5 pb-20 md:px-8 md:pb-28">
          <Reveal className="mx-auto max-w-6xl">
            <div className="vrmed-radial relative overflow-hidden rounded-3xl border border-border px-6 py-20 text-center md:py-24">
              <DotPattern className="text-primary/[0.09] [mask-image:radial-gradient(60%_80%_at_50%_50%,#000,transparent)]" />
              <div className="relative mx-auto max-w-xl">
                <h2 className="text-balance font-serif text-3xl font-medium tracking-tight md:text-5xl">
                  Sua próxima aula de anatomia começa aqui.
                </h2>
                <p className="mt-4 text-pretty text-muted-foreground">
                  Sem instalar nada, sem cadastro. Abra um modelo e comece a
                  explorar agora mesmo.
                </p>
                <div className="mt-8 flex flex-wrap justify-center gap-3">
                  <Button asChild size="lg" className="shadow-md">
                    <Link href="/viewer">
                      Iniciar estudo
                      <ArrowRight />
                    </Link>
                  </Button>
                  <Button asChild size="lg" variant="outline">
                    <Link href="/quiz">Testar no quiz</Link>
                  </Button>
                </div>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      {/* ------------------------------ Rodapé --------------------------- */}
      <footer className="border-t border-border bg-card">
        <div className="mx-auto grid max-w-6xl gap-10 px-5 py-12 md:grid-cols-[1.5fr_1fr_1fr] md:px-8">
          <div className="flex flex-col gap-3">
            <Logo />
            <p className="max-w-xs text-sm text-muted-foreground">
              Estudo de anatomia em 3D e realidade virtual. Projeto de Iniciação
              Científica em educação médica.
            </p>
          </div>
          <nav className="flex flex-col gap-2.5 text-sm">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Plataforma
            </p>
            <Link href="/viewer" className="text-muted-foreground hover:text-foreground">
              Visualizador
            </Link>
            <Link href="/compare" className="text-muted-foreground hover:text-foreground">
              Comparar
            </Link>
            <Link href="/quiz" className="text-muted-foreground hover:text-foreground">
              Quiz
            </Link>
            <Link href="/sala" className="text-muted-foreground hover:text-foreground">
              Sala de estudos
            </Link>
            <Link href="/duelo" className="text-muted-foreground hover:text-foreground">
              Duelo 1×1
            </Link>
            <Link href="/clinica" className="text-muted-foreground hover:text-foreground">
              Clínica
            </Link>
            <Link href="/arena" className="text-muted-foreground hover:text-foreground">
              Arena VR
            </Link>
            <Link href="/history" className="text-muted-foreground hover:text-foreground">
              Histórico
            </Link>
          </nav>
          <nav className="flex flex-col gap-2.5 text-sm">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Projeto
            </p>
            <Link href="#pesquisa" className="text-muted-foreground hover:text-foreground">
              Pesquisa
            </Link>
            <Link href="#fontes" className="text-muted-foreground hover:text-foreground">
              Fontes
            </Link>
            <Link href="/privacidade" className="text-muted-foreground hover:text-foreground">
              Privacidade
            </Link>
          </nav>
        </div>
        <div className="border-t border-border">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-5 py-5 text-xs text-muted-foreground md:flex-row md:px-8">
            <p>© {new Date().getFullYear()} VRmed · Iniciação Científica</p>
            <p className="text-center md:text-right">Conteúdo educacional para estudo de anatomia. Não substitui livros-texto, aulas, laudos nem avaliação médica.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
