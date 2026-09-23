"use client";

import { createContext, useContext } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import type { JanelaXR } from "@/lib/janelas-estudo-xr";

export type EventoJanelaXR = ThreeEvent<PointerEvent>;
export const ContextoJanelaXR = createContext<{
  id: JanelaXR | null; ordem: number; escala: number;
  arrastando: boolean; aumentar: () => void; diminuir: () => void;
  aproximar: () => void; afastar: () => void; restaurar: () => void;
  aoApertar: (e: EventoJanelaXR) => void; aoMover: (e: EventoJanelaXR) => void; aoSoltar: (e: EventoJanelaXR) => void;
}>({
  id: null, ordem: 1500, escala: 1, arrastando: false,
  aumentar: () => {}, diminuir: () => {}, aproximar: () => {}, afastar: () => {}, restaurar: () => {},
  aoApertar: () => {}, aoMover: () => {}, aoSoltar: () => {},
});
export const useJanelaXR = () => useContext(ContextoJanelaXR);
