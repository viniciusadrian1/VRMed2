import Link from "next/link";
import {
  FileText,
  Glasses,
  GraduationCap,
  Lamp,
  MapPin,
  ScanLine,
  Swords,
  Volume2,
} from "lucide-react";
import { Reveal } from "./Reveal";
import { CatalogGlyph } from "./mockups";

/**
 * Grade "bento" com as demais capacidades da plataforma. Mistura cartões de
 * tamanhos diferentes para um layout moderno e respirado, sem repetir o grid
 * uniforme de funcionalidades. Os cartões com `href` levam às respectivas
 * páginas — é por aqui que quem chega pela landing descobre Sala, Duelo,
 * Clínica e Arena.
 */
export function BentoGrid() {
  return (
    <div className="grid auto-rows-[minmax(0,1fr)] gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {/* Catálogo — cartão alto, ocupa duas linhas */}
      <Reveal className="sm:row-span-2">
        <article className="flex h-full flex-col rounded-2xl border border-border bg-card p-6 shadow-sm">
          <span className="grid size-11 place-items-center rounded-xl bg-accent text-accent-foreground">
            <MapPin className="size-5" />
          </span>
          <h3 className="mt-4 text-lg font-semibold">Três níveis de detalhe</h3>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
            Do corpo inteiro ao detalhe regional: 18 modelos organizados em
            sistemas, regiões anatômicas e órgãos individuais.
          </p>
          <div className="mt-auto pt-6">
            <CatalogGlyph />
          </div>
        </article>
      </Reveal>

      {/* Sala de estudos */}
      <Reveal delay={0.05}>
        <BentoCard
          icon={Lamp}
          title="Sala de estudos"
          href="/sala"
          description="Quarto 3D com flashcards, rádio e tutor de IA; funciona no desktop e no headset."
        />
      </Reveal>

      {/* Duelo 1×1 */}
      <Reveal delay={0.1}>
        <BentoCard
          icon={Swords}
          title="Duelo 1×1"
          href="/duelo"
          description="Quiz de anatomia contra bot em três dificuldades; online em breve."
        />
      </Reveal>

      {/* Clínica */}
      <Reveal delay={0.15}>
        <BentoCard
          icon={ScanLine}
          title="Clínica"
          href="/clinica"
          description="Casos em 3D a partir de exames reais anonimizados. Visualização educacional, não substitui laudo."
        />
      </Reveal>

      {/* Arena VR */}
      <Reveal delay={0.2}>
        <BentoCard
          icon={Glasses}
          title="Arena VR"
          href="/arena"
          description="Desafio de anatomia imersivo em qualquer headset WebXR, direto do navegador."
        />
      </Reveal>

      {/* Quiz */}
      <Reveal delay={0.25}>
        <BentoCard
          icon={GraduationCap}
          title="Modo quiz"
          href="/quiz"
          description="Teste-se identificando estruturas marcadas sobre os próprios modelos 3D."
        />
      </Reveal>

      {/* Narração */}
      <Reveal delay={0.3}>
        <BentoCard
          icon={Volume2}
          title="Narração em áudio"
          description="Ouça a descrição de cada estrutura com a voz do navegador, em português."
        />
      </Reveal>

      {/* PDF — cartão largo */}
      <Reveal delay={0.35} className="sm:col-span-2">
        <article className="flex h-full items-center gap-5 rounded-2xl border border-border bg-card p-6 shadow-sm">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-accent text-accent-foreground">
            <FileText className="size-5" />
          </span>
          <div>
            <h3 className="text-lg font-semibold">
              Histórico e exportação em PDF
            </h3>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              Salve sessões de estudo com anotações, conversas e capturas — e
              exporte tudo num relatório pronto para revisar.
            </p>
          </div>
        </article>
      </Reveal>
    </div>
  );
}

function BentoCard({
  icon: Icon,
  title,
  description,
  href,
}: {
  icon: typeof Glasses;
  title: string;
  description: string;
  /** Quando presente, o cartão inteiro vira um link para a rota. */
  href?: string;
}) {
  const card = (
    <article
      className={
        "flex h-full flex-col rounded-2xl border border-border bg-card p-6 shadow-sm" +
        (href ? " transition-colors hover:border-primary/40 hover:shadow-md" : "")
      }
    >
      <span className="grid size-11 place-items-center rounded-xl bg-accent text-accent-foreground">
        <Icon className="size-5" />
      </span>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>
      {href ? (
        <span className="mt-auto pt-4 text-sm font-medium text-primary">
          Abrir →
        </span>
      ) : null}
    </article>
  );

  if (!href) return card;

  return (
    <Link
      href={href}
      className="block h-full rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {card}
    </Link>
  );
}
