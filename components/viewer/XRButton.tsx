"use client";

import { useEffect, useState } from "react";
import { Glasses } from "lucide-react";
import { viewerBridge } from "@/lib/viewer-bridge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/** Botão de entrada em realidade virtual (WebXR). */
export function XRButton() {
  const [supported, setSupported] = useState<boolean | null>(null);

  useEffect(() => {
    if (!navigator.xr) {
      setSupported(false);
      return;
    }
    navigator.xr
      .isSessionSupported("immersive-vr")
      .then(setSupported)
      .catch(() => setSupported(false));
  }, []);

  const button = (
    <Button
      variant={supported ? "default" : "outline"}
      size="sm"
      disabled={supported !== true}
      onClick={() => viewerBridge.enterVR()}
    >
      <Glasses />
      Entrar em VR
    </Button>
  );

  if (supported === true) return button;

  // O botão fica na barra superior, fora de qualquer TooltipProvider da
  // página — por isso fornece o seu próprio provedor.
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {/* span garante a tooltip mesmo com o botão desabilitado */}
          <span tabIndex={0}>{button}</span>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          {supported === null
            ? "Verificando suporte a VR…"
            : "Este dispositivo ou navegador não suporta WebXR."}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
