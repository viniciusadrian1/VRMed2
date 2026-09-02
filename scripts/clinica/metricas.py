"""
Métricas por máscara: volume (mL), bounding box (mm, RAS) e componentes conexos.

Volume e bbox vão para o relatório como "medida automática — visualização
educacional, não substitui laudo". O número de componentes denuncia ilhas
soltas que viram "linhas soltas" na malha (lição do LIDC: `heart` saiu com
8 componentes, 7 deles com menos de 50 voxels).
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage


def metricas_mascara(caminho: Path) -> dict:
    img = nib.load(str(caminho))
    zooms = np.array(img.header.get_zooms()[:3], dtype=float)  # robusto a affine oblíquo
    mask = np.asarray(img.dataobj) > 0.5
    voxels = int(mask.sum())
    if voxels == 0:
        return {"presente": False}

    mm3_voxel = float(np.prod(zooms))
    idx = np.argwhere(mask)
    lo, hi = idx.min(0), idx.max(0)
    cantos = np.array(
        [[x, y, z, 1.0] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    )
    mm = (cantos @ img.affine.T)[:, :3]
    rotulos, n = ndimage.label(mask)
    tamanhos = np.bincount(rotulos.ravel())[1:]
    ilhas = np.sort(tamanhos)[::-1][1:6] * mm3_voxel
    return {
        "presente": True,
        "voxels": voxels,
        "volume_ml": round(voxels * mm3_voxel / 1000.0, 1),
        "bbox_mm": {
            "min": [round(float(v), 1) for v in mm.min(0)],
            "max": [round(float(v), 1) for v in mm.max(0)],
        },
        "extensao_mm": [round(float(v), 1) for v in (mm.max(0) - mm.min(0))],
        "componentes": int(n),
        "fracao_maior_componente": round(float(tamanhos.max()) / voxels, 4),
        "ilhas_mm3": [round(float(v), 1) for v in ilhas],
    }


def tabela(masks_dir: Path, estruturas: list[str] | None = None) -> dict[str, dict]:
    saida: dict[str, dict] = {}
    for caminho in sorted(masks_dir.glob("*.nii.gz")):
        nome = caminho.name.removesuffix(".nii.gz")
        if estruturas is not None and nome not in estruturas:
            continue
        saida[nome] = metricas_mascara(caminho)
    return saida


def formatar_markdown(tab: dict[str, dict]) -> str:
    linhas = [
        "| estrutura | volume (mL) | extensão x×y×z (mm) | componentes | maior comp. | ilhas (mm³) |",
        "|---|---:|---|---:|---:|---|",
    ]
    for nome, m in tab.items():
        if not m.get("presente"):
            linhas.append(f"| {nome} | — | ausente no exame | | | |")
            continue
        ext = "×".join(f"{v:.0f}" for v in m["extensao_mm"])
        ilhas = ", ".join(f"{v:.0f}" for v in m["ilhas_mm3"]) or "—"
        linhas.append(
            f"| {nome} | {m['volume_ml']:.1f} | {ext} | {m['componentes']} | "
            f"{m['fracao_maior_componente'] * 100:.1f}% | {ilhas} |"
        )
    return "\n".join(linhas)
