import { BookMarked } from "lucide-react";

/** Chip visual que destaca uma fonte médica citada pelo tutor. */
export function SourceCitation({ source }: { source: string }) {
  return (
    <span
      className="mx-0.5 inline-flex items-center gap-1 rounded-md border border-border bg-accent/70 px-1.5 py-0.5 align-baseline text-[11px] font-medium text-accent-foreground"
      title={`Fonte citada: ${source}`}
    >
      <BookMarked className="size-3" />
      {source}
    </span>
  );
}
