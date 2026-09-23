"use client";

import { createContext, useContext, useEffect, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import { ARENA_INICIAL, type EstadoArena } from "@/lib/duelo-apresentacao";

const Leitura = createContext<EstadoArena>(ARENA_INICIAL);
const Escrita = createContext<Dispatch<SetStateAction<EstadoArena>>>(() => {});

/** A arena recebe uma cópia da partida; nunca escreve no estado do jogo. */
export function ProvedorArena({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState(ARENA_INICIAL);
  return <Escrita.Provider value={setEstado}><Leitura.Provider value={estado}>{children}</Leitura.Provider></Escrita.Provider>;
}

export const useEstadoArena = () => useContext(Leitura);

export function PublicarEstadoArena(props: EstadoArena) {
  const publicar = useContext(Escrita);
  const { fase, resultado, erro, tempo, rodada, combo, meus, outros } = props;
  useEffect(() => {
    publicar({ fase, resultado, erro, tempo, rodada, combo, meus, outros });
  }, [publicar, fase, resultado, erro, tempo, rodada, combo, meus, outros]);
  return null;
}
