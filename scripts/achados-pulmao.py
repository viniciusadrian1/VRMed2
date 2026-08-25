# -*- coding: utf-8 -*-
"""
achados-pulmao.py — extrai ACHADOS quantitativos de uma TC de tórax para o
modo Clínica do VRmed, para projetar sobre o modelo ilustrativo de pulmão.

O que mede (métodos clássicos por limiar de densidade, sem IA generativa):
  * Enfisema: %% de voxels do parênquima abaixo de -950 HU (LAA-950),
    por lobo e total. É a métrica padrão de quantificação de enfisema.
  * Lesões densas candidatas: componentes conexos de voxels > -300 HU dentro
    do pulmão (erodido para excluir parede/pleura), filtrados por tamanho e
    forma. A árvore vascular forma um componente gigante e cai no filtro de
    tamanho; sobram opacidades focais isoladas.

Limitações (declaradas no JSON): nódulos colados na pleura ou em vasos
calibrosos podem ser perdidos; é um DETECTOR DE CANDIDATOS educacional,
não um CAD diagnóstico.

Uso:
  python scripts/achados-pulmao.py --ct .clinica-dados/lidc-torax.nii.gz \
      --masks-dir .clinica-dados/torax-alta_masks \
      --output public/pacientes/torax-alta-achados.json
"""

import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage

LOBOS = [
    "lung_upper_lobe_left",
    "lung_lower_lobe_left",
    "lung_upper_lobe_right",
    "lung_middle_lobe_right",
    "lung_lower_lobe_right",
]

LIMIAR_ENFISEMA_HU = -950
LIMIAR_LESAO_HU = -300
# ponytail: filtros fixos de tamanho/forma; expor como flags se algum caso real pedir
LESAO_VOL_MIN_MM3 = 65.0        # ~esfera de 5mm
LESAO_VOL_MAX_MM3 = 50000.0     # acima disso é a árvore vascular ou consolidação maciça
LESAO_ALONGAMENTO_MAX = 3.5     # vasos são tubulares; nódulos, ~esféricos
LESAO_HU_MEDIO_MIN = -150       # aglomerado vascular difuso fica abaixo disso
MAX_LESOES = 10                 # só os maiores candidatos; 36 marcadores = ruído visual

# Mesma convenção do tc-para-vrmed.py: RAS (x,y,z) -> glTF (x, z, -y)
RAS_PARA_GLTF = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=float)


