import {
  Box,
  Camera,
  Layers,
  Move3d,
  ScanLine,
  Sparkles,
} from "lucide-react";

/**
 * Mockups visuais das funcionalidades, usados na vitrine da landing page.
 * São puramente apresentacionais (SVG/CSS com os tokens do tema) — leves,
 * nítidos e compatíveis com o modo claro e escuro. Não substituem o produto:
 * representam-no em miniatura para mostrar o que o estudante encontra.
 */

/** Moldura de "janela de aplicativo" — barra de título com pontos e rótulo. */
function WindowFrame({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-xl shadow-primary/5 ring-1 ring-black/[0.02]">
      <div className="flex items-center gap-2 border-b border-border bg-muted/50 px-4 py-2.5">
        <span className="flex gap-1.5" aria-hidden>
          <span className="size-2.5 rounded-full bg-destructive/40" />
          <span className="size-2.5 rounded-full bg-warning/50" />
          <span className="size-2.5 rounded-full bg-success/50" />
        </span>
        <span className="ml-1 text-xs font-medium text-muted-foreground">
          {label}
        </span>
      </div>
      {children}
    </div>
  );
}

/** Silhueta estilizada de um coração — usada nos mockups do visualizador. */
function HeartGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 100 100" className={className} aria-hidden>
      <defs>
        <radialGradient id="heartFill" cx="42%" cy="34%" r="72%">
          <stop offset="0%" stopColor="#d65f52" />
          <stop offset="55%" stopColor="#b8463b" />
          <stop offset="100%" stopColor="#7e2c25" />
        </radialGradient>
      </defs>
      <path
        d="M50 86C26 70 14 56 14 40c0-11 8-19 18-19 7 0 13 4 18 11 5-7 11-11 18-11 10 0 18 8 18 19 0 16-12 30-36 46Z"
        fill="url(#heartFill)"
        stroke="rgba(0,0,0,0.12)"
        strokeWidth="1"
      />
      <path
        d="M50 32c-4 8-4 18 0 28M40 40c6 2 14 2 20 0"
        fill="none"
        stroke="rgba(255,255,255,0.35)"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Pino de anotação numerado, posicionado sobre o modelo. */
function Pin({
  n,
  className,
}: {
  n: number;
  className?: string;
}) {
  return (
    <span
      className={`absolute grid size-6 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground shadow-md ring-2 ring-white/80 ${className}`}
    >
      {n}
    </span>
  );
}

/* -------------------------------------------------------------------------- */
/* Visualizador 3D + camadas + cortes                                          */
/* -------------------------------------------------------------------------- */

export function ViewerMockup() {
  const tools = [Move3d, ScanLine, Layers, Camera];
  const layers = [
    { name: "Pericárdio", w: "82%" },
    { name: "Miocárdio", w: "100%" },
    { name: "Ventrículos", w: "64%" },
  ];
  return (
    <WindowFrame label="Visualizador 3D · Coração">
      <div className="flex">
        {/* Barra de ferramentas */}
        <div className="flex flex-col items-center gap-2 border-r border-border bg-card px-2 py-3">
          {tools.map((Icon, i) => (
            <span
              key={i}
              className={`grid size-7 place-items-center rounded-md ${
                i === 0
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground"
              }`}
            >
              <Icon className="size-4" />
            </span>
          ))}
        </div>

        {/* Palco 3D */}
        <div className="vrmed-radial relative grid flex-1 place-items-center overflow-hidden py-6">
          <div className="vrmed-grid absolute inset-0 opacity-40" aria-hidden />
          <div className="relative size-40">
            <HeartGlyph className="size-full drop-shadow-lg" />
            <Pin n={1} className="left-[34%] top-[30%]" />
            <Pin n={2} className="left-[66%] top-[44%]" />
            <Pin n={3} className="left-[46%] top-[72%]" />
          </div>
          <span className="absolute bottom-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-border bg-card/90 px-3 py-1 text-[11px] font-medium shadow-sm backdrop-blur">
            Estrutura: Ventrículo esquerdo
          </span>
        </div>

        {/* Painel de camadas */}
        <div className="hidden w-36 flex-col gap-3 border-l border-border bg-card p-3 sm:flex">
          <p className="text-[11px] font-semibold text-muted-foreground">
            Camadas
          </p>
          {layers.map((l) => (
            <div key={l.name} className="flex flex-col gap-1.5">
              <span className="flex items-center gap-1.5 text-[11px]">
                <span className="size-3 rounded-[4px] border border-primary bg-primary/80" />
                {l.name}
              </span>
              <span className="h-1 rounded-full bg-muted">
                <span
                  className="block h-full rounded-full bg-primary/70"
                  style={{ width: l.w }}
                />
              </span>
            </div>
          ))}
        </div>
      </div>
    </WindowFrame>
  );
}

