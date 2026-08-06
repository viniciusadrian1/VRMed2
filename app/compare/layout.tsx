import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Comparar saudável × patológico",
  description:
    "Confronte a anatomia saudável e a patológica lado a lado, com câmeras sincronizadas e as diferenças anatômicas chave em destaque.",
};

export default function CompareLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
