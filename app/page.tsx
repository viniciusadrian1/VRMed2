import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  Languages,
  MonitorSmartphone,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { BentoGrid } from "@/components/landing/BentoGrid";
import { FeatureShowcase } from "@/components/landing/FeatureShowcase";
import { HeroScene } from "@/components/landing/HeroScene";
import { LandingHeader } from "@/components/landing/LandingHeader";
import { Marquee } from "@/components/landing/Marquee";
import { Reveal } from "@/components/landing/Reveal";
import { SectionHeading } from "@/components/landing/SectionHeading";
import { Logo } from "@/components/layout/Logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ORGANS, REGIONS, SYSTEMS } from "@/lib/organs";

/* -------------------------------------------------------------------------- */
/* Dados estáticos da página                                                   */
/* -------------------------------------------------------------------------- */

const HERO_STATS = [
  { icon: Boxes, value: "18", label: "Modelos 3D" },
  { icon: Sparkles, value: "IA", label: "Tutor com fontes" },
  { icon: MonitorSmartphone, value: "VR", label: "No navegador" },
  { icon: Languages, value: "100%", label: "Em português" },
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
    label: "Bases e diretrizes",
    items: ["PubMed", "Cochrane Library", "UpToDate", "AMBOSS"],
  },
  {
    label: "Periódicos científicos",
    items: ["NEJM", "JAMA", "The Lancet", "BMJ"],
  },
  {
    label: "Instituições de referência",
    items: ["Mayo Clinic", "Cleveland Clinic", "NIH / MedlinePlus", "WHO"],
  },
  {
    label: "Atlas de anatomia",
    items: ["Gray's Anatomy", "Netter Atlas", "Sobotta", "Moore"],
  },
];

const ALL_SOURCES = SOURCE_GROUPS.flatMap((group) => group.items);

