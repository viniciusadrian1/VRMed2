"use client";

import { FileDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { FeedbackPayload } from "@/types";

const CSV_COLUMNS = [
  "timestamp",
  "organ",
  "rating",
  "tags",
  "comment",
  "userPrompt",
  "aiResponse",
];

/** Converte os registros de feedback para CSV (com escape de aspas e de fórmulas (CSV injection)). */
function toCsv(rows: FeedbackPayload[]): string {
  const escape = (value: string) => {
    const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
    return `"${safe.replace(/"/g, '""')}"`;
  };
  const lines = rows.map((row) =>
    [
      row.timestamp,
      row.currentOrgan,
      row.rating,
      row.tags.join("|"),
      row.comment,
      row.userPrompt,
      row.aiResponse,
    ]
      .map((cell) => escape(String(cell ?? "")))
      .join(","),
  );
  return [CSV_COLUMNS.join(","), ...lines].join("\n");
}

/** Botão de exportação dos feedbacks como arquivo CSV. */
export function FeedbackExport({ data }: { data: FeedbackPayload[] }) {
  const handleExport = () => {
    // BOM (﻿) garante a leitura correta de acentos no Excel.
    const blob = new Blob([`﻿${toCsv(data)}`], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `vrmed-feedback-${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleExport}
      disabled={data.length === 0}
    >
      <FileDown />
      Exportar CSV
    </Button>
  );
}
