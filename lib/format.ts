/** Pequenos utilitários de formatação e identificadores. */

/** Gera um identificador único (UUID quando disponível). */
export function genId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
}

/** Formata um timestamp como data curta pt-BR (ex.: 16/05/2026). */
export function formatDate(ts: number): string {
  return new Date(ts).toLocaleDateString("pt-BR");
}

/** Formata um timestamp como data e hora curtas pt-BR. */
export function formatDateTime(ts: number): string {
  return new Date(ts).toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

/** Converte uma duração em milissegundos para texto legível (ex.: "2 min 30 s"). */
export function formatDuration(ms: number): string {
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds} s`;
  return `${minutes} min${seconds ? ` ${seconds} s` : ""}`;
}

/** Hash não-criptográfico estável (FNV-1a) — usado para anonimizar perguntas. */
export function stableHash(input: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

/** Limita um número a um intervalo. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
