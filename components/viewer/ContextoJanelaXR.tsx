"use client";

import { createContext, useContext } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import type { JanelaXR } from "@/lib/janelas-estudo-xr";
import type { BordaPainelXR } from "@/lib/gestos-janelas-xr";

export type EventoJanelaXR = ThreeEvent<PointerEvent>;
export const ContextoJanelaXR = createContext<{
  id: JanelaXR | null; ordem: number; escala: number;
  arrastando: boolean; restaurar: () => void;
  aoRedimensionar: (e: EventoJanelaXR, borda: BordaPainelXR, largura: number, altura: number) => void;
  aoApertar: (e: EventoJanelaXR) => void; aoMover: (e: EventoJanelaXR) => void; aoSoltar: (e: EventoJanelaXR) => void;
}>({
  id: null, ordem: 1500, escala: 1, arrastando: false,
  restaurar: () => {}, aoRedimensionar: () => {},
  aoApertar: () => {}, aoMover: () => {}, aoSoltar: () => {},
});
export const useJanelaXR = () => useContext(ContextoJanelaXR);
