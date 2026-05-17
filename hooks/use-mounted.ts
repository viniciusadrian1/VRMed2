"use client";

import { useEffect, useState } from "react";

/**
 * Retorna `true` somente após a montagem no cliente.
 * Útil para evitar divergências de hidratação ao ler tema ou localStorage.
 */
export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted;
}