def para_gltf(pontos_vox: np.ndarray, affine: np.ndarray) -> np.ndarray:
    mm = pontos_vox @ affine[:3, :3].T + affine[:3, 3]
    return mm @ RAS_PARA_GLTF.T


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ct", required=True)
    ap.add_argument("--masks-dir", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    img = nib.load(args.ct)
    ct = np.asarray(img.dataobj, dtype=np.float32)
    affine = img.affine
    espacamento = np.abs(np.diag(affine)[:3])
    vol_voxel_mm3 = float(np.prod(espacamento))

    masks_dir = Path(args.masks_dir)
    pulmao = np.zeros(ct.shape, dtype=bool)
    lobos_masks: dict[str, np.ndarray] = {}
    for nome in LOBOS:
        caminho = masks_dir / f"{nome}.nii.gz"
        m = np.asarray(nib.load(caminho).dataobj) > 0
        lobos_masks[nome] = m
        pulmao |= m

    # --- Enfisema (LAA-950) por lobo e total -------------------------------
    lobos_json = {}
    for nome, m in lobos_masks.items():
        hu = ct[m]
        lobos_json[nome] = {
            "volumeMl": round(float(m.sum()) * vol_voxel_mm3 / 1000.0, 1),
            "enfisemaPct": round(float((hu < LIMIAR_ENFISEMA_HU).mean()) * 100.0, 2),
            "huMedio": round(float(hu.mean()), 1),
        }
    hu_pulmao = ct[pulmao]
    enfisema_total = round(float((hu_pulmao < LIMIAR_ENFISEMA_HU).mean()) * 100.0, 2)

    # --- Lesões densas candidatas ------------------------------------------
    # Erode ~3mm para não pegar parede torácica/pleura na borda da máscara.
    raio_vox = np.maximum(1, np.round(3.0 / espacamento).astype(int))
    nucleo = ndimage.binary_erosion(pulmao, iterations=1,
                                    structure=np.ones((raio_vox[0] * 2 + 1,
                                                       raio_vox[1] * 2 + 1,
                                                       raio_vox[2] * 2 + 1), bool))
    candidato = nucleo & (ct > LIMIAR_LESAO_HU)
    rotulos, n = ndimage.label(candidato)

    # BBox do pulmão inteiro em glTF, para normalizar as posições dos achados
    idx = np.argwhere(pulmao)
    cantos_gltf = para_gltf(idx[:: max(1, len(idx) // 20000)].astype(float), affine)
    bb_min, bb_max = cantos_gltf.min(axis=0), cantos_gltf.max(axis=0)
    bb_tam = np.maximum(bb_max - bb_min, 1e-6)

    lesoes = []
    fatias = ndimage.find_objects(rotulos)
    for i, fatia in enumerate(fatias, start=1):
        if fatia is None:
            continue
        comp = rotulos[fatia] == i
        vol_mm3 = float(comp.sum()) * vol_voxel_mm3
        if not (LESAO_VOL_MIN_MM3 <= vol_mm3 <= LESAO_VOL_MAX_MM3):
            continue
        lados_mm = np.array([(s.stop - s.start) for s in fatia]) * espacamento
        if lados_mm.max() / max(lados_mm.min(), 1e-6) > LESAO_ALONGAMENTO_MAX:
            continue  # tubular: vaso
        centro_vox = np.array([(s.start + s.stop) / 2.0 for s in fatia])
        centro_gltf = para_gltf(centro_vox[None, :], affine)[0]
        pos_norm = (centro_gltf - bb_min) / bb_tam
        diametro_mm = 2.0 * (3.0 * vol_mm3 / (4.0 * np.pi)) ** (1.0 / 3.0)
        hu_medio = float(ct[fatia][comp].mean())
        if hu_medio < LESAO_HU_MEDIO_MIN:
            continue
        lobo = next((nome for nome, m in lobos_masks.items()
                     if m[tuple(np.round(centro_vox).astype(int))]), "pulmao")
        lesoes.append({
            "posNorm": [round(float(v), 4) for v in pos_norm],
            "diametroMm": round(diametro_mm, 1),
            "volumeMm3": round(vol_mm3, 1),
            "huMedio": round(hu_medio, 1),
            "lobo": lobo,
        })

    lesoes.sort(key=lambda item: -item["diametroMm"])
    descartadas = max(0, len(lesoes) - MAX_LESOES)
    lesoes = lesoes[:MAX_LESOES]

    saida = {
        "metodo": {
            "enfisema": f"LAA-950: %% de voxels do parênquima < {LIMIAR_ENFISEMA_HU} HU",
            "lesoes": f"componentes conexos > {LIMIAR_LESAO_HU} HU no núcleo do pulmão, "
                      f"{LESAO_VOL_MIN_MM3:.0f}-{LESAO_VOL_MAX_MM3:.0f} mm³, "
                      f"alongamento < {LESAO_ALONGAMENTO_MAX}",
            "limitacoes": "candidatos educacionais; lesões justapleurais/justavasculares "
                          "podem ser perdidas; localização no modelo ilustrativo é aproximada",
            "candidatosMenoresOmitidos": descartadas,
        },
        "enfisemaPctTotal": enfisema_total,
        "bboxMm": [round(float(v), 1) for v in bb_tam],
        "lobos": lobos_json,
        "lesoes": lesoes,
    }
    Path(args.output).write_text(json.dumps(saida, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    print(f"[achados-pulmao] enfisema total: {enfisema_total}% | "
          f"lesoes candidatas: {len(lesoes)} | -> {args.output}")


if __name__ == "__main__":
    main()
