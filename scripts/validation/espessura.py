"""
Calibre característico (espessura em mm) de uma estrutura segmentada e sua faixa.

Por que EDT sobre o esqueleto: a transformada de distância euclidiana com
`sampling=zooms` devolve, em cada voxel interno, a distância em mm até a borda
mais próxima — então `2 * EDT` é a espessura local. A mediana de `2 * EDT` sobre
TODOS os voxels é enviesada para baixo, porque a casca (EDT pequeno) domina a
contagem numa estrutura fina. O esqueleto fica no eixo medial, onde `2 * EDT`
é justamente o calibre local, então a mediana sobre ele é o estimador honesto.

Não agrega erro de etapa nenhuma: mede só a máscara de entrada (Tier 1 opera
sobre esta mesma máscara como referência).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize

FAIXAS = ("<3mm", "3-10mm", "10-30mm", ">30mm")


def calibre_mm(mask: np.ndarray, zooms: np.ndarray) -> dict:
    """Estatísticas de espessura local (2 × EDT) em mm de uma máscara binária."""
    m = np.asarray(mask) > 0
    if not m.any():
        return {
            "calibre_mediano_mm": 0.0,
            "calibre_p90_mm": 0.0,
            "calibre_max_mm": 0.0,
            "espessura_mediana_no_esqueleto_mm": 0.0,
        }

    edt = ndimage.distance_transform_edt(m, sampling=np.asarray(zooms, dtype=float))
    dentro = edt[m] * 2.0

    esq = skeletonize(m)
    if esq.any():
        referencia = float(np.median(edt[esq] * 2.0))
    else:
        # ponytail: fallback do enunciado — p90 aproxima o eixo medial quando o
        # esqueleto sai vazio (estrutura de 1 voxel de espessura).
        referencia = float(np.percentile(dentro, 90))

    return {
        "calibre_mediano_mm": float(np.median(dentro)),
        "calibre_p90_mm": float(np.percentile(dentro, 90)),
        "calibre_max_mm": float(dentro.max()),
        "espessura_mediana_no_esqueleto_mm": referencia,
    }


def faixa_de_calibre(calibre: float) -> str:
    """Coloca um calibre em mm numa das FAIXAS."""
    if calibre < 3.0:
        return FAIXAS[0]
    if calibre < 10.0:
        return FAIXAS[1]
    if calibre < 30.0:
        return FAIXAS[2]
    return FAIXAS[3]


def classificar(mask: np.ndarray, zooms: np.ndarray) -> dict:
    """calibre_mm() + a faixa do valor de referência (esqueleto)."""
    d = calibre_mm(mask, zooms)
    d["faixa"] = faixa_de_calibre(d["espessura_mediana_no_esqueleto_mm"])
    return d


def _demo() -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import nibabel as nib

    from validation.phantom import esfera, tubo_fino

    print("== fantomas (calibre conhecido) ==")
    casos = [
        ("tubo d=2 mm", 2.0, tubo_fino(2.0, 30.0, spacing=(0.25, 0.25, 0.25))),
        ("tubo d=5 mm", 5.0, tubo_fino(5.0, 40.0, spacing=(0.5, 0.5, 0.5))),
        ("tubo d=20 mm", 20.0, tubo_fino(20.0, 60.0, spacing=(1.0, 1.0, 1.0))),
        ("esfera d=40 mm", 40.0, esfera(40.0, spacing=(1.0, 1.0, 1.0))),
    ]
    for rotulo, real, (mask, affine) in casos:
        z = np.linalg.norm(affine[:3, :3], axis=0)
        r = classificar(mask, z)
        est = r["espessura_mediana_no_esqueleto_mm"]
        err = 100.0 * (est - real) / real
        print(f"{rotulo:>16}: est={est:6.2f} mm  erro={err:+6.1f} %  faixa={r['faixa']:>8}"
              f"  (mediana={r['calibre_mediano_mm']:.2f}  p90={r['calibre_p90_mm']:.2f}"
              f"  max={r['calibre_max_mm']:.2f})")
        assert abs(err) < 20.0, f"{rotulo}: erro {err:+.1f} % acima de 20 %"

    print("\n== estruturas reais ==")
    raiz = Path(__file__).resolve().parents[2] / ".clinica-dados"
    alvos = [
        (raiz / "torax-alta_masks", ("aorta", "trachea", "esophagus", "heart")),
        (raiz / "cta-cardio" / "masks", ("pulmonary_vein", "common_carotid_artery_left")),
    ]
    for pasta, nomes in alvos:
        for nome in nomes:
            p = pasta / f"{nome}.nii.gz"
            if not p.exists():
                print(f"{nome:>22}: ausente ({p})")
                continue
            img = nib.load(str(p))
            mask = np.asarray(img.dataobj) > 0.5
            z = np.linalg.norm(img.affine[:3, :3], axis=0)
            r = classificar(mask, z)
            print(f"{nome:>22}: calibre={r['espessura_mediana_no_esqueleto_mm']:6.2f} mm"
                  f"  faixa={r['faixa']:>8}  mediana={r['calibre_mediano_mm']:5.2f}"
                  f"  p90={r['calibre_p90_mm']:6.2f}  max={r['calibre_max_mm']:6.2f}"
                  f"  voxels={int(mask.sum())}  zooms={np.round(z, 2)}")


if __name__ == "__main__":
    _demo()
