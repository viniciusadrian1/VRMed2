import type { Metadata } from "next";
import { SalaApp } from "@/components/sala/SalaApp";

export const metadata: Metadata = {
  title: "Sala de Estudos",
  description:
    "Sala de estudos individual em 3D/VR: música lo-fi, flashcards por tema, hub de modos e tutor de IA para dúvidas de anatomia.",
};

/**
 * Modo 1 do plano multi-modo: Sala de Estudos Individual.
 * Rota isolada — não toca a store global nem o visualizador (mesmo padrão
 * de isolamento da Arena e da Clínica).
 */
export default function SalaPage() {
  return <SalaApp />;
}
