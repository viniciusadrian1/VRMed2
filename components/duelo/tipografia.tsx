"use client";

import type { ComponentProps } from "react";
import { Button3D, Text3D } from "@/components/arena/ui3d";

/** Acabamento opt-in do Duelo: não muda Arena, Sala, Clínica ou painéis de estudo. */
export function TextoDuelo(props: ComponentProps<typeof Text3D>) {
  return <Text3D tratamento="interface" {...props} />;
}

export function BotaoDuelo(props: ComponentProps<typeof Button3D>) {
  return <Button3D tratamentoTexto="interface" {...props} />;
}
