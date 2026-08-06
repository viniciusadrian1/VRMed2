import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Histórico de estudo",
  description:
    "Retome sessões de estudo salvas — com anotações, conversas com o tutor e capturas — e exporte tudo em PDF para revisar.",
};

export default function HistoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
