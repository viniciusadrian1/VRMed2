import { create } from "zustand";
import { validarComandoTutor, type ComandoTutor, type ContextoTutor } from "./tutor-3d.ts";

/** Estado efêmero: não persiste comandos nem permite reaplicá-los em outro GLB. */
export const useTutor3D = create<{
  ativo: boolean;
  contexto: ContextoTutor | null;
  foco: { id: string; label: string; sequencia: number } | null;
  sequencia: number;
  registrar: (organId: string, nome: string, rotulos: string[]) => void;
  limparContexto: () => void;
  habilitar: (ativo: boolean) => void;
  limparFoco: () => void;
  aplicar: (comando: ComandoTutor, contexto: ContextoTutor) => boolean;
}>((set, get) => ({
  ativo: true, contexto: null, foco: null, sequencia: 0,
  registrar: (organId, nome, rotulos) => set((s) => ({
    foco: null,
    sequencia: s.sequencia + 1,
    contexto: {
      organId, revisao: s.sequencia + 1,
      alvos: [{ id: "modelo", label: nome }, ...[...new Set(rotulos)].slice(0, 100).map((label, i) => ({ id: `e${i}`, label }))],
    },
  })),
  limparContexto: () => set({ contexto: null, foco: null }),
  habilitar: (ativo) => set((s) => ({ ativo, foco: null, sequencia: s.sequencia + 1,
    contexto: s.contexto ? { ...s.contexto, revisao: s.sequencia + 1 } : null })),
  limparFoco: () => set({ foco: null }),
  aplicar: (comando, contexto) => {
    const atual = get();
    if (!atual.ativo || atual.contexto !== contexto || !validarComandoTutor(comando, contexto)) return false;
    const alvo = contexto.alvos.find((a) => a.id === comando.alvo)!;
    set({ sequencia: atual.sequencia + 1, foco: comando.acao === "restaurar" ? null : { ...alvo, sequencia: atual.sequencia + 1 } });
    return true;
  },
}));