/* -------------------------------------------------------------------------- */
/* Tutor de IA                                                                  */
/* -------------------------------------------------------------------------- */

export function TutorMockup() {
  return (
    <WindowFrame label="Tutor de IA">
      <div className="flex flex-col gap-3 bg-gradient-to-b from-transparent to-accent/30 p-4">
        {/* Pergunta do usuário */}
        <div className="ml-auto max-w-[78%] rounded-2xl rounded-tr-sm bg-primary px-3.5 py-2 text-sm text-primary-foreground shadow-sm">
          O que causa a hipertrofia ventricular esquerda?
        </div>

        {/* Resposta da IA */}
        <div className="max-w-[88%] rounded-2xl rounded-tl-sm border border-border bg-card px-3.5 py-3 shadow-sm">
          <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold text-primary">
            <Sparkles className="size-3.5" />
            VRmed
          </div>
          <div className="space-y-1.5" aria-hidden>
            <span className="block h-2 w-full rounded-full bg-muted" />
            <span className="block h-2 w-[92%] rounded-full bg-muted" />
            <span className="block h-2 w-[74%] rounded-full bg-muted" />
          </div>
          <p className="mt-2 text-[13px] leading-relaxed text-foreground">
            Decorre da sobrecarga crônica de pressão — sobretudo hipertensão
            arterial e estenose aórtica.
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <span className="rounded-full border border-border bg-accent px-2 py-0.5 text-[10px] font-medium text-accent-foreground">
              Fonte · Mayo Clinic
            </span>
            <span className="rounded-full border border-border bg-accent px-2 py-0.5 text-[10px] font-medium text-accent-foreground">
              Fonte · NEJM
            </span>
          </div>
        </div>

        {/* Campo de entrada */}
        <div className="mt-1 flex items-center gap-2 rounded-full border border-border bg-card px-3 py-2 text-xs text-muted-foreground shadow-sm">
          Pergunte sobre a estrutura em foco…
          <span className="ml-auto grid size-6 place-items-center rounded-full bg-primary text-primary-foreground">
            ↑
          </span>
        </div>
      </div>
    </WindowFrame>
  );
}

/* -------------------------------------------------------------------------- */
/* Comparação saudável × patológico                                            */
/* -------------------------------------------------------------------------- */

export function CompareMockup() {
  return (
    <WindowFrame label="Comparar · Coração">
      <div className="grid grid-cols-2 divide-x divide-border">
        {[
          { tag: "Saudável", scale: "scale-100", tint: "" },
          { tag: "Patológico", scale: "scale-110", tint: "saturate-[1.15]" },
        ].map((side) => (
          <div
            key={side.tag}
            className="vrmed-radial relative grid place-items-center py-8"
          >
            <span className="absolute left-3 top-3 rounded-full border border-border bg-card/90 px-2.5 py-0.5 text-[11px] font-medium shadow-sm backdrop-blur">
              {side.tag}
            </span>
            <HeartGlyph
              className={`size-28 drop-shadow-lg transition ${side.scale} ${side.tint}`}
            />
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-1.5 border-t border-border bg-card p-3">
        {[
          "Parede ventricular espessada",
          "Câmara reduzida",
          "Maior rigidez diastólica",
        ].map((note) => (
          <span
            key={note}
            className="rounded-full bg-muted px-2.5 py-1 text-[11px] font-medium text-muted-foreground"
          >
            {note}
          </span>
        ))}
      </div>
    </WindowFrame>
  );
}

/* -------------------------------------------------------------------------- */
/* Mini-ícone de catálogo (usado na bento grid)                                */
/* -------------------------------------------------------------------------- */

export function CatalogGlyph() {
  const items = ["Sistemas", "Regiões", "Órgãos"];
  return (
    <div className="flex flex-col gap-1.5">
      {items.map((label) => (
        <div
          key={label}
          className="flex items-center gap-2 rounded-lg border border-border bg-background/60 px-2.5 py-1.5"
        >
          <span className="grid size-5 place-items-center rounded-md bg-accent text-accent-foreground">
            <Box className="size-3" />
          </span>
          <span className="text-[11px] font-medium">{label}</span>
          <span className="ml-auto text-[10px] font-semibold text-muted-foreground">
            6
          </span>
        </div>
      ))}
    </div>
  );
}
