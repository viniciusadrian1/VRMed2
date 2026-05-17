/**
 * Helpers para a Web Speech API (síntese de voz).
 * A narração dos órgãos usa `window.speechSynthesis`; quando uma voz pt-BR
 * não está disponível, o componente de áudio recorre a um arquivo pré-gravado.
 */

/** Verifica se o navegador suporta síntese de voz. */
export function isSpeechSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "speechSynthesis" in window &&
    "SpeechSynthesisUtterance" in window
  );
}

/**
 * Aguarda o carregamento da lista de vozes — em alguns navegadores ela é
 * preenchida de forma assíncrona após o evento `voiceschanged`.
 */
export function loadVoices(timeoutMs = 1500): Promise<SpeechSynthesisVoice[]> {
  return new Promise((resolve) => {
    if (!isSpeechSupported()) {
      resolve([]);
      return;
    }

    const immediate = window.speechSynthesis.getVoices();
    if (immediate.length > 0) {
      resolve(immediate);
      return;
    }

    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      window.speechSynthesis.removeEventListener("voiceschanged", finish);
      resolve(window.speechSynthesis.getVoices());
    };

    window.speechSynthesis.addEventListener("voiceschanged", finish);
    window.setTimeout(finish, timeoutMs);
  });
}

/** Seleciona a melhor voz em português a partir de uma lista de vozes. */
export function pickPortugueseVoice(
  voices: SpeechSynthesisVoice[],
): SpeechSynthesisVoice | null {
  return (
    voices.find((v) => v.lang.toLowerCase() === "pt-br") ??
    voices.find((v) => v.lang.toLowerCase().startsWith("pt")) ??
    null
  );
}

export interface SpeakOptions {
  voice?: SpeechSynthesisVoice | null;
  rate?: number;
  onBoundary?: (event: SpeechSynthesisEvent) => void;
  onEnd?: () => void;
  onError?: () => void;
}

/** Cria um utterance configurado para narração em português. */
export function createUtterance(
  text: string,
  options: SpeakOptions = {},
): SpeechSynthesisUtterance {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = options.voice?.lang ?? "pt-BR";
  if (options.voice) utterance.voice = options.voice;
  utterance.rate = options.rate ?? 1;
  utterance.pitch = 1;
  if (options.onBoundary) utterance.onboundary = options.onBoundary;
  if (options.onEnd) utterance.onend = options.onEnd;
  if (options.onError) utterance.onerror = options.onError;
  return utterance;
}

/** Interrompe imediatamente qualquer narração em andamento. */
export function cancelSpeech(): void {
  if (isSpeechSupported()) {
    window.speechSynthesis.cancel();
  }
}
