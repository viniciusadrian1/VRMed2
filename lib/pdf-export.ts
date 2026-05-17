import { jsPDF } from "jspdf";
import { formatDateTime } from "@/lib/format";
import type { StudySession } from "@/types";

/* Paleta clínica em RGB — espelha os tokens de tema do app. */
type RGB = [number, number, number];
const PRIMARY: RGB = [15, 76, 129];
const TEXT: RGB = [26, 26, 26];
const MUTED: RGB = [111, 110, 105];
const BORDER: RGB = [220, 216, 208];

const PAGE_W = 595.28; // A4 em pontos
const PAGE_H = 841.89;
const MARGIN = 48;
const CONTENT_W = PAGE_W - MARGIN * 2;

function setText(doc: jsPDF, c: RGB) {
  doc.setTextColor(c[0], c[1], c[2]);
}

/** Remove a marcação Markdown para exibição como texto simples no PDF. */
function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^[-*]\s+/gm, "• ")
    .trim();
}

/**
 * Exporta uma sessão de estudo como PDF.
 *
 * O documento é construído diretamente com jsPDF (texto selecionável e
 * paleta clínica). Optou-se por jsPDF em vez de capturar o DOM com
 * html2canvas porque este último não interpreta as cores oklch do Tailwind v4.
 */
export function exportSessionToPdf(session: StudySession): void {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  let y = MARGIN;

  const ensureSpace = (needed: number) => {
    if (y + needed > PAGE_H - MARGIN) {
      doc.addPage();
      y = MARGIN;
    }
  };

  const paragraph = (
    content: string,
    options: {
      size?: number;
      color?: RGB;
      font?: "normal" | "bold";
      gap?: number;
    } = {},
  ) => {
    const size = options.size ?? 10;
    doc.setFont("helvetica", options.font ?? "normal");
    doc.setFontSize(size);
    setText(doc, options.color ?? TEXT);
    const lineHeight = size * 1.42;
    for (const line of doc.splitTextToSize(content, CONTENT_W)) {
      ensureSpace(lineHeight);
      doc.text(line, MARGIN, y);
      y += lineHeight;
    }
    y += options.gap ?? 4;
  };

  const sectionTitle = (label: string) => {
    ensureSpace(46);
    y += 10;
    doc.setFont("times", "bold");
    doc.setFontSize(14);
    setText(doc, PRIMARY);
    doc.text(label, MARGIN, y);
    y += 8;
    doc.setDrawColor(BORDER[0], BORDER[1], BORDER[2]);
    doc.line(MARGIN, y, PAGE_W - MARGIN, y);
    y += 16;
  };

  /* ---------------------------- Capa ---------------------------- */
  doc.setFillColor(PRIMARY[0], PRIMARY[1], PRIMARY[2]);
  doc.rect(0, 0, PAGE_W, 6, "F");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  setText(doc, PRIMARY);
  doc.text("VRMED · SESSÃO DE ESTUDO", MARGIN, y + 8);
  y += 36;

  doc.setFont("times", "bold");
  doc.setFontSize(25);
  setText(doc, TEXT);
  for (const line of doc.splitTextToSize(session.name, CONTENT_W)) {
    doc.text(line, MARGIN, y);
    y += 30;
  }
  y += 6;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);
  setText(doc, MUTED);
  doc.text(`Órgão estudado: ${session.organName}`, MARGIN, y);
  y += 16;
  doc.text(`Data: ${formatDateTime(session.createdAt)}`, MARGIN, y);
  y += 24;

  if (session.screenshot) {
    try {
      const props = doc.getImageProperties(session.screenshot);
      const imageWidth = CONTENT_W;
      const imageHeight = (props.height / props.width) * imageWidth;
      ensureSpace(imageHeight + 12);
      const format = session.screenshot.startsWith("data:image/png")
        ? "PNG"
        : "JPEG";
      doc.addImage(
        session.screenshot,
        format,
        MARGIN,
        y,
        imageWidth,
        imageHeight,
      );
      doc.setDrawColor(BORDER[0], BORDER[1], BORDER[2]);
      doc.rect(MARGIN, y, imageWidth, imageHeight);
      y += imageHeight + 8;
    } catch {
      /* dataURL inválido — segue sem a imagem */
    }
  }

  /* ------------------------- Anotações -------------------------- */
  if (session.annotations.length > 0) {
    sectionTitle("Anotações");
    session.annotations.forEach((annotation, index) => {
      paragraph(`${index + 1}. ${annotation.text || "(sem descrição)"}`);
    });
  }

  /* --------------------- Transcrição do chat -------------------- */
  const chatMessages = session.chat.filter((m) => m.content.trim().length > 0);
  if (chatMessages.length > 0) {
    sectionTitle("Conversa com o tutor de IA");
    for (const message of chatMessages) {
      const isUser = message.role === "user";
      paragraph(isUser ? "Pergunta" : "Tutor de IA", {
        size: 9,
        font: "bold",
        color: isUser ? TEXT : PRIMARY,
        gap: 1,
      });
      paragraph(stripMarkdown(message.content), {
        size: 10,
        color: isUser ? TEXT : MUTED,
        gap: 12,
      });
    }
  }

  /* ----------------------- Resultado do quiz -------------------- */
  if (session.quizResult) {
    const quiz = session.quizResult;
    sectionTitle("Resultado do quiz");
    const percent = quiz.total
      ? Math.round((quiz.score / quiz.total) * 100)
      : 0;
    paragraph(`Pontuação: ${quiz.score} de ${quiz.total} (${percent}%)`, {
      size: 12,
      font: "bold",
    });
    paragraph(
      `Modo: ${quiz.mode === "timed" ? "Cronometrado" : "Tempo livre"}`,
      { size: 10, color: MUTED },
    );
  }

  /* --------------------- Rodapé em cada página ------------------ */
  const pageCount = doc.getNumberOfPages();
  for (let page = 1; page <= pageCount; page += 1) {
    doc.setPage(page);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    setText(doc, MUTED);
    doc.text(
      "Gerado pelo VRmed — ferramenta de estudo, não substitui avaliação clínica profissional.",
      MARGIN,
      PAGE_H - 24,
    );
    doc.text(`${page} / ${pageCount}`, PAGE_W - MARGIN, PAGE_H - 24, {
      align: "right",
    });
  }

  doc.save(`vrmed-${session.organId}-${session.id.slice(0, 8)}.pdf`);
}
