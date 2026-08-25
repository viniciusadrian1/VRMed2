"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ScanLine, ShieldAlert } from "lucide-react";
import { ClinicaViewer } from "./ClinicaViewer";

/** Um caso processado pelo pipeline tc-para-vrmed. */
export interface CasoClinico {
  slug: string;
  titulo: string;
  descricao: string;
  glb: string;
  dataProcessamento: string;
  fonteDados: string;
}

/**
 * VRmed Clínica — lista de casos + visualizador.
 *
 * Os casos vêm de /pacientes/manifest.json, gerado pelo pipeline offline
 * (Fase 1). Estado 100% local: nenhuma dependência da store global.
 */
export function ClinicaApp() {
  const [casos, setCasos] = useState<CasoClinico[] | null>(null);
  const [erro, setErro] = useState(false);
  const [selecionado, setSelecionado] = useState<CasoClinico | null>(null);

  useEffect(() => {
    let cancelado = false;
    fetch("/pacientes/manifest.json")
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data: CasoClinico[]) => {
        if (!cancelado) setCasos(data);
      })
      .catch(() => {
        if (!cancelado) {
          setCasos([]);
          setErro(true);
        }
      });
    return () => {
      cancelado = true;
    };
  }, []);

  if (selecionado) {
    return (
      <main className="relative h-dvh w-full overflow-hidden bg-[#101820]">
        <ClinicaViewer caso={selecionado} />
        <button
          type="button"
          onClick={() => setSelecionado(null)}
          className="absolute left-4 top-4 z-20 flex items-center gap-1.5 rounded-full border border-white/15 bg-black/50 px-4 py-2 text-sm font-medium text-white backdrop-blur hover:bg-black/70"
        >
          <ArrowLeft className="size-4" />
          Casos
        </button>
      </main>
    );
  }

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex h-16 max-w-5xl items-center gap-3 px-5">
          <Link
            href="/"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ← VRmed
          </Link>
          <span className="ml-2 flex items-center gap-2 font-serif text-xl font-medium">
            <ScanLine className="size-5 text-primary" />
            Clínica
          </span>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-10">
        <h1 className="font-serif text-3xl font-medium tracking-tight">
          Casos em 3D a partir de exames reais
        </h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Cada caso abaixo foi gerado por segmentação automática de uma
          tomografia real e anonimizada. Explore em 3D, identifique estruturas
          com um clique e entre em VR.
        </p>

        {/* Enquadramento obrigatório (PROMPT-CLINICA §1): visualização, nunca diagnóstico. */}
        <p className="mt-4 flex max-w-2xl items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm">
          <ShieldAlert className="mt-0.5 size-4 shrink-0 text-warning" />
          Visualização educacional a partir de exame real anonimizado. Não
          substitui laudo ou avaliação médica.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {casos === null && (
            <p className="text-sm text-muted-foreground">Carregando casos…</p>
          )}
          {casos?.length === 0 && (
            <div className="rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground sm:col-span-2">
              {erro
                ? "Nenhum caso publicado ainda — o manifest (/pacientes/manifest.json) não foi encontrado."
                : "Nenhum caso processado ainda. Rode o pipeline scripts/tc-para-vrmed.py e adicione o resultado ao manifest."}
            </div>
          )}
          {casos?.map((caso) => (
            <button
              key={caso.slug}
              type="button"
              onClick={() => setSelecionado(caso)}
              className="rounded-xl border border-border bg-card p-5 text-left shadow-sm transition hover:border-primary/50 hover:shadow-md"
            >
              <h2 className="font-serif text-lg font-medium">{caso.titulo}</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {caso.descricao}
              </p>
              <p className="mt-3 text-xs text-muted-foreground">
                Fonte: {caso.fonteDados} · processado em {caso.dataProcessamento}
              </p>
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
