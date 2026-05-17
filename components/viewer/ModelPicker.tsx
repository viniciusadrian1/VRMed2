"use client";

import { useMemo, useState } from "react";
import { Box, ChevronsUpDown } from "lucide-react";
import {
  CATEGORY_LABELS,
  ORGANS,
  REGIONS,
  SYSTEMS,
  getOrganById,
} from "@/lib/organs";
import { useVRMedStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { OrganCategory, OrganDefinition } from "@/types";

interface ModelPickerProps {
  /** Estilo do botão que abre o catálogo. */
  variant?: "compact" | "prominent";
}

/** Seletor de modelos — sistemas anatômicos e órgãos individuais. */
export function ModelPicker({ variant = "compact" }: ModelPickerProps) {
  const currentOrganId = useVRMedStore((s) => s.currentOrganId);
  const setCurrentOrgan = useVRMedStore((s) => s.setCurrentOrgan);
  const [open, setOpen] = useState(false);
  const current = getOrganById(currentOrganId);

  const organsByCategory = useMemo(() => {
    const map = new Map<OrganCategory, OrganDefinition[]>();
    for (const organ of ORGANS) {
      if (!organ.category) continue;
      const list = map.get(organ.category) ?? [];
      list.push(organ);
      map.set(organ.category, list);
    }
    return [...map.entries()];
  }, []);

  const handleSelect = (id: string) => {
    if (id !== currentOrganId) setCurrentOrgan(id);
    setOpen(false);
  };

  const renderCard = (model: OrganDefinition) => {
    const active = model.id === currentOrganId;
    return (
      <button
        key={model.id}
        type="button"
        onClick={() => handleSelect(model.id)}
        aria-current={active ? "true" : undefined}
        className={cn(
          "flex flex-col gap-1 rounded-lg border p-3 text-left transition-colors",
          active
            ? "border-primary bg-accent"
            : "border-border hover:bg-muted",
        )}
      >
        <div className="flex items-center gap-2">
          <span className="font-medium">{model.name}</span>
          {model.kind === "system" && (
            <Badge variant="outline" className="text-[10px]">
              corpo inteiro
            </Badge>
          )}
          {model.pathologicalPath && (
            <Badge variant="outline" className="text-[10px]">
              comparável
            </Badge>
          )}
        </div>
        <span className="text-xs text-muted-foreground">{model.blurb}</span>
      </button>
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {variant === "prominent" ? (
          <Button size="lg">
            <Box />
            Escolher um modelo
          </Button>
        ) : (
          <Button variant="secondary" className="shadow-md">
            <Box />
            <span className="max-w-40 truncate">
              {current ? current.name : "Selecionar modelo"}
            </span>
            <ChevronsUpDown className="opacity-60" />
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl">
            Catálogo de modelos
          </DialogTitle>
          <DialogDescription>
            Escolha um sistema anatômico de corpo inteiro ou um órgão
            individual para estudar no visualizador 3D.
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] space-y-5 overflow-y-auto pr-1">
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Sistemas anatômicos
            </h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {SYSTEMS.map(renderCard)}
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Anatomia regional
            </h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {REGIONS.map(renderCard)}
            </div>
          </section>

          {organsByCategory.map(([category, organs]) => (
            <section key={category}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {CATEGORY_LABELS[category]}
              </h3>
              <div className="grid gap-2 sm:grid-cols-2">
                {organs.map(renderCard)}
              </div>
            </section>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
