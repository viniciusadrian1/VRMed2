"use client";

import { createContext, useCallback, useContext, useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";

type Acao = { titulo: string; desabilitado: boolean; executar: () => void; x: number; y: number };
const Registro = createContext<(id: string, acao: Acao) => () => void>(() => () => {});
const Acoes = createContext<Record<string, Acao>>({});
const RegistroTexto = createContext<(texto: string) => void>(() => {});
const Texto = createContext("");

/** Registro local à sala: teclado e laser executam exatamente a mesma ação. */
export function MonitorAcessivelProvider({ children }: { children: ReactNode }) {
  const [acoes, setAcoes] = useState<Record<string, Acao>>({});
  const [texto, setTexto] = useState("");
  const registrar = useCallback((id: string, acao: Acao) => {
    setAcoes((atuais) => ({ ...atuais, [id]: acao }));
    return () => setAcoes((atuais) => {
      const copia = { ...atuais }; delete copia[id]; return copia;
    });
  }, []);
  return <Registro.Provider value={registrar}><Acoes.Provider value={acoes}>
    <RegistroTexto.Provider value={setTexto}><Texto.Provider value={texto}>{children}</Texto.Provider></RegistroTexto.Provider>
  </Acoes.Provider></Registro.Provider>;
}

export function useAcaoMonitor(titulo: string, onClick: () => void, desabilitado = false, posicao: [number, number, number] = [0, 0, 0]) {
  const id = useId(), registrar = useContext(Registro), callback = useRef(onClick);
  const [x, y] = posicao;
  useLayoutEffect(() => { callback.current = onClick; }, [onClick]);
  const acao = useMemo(() => ({ titulo, desabilitado, x, y, executar: () => callback.current() }), [titulo, desabilitado, x, y]);
  useEffect(() => registrar(id, acao), [registrar, id, acao]);
}

export function useTextoMonitor(texto: string) {
  const registrar = useContext(RegistroTexto);
  useEffect(() => { registrar(texto); return () => registrar(""); }, [registrar, texto]);
}

export function MonitorAcessivel() {
  const acoes = useContext(Acoes);
  const texto = useContext(Texto);
  return <nav aria-label="Controles do monitor de estudos"
    className="sr-only focus-within:not-sr-only focus-within:absolute focus-within:left-4 focus-within:top-16 focus-within:z-30 focus-within:flex focus-within:max-w-xl focus-within:flex-wrap focus-within:gap-2 focus-within:rounded-xl focus-within:bg-slate-950 focus-within:p-4 focus-within:text-white">
    <p role="status" aria-live="polite" className="w-full">{texto}</p>
    {Object.entries(acoes).sort(([, a], [, b]) => b.y - a.y || a.x - b.x).map(([id, acao]) => <button key={id} type="button" disabled={acao.desabilitado}
      className="rounded px-3 py-2 focus:outline-2 focus:outline-amber-300 disabled:opacity-50" onClick={acao.executar}>{acao.titulo}</button>)}
  </nav>;
}
