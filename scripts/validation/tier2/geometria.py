"""Parte K — controle de geometria entre predicao e ground truth.

Regra: um Dice so significa alguma coisa se as duas mascaras estiverem NA MESMA
GRADE. Este modulo verifica isso e FALHA ALTO (`DesalinhamentoGeometrico`) em
vez de avisar em silencio e deixar o numero ruim sair como "erro de modelo".

Tres verificacoes independentes:

1. `descrever_nifti` / `verificar_alinhamento` — shape, zooms, affine, origem,
   orientacao (codigos de eixo), determinante. Os zooms saem de
   `header.get_zooms()`, NAO de `np.diag(affine)`: a diagonal do affine so
   coincide com o tamanho do voxel quando nao ha rotacao, e num RTSTRUCT
   reamostrado essa hipotese nao se sustenta sozinha.
2. `metadados_dicom` — o que a Parte K exige para reproduzir a comparacao a
   partir do DICOM original: ImagePositionPatient da primeira e da ultima
   fatia, ImageOrientationPatient, spacing, e a ordem em que as fatias foram
   lidas.
3. `checar_flip_eixo` — sanidade de INVERSAO DE EIXO. Duas mascaras com volume
   parecido em mm e Dice quase zero nao sao um modelo ruim: sao um eixo
   invertido. Isso e reportado como tal, com nome proprio.
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np

from ..segmentation_metrics import dice as _dice

TOL = 1e-4


class DesalinhamentoGeometrico(AssertionError):
    """Predicao e ground truth nao estao na mesma grade — comparar seria mentira."""


def descrever_nifti(caminho: Path) -> dict:
    """Geometria completa de um NIfTI, do jeito que a Parte K pede."""
    img = nib.load(str(caminho))
    affine = np.asarray(img.affine, dtype=float)
    zooms = tuple(float(z) for z in img.header.get_zooms()[:3])  # header, nao diag(affine)
    return {
        "caminho": str(caminho),
        "shape": tuple(int(s) for s in img.shape[:3]),
        "zooms_mm": zooms,
        "affine": affine.tolist(),
        "origem_mm": [float(v) for v in affine[:3, 3]],
        "orientacao": "".join(nib.aff2axcodes(affine)),
        "determinante": float(np.linalg.det(affine[:3, :3])),
    }


def verificar_alinhamento(
    caminho_a: Path,
    caminho_b: Path,
    rotulos: tuple[str, str] = ("predicao", "ground_truth"),
    tol: float = TOL,
) -> dict:
    """Compara a geometria de dois NIfTI. Levanta DesalinhamentoGeometrico se divergir.

    Devolve o dicionario com as duas descricoes, as diferencas e o veredito.
    """
    a, b = descrever_nifti(caminho_a), descrever_nifti(caminho_b)
    aff_a, aff_b = np.array(a["affine"]), np.array(b["affine"])

    falhas = []
    if a["shape"] != b["shape"]:
        falhas.append(f"shape {a['shape']} != {b['shape']}")
    if not np.allclose(a["zooms_mm"], b["zooms_mm"], atol=tol, rtol=0):
        falhas.append(f"zooms {a['zooms_mm']} != {b['zooms_mm']}")
    if not np.allclose(aff_a, aff_b, atol=tol, rtol=0):
        falhas.append(f"affine difere (max |delta| = {float(np.abs(aff_a - aff_b).max()):.6g})")
    if a["orientacao"] != b["orientacao"]:
        falhas.append(f"orientacao {a['orientacao']} != {b['orientacao']}")

    resultado = {
        rotulos[0]: a,
        rotulos[1]: b,
        "tolerancia": tol,
        "delta_affine_max": float(np.abs(aff_a - aff_b).max()),
        "delta_origem_mm": [float(v) for v in (aff_a[:3, 3] - aff_b[:3, 3])],
        "alinhado": not falhas,
        "falhas": falhas,
        "veredito": "mesma grade" if not falhas else "GRADES DIFERENTES",
    }
    if falhas:
        raise DesalinhamentoGeometrico(
            f"{rotulos[0]} x {rotulos[1]}: " + "; ".join(falhas) + " — comparacao invalida"
        )
    return resultado


def metadados_dicom(dicom_dir: Path) -> dict:
    """Metadados de geometria da serie DICOM original (pydicom, sem pixels).

    As fatias sao ordenadas pela projecao do ImagePositionPatient na normal do
    plano (produto vetorial das duas direcoes do ImageOrientationPatient) — o
    unico criterio espacial correto; InstanceNumber e so um rotulo.
    """
    import pydicom

    arquivos = sorted(Path(dicom_dir).glob("*.dcm"))
    if not arquivos:
        raise FileNotFoundError(f"nenhum .dcm em {dicom_dir}")

    fatias = []
    for f in arquivos:
        ds = pydicom.dcmread(str(f), stop_before_pixels=True)
        if not hasattr(ds, "ImagePositionPatient"):
            continue
        fatias.append((f, ds))
    if not fatias:
        raise ValueError(f"nenhuma fatia com ImagePositionPatient em {dicom_dir}")

    iop = [float(v) for v in fatias[0][1].ImageOrientationPatient]
    normal = np.cross(np.array(iop[:3]), np.array(iop[3:]))
    fatias.sort(key=lambda par: float(np.dot(np.array(par[1].ImagePositionPatient, float), normal)))

    posicoes = np.array([[float(v) for v in ds.ImagePositionPatient] for _, ds in fatias])
    projecoes = posicoes @ normal
    diffs = np.diff(projecoes)
    primeiro, ultimo = fatias[0][1], fatias[-1][1]

    def _tag(ds, nome):
        v = getattr(ds, nome, None)
        return float(v) if v is not None else None

    return {
        "n_fatias": len(fatias),
        "criterio_ordenacao": "projecao de ImagePositionPatient na normal de ImageOrientationPatient",
        "image_orientation_patient": iop,
        "normal_do_plano": [float(v) for v in normal],
        "ipp_primeira_fatia": [float(v) for v in posicoes[0]],
        "ipp_ultima_fatia": [float(v) for v in posicoes[-1]],
        "arquivo_primeira_fatia": fatias[0][0].name,
        "arquivo_ultima_fatia": fatias[-1][0].name,
        "pixel_spacing_mm": [float(v) for v in primeiro.PixelSpacing],
        "slice_thickness_mm": _tag(primeiro, "SliceThickness"),
        "spacing_between_slices_mm": _tag(primeiro, "SpacingBetweenSlices"),
        "espacamento_z_mediano_mm": float(np.median(diffs)) if diffs.size else None,
        "espacamento_z_uniforme": bool(diffs.size and np.allclose(diffs, diffs[0], atol=1e-3)),
        "z_cresce_na_ordem_lida": bool(posicoes[-1][2] > posicoes[0][2]),
        "instance_number_primeira": getattr(primeiro, "InstanceNumber", None),
        "instance_number_ultima": getattr(ultimo, "InstanceNumber", None),
    }


def checar_flip_eixo(
    pred: np.ndarray,
    gt: np.ndarray,
    spacing,
    limiar_dice: float = 0.10,
    tol_volume: float = 0.25,
) -> dict:
    """Sanidade de inversao de eixo: volume parecido + Dice ~0 = eixo invertido.

    Nao "corrige" nada — so nomeia o problema, para nao sair como Dice ruim.
    """
    pred, gt = np.asarray(pred) > 0.5, np.asarray(gt) > 0.5
    voxel_mm3 = float(np.prod(np.asarray(spacing, dtype=float)))
    v_pred, v_gt = int(pred.sum()) * voxel_mm3, int(gt.sum()) * voxel_mm3
    d = _dice(pred, gt)
    base = {
        "dice": d,
        "volume_pred_mm3": v_pred,
        "volume_gt_mm3": v_gt,
        "razao_volume": (min(v_pred, v_gt) / max(v_pred, v_gt)) if max(v_pred, v_gt) > 0 else None,
        "eixo_invertido": None,
        "dice_apos_flip": None,
    }
    if v_pred == 0 or v_gt == 0:
        return {**base, "veredito": "mascara vazia — teste de inversao nao aplicavel"}
    if d >= limiar_dice:
        return {**base, "veredito": "sem suspeita de inversao de eixo"}
    if base["razao_volume"] < 1.0 - tol_volume:
        return {
            **base,
            "veredito": "dice baixo com volumes divergentes — nao e inversao de eixo",
        }

    flips = {eixo: _dice(np.flip(pred, axis=eixo), gt) for eixo in range(pred.ndim)}
    melhor = max(flips, key=flips.get)
    base["dice_apos_flip"] = {str(k): v for k, v in flips.items()}
    if flips[melhor] > max(0.5, 3 * d):
        return {
            **base,
            "eixo_invertido": int(melhor),
            "veredito": (
                f"INVERSAO DE EIXO no eixo {melhor} do array "
                f"(dice {d:.3f} -> {flips[melhor]:.3f} apos flip) — nao e erro de modelo"
            ),
        }
    return {
        **base,
        "veredito": (
            "dice baixo com volumes parecidos, mas nenhum flip de eixo unico explica — "
            "investigar translacao/rotacao antes de atribuir ao modelo"
        ),
    }


# ------------------------------------------------------------------ autoteste


def _autoteste() -> None:
    """Sanidade minima: alinhamento identico passa, grade diferente falha, flip e detectado."""
    import tempfile

    cubo = np.zeros((24, 24, 24), dtype=np.uint8)
    cubo[4:12, 6:18, 6:18] = 1  # assimetrico no eixo 0 para o flip ser detectavel
    aff = np.diag([1.5, 1.5, 3.0, 1.0])

    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a.nii.gz"
        b = Path(td) / "b.nii.gz"
        c = Path(td) / "c.nii.gz"
        nib.save(nib.Nifti1Image(cubo, aff), str(a))
        nib.save(nib.Nifti1Image(cubo, aff), str(b))
        deslocado = aff.copy()
        deslocado[2, 3] += 1.0
        nib.save(nib.Nifti1Image(cubo, deslocado), str(c))

        r = verificar_alinhamento(a, b)
        assert r["alinhado"] and r["veredito"] == "mesma grade", r
        assert r["predicao"]["zooms_mm"] == (1.5, 1.5, 3.0), r["predicao"]["zooms_mm"]

        try:
            verificar_alinhamento(a, c)
        except DesalinhamentoGeometrico as e:
            assert "affine" in str(e), e
        else:
            raise AssertionError("grade deslocada passou pelo assert de alinhamento")

    spacing = (1.5, 1.5, 3.0)
    ok = checar_flip_eixo(cubo, cubo, spacing)
    assert ok["veredito"] == "sem suspeita de inversao de eixo", ok
    inv = checar_flip_eixo(np.flip(cubo, axis=0), cubo, spacing)
    assert inv["eixo_invertido"] == 0, inv
    menor = np.zeros_like(cubo)
    menor[4:6, 6:18, 6:18] = 1
    outro = np.zeros_like(cubo)
    outro[18:20, 6:18, 6:18] = 1
    dif = checar_flip_eixo(menor * 0 + outro, cubo, spacing)
    assert "volumes divergentes" in dif["veredito"], dif
    print("geometria.py: autoteste OK")


if __name__ == "__main__":
    _autoteste()
