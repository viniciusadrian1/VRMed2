"use client";

import { createContext, useContext } from "react";

/** Só muda adaptações de entrada/portais; o conteúdo visual continua sendo o do site. */
export const ContextoDOMXR = createContext(false);
export const ContextoPortalDOMXR = createContext<HTMLElement | null>(null);
export const useDOMImersivo = () => useContext(ContextoDOMXR);
