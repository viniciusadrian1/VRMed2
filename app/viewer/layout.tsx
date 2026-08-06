import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Visualizador 3D",
  description:
    "Explore modelos anatômicos em 3D: gire, corte em planos axial, sagital e coronal, isole camadas, ative o raio-X e identifique estruturas com um clique.",
};

export default function ViewerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
