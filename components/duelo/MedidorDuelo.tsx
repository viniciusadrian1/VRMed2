"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";

/** Medição local opt-in. Não envia telemetria e não confunde pausa da aba com GPU lenta. */
export function MedidorDuelo({ publicar }: { publicar: (texto: string) => void }) {
  const amostras = useRef<number[]>([]);
  const tempo = useRef(0);
  useFrame(({ gl }, delta) => {
    if ((!gl.xr.isPresenting && document.visibilityState !== "visible") || delta > 0.5) {
      amostras.current = []; tempo.current = 0; return;
    }
    amostras.current.push(delta * 1000);
    tempo.current += delta;
    if (tempo.current < 5) return;
    const ordenadas = [...amostras.current].sort((a, b) => a - b);
    const p95 = ordenadas[Math.min(ordenadas.length - 1, Math.floor(ordenadas.length * 0.95))];
    publicar(`${gl.xr.isPresenting ? "XR" : "Desktop"} · ${(amostras.current.length / tempo.current).toFixed(0)} FPS · p95 ${p95.toFixed(1)} ms · ${gl.info.render.calls} chamadas · ${gl.info.render.triangles.toLocaleString("pt-BR")} triângulos · DPR ${gl.getPixelRatio()}`);
    amostras.current = []; tempo.current = 0;
  });
  return null;
}
