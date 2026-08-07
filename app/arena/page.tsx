import type { Metadata } from "next";
import { ArenaScene } from "@/components/arena/ArenaScene";

export const metadata: Metadata = {
  title: "Arena — desafio de anatomia em VR",
  description:
    "Encontre estruturas anatômicas contra o relógio, em realidade virtual. Uma partida de 60 segundos dentro do corpo humano.",
};

/**
 * Rota da Arena — modo jogo, isolado do restante do app.
 *
 * Nada aqui importa o visualizador, a store global ou a UI de estudo: se a
 * Arena quebrar na véspera do evento, o VRmed continua de pé para a banca.
 */
export default function ArenaPage() {
  return (
    <main className="relative h-dvh w-full overflow-hidden bg-[#101820]">
      <ArenaScene />
    </main>
  );
}
