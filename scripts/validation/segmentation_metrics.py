"""Metricas de segmentacao (predicao vs ground-truth) em milimetros.

Sem MONAI e sem surface-distance: apenas numpy + scipy.

DEFINICAO DE FRONTEIRA (fixada aqui, explicite ao comparar com outras libs):
    superficie(M) = M AND NOT binary_erosion(M, conectividade=1)
Ou seja, a fronteira e a camada *interna* de voxels da mascara que tocam o
fundo por FACE (vizinhanca 6 em 3D / 4 em 2D). A borda do volume conta como
fundo (`border_value=0` na erosao), entao uma estrutura cortada pelo campo de
visao tem essa face contada como superficie.

As distancias sao entre CENTROS DE VOXEL de superficie, obtidas com
`distance_transform_edt(~superficie(B), sampling=spacing)` amostrada nos
voxels de superficie(A). Isso quantiza as distancias na grade (nao ha
interpolacao sub-voxel nem area de triangulo, como fariam metricas baseadas
em malha); o menor valor nao-nulo possivel e ~1 voxel.

Convencoes das metricas simetricas:
    ASSD  = media de TODAS as distancias das duas direcoes, ponderada pelo
            numero de voxels de superficie de cada lado.
    HD95  = max(percentil 95 de A->B, percentil 95 de B->A)  (convencao MONAI)
    HD    = max(max A->B, max B->A)
    NSD@t = (#{A->B <= t} + #{B->A <= t}) / (n_A + n_B)

Convencoes de caso degenerado:
    - ambas as mascaras vazias: dice = iou = 1.0, distancias = 0.0, NSD = 1.0
    - apenas uma vazia: dice = iou = 0.0, distancias = nan, NSD = 0.0
"""

from __future__ import annotations

import argparse
import json
from typing import Sequence

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt

Mascara = np.ndarray
Spacing = Sequence[float]


def _bool(m: Mascara) -> np.ndarray:
    """Normaliza qualquer entrada para booleano (limiar > 0.5 para rotulos/probabilidades)."""
    a = np.asarray(m)
    return a if a.dtype == bool else a > 0.5


def dice(a: Mascara, b: Mascara) -> float:
    """Coeficiente de Dice (2|A∩B| / (|A|+|B|)). Vazio vs vazio = 1.0."""
    a, b = _bool(a), _bool(b)
    soma = int(a.sum()) + int(b.sum())
    if soma == 0:
        return 1.0
    return float(2.0 * np.count_nonzero(a & b) / soma)


def iou(a: Mascara, b: Mascara) -> float:
    """Indice de Jaccard (|A∩B| / |A∪B|). Vazio vs vazio = 1.0."""
    a, b = _bool(a), _bool(b)
    uniao = int(np.count_nonzero(a | b))
    if uniao == 0:
        return 1.0
    return float(np.count_nonzero(a & b) / uniao)


def volume_error_pct(a: Mascara, b: Mascara, spacing: Spacing) -> float:
    """Erro relativo de volume de A em relacao a B, em %: (V_A - V_B) / V_B * 100.

    `spacing` em mm por eixo, na mesma ordem dos eixos do array (o volume em si
    cancela na razao, mas o spacing entra para manter a semantica fisica).
    """
    a, b = _bool(a), _bool(b)
    voxel_mm3 = float(np.prod(np.asarray(spacing, dtype=float)))
    vol_a = int(a.sum()) * voxel_mm3
    vol_b = int(b.sum()) * voxel_mm3
    if vol_b == 0:
        return 0.0 if vol_a == 0 else float("inf")
    return float((vol_a - vol_b) / vol_b * 100.0)


def _superficie(m: np.ndarray) -> np.ndarray:
    """Camada interna de voxels da mascara com ao menos um vizinho-de-face no fundo."""
    if not m.any():
        return np.zeros_like(m, dtype=bool)
    # conectividade 1 = vizinhanca de face (6 em 3D); border_value=0 => fora do
    # volume conta como fundo, logo estrutura cortada pelo FOV expoe superficie.
    return m & ~binary_erosion(m, structure=None, border_value=0)


