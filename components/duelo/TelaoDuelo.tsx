"use client";

import { useLayoutEffect, useRef } from "react";
import * as THREE from "three";
import { pintarTelao, RESOLUCAO_TELAO } from "@/lib/telao-duelo";

let fonteLocal: Promise<string> | undefined;
function fonteDoTelao() {
  return fonteLocal ??= new FontFace("VRmedTelao", "url(/fonts/inter-600.woff)", { weight: "600" }).load()
    .then((fonte) => { document.fonts.add(fonte); return "VRmedTelao"; })
    .catch(() => "sans-serif");
}

export function TelaoDuelo({ texto, cor, position, tamanho = [2.34, .69], compacto = false }: {
  texto: string; cor: string; position: [number, number, number]; tamanho?: [number, number]; compacto?: boolean;
}) {
  const material = useRef<THREE.MeshStandardMaterial>(null);
  const atualizar = useRef<((texto: string, cor: string) => void) | null>(null);
  useLayoutEffect(() => {
    const mat = material.current;
    if (!mat) return;
    const canvas = document.createElement("canvas");
    [canvas.width, canvas.height] = RESOLUCAO_TELAO;
    if (compacto) { canvas.width /= 2; canvas.height /= 2; }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (compacto) ctx.scale(.5, .5);
    const textura = new THREE.CanvasTexture(canvas);
    textura.colorSpace = THREE.SRGBColorSpace;
    mat.map = textura; mat.emissiveMap = textura; mat.needsUpdate = true;
    let cancelado = false, fonte = "sans-serif";
    let ultimoTexto = "DUELO 1×1", ultimaCor = "#9ccdd4";
    const desenhar = (valor: string, tinta: string) => {
      ultimoTexto = valor; ultimaCor = tinta;
      pintarTelao(ctx, valor, tinta, fonte);
      textura.needsUpdate = true;
    };
    atualizar.current = desenhar;
    void fonteDoTelao().then((nome) => {
      if (cancelado) return;
      fonte = nome; desenhar(ultimoTexto, ultimaCor);
    });
    return () => {
      cancelado = true; atualizar.current = null;
      mat.map = null; mat.emissiveMap = null; textura.dispose();
    };
  }, [compacto]);
  // Reutiliza a mesma textura. Só redesenha quando muda o valor visível, não por frame.
  useLayoutEffect(() => { atualizar.current?.(texto, cor); }, [texto, cor, compacto]);
  return <group pointerEvents="none">
    <mesh position={position} raycast={() => null}>
      <planeGeometry args={tamanho} />
      <meshStandardMaterial ref={material} roughness={.55} metalness={0}
        emissive="#ffffff" emissiveIntensity={.35} depthTest depthWrite />
    </mesh>
  </group>;
}
