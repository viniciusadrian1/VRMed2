"use client";

import { create } from "zustand";
import { getAudioFallbackPath, getDescriptionPath } from "@/lib/organs";
import { cancelSpeech, isSpeechSupported, loadVoices, pickPortugueseVoice, speak } from "@/lib/tts";
import { track } from "@/lib/analytics";
import type { OrganDescription } from "@/types";

/** Um único reprodutor para DOM e XR, inclusive quando a aba Áudio fica fechada. */
export const useNarracaoEstudo = create<{
  organId: string | null; description: OrganDescription | null; loading: boolean;
  status: "idle" | "playing" | "paused"; rate: number; erro: boolean;
}>(() => ({ organId: null, description: null, loading: false, status: "idle", rate: 1, erro: false }));

let audio: HTMLAudioElement | null = null;
let voz: SpeechSynthesisVoice | null = null;
let busca: AbortController | null = null;
let geracao = 0;
let inicio = 0;

function registrarEscuta() {
  if (inicio) track("audio_narration_played", { organ: useNarracaoEstudo.getState().organId, listenedMs: Date.now() - inicio });
  inicio = 0;
}

export function pararNarracao() {
  geracao++;
  cancelSpeech();
  if (audio) { audio.pause(); audio.currentTime = 0; }
  registrarEscuta();
  useNarracaoEstudo.setState({ status: "idle" });
}

export async function prepararNarracao(organId: string | null) {
  if (useNarracaoEstudo.getState().organId === organId) return;
  pararNarracao(); busca?.abort(); busca = null; audio = null;
  useNarracaoEstudo.setState({ organId, description: null, loading: Boolean(organId), erro: false });
  if (!organId) return;
  const controller = new AbortController(); busca = controller;
  void loadVoices().then((vozes) => { if (busca === controller) voz = pickPortugueseVoice(vozes); });
  try {
    const res = await fetch(getDescriptionPath(organId), { signal: controller.signal });
    const description: OrganDescription | null = res.ok ? await res.json() : null;
    if (busca === controller) useNarracaoEstudo.setState({ description });
  } catch {
    // A descrição indisponível é comunicada nos dois painéis; abortar é normal.
  } finally {
    if (busca === controller) useNarracaoEstudo.setState({ loading: false });
  }
}

export function encerrarNarracao() {
  busca?.abort(); busca = null;
  pararNarracao(); audio = null;
  useNarracaoEstudo.setState({ organId: null, description: null, loading: false });
}

export function pausarNarracao() {
  if (useNarracaoEstudo.getState().status !== "playing") return;
  if (isSpeechSupported()) window.speechSynthesis.pause(); else audio?.pause();
  useNarracaoEstudo.setState({ status: "paused" });
}

export function velocidadeNarracao(rate: number) {
  const valor = Math.min(2, Math.max(0.5, rate));
  useNarracaoEstudo.setState({ rate: valor });
  if (audio) audio.playbackRate = valor;
  // Web Speech não muda a velocidade de uma fala já iniciada.
}

export function ouvirNarracao() {
  const { description, organId, rate, status } = useNarracaoEstudo.getState();
  if (!description || !organId || status === "playing") return;
  if (status === "paused") {
    const atual = geracao;
    useNarracaoEstudo.setState({ status: "playing", erro: false });
    if (isSpeechSupported()) window.speechSynthesis.resume();
    else void audio?.play().catch(() => {
      if (geracao === atual) useNarracaoEstudo.setState({ status: "idle", erro: true });
    });
    return;
  }
  const atual = ++geracao;
  const terminar = () => {
    if (geracao !== atual) return;
    registrarEscuta(); useNarracaoEstudo.setState({ status: "idle" });
  };
  const falhar = () => {
    if (geracao !== atual) return;
    registrarEscuta(); useNarracaoEstudo.setState({ status: "idle", erro: true });
  };
  useNarracaoEstudo.setState({ status: "playing", erro: false });
  inicio = Date.now();
  if (isSpeechSupported()) speak(description.fullDescription, { voice: voz, rate, onEnd: terminar, onError: falhar });
  else {
    audio ??= new Audio(getAudioFallbackPath(organId));
    audio.playbackRate = rate; audio.currentTime = 0;
    audio.onended = terminar; audio.onerror = falhar;
    void audio.play().catch(falhar);
  }
}
