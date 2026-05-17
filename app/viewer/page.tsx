"use client";

import { useEffect, useRef, useState } from "react";
import { Box, MessageSquare, PanelRightOpen, Sparkles } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { InspectBar } from "@/components/viewer/InspectBar";
import { ModelPicker } from "@/components/viewer/ModelPicker";
import { SaveSessionButton } from "@/components/viewer/SaveSessionButton";
import { Scene } from "@/components/viewer/Scene";
import { ToolsPanel } from "@/components/viewer/ToolsPanel";
import { ViewerControls } from "@/components/viewer/ViewerControls";
import { ViewerLoader } from "@/components/viewer/ViewerLoader";
import { XRButton } from "@/components/viewer/XRButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useMediaQuery } from "@/hooks/use-media-query";
import { track } from "@/lib/analytics";
import { getOrganById } from "@/lib/organs";
import { useVRMedStore } from "@/lib/store";

/** Estado inicial exibido quando nenhum órgão foi selecionado. */
function EmptyViewerState() {
  return (
    <div className="absolute inset-0 z-10 grid place-items-center p-6">
      <div className="flex max-w-sm flex-col items-center gap-4 rounded-2xl border border-border bg-card/90 p-8 text-center shadow-lg backdrop-blur-sm">
        <span className="grid size-14 place-items-center rounded-2xl bg-accent text-accent-foreground">
          <Box className="size-7" />
        </span>
        <div>
          <h2 className="font-serif text-xl font-medium">
            Nenhum órgão selecionado
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Escolha uma estrutura anatômica no catálogo para iniciar a
            exploração em 3D.
          </p>
        </div>
        <ModelPicker variant="prominent" />
      </div>
    </div>
  );
}

export default function ViewerPage() {
  const organId = useVRMedStore((s) => s.currentOrganId);
  const modelKind = useVRMedStore((s) => s.modelKind);
  const isChatOpen = useVRMedStore((s) => s.isChatOpen);
  const setChatOpen = useVRMedStore((s) => s.setChatOpen);
  const organ = getOrganById(organId);

  const isDesktop = useMediaQuery("(min-width: 768px)");
  const [toolsOpen, setToolsOpen] = useState(false);
  const didInit = useRef(false);

  // Abre o painel de ferramentas automaticamente uma vez, no desktop.
  useEffect(() => {
    if (!didInit.current && isDesktop) {
      didInit.current = true;
      setToolsOpen(true);
    }
  }, [isDesktop]);

  // Telemetria: tempo de permanência registrado ao sair de cada órgão.
  useEffect(() => {
    if (!organId) return;
    const since = Date.now();
    return () => {
      track("organ_viewed", { organ: organId, dwellMs: Date.now() - since });
    };
  }, [organId]);

  return (
    <AppShell
      title="Visualizador 3D"
      description={organ ? organ.name : "Selecione um órgão para começar"}
      fullBleed
      actions={
        <>
          <SaveSessionButton />
          <XRButton />
        </>
      }
    >
      <TooltipProvider delayDuration={300}>
        <div className="flex h-full">
          <ViewerControls />

          <div className="vrmed-radial relative min-w-0 flex-1">
            <Scene />
            <ViewerLoader />

            <div className="pointer-events-none absolute inset-x-4 top-4 flex items-start justify-between gap-3">
              <div className="pointer-events-auto">
                <ModelPicker />
              </div>
              <div className="pointer-events-auto flex items-center gap-2">
                {organ && modelKind === "placeholder" && (
                  <Badge
                    variant="outline"
                    className="bg-card/90 shadow-sm backdrop-blur-sm"
                  >
                    <Sparkles className="size-3" />
                    Modelo de demonstração
                  </Badge>
                )}
                {!toolsOpen && (
                  <Button
                    variant="secondary"
                    size="sm"
                    className="shadow-md"
                    onClick={() => setToolsOpen(true)}
                  >
                    <PanelRightOpen />
                    Ferramentas
                  </Button>
                )}
              </div>
            </div>

            {!organId && <EmptyViewerState />}

            {/* Identificação de estruturas por clique */}
            <InspectBar />

            {/* Botão flutuante de acesso ao tutor de IA */}
            {!isChatOpen && (
              <Button
                size="lg"
                className="absolute bottom-5 right-5 shadow-lg"
                onClick={() => setChatOpen(true)}
              >
                <MessageSquare />
                Tutor de IA
              </Button>
            )}
          </div>

          <ToolsPanel open={toolsOpen} onClose={() => setToolsOpen(false)} />
          <ChatPanel />
        </div>
      </TooltipProvider>
    </AppShell>
  );
}
