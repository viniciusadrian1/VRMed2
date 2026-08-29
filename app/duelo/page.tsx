import type { Metadata } from "next";
import { DueloApp } from "@/components/duelo/DueloApp";

export const metadata: Metadata = {
  title: "Duelo 1×1 · VRmed",
  description:
    "Duelo de conhecimento médico em 3D/VR: identifique órgãos e estruturas anatômicas antes do oponente. Contra bot em três dificuldades; online em breve.",
};

/**
 * Modo 2 do plano multi-modo: Jogo de Conhecimento Médico 1×1.
 * Rota isolada (estado local, canvas próprio) — padrão Arena/Clínica/Sala.
 */
export default function DueloPage() {
  return <DueloApp />;
}
