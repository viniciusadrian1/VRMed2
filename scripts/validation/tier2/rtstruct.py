"""RTSTRUCT DICOM -> mascaras NIfTI, via dcmrtstruct2nii.

Duas pegadinhas que o resto do pipeline precisa saber:

1. O dcmrtstruct2nii grava foreground = 255, nao 1. Toda leitura tem que
   limiarizar em > 0.5 — e o que `_bool()` de segmentation_metrics.py faz.
   `carregar_mascara()` aqui faz o mesmo, para nao depender de disciplina.
2. Com `convert_original_dicom=True` ele grava tambem `image.nii.gz`: a serie
   de referencia reamostrada na MESMA grade em que ele rasterizou os contornos.
   E esse arquivo — e nenhuma conversao paralela — que deve alimentar o
   TotalSegmentator, para que predicao e GT compartilhem a grade POR
   CONSTRUCAO em vez de por verificacao otimista.

Os nomes de ROI vem do arquivo, nunca da literatura: use `listar_rois()` antes
de escrever qualquer mapeamento.
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np

PREFIXO_MASCARA = "mask_"  # convencao de nome do dcmrtstruct2nii
NOME_IMAGEM = "image.nii.gz"


def _compat_pydicom() -> None:
    """dcmrtstruct2nii 5 chama `pydicom.read_file`, removido no pydicom 3.

    Restaurar o alias e mais barato — e menos invasivo — do que rebaixar o
    pydicom 3.0.2 que o pipeline de producao usa. `read_file` era so um alias
    depreciado de `dcmread` no pydicom 2.x, mesma assinatura e mesmo retorno.
    """
    import pydicom

    if not hasattr(pydicom, "read_file"):
        pydicom.read_file = pydicom.dcmread


def listar_rois(rtstruct: Path) -> list[str]:
    """Nomes REAIS das ROIs no RTSTRUCT (o mesmo que `dcmrtstruct2nii ls` imprime)."""
    from dcmrtstruct2nii import list_rt_structs

    _compat_pydicom()
    return list(list_rt_structs(str(rtstruct)))


def converter(rtstruct: Path, dicom_dir: Path, saida: Path, estruturas=None) -> dict:
    """Converte o RTSTRUCT em NIfTI (uma mascara por ROI) + `image.nii.gz`.

    Devolve {imagem, mascaras: {roi: caminho}, foreground}.
    """
    from dcmrtstruct2nii import dcmrtstruct2nii as _converter

    _compat_pydicom()
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    _converter(
        str(rtstruct),
        str(dicom_dir),
        str(saida),
        structures=list(estruturas) if estruturas else None,
        gzip=True,
        mask_background_value=0,
        mask_foreground_value=255,  # explicito: e o valor que precisa ser limiarizado
        convert_original_dicom=True,
    )
    imagem = saida / NOME_IMAGEM
    if not imagem.exists():
        raise FileNotFoundError(f"dcmrtstruct2nii nao gravou {imagem}")
    mascaras = {
        p.name[len(PREFIXO_MASCARA) :].removesuffix(".nii.gz"): p
        for p in sorted(saida.glob(f"{PREFIXO_MASCARA}*.nii.gz"))
    }
    return {"imagem": imagem, "mascaras": mascaras, "foreground": 255}


def carregar_mascara(caminho: Path) -> np.ndarray:
    """Booleano com limiar > 0.5 (foreground 255 do dcmrtstruct2nii vira True)."""
    return np.asarray(nib.load(str(caminho)).dataobj) > 0.5
