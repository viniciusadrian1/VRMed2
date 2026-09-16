"use client";

import { getOrganById } from "@/lib/organs";
import { useVRMedStore } from "@/lib/store";
import { Slider } from "@/components/ui/slider";

/**
 * Controle da abertura na tela (computador e celular) para modelos que se
 * separam em partes, como o crânio. No VR o mesmo valor é mexido pelo
 * analógico esquerdo — os dois escrevem em `explosao` no store.
 */
export function ExplosaoControl() {
  const explosao = useVRMedStore((s) => getOrganById(s.currentOrganId)?.explosao);
  const pronto = useVRMedStore((s) => s.layers.length > 0);
  const valor = useVRMedStore((s) => s.explosao);
  const setExplosao = useVRMedStore((s) => s.setExplosao);

  if (!explosao || !pronto) return null;

  return (
    // Abaixo da linha do seletor de modelo e do botão Ferramentas; só a
    // pílula captura clique, para a faixa não bloquear o giro do modelo.
    <div className="pointer-events-none absolute inset-x-0 top-16 flex justify-center px-4">
      <div className="pointer-events-auto flex w-full max-w-xs items-center gap-3 rounded-full border border-border bg-card/90 px-4 py-2 shadow-sm backdrop-blur-sm">
        <span className="shrink-0 text-sm font-medium">{explosao.rotulo}</span>
        <Slider
          value={[Math.round(valor * 100)]}
          min={0}
          max={100}
          step={1}
          onValueChange={([v]) => setExplosao(v / 100)}
          aria-label={explosao.rotulo}
        />
      </div>
    </div>
  );
}
