"use client";

import { PanelRightClose } from "lucide-react";
import { useMediaQuery } from "@/hooks/use-media-query";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AnnotationPanel } from "./AnnotationSystem";
import { AudioNarration } from "./AudioNarration";
import { ClippingPlaneControls } from "./ClippingPlaneControls";
import { LayersPanel } from "./LayersPanel";

interface ToolsPanelProps {
  open: boolean;
  onClose: () => void;
}

/** Conteúdo do painel — compartilhado entre o desktop e o drawer mobile. */
function ToolsPanelContent({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-3">
        <h2 className="text-sm font-semibold">Ferramentas do modelo</h2>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onClose}
          aria-label="Fechar painel de ferramentas"
        >
          <PanelRightClose />
        </Button>
      </div>
      <Tabs defaultValue="camadas" className="flex min-h-0 flex-1 flex-col">
        <TabsList className="m-2 mb-0 w-auto">
          <TabsTrigger value="camadas">Camadas</TabsTrigger>
          <TabsTrigger value="cortes">Cortes</TabsTrigger>
          <TabsTrigger value="anotacoes">Notas</TabsTrigger>
          <TabsTrigger value="audio">Áudio</TabsTrigger>
        </TabsList>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <TabsContent value="camadas" className="mt-0">
            <LayersPanel />
          </TabsContent>
          <TabsContent value="cortes" className="mt-0">
            <ClippingPlaneControls />
          </TabsContent>
          <TabsContent value="anotacoes" className="mt-0">
            <AnnotationPanel />
          </TabsContent>
          {/* forceMount mantém a narração viva ao trocar de aba; a classe esconde quando inativa */}
          <TabsContent
            value="audio"
            forceMount
            className="mt-0 data-[state=inactive]:hidden"
          >
            <AudioNarration />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

/**
 * Painel lateral de ferramentas do visualizador.
 * No desktop é uma coluna fixa retrátil; no mobile, um drawer inferior.
 */
export function ToolsPanel({ open, onClose }: ToolsPanelProps) {
  const isDesktop = useMediaQuery("(min-width: 768px)");

  if (isDesktop) {
    if (!open) return null;
    return (
      <aside className="hidden w-[340px] shrink-0 border-l border-border bg-card md:block">
        <ToolsPanelContent onClose={onClose} />
      </aside>
    );
  }

  return (
    <Sheet open={open} onOpenChange={(value) => !value && onClose()}>
      <SheetContent side="bottom" className="h-[82dvh] gap-0 p-0">
        <SheetTitle className="sr-only">Ferramentas do modelo 3D</SheetTitle>
        <ToolsPanelContent onClose={onClose} />
      </SheetContent>
    </Sheet>
  );
}