const CATALOG_TIERS = [
  {
    label: "Sistemas",
    caption: "Corpo inteiro, por sistema anatômico",
    items: SYSTEMS.map((s) => s.name),
  },
  {
    label: "Regiões",
    caption: "Anatomia regional detalhada e nomeada",
    items: REGIONS.map((r) => r.name),
  },
  {
    label: "Órgãos",
    caption: "Modelos individuais, com par patológico",
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
          <div
            className="vrmed-grid pointer-events-none absolute inset-0 opacity-60 [mask-image:radial-gradient(70%_60%_at_50%_30%,#000,transparent)]"
            aria-hidden
          />
          <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-5 py-16 md:grid-cols-2 md:gap-10 md:px-8 md:py-24">
            <Reveal>
              <Badge variant="accent" className="mb-5">
                <Sparkles className="size-3" />
                Projeto de Iniciação Científica
              </Badge>
              <h1 className="text-balance font-serif text-[2.6rem] font-medium leading-[1.05] tracking-tight md:text-6xl">
                A anatomia humana, em 3D e ao seu alcance.
              </h1>
              <p className="mt-5 max-w-md text-pretty text-base text-muted-foreground md:text-lg">
                O VRmed reúne modelos 3D interativos, cortes anatômicos,
                realidade virtual e um tutor de IA — feito para estudantes de
                medicina e das áreas da saúde.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
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
                {/* Halo suave atrás do modelo */}
                <div
                  className="absolute inset-0 -z-10 bg-[radial-gradient(closest-side,color-mix(in_srgb,var(--primary)_18%,transparent),transparent)] blur-2xl"
                  aria-hidden
                />
                <div className="relative h-[340px] w-full overflow-hidden rounded-3xl border border-border bg-card/40 shadow-2xl shadow-primary/10 backdrop-blur-sm md:h-[480px]">
                  <HeroScene />
                  {/* Etiqueta flutuante: identificação por clique */}
                  <span className="absolute bottom-4 left-4 flex items-center gap-1.5 rounded-full border border-border bg-card/90 px-3 py-1.5 text-xs font-medium shadow-md backdrop-blur">
                    <span className="size-2 rounded-full bg-primary" />
                    Corte transversal · 4 camadas
                  </span>
                </div>
                {/* Chip flutuante: tutor de IA */}
                <div className="absolute -right-2 top-6 hidden rounded-xl border border-border bg-card px-3 py-2 shadow-lg md:block">
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
          <div className="relative mx-auto max-w-6xl px-5 pb-14 md:px-8">
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
                    <dd className="order-1 font-serif text-2xl font-medium md:text-3xl">
                      {stat.value}
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
            <p className="mb-5 text-center text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Fundamentado em referências médicas reconhecidas
            </p>
            <Marquee items={ALL_SOURCES} label="Fontes médicas de referência" />
          </div>
        </section>

        {/* ----------------------------- Recursos ------------------------- */}
        <section
          id="recursos"
          className="mx-auto max-w-6xl scroll-mt-20 px-5 py-20 md:px-8 md:py-28"
        >
          <SectionHeading
            eyebrow="Recursos"
            title="Estude com a profundidade de uma dissecação."
            description="Cada ferramenta foi pensada para transformar a anatomia plana do papel numa experiência tridimensional, interativa e fundamentada."
            className="mb-16"
          />
          <FeatureShowcase />
        </section>

        {/* ------------------------ Bento de capacidades ------------------ */}
        <section className="border-y border-border bg-card">
          <div className="mx-auto max-w-6xl px-5 py-20 md:px-8 md:py-28">
            <SectionHeading
              eyebrow="E ainda"
              title="Tudo o que um plantão de estudos precisa."
              className="mb-12"
            />
            <BentoGrid />
          </div>
        </section>

        {/* ----------------------------- Catálogo ------------------------- */}
        <section
          id="catalogo"
          className="mx-auto max-w-6xl scroll-mt-20 px-5 py-20 md:px-8 md:py-28"
        >
          <SectionHeading
            eyebrow="Catálogo"
            title="Três níveis de detalhe, um corpo inteiro para explorar."
            description="Comece pelo sistema completo, aprofunde numa região e termine no órgão — todos no mesmo ambiente."
            className="mb-12"
          />
          <div className="grid gap-5 md:grid-cols-3">
            {CATALOG_TIERS.map((tier, index) => (
              <Reveal key={tier.label} delay={index * 0.08}>
                <div className="flex h-full flex-col rounded-2xl border border-border bg-card p-6 shadow-sm">
                  <div className="flex items-baseline justify-between">
                    <h3 className="font-serif text-xl font-medium">
                      {tier.label}
                    </h3>
                    <span className="text-sm font-semibold text-primary">
                      {tier.items.length}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {tier.caption}
                  </p>
                  <ul className="mt-4 flex flex-wrap gap-2">
                    {tier.items.map((item) => (
                      <li
                        key={item}
                        className="rounded-lg border border-border bg-background px-2.5 py-1 text-xs font-medium"
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal className="mt-10 flex justify-center">
            <Button asChild size="lg">
              <Link href="/viewer">
                Explorar o catálogo
                <ArrowRight />
              </Link>
            </Button>
          </Reveal>
        </section>

        {/* -------------------------- Como funciona ----------------------- */}
        <section className="border-y border-border bg-card">
          <div className="mx-auto max-w-6xl px-5 py-20 md:px-8 md:py-28">
            <SectionHeading
              eyebrow="Como funciona"
              title="Três passos, do primeiro acesso ao domínio do conteúdo."
              className="mb-12"
            />
            <ol className="grid gap-8 md:grid-cols-3">
              {STEPS.map((step, index) => (
                <Reveal key={step.title} delay={index * 0.1}>
                  <li className="relative flex flex-col gap-3">
                    <span className="grid size-11 place-items-center rounded-full bg-primary font-serif text-lg text-primary-foreground shadow-sm">
                      {index + 1}
                    </span>
                    <h3 className="text-lg font-semibold">{step.title}</h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {step.description}
                    </p>
                  </li>
                </Reveal>
              ))}
            </ol>
          </div>
        </section>

        {/* ------------------------------ Fontes -------------------------- */}
        <section
          id="fontes"
          className="mx-auto max-w-6xl scroll-mt-20 px-5 py-20 md:px-8 md:py-28"
        >
          <SectionHeading
            eyebrow="Fontes"
            title="Confiança que você pode citar."
            description="O tutor de IA é instruído a responder citando exclusivamente fontes médicas reconhecidas. Estas são as referências utilizadas:"
            className="mb-12"
          />
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {SOURCE_GROUPS.map((group, index) => (
              <Reveal key={group.label} delay={(index % 4) * 0.07}>
                <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                  {group.label}
                </h3>
                <ul className="flex flex-col gap-2">
                  {group.items.map((item) => (
                    <li
                      key={item}
                      className="rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium"
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </Reveal>
            ))}
          </div>
        </section>

        {/* --------------------------- Pesquisa --------------------------- */}
        <section
          id="pesquisa"
          className="mx-auto max-w-6xl scroll-mt-20 px-5 pb-20 md:px-8 md:pb-28"
        >
          <Reveal>
            <div className="overflow-hidden rounded-3xl border border-border bg-card shadow-sm">
              <div className="grid gap-8 p-8 md:grid-cols-[1.4fr_1fr] md:p-12">
                <div>
                  <p className="text-sm font-medium uppercase tracking-[0.14em] text-primary">
                    Para pesquisadores
                  </p>
                  <h2 className="mt-3 font-serif text-3xl font-medium tracking-tight">
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
                    "Avaliação das respostas da IA por especialistas.",
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
            <div className="vrmed-radial relative overflow-hidden rounded-3xl border border-border px-6 py-16 text-center md:py-20">
              <div
                className="vrmed-grid pointer-events-none absolute inset-0 opacity-50 [mask-image:radial-gradient(60%_80%_at_50%_50%,#000,transparent)]"
                aria-hidden
              />
              <div className="relative mx-auto max-w-xl">
                <h2 className="text-balance font-serif text-3xl font-medium tracking-tight md:text-4xl">
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
            <p>Feito para estudantes da área da saúde.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
