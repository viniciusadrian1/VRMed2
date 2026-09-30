"use client";

import { Mic, Square, X } from "lucide-react";
import type { useDitadoTutor } from "@/hooks/use-ditado-tutor";
import { GRAVACAO_MAX_SEGUNDOS } from "@/lib/transcricao";

/** Mesmos controles no site e na captura do painel XR, sem uma interface paralela. */
export function ControlesDitado({ ditado, desabilitado = false, escuro = false }: {
  ditado: ReturnType<typeof useDitadoTutor>; desabilitado?: boolean; escuro?: boolean;
}) {
  const gravando = ditado.fase === "gravando";
  const aguardando = ditado.fase === "permissao" || ditado.fase === "transcrevendo";
  const botao = "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2";
  return <div className={`mb-2 text-xs ${escuro ? "text-white/75" : "text-muted-foreground"}`}>
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" disabled={desabilitado || aguardando}
        aria-label={gravando ? "Parar e transcrever" : "Ditar pergunta"} aria-pressed={gravando}
        className={`${botao} ${gravando ? "border-red-500 bg-red-500/10 text-red-600" : escuro ? "border-white/20 hover:bg-white/10" : "border-border text-foreground hover:bg-muted"}`}
        onClick={gravando ? ditado.parar : ditado.iniciar}>
        {gravando ? <Square className="size-4" /> : <Mic className="size-4" />}
        {gravando ? `Parar e transcrever · ${ditado.segundos}s` : aguardando ? "Aguarde…" : "Ditar pergunta"}
      </button>
      {ditado.ocupado && <button type="button" className={`${botao} ${escuro ? "border-white/20" : "border-border"}`}
        onClick={ditado.cancelar} aria-label="Cancelar ditado"><X className="size-4" />Cancelar</button>}
    </div>
    <p className="mt-1.5 leading-relaxed" role={ditado.fase === "erro" ? "alert" : "status"}>
      {ditado.mensagem || `Até ${GRAVACAO_MAX_SEGUNDOS}s. Áudio enviado à OpenAI para transcrever; revise antes de enviar ao tutor. Não dite dados pessoais.`}
    </p>
  </div>;
}
