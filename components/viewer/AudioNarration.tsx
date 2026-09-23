"use client";

import { Pause, Play, Square, Volume2 } from "lucide-react";
import { useVRMedStore } from "@/lib/store";
import { isSpeechSupported } from "@/lib/tts";
import { ouvirNarracao, pausarNarracao, pararNarracao, useNarracaoEstudo, velocidadeNarracao } from "@/lib/narracao-estudo";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Slider } from "@/components/ui/slider";

/** O reprodutor é compartilhado com a aba Áudio em AR/VR. */
export function AudioNarration() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  const { description, loading, status, rate, erro: audioError } = useNarracaoEstudo();
  const useSpeech = isSpeechSupported();
  const handlePlay = ouvirNarracao;
  const handlePause = pausarNarracao;
  const handleStop = pararNarracao;
  const setRate = velocidadeNarracao;

  if (!organId) {
    return (
      <p className="px-4 py-10 text-center text-sm text-muted-foreground">
        Selecione um órgão para ver sua descrição.
      </p>
    );
  }

  if (loading) {
    return (
      <div className="space-y-2 p-3">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-9 w-full" />
      </div>
    );
  }

  if (!description) {
    return (
      <p className="px-4 py-10 text-center text-sm text-muted-foreground">
        Este modelo ainda não tem descrição narrada.
      </p>
    );
  }

  const narrationDisabled =
    loading || !description;

  return (
    <div className="flex flex-col gap-3 p-3">
      <div>
        <h3 className="font-serif text-lg font-medium">{description.name}</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {description.shortDescription}
        </p>
      </div>

      <div className="rounded-lg border border-border p-3">
        <div className="flex items-center gap-2">
          {status === "playing" ? (
            <Button size="sm" variant="secondary" onClick={handlePause}>
              <Pause />
              Pausar
            </Button>
          ) : (
            <Button size="sm" onClick={handlePlay} disabled={narrationDisabled}>
              <Play />
              {status === "paused" ? "Retomar" : "Ouvir descrição"}
            </Button>
          )}
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={handleStop}
            disabled={status === "idle"}
            aria-label="Parar narração"
          >
            <Square />
          </Button>
          <span
            className="ml-auto flex items-center gap-1 text-xs text-muted-foreground"
            aria-live="polite"
          >
            <Volume2 className="size-3.5" />
            {status === "playing"
              ? "Narrando…"
              : status === "paused"
                ? "Pausado"
                : useSpeech
                  ? "Voz do navegador"
                  : "Áudio alternativo"}
          </span>
        </div>

        <div className="mt-3 flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Velocidade</span>
          <Slider
            value={[rate]}
            min={0.5}
            max={2}
            step={0.25}
            onValueChange={([value]) => setRate(value)}
            aria-label="Velocidade da narração"
            className="flex-1"
          />
          <span className="w-9 text-right text-xs tabular-nums">
            {rate.toFixed(2)}×
          </span>
        </div>

        {audioError && (
          <p className="mt-2 text-xs text-muted-foreground">
            Narração em áudio indisponível neste navegador. O texto abaixo segue
            disponível para leitura.
          </p>
        )}
      </div>

      <Accordion type="single" collapsible defaultValue="texto">
        <AccordionItem value="texto">
          <AccordionTrigger>Descrição completa</AccordionTrigger>
          <AccordionContent>
            {/* O texto é a transcrição acessível da narração em áudio. */}
            <p className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
              {description.fullDescription}
            </p>
            {description.sources.length > 0 && (
              <div className="mt-3">
                <p className="mb-1.5 text-xs font-semibold text-muted-foreground">
                  Fontes
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {description.sources.map((source) => (
                    <Badge key={source} variant="secondary">
                      {source}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
