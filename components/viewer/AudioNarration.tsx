"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Pause, Play, Square, Volume2 } from "lucide-react";
import { track } from "@/lib/analytics";
import {
  getAudioFallbackPath,
  getDescriptionPath,
} from "@/lib/organs";
import { useVRMedStore } from "@/lib/store";
import {
  cancelSpeech,
  isSpeechSupported,
  loadVoices,
  pickPortugueseVoice,
  speak,
} from "@/lib/tts";
import { useMounted } from "@/hooks/use-mounted";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Slider } from "@/components/ui/slider";
import type { OrganDescription } from "@/types";

type PlayStatus = "idle" | "playing" | "paused";

/** Painel de narração em áudio e descrição textual do órgão. */
export function AudioNarration() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  const mounted = useMounted();

  const [description, setDescription] = useState<OrganDescription | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<PlayStatus>("idle");
  const [rate, setRate] = useState(1);

  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);
  const [voiceResolved, setVoiceResolved] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [audioError, setAudioError] = useState(false);
  const startedAtRef = useRef(0);

  // Usa a síntese de voz sempre que o navegador a suporta. A voz pt-BR é
  // apenas uma preferência (voiceRef); sem ela, o navegador narra com a voz
  // padrão a partir do `lang`. O áudio pré-gravado é só o último recurso.
  const useSpeech = mounted && isSpeechSupported();

  // Carrega as vozes do navegador uma única vez.
  useEffect(() => {
    let cancelled = false;
    loadVoices().then((voices) => {
      if (cancelled) return;
      voiceRef.current = pickPortugueseVoice(voices);
      setVoiceResolved(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Busca a descrição do órgão atual.
  useEffect(() => {
    if (!organId) {
      setDescription(null);
      return;
    }
    setLoading(true);
    setDescription(null);
    setAudioError(false);
    let cancelled = false;
    fetch(getDescriptionPath(organId))
      .then((res) => (res.ok ? (res.json() as Promise<OrganDescription>) : null))
      .then((data) => {
        if (!cancelled) setDescription(data);
      })
      .catch(() => {
        if (!cancelled) setDescription(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [organId]);

  const finishTracking = useCallback(() => {
    if (startedAtRef.current > 0) {
      track("audio_narration_played", {
        organ: organId,
        listenedMs: Date.now() - startedAtRef.current,
      });
      startedAtRef.current = 0;
    }
  }, [organId]);

  // Interrompe a narração ao trocar de órgão ou desmontar.
  useEffect(() => {
    return () => {
      cancelSpeech();
      audioRef.current?.pause();
      setStatus("idle");
    };
  }, [organId]);

  // Contorna a limitação do Chrome que interrompe a síntese após ~15 s.
  useEffect(() => {
    if (status !== "playing" || !useSpeech) return;
    const keepAlive = window.setInterval(() => {
      window.speechSynthesis.pause();
      window.speechSynthesis.resume();
    }, 10_000);
    return () => window.clearInterval(keepAlive);
  }, [status, useSpeech]);

  // Mantém a velocidade do áudio de fallback sincronizada.
  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = rate;
  }, [rate]);

  const handlePlay = () => {
    if (!description) return;

    if (status === "paused") {
      if (useSpeech) window.speechSynthesis.resume();
      else void audioRef.current?.play();
      setStatus("playing");
      return;
    }

    startedAtRef.current = Date.now();

    if (useSpeech) {
      speak(description.fullDescription, {
        voice: voiceRef.current,
        rate,
        onEnd: () => {
          setStatus("idle");
          finishTracking();
        },
        onError: () => setStatus("idle"),
      });
    } else if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.playbackRate = rate;
      void audioRef.current.play().catch(() => setAudioError(true));
    }
    setStatus("playing");
  };

  const handlePause = () => {
    if (useSpeech) window.speechSynthesis.pause();
    else audioRef.current?.pause();
    setStatus("paused");
  };

  const handleStop = () => {
    cancelSpeech();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    finishTracking();
    setStatus("idle");
  };

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
        Descrição indisponível. Adicione o arquivo{" "}
        <code className="text-xs">/descriptions/{organId}.json</code>.
      </p>
    );
  }

  const narrationDisabled =
    (!useSpeech && audioError) || (!useSpeech && !voiceResolved);

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
                  : "Áudio pré-gravado"}
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

        {narrationDisabled && (
          <p className="mt-2 text-xs text-muted-foreground">
            Narração em áudio indisponível neste navegador. O texto abaixo segue
            disponível para leitura.
          </p>
        )}
      </div>

      {/* Áudio de fallback usado quando não há voz pt-BR disponível. */}
      {!useSpeech && voiceResolved && organId && (
        <audio
          ref={audioRef}
          src={getAudioFallbackPath(organId)}
          preload="none"
          onEnded={() => {
            finishTracking();
            setStatus("idle");
          }}
          onError={() => setAudioError(true)}
          className="hidden"
        />
      )}

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
