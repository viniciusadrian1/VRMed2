"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { criarDitadoTutor } from "@/lib/ditado-tutor";
import { CANCELAR_DITADO } from "@/lib/transcricao";

export function useDitadoTutor(aoTexto: (texto: string) => void, ativo = true, sessao?: XRSession) {
  const [controle] = useState(() => criarDitadoTutor(() => {}));
  useEffect(() => { controle.atualizarRetorno(aoTexto); }, [controle, aoTexto]);
  const estado = useSyncExternalStore(controle.subscribe, controle.getSnapshot, controle.getSnapshot);
  useEffect(() => {
    if (!ativo) controle.cancelar();
    const aoOcultar = () => { if (document.hidden) controle.cancelar(); };
    const aoPausarXR = () => { if (sessao?.visibilityState !== "visible") controle.cancelar(); };
    const vincular = () => {
      sessao?.addEventListener("visibilitychange", aoPausarXR);
      sessao?.addEventListener("end", controle.cancelar);
    };
    const desvincular = () => {
      sessao?.removeEventListener("visibilitychange", aoPausarXR);
      sessao?.removeEventListener("end", controle.cancelar);
    };
    vincular();
    document.addEventListener("visibilitychange", aoOcultar);
    window.addEventListener("pagehide", controle.cancelar);
    window.addEventListener(CANCELAR_DITADO, controle.cancelar);
    return () => {
      document.removeEventListener("visibilitychange", aoOcultar);
      window.removeEventListener("pagehide", controle.cancelar);
      window.removeEventListener(CANCELAR_DITADO, controle.cancelar);
      desvincular();
      controle.cancelar();
    };
  }, [controle, ativo, sessao]);
  const ocupado = estado.fase === "permissao" || estado.fase === "gravando" || estado.fase === "transcrevendo";
  return { ...estado, ocupado, iniciar: () => {
    if (ativo && (!sessao || sessao.visibilityState === "visible")) void controle.iniciar();
  }, parar: controle.parar, cancelar: controle.cancelar };
}
