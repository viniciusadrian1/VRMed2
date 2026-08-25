import type { Metadata } from "next";
import { ClinicaApp } from "@/components/clinica/ClinicaApp";

export const metadata: Metadata = {
  title: "Clínica — casos em 3D a partir de exames reais",
  description:
    "Visualize em 3D e VR modelos gerados a partir de tomografias reais anonimizadas. Visualização educacional — não substitui laudo ou avaliação médica.",
};

/**
 * VRmed Clínica — terceiro modo do app (PROMPT-CLINICA.md).
 *
 * Rota isolada como a Arena: nada aqui importa a store global nem altera o
 * visualizador de estudo. Se a Clínica quebrar, o resto do VRmed fica de pé.
 */
export default function ClinicaPage() {
  return <ClinicaApp />;
}
