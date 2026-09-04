"""Nomes de ROI do ground truth LCTSC -> nomes de saida do TotalSegmentator.

O GT contorna o pulmao INTEIRO por lado; o TotalSegmentator (tarefa `total`)
entrega lobo a lobo. Entao Lung_L e Lung_R sao UNIOES de lobos — feitas aqui,
no lado da predicao, nunca dividindo o GT.

CAVEATS que pertencem a interpretacao das metricas, nao a ingestao (registre-os
no relatorio; NAO os "conserte" silenciosamente recortando mascara):
  - As definicoes de contorno NAO sao identicas. Medido em LCTSC-Train-S1-001:
    o GT "Heart" ocupa 27 fatias em Z (35-61) contra 41 da predicao `heart`
    (35-75), com volume total parecido — o contorno de radioterapia e mais
    curto e mais largo que o orgao que o TotalSegmentator delimita. Parte do
    Dice que sobrar ai e diferenca de convencao, nao erro de segmentacao.
  - Em geral o GT so existe na extensao em Z que o contornador escolheu, e o
    TotalSegmentator preenche todo o campo de visao. Nesse caso Esophagus e
    SpinalCord bateram em extensao, mas isso e observacao de UM caso, nao
    garantia — cheque antes de agregar varios casos.

Os nomes de ROI do GT sao normalizados (minusculas, sem espacos/underscores)
porque variam de caso para caso; a chave canonica e a da literatura, o nome
REAL vem sempre de `rtstruct.listar_rois()`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# ROI canonica do LCTSC -> estruturas da tarefa `total` do TotalSegmentator.
MAPA_LCTSC: dict[str, tuple[str, ...]] = {
    "Esophagus": ("esophagus",),
    "Heart": ("heart",),
    "Lung_L": ("lung_upper_lobe_left", "lung_lower_lobe_left"),
    "Lung_R": ("lung_upper_lobe_right", "lung_middle_lobe_right", "lung_lower_lobe_right"),
    "SpinalCord": ("spinal_cord",),
}


def _chave(nome: str) -> str:
    return nome.strip().lower().replace("_", "").replace(" ", "").replace("-", "")


_CANONICO = {_chave(k): k for k in MAPA_LCTSC}


def canonizar(nome_real: str) -> str | None:
    """Nome REAL lido do RTSTRUCT -> chave canonica do MAPA_LCTSC (None se nao mapeada)."""
    return _CANONICO.get(_chave(nome_real))


def roi_subset() -> list[str]:
    """Lista plana de estruturas do TotalSegmentator necessarias para este GT."""
    return sorted({n for alvos in MAPA_LCTSC.values() for n in alvos})


def unir_predicao(masks_dir: Path, alvos) -> tuple[np.ndarray, Path]:
    """Uniao booleana das mascaras do TotalSegmentator listadas em `alvos`.

    Devolve (mascara, caminho_de_referencia_geometrica). O caminho e o do
    primeiro alvo — e o arquivo contra o qual a Parte K checa a grade.
    """
    import nibabel as nib

    masks_dir = Path(masks_dir)
    caminhos = [masks_dir / f"{n}.nii.gz" for n in alvos]
    faltando = [str(p) for p in caminhos if not p.exists()]
    if faltando:
        raise FileNotFoundError(f"mascara(s) ausente(s) do TotalSegmentator: {faltando}")

    uniao = None
    for p in caminhos:
        m = np.asarray(nib.load(str(p)).dataobj) > 0.5
        uniao = m if uniao is None else (uniao | m)
    return uniao, caminhos[0]
