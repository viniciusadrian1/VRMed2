import Link from "next/link";
import {
  ArrowRight,
  Box,
  Glasses,
  GraduationCap,
  Scissors,
  ShieldCheck,
  Sparkles,
  SplitSquareHorizontal,
  type LucideIcon,
} from "lucide-react";
import { HeroScene } from "@/components/landing/HeroScene";
import { LandingHeader } from "@/components/landing/LandingHeader";
import { Reveal } from "@/components/landing/Reveal";
import { Logo } from "@/components/layout/Logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface Feature {
  icon: LucideIcon;
  title: string;
  description: string;
}

const FEATURES: Feature[] = [
  {
    icon: Box,
    title: "Visualização 3D",
    description:
      "Gire, amplie e inspecione modelos anatômicos com controles precisos de câmera e manipulação direta.",
  },
  {
    icon: Scissors,
    title: "Cortes anatômicos",
    description:
      "Planos axial, sagital e coronal independentes revelam estruturas internas com superfícies de corte realistas.",
  },
  {
    icon: SplitSquareHorizontal,
    title: "Modo comparação",
    description:
      "Confronte anatomia saudável e patológica lado a lado, com câmeras sincronizadas.",
  },
  {
    icon: Sparkles,
    title: "Tutor de IA",
    description:
      "Tire dúvidas com um assistente que responde citando apenas fontes médicas reconhecidas.",
  },
  {
    icon: Glasses,
    title: "Suporte a VR",
    description:
      "Entre em imersão total com qualquer headset compatível com WebXR, direto do navegador.",
  },
  {
    icon: GraduationCap,
    title: "Modo quiz",
    description:
      "Teste seu conhecimento identificando estruturas marcadas diretamente sobre os modelos.",
  },
];

