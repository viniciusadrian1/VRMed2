import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Quiz de anatomia",
  description:
    "Teste seu conhecimento identificando estruturas marcadas diretamente sobre os modelos 3D, no modo livre ou cronometrado.",
};

export default function QuizLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
