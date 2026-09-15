"use client";

import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Panel, Text3D } from "@/components/arena/ui3d";
import { VERSAO_POSE, diagnosticoPose } from "@/components/viewer/XRManipulation";

const TMP = new THREE.Vector3();

/** m → "1,23 m", ou "—" enquanto não há número. */
function metros(v: number): string {
  return Number.isFinite(v) ? `${v.toFixed(2).replace(".", ",")} m` : "—";
}

/** m → "14,0 cm": o tamanho do modelo, na unidade de `tamanhoRealCm`. */
function cm(v: number): string {
  return Number.isFinite(v) ? `${(v * 100).toFixed(1).replace(".", ",")} cm` : "—";
}

/**
 * Painel de diagnóstico da pose, só com `?debug=xr` na URL.
 *
 * POR QUE ELE EXISTE
 *
 * A altura em que o órgão nasce foi "corrigida" várias vezes lendo o código, e
 * no óculos continuou errada. O que o Quest reporta nos primeiros quadros não
 * aparece em lugar nenhum fora dele, e o painel de preview do computador não
 * desenha quadros de XR. Este painel mostra, dentro do óculos, os números que
 * decidem a colocação — para a próxima correção sair de medida, não de palpite.
 *
 * O que ler nele:
 *  - "olhos" e "órgão" são alturas acima do chão. Num órgão pequeno, os dois
 *    têm de ficar próximos (o órgão ~5 cm abaixo). Se o órgão estiver muito
 *    acima dos olhos, o erro está na altura usada, e a linha "fonte" diz qual.
 *  - "fonte": real (rastreio firme), estimada (o headset chutou) ou suposta
 *    (nenhuma pose veio). Só "real" é confiável.
 *  - "maior eixo" é a mesma grandeza de `tamanhoRealCm` em `lib/organs.ts`:
 *    os dois têm de bater. Se não baterem, a escala está sendo aplicada errado.
 *  - a versão confirma que o óculos está rodando o código novo, e não um
 *    bundle em cache.
 *
 * Colocar como FILHO do <XROrigin>: a posição fica relativa aos pés.
 */
export function DiagnosticoXR({
  position = [0.5, 1.15, -0.6],
}: {
  position?: [number, number, number];
}) {
  const [texto, setTexto] = useState("aguardando pose…");
  const ultimo = useRef(0);

  useFrame((state) => {
    // 4 atualizações por segundo bastam para ler; texto a cada quadro pesaria.
    const agora = state.clock.elapsedTime;
    if (agora - ultimo.current < 0.25) return;
    ultimo.current = agora;

    const camera = state.gl.xr.getCamera();
    const origem = camera.parent;
    const chaoY = origem ? origem.getWorldPosition(TMP).y : 0;
    const olhosAgora = camera.getWorldPosition(TMP).y - chaoY;
    const orgaoAgora = diagnosticoPose.modelo
      ? diagnosticoPose.modelo.getWorldPosition(TMP).y - chaoY
      : NaN;
    const d = diagnosticoPose;

    setTexto(
      [
        `diagnóstico ${VERSAO_POSE}`,
        `olhos agora: ${metros(olhosAgora)}`,
        `órgão agora: ${metros(orgaoAgora)}`,
        `olhos na colocação: ${metros(d.olhosAcimaDoChao)}`,
        `fonte: ${d.fonte} · estimadas descartadas: ${d.posesEstimadasDescartadas}`,
        `maior eixo: ${cm(d.maiorEixo)} · altura: ${cm(d.alturaModelo)}`,
        `${d.apoiado ? "apoiado" : "flutuando"} · centro a ${metros(d.distancia)}`,
      ].join("\n"),
    );
  });

  return (
    <group position={position} rotation={[0, -0.35, 0]}>
      <Panel width={0.62} height={0.34} opacity={0.85} />
      <Text3D position={[0, 0, 0.005]} size={0.026} maxWidth={0.58}>
        {texto}
      </Text3D>
    </group>
  );
}
