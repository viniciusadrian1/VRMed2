"use client";

import { FileDown } from "lucide-react";
import { track } from "@/lib/analytics";
import { exportSessionToPdf } from "@/lib/pdf-export";
import { Button } from "@/components/ui/button";
import type { StudySession } from "@/types";

/** Botão que exporta uma sessão de estudo como PDF. */
export function PDFExportButton({ session }: { session: StudySession }) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => {
        exportSessionToPdf(session);
        track("pdf_exported", { organ: session.organId });
      }}
    >
      <FileDown />
      PDF
    </Button>
  );
}
