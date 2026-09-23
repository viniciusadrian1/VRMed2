"use client";

import { Button3D } from "@/components/arena/ui3d";

/** Aparência de lousa, contrato de interação único com Hospital/Arena/Sala. */
export function BotaoLousa({ texto, position, onClick, cor = "#f8fbef", size = 0.14,
  width = 2.3, altura, destaque = null, desabilitado = false }: {
  texto: string; position: [number, number, number]; onClick: () => void;
  cor?: string; size?: number; width?: number; altura?: number;
  destaque?: "certo" | "errado" | null; desabilitado?: boolean;
}) {
  const h = altura ?? size * 1.9;
  // Reserva conservadora para rótulos anatômicos longos, sem ampliar o alvo.
  const tamanho = Math.min(size, h * 0.5, (width * 0.86) / Math.max(1, texto.length * 0.6));
  return <Button3D label={texto} position={position} onClick={onClick}
    width={width} height={h} tamanhoTexto={tamanho}
    color="#31574d" corRotulo={cor} destaque={destaque} desabilitado={desabilitado} />;
}
