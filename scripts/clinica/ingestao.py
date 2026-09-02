"""
Etapa 1 — ingestão: série DICOM | NRRD | NIfTI → NIfTI (.nii.gz) em unidades
Hounsfield, com espaçamento real e validação de entrada.

- DICOM: SimpleITK ordena as fatias pela posição (ImagePositionPatient), não
  pelo nome do arquivo, e aplica RescaleSlope/Intercept (→ HU).
- Espaçamento vem de img.GetSpacing() (PixelSpacing + distância real entre
  fatias) — nunca de np.diag(affine), que erra em exame oblíquo.
- Validação: fatia > 3 mm avisa ("escadinha"); intensidades fora de HU
  rejeitam (a segmentação e as cores dependem de HU de verdade).

Checagem rápida:
  python scripts/clinica/ingestao.py <dicom_dir|arquivo> <saida.nii.gz> [referencia.nii.gz]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import SimpleITK as sitk

ESPESSURA_MAX_MM = 3.0  # acima disso o modelo sai em degraus (plano, etapa 1)
LPS_PARA_RAS = np.diag([-1.0, -1.0, 1.0])  # SimpleITK é LPS; o resto do pipeline é RAS


class EntradaInvalida(ValueError):
    """Exame que não serve como entrada do pipeline (mensagem já em pt-BR)."""


def _serie_dicom(pasta: Path, serie: str | None, log) -> tuple[sitk.Image, dict, list[float]]:
    reader = sitk.ImageSeriesReader()
    ids = list(reader.GetGDCMSeriesIDs(str(pasta)))
    if not ids:
        raise EntradaInvalida(f"nenhuma série DICOM em {pasta}")
    por_serie = {uid: reader.GetGDCMSeriesFileNames(str(pasta), uid) for uid in ids}
    if serie is None:
        # A aquisição principal é a série com mais fatias (scouts têm 1–3).
        serie = max(por_serie, key=lambda uid: len(por_serie[uid]))
        if len(ids) > 1:
            # UID só no console (para --serie); no relatório seria dado identificável.
            log(f"{len(ids)} séries na pasta; usando a de mais fatias ({len(por_serie[serie])}, --serie {serie})")
    if serie not in por_serie:
        raise EntradaInvalida(f"série {serie} não está em {pasta}")
    arquivos = por_serie[serie]  # já ordenados por ImagePositionPatient
    reader.SetFileNames(arquivos)
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()
    img = reader.Execute()  # GDCM aplica RescaleSlope/Intercept → HU

    def tag(i: int, chave: str) -> str:
        return reader.GetMetaData(i, chave).strip() if reader.HasMetaDataKey(i, chave) else ""

    posicoes = []
    for i in range(len(arquivos)):
        ipp = tag(i, "0020|0032")
        if ipp:
            posicoes.append(np.array([float(v) for v in ipp.split("\\")]))
    passos = [float(np.linalg.norm(b - a)) for a, b in zip(posicoes, posicoes[1:])]
    meta = {
        "fatias": len(arquivos),
        "modalidade": tag(0, "0008|0060"),
        "fabricante": tag(0, "0008|0070"),
        "kvp": tag(0, "0018|0060"),
        "contraste": tag(0, "0018|0010"),
        "espessura_tag_mm": tag(0, "0018|0050"),
        "rescale_slope": tag(0, "0028|1053"),
        "rescale_intercept": tag(0, "0028|1052"),
        # Só o FATO de estar vazio — nunca o valor (dados públicos anonimizados).
        "paciente_anonimizado": tag(0, "0010|0010").upper() in ("", "ANONYMOUS", "ANONYMIZED"),
    }
    return img, meta, passos


def validar(img: sitk.Image, passos: list[float], forcar: bool) -> tuple[list[str], dict]:
    """Avisos (lista) + estatísticas; levanta EntradaInvalida se não for HU."""
    avisos: list[str] = []
    sz = max(img.GetSpacing())  # eixo mais grosso = direção de fatia (NIfTI/NRRD: qualquer índice)
    arr = sitk.GetArrayViewFromImage(img)
    sub = arr[::4, ::4, ::4]
    stats = {
        "hu_min": float(arr.min()),
        "hu_mediana": float(np.median(sub)),
        "hu_max": float(arr.max()),
    }
    # HU de verdade tem ar/pulmão/gás ≈ -1000. Bruto sem rescale fica em 0..4095
    # (min ≥ 0) ou, com padding negativo (GE: -2000 fora do FOV), tem o ar em
    # ~+24 — nenhum dos dois cai nesta banda. A mediana NÃO serve de critério:
    # mede o enquadramento (CTA recortada ao coração tem mediana +40 e é HU).
    fracao_ar = float(((sub > -1100) & (sub < -900)).mean())
    if sz > ESPESSURA_MAX_MM:
        avisos.append(
            f"fatias de {sz:.2f} mm (> {ESPESSURA_MAX_MM:.0f} mm): o modelo sai em degraus — "
            "prefira uma série fina (TC cardíaca boa fica em 0,5–1,25 mm)"
        )
    if passos:
        pmin, pmax = min(passos), max(passos)
        if pmax - pmin > 0.05 * max(pmax, 1e-6):
            avisos.append(
                f"passo entre fatias irregular ({pmin:.2f}–{pmax:.2f} mm): fatias faltando ou série mista"
            )
    if not (stats["hu_min"] <= -900 and fracao_ar >= 0.01):
        msg = (
            f"intensidades não parecem HU (min {stats['hu_min']:.0f}, esperado ≤ -900; "
            f"{fracao_ar:.1%} dos voxels perto de -1000 HU, esperado ≥ 1%): "
            "RescaleSlope/Intercept não aplicados?"
        )
        if not forcar:
            raise EntradaInvalida(msg)
        avisos.append(msg)
    direcao = np.array(img.GetDirection()).reshape(3, 3)
    if np.abs(np.abs(direcao) - np.eye(3)).max() > 0.01:
        avisos.append(
            "orientação oblíqua (gantry tilt?): tc-para-vrmed.py assume affine diagonal — "
            "reamostrar antes da malha"
        )
    return avisos, stats


def salvar_nifti(img: sitk.Image, destino: Path) -> None:
    """int16 (HU cabe com folga) + gzip. SimpleITK escreve qform/sform em RAS —
    o nibabel do resto do pipeline lê o affine certo."""
    arr = sitk.GetArrayFromImage(img)
    arr16 = np.clip(np.rint(arr), -32768, 32767).astype(np.int16)
    saida = sitk.GetImageFromArray(arr16)
    saida.CopyInformation(img)
    destino.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(saida, str(destino), useCompression=True)


def ingerir(
    entrada: Path,
    destino: Path,
    serie: str | None = None,
    forcar: bool = False,
    log=print,
) -> dict:
    """Entrada (pasta DICOM ou arquivo) → destino .nii.gz em HU. Devolve o
    resumo para o relatório (shape, spacing, HU, metadados não identificáveis, avisos)."""
    inicio = time.time()
    if entrada.is_dir():
        img, meta, passos = _serie_dicom(entrada, serie, log)
        origem = "dicom"
    else:
        img = sitk.ReadImage(str(entrada))
        meta, passos, origem = {}, [], entrada.suffix.lstrip(".") or "arquivo"
    if img.GetDimension() != 3:
        raise EntradaInvalida(f"volume {img.GetDimension()}D (multi-fase?) — escolha uma fase 3D")
    if img.GetNumberOfComponentsPerPixel() != 1:
        raise EntradaInvalida("imagem não escalar (RGB?) — não é uma TC")

    avisos, stats = validar(img, passos, forcar)
    salvar_nifti(img, destino)
    for aviso in avisos:
        log(f"AVISO: {aviso}")
    return {
        "entrada": str(entrada),
        "origem": origem,
        "saida": str(destino),
        "shape_xyz": list(img.GetSize()),
        "spacing_mm": [round(v, 4) for v in img.GetSpacing()],
        # Em RAS (SimpleITK devolve LPS): mesma convenção de ct.nii.gz e bbox_mm.
        "origem_mm_ras": [round(float(v), 2) for v in LPS_PARA_RAS @ np.array(img.GetOrigin())],
        "direcao_ras": [
            round(float(v), 4)
            for v in (LPS_PARA_RAS @ np.array(img.GetDirection()).reshape(3, 3)).ravel()
        ],
        **stats,
        "meta": meta,
        "avisos": avisos,
        "tempo_s": round(time.time() - inicio, 1),
    }


def _checagem(argv: list[str]) -> int:
    """Roda a ingestão e, se houver referência, confere shape/zooms/HU contra
    um NIfTI já aceito (regressão: o LIDC convertido ad hoc em agosto)."""
    import nibabel as nib

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # stdout em pipe no Windows é cp1252
    if len(argv) < 2:
        print(__doc__)
        return 2
    info = ingerir(Path(argv[0]), Path(argv[1]))
    print({k: v for k, v in info.items() if k != "direcao_ras"})
    if len(argv) < 3:
        return 0
    novo, ref = nib.load(argv[1]), nib.load(argv[2])
    a, b = np.asarray(novo.dataobj), np.asarray(ref.dataobj)
    assert novo.shape == ref.shape, (novo.shape, ref.shape)
    assert np.allclose(novo.header.get_zooms(), ref.header.get_zooms(), atol=1e-3)
    assert np.allclose(novo.affine, ref.affine, atol=0.01), "affine diferente"
    assert float(np.abs(a.astype(np.float32) - b.astype(np.float32)).max()) <= 1.0, "HU diferente"
    print("OK: idêntico à referência (shape, zooms, affine, HU)")
    return 0


if __name__ == "__main__":
    sys.exit(_checagem(sys.argv[1:]))