def surface_distances(a: Mascara, b: Mascara, spacing: Spacing) -> dict:
    """Distancias de superficie simetricas em mm entre A e B.

    Retorna: assd_mm, hd95_mm, hd_mm, nsd_1mm, nsd_2mm.
    Ver o docstring do modulo para a definicao exata de fronteira e das
    convencoes simetricas usadas.
    """
    a, b = _bool(a), _bool(b)
    if a.shape != b.shape:
        raise ValueError(f"formas diferentes: {a.shape} vs {b.shape}")
    spacing = tuple(float(s) for s in spacing)
    if len(spacing) != a.ndim:
        raise ValueError(f"spacing com {len(spacing)} valores para array {a.ndim}D")

    sa, sb = _superficie(a), _superficie(b)
    vazio_a, vazio_b = not sa.any(), not sb.any()

    if vazio_a and vazio_b:
        return {"assd_mm": 0.0, "hd95_mm": 0.0, "hd_mm": 0.0, "nsd_1mm": 1.0, "nsd_2mm": 1.0}
    if vazio_a or vazio_b:
        nan = float("nan")
        return {"assd_mm": nan, "hd95_mm": nan, "hd_mm": nan, "nsd_1mm": 0.0, "nsd_2mm": 0.0}

    # distancia de cada voxel ate a superficie mais proxima do outro conjunto
    d_ab = distance_transform_edt(~sb, sampling=spacing)[sa]  # A -> B
    d_ba = distance_transform_edt(~sa, sampling=spacing)[sb]  # B -> A

    def nsd(tau: float) -> float:
        dentro = int(np.count_nonzero(d_ab <= tau)) + int(np.count_nonzero(d_ba <= tau))
        return float(dentro / (d_ab.size + d_ba.size))

    # NSD com limiar ANCORADO NO VOXEL, alem dos limiares fixos em mm.
    #
    # Por que: `nsd_1mm` e `nsd_2mm` sao cegos ao eixo mais grosso sempre que o
    # spacing desse eixo excede o limiar. No LCTSC (0,977 x 0,977 x 3,0 mm)
    # NENHUM deslocamento em Z cabe sob 1 mm ou 2 mm — o menor deslocamento
    # possivel em Z ja vale 3,0 mm. As duas colunas creditam apenas concordancia
    # NO PLANO, e por isso nao podem sustentar argumento sobre o eixo Z.
    #
    # O limiar ancorado usa `k x max(spacing)`: e a menor distancia que a grade
    # consegue expressar em TODOS os eixos, entao a metrica deixa de ter um eixo
    # estruturalmente cego. k = 1 e k = 2 sao os mesmos multiplicadores dos
    # limiares fixos, escolhidos por simetria com eles e NAO por produzirem
    # numero melhor. Em grade isotropica de 1 mm as duas familias coincidem.
    passo = float(max(spacing))
    return {
        "assd_mm": float((d_ab.sum() + d_ba.sum()) / (d_ab.size + d_ba.size)),
        "hd95_mm": float(max(np.percentile(d_ab, 95), np.percentile(d_ba, 95))),
        "hd_mm": float(max(d_ab.max(), d_ba.max())),
        "nsd_1mm": nsd(1.0),
        "nsd_2mm": nsd(2.0),
        "nsd_1vox": nsd(1.0 * passo),
        "nsd_2vox": nsd(2.0 * passo),
        "nsd_tau_vox_mm": passo,
    }


def compare_masks(pred: Mascara, gt: Mascara, spacing: Spacing) -> dict:
    """Junta todas as metricas de `pred` contra `gt`, com spacing em mm por eixo."""
    return {
        "dice": dice(pred, gt),
        "iou": iou(pred, gt),
        **surface_distances(pred, gt, spacing),
        "volume_error_pct": volume_error_pct(pred, gt, spacing),
    }


# ---------------------------------------------------------------- CLI / testes


def _zooms_de(affine: np.ndarray) -> np.ndarray:
    """Tamanho de voxel em mm por eixo, a partir do affine (mesma convencao de malha.py)."""
    return np.linalg.norm(affine[:3, :3], axis=0)


