"use client";

import { useEffect, useState } from "react";
import { Glasses, ScanEye } from "lucide-react";
import { viewerBridge } from "@/lib/viewer-bridge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * Os dois modos imersivos são a MESMA verificação com outro `XRSessionMode`:
 * um aparelho pode suportar um e não o outro (Quest 2/3 suportam ambos; um
 * celular com WebXR normalmente só faz `immersive-ar`). Por isso cada botão
 * pergunta pelo seu modo em vez de herdar a resposta do outro.
 */
const MODOS = {
  vr: {
    sessao: "immersive-vr" as XRSessionMode,
    rotulo: "Entrar em VR",
    Icone: Glasses,
    entrar: () => viewerBridge.enterVR(),
    semSuporte: "Este dispositivo ou navegador não suporta WebXR em VR.",
  },
  ar: {
    sessao: "immersive-ar" as XRSessionMode,
    rotulo: "Entrar em AR",
    Icone: ScanEye,
    entrar: () => viewerBridge.enterAR(),
    semSuporte: "Este dispositivo ou navegador não suporta WebXR em AR.",
  },
};

/** Botão de entrada em realidade virtual ou aumentada (WebXR). */
export function XRButton({ modo = "vr" }: { modo?: keyof typeof MODOS }) {
  const { sessao, rotulo, Icone, entrar, semSuporte } = MODOS[modo];
  const [supported, setSupported] = useState<boolean | null>(null);

  useEffect(() => {
    if (!navigator.xr) {
      setSupported(false);
      return;
    }
    navigator.xr
      .isSessionSupported(sessao)
      .then(setSupported)
      .catch(() => setSupported(false));
  }, [sessao]);

  // Abaixo de sm só o ícone: com o texto, as ações da barra superior passavam
  // da largura do celular e empurravam o tema e "Sobre o projeto" para fora.
  const button = (
    <Button
      variant={supported ? "default" : "outline"}
      size="sm"
      disabled={supported !== true}
      onClick={entrar}
      aria-label={rotulo}
    >
      <Icone />
      <span className="hidden sm:inline">{rotulo}</span>
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
            ? `Verificando suporte a ${modo.toUpperCase()}…`
            : semSuporte}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
