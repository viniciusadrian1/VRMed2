"use client";

import { createContext, useContext } from "react";

/** Só muda adaptações de entrada/portais; o conteúdo visual continua sendo o do site. */
export const ContextoDOMXR = createContext(false);
export const ContextoPortalDOMXR = createContext<HTMLElement | null>(null);
// A raiz HTML dos painéis é separada da árvore R3F; repassa a sessão real.
export const ContextoSessaoDOMXR = createContext<XRSession | undefined>(undefined);
export const useDOMImersivo = () => useContext(ContextoDOMXR);
export const useSessaoDOMXR = () => useContext(ContextoSessaoDOMXR);