const STEPS = [
  {
    title: "Escolha o que estudar",
    description:
      "Selecione um órgão no catálogo e abra-o no visualizador 3D interativo.",
  },
  {
    title: "Explore livremente",
    description:
      "Gire, corte, isole camadas e ative o modo raio-X para revelar cada estrutura.",
  },
  {
    title: "Aprofunde o aprendizado",
    description:
      "Converse com o tutor de IA, teste-se no quiz e exporte a sessão em PDF.",
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

export default function LandingPage() {
  return (
    <div className="min-h-dvh">
      <LandingHeader />

      {/* ----------------------------- Hero ----------------------------- */}
      <section className="vrmed-radial relative overflow-hidden">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-5 py-16 md:grid-cols-2 md:gap-8 md:px-8 md:py-24">
          <Reveal>
            <Badge variant="accent" className="mb-5">
              <Sparkles className="size-3" />
              Projeto de Iniciação Científica
            </Badge>
            <h1 className="font-serif text-4xl font-medium leading-[1.08] tracking-tight md:text-6xl">
              A anatomia humana, em três dimensões e ao seu alcance.
            </h1>
            <p className="mt-5 max-w-md text-base text-muted-foreground md:text-lg">
              O VRmed reúne modelos 3D interativos, cortes anatômicos, realidade
              virtual e um tutor de IA — pensado para estudantes de medicina e
              das áreas da saúde.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link href="/viewer">
                  Iniciar estudo
                  <ArrowRight />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="#como-funciona">Como funciona</Link>
              </Button>
            </div>
            <p className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
              <ShieldCheck className="size-4 text-primary" />
              Respostas do tutor fundamentadas apenas em fontes médicas
              confiáveis.
            </p>
          </Reveal>

          <Reveal delay={0.15}>
            <div className="h-[340px] w-full md:h-[480px]">
              <HeroScene />
            </div>
          </Reveal>
        </div>
      </section>

      {/* -------------------------- Como funciona ------------------------ */}
      <section id="como-funciona" className="border-y border-border bg-card">
        <div className="mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-20">
          <Reveal className="mb-10 max-w-xl">
            <p className="text-sm font-medium uppercase tracking-wider text-primary">
              Como funciona
            </p>
            <h2 className="mt-2 font-serif text-3xl font-medium tracking-tight md:text-4xl">
              Três passos, do primeiro acesso ao domínio do conteúdo.
            </h2>
          </Reveal>
          <div className="grid gap-6 md:grid-cols-3">
            {STEPS.map((step, index) => (
              <Reveal key={step.title} delay={index * 0.1}>
                <div className="flex flex-col gap-3">
                  <span className="grid size-10 place-items-center rounded-full bg-primary font-serif text-lg text-primary-foreground">
                    {index + 1}
                  </span>
                  <h3 className="text-lg font-semibold">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {step.description}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ----------------------------- Recursos -------------------------- */}
      <section
        id="recursos"
        className="mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24"
      >
        <Reveal className="mb-12 max-w-xl">
          <p className="text-sm font-medium uppercase tracking-wider text-primary">
            Recursos
          </p>
          <h2 className="mt-2 font-serif text-3xl font-medium tracking-tight md:text-4xl">
            Ferramentas para estudar com a profundidade de uma dissecação.
          </h2>
        </Reveal>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, index) => (
            <Reveal key={feature.title} delay={(index % 3) * 0.08}>
              <Card className="h-full p-6 transition-shadow hover:shadow-md">
                <span className="grid size-11 place-items-center rounded-xl bg-accent text-accent-foreground">
                  <feature.icon className="size-5" />
                </span>
                <h3 className="mt-4 text-lg font-semibold">{feature.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  {feature.description}
                </p>
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ------------------------------ Fontes --------------------------- */}
      <section id="fontes" className="border-y border-border bg-card">
        <div className="mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24">
          <Reveal className="mb-12 max-w-xl">
            <p className="text-sm font-medium uppercase tracking-wider text-primary">
              Fontes
            </p>
            <h2 className="mt-2 font-serif text-3xl font-medium tracking-tight md:text-4xl">
              Fundamentado em referências que você pode confiar.
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              O tutor de IA é instruído a responder citando exclusivamente
              fontes médicas reconhecidas. Estas são as referências utilizadas:
            </p>
          </Reveal>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {SOURCE_GROUPS.map((group, index) => (
              <Reveal key={group.label} delay={(index % 4) * 0.07}>
                <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                  {group.label}
                </h3>
                <ul className="flex flex-col gap-2">
                  {group.items.map((item) => (
                    <li
                      key={item}
                      className="rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium"
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* --------------------------- Pesquisa ---------------------------- */}
      <section id="sobre" className="mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24">
        <Reveal>
          <Card className="overflow-hidden">
            <div className="grid gap-8 p-8 md:grid-cols-[1.4fr_1fr] md:p-12">
              <div>
                <p className="text-sm font-medium uppercase tracking-wider text-primary">
                  Para pesquisadores
                </p>
                <h2 className="mt-2 font-serif text-3xl font-medium tracking-tight">
                  Construído como pesquisa, aberto à pesquisa.
                </h2>
                <p className="mt-4 text-sm text-muted-foreground md:text-base">
                  O VRmed é desenvolvido como projeto de Iniciação Científica.
                  Com consentimento explícito, a aplicação coleta dados de uso{" "}
                  <strong className="font-medium text-foreground">
                    anônimos e sem informação pessoal
                  </strong>{" "}
                  — quais órgãos são mais estudados, quais ferramentas são mais
                  usadas e como o tutor de IA é avaliado — para gerar evidências
                  quantitativas e qualitativas sobre o aprendizado imersivo.
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
              <ul className="flex flex-col justify-center gap-4 rounded-xl bg-accent/50 p-6 text-sm">
                <li className="flex gap-3">
                  <ShieldCheck className="size-5 shrink-0 text-primary" />
                  <span>Consentimento solicitado antes de qualquer coleta.</span>
                </li>
                <li className="flex gap-3">
                  <ShieldCheck className="size-5 shrink-0 text-primary" />
                  <span>Dados anônimos, sem identificação dos estudantes.</span>
                </li>
                <li className="flex gap-3">
                  <ShieldCheck className="size-5 shrink-0 text-primary" />
                  <span>Avaliação das respostas da IA por especialistas.</span>
                </li>
              </ul>
            </div>
          </Card>
        </Reveal>
      </section>

      {/* ------------------------------ Rodapé --------------------------- */}
      <footer className="border-t border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-10 md:flex-row md:items-center md:px-8">
          <div className="flex flex-col gap-2">
            <Logo />
            <p className="text-sm text-muted-foreground">
              Estudo de anatomia em 3D e realidade virtual — Projeto de
              Iniciação Científica.
            </p>
          </div>
          <nav className="flex gap-4 text-sm text-muted-foreground md:ml-auto">
            <Link href="/viewer" className="hover:text-foreground">
              Visualizador
            </Link>
            <Link href="/quiz" className="hover:text-foreground">
              Quiz
            </Link>
            <Link href="/privacidade" className="hover:text-foreground">
              Privacidade
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