def _carregar(caminho: str) -> tuple[np.ndarray, np.ndarray]:
    import nibabel as nib

    img = nib.load(caminho)
    return np.asarray(img.dataobj) > 0.5, img.affine


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Metricas de segmentacao (mm) predicao vs ground-truth.")
    p.add_argument("--prediction", required=True, help="NIfTI da mascara predita")
    p.add_argument("--ground-truth", required=True, help="NIfTI da mascara de referencia")
    p.add_argument(
        "--spacing",
        nargs=3,
        type=float,
        default=None,
        metavar=("SX", "SY", "SZ"),
        help="spacing em mm por eixo; sobrescreve o do affine (obrigatorio se o affine nao trouxer)",
    )
    args = p.parse_args(argv)

    pred, aff_pred = _carregar(args.prediction)
    gt, aff_gt = _carregar(args.ground_truth)

    if args.spacing is not None:
        spacing = tuple(args.spacing)
    else:
        spacing = tuple(_zooms_de(aff_pred))
        if not np.allclose(spacing, _zooms_de(aff_gt), rtol=1e-3):
            raise SystemExit(
                f"spacing divergente entre as imagens ({spacing} vs {tuple(_zooms_de(aff_gt))}); "
                "passe --spacing explicitamente"
            )
        if not np.all(np.isfinite(spacing)) or np.any(np.asarray(spacing) <= 0):
            raise SystemExit("affine sem spacing valido; passe --spacing")

    r = compare_masks(pred, gt, spacing)
    saida = {
        "dice": r["dice"],
        "iou": r["iou"],
        "nsd_1mm": r["nsd_1mm"],
        "nsd_2mm": r["nsd_2mm"],
        "hd95_mm": r["hd95_mm"],
        "assd_mm": r["assd_mm"],
        "volume_error_pct": r["volume_error_pct"],
        "hd_mm": r["hd_mm"],
        "spacing_mm": list(spacing),
    }
    print(json.dumps(saida, indent=2))
    return 0


def _autoteste() -> None:
    """Sanidade: identidade, dilatacao de 1 voxel e mascara real de coracao."""
    from scipy.ndimage import binary_dilation

    spacing = (1.5, 1.0, 2.0)
    cubo = np.zeros((30, 30, 30), dtype=bool)
    cubo[10:20, 10:20, 10:20] = True

    # (1) contra ela mesma
    r = compare_masks(cubo, cubo, spacing)
    assert r["dice"] == 1.0 and r["iou"] == 1.0, r
    assert r["assd_mm"] == 0.0 and r["hd95_mm"] == 0.0 and r["hd_mm"] == 0.0, r
    assert r["nsd_1mm"] == 1.0 and r["nsd_2mm"] == 1.0, r
    assert r["volume_error_pct"] == 0.0, r
    print("(1) identidade:", json.dumps(r))

    # (2) contra dilatacao de 1 voxel (face): HD deve ser ~1 voxel no eixo mais fino
    dil = binary_dilation(cubo, structure=None, iterations=1)
    r2 = compare_masks(dil, cubo, spacing)
    assert r2["dice"] < 1.0, r2
    assert abs(r2["hd_mm"] - max(spacing)) < 1e-9, (r2["hd_mm"], max(spacing))
    assert min(spacing) - 1e-9 <= r2["hd95_mm"] <= max(spacing) + 1e-9, r2
    assert r2["volume_error_pct"] > 0.0, r2
    print("(2) dilatada 1 voxel (spacing", spacing, "):", json.dumps(r2))

    # (3) dado real: heart.nii.gz vs sua propria erosao/dilatacao
    import nibabel as nib

    caminho = ".clinica-dados/torax-alta_masks/heart.nii.gz"
    img = nib.load(caminho)
    heart = np.asarray(img.dataobj) > 0.5
    sp = tuple(_zooms_de(img.affine))
    print("(3) heart.nii.gz", heart.shape, "spacing_mm", sp, "voxels", int(heart.sum()))
    print("    identidade:", json.dumps(compare_masks(heart, heart, sp)))
    print("    dilatada 1 voxel:", json.dumps(compare_masks(binary_dilation(heart), heart, sp)))
    print("OK")


if __name__ == "__main__":
    import sys

    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        raise SystemExit(_main())
