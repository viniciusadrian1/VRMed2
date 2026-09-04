"""Transformacoes espaciais canonicas do VRmed.

Espacos usados no pipeline:
  voxel   -> indice do array NIfTI (i, j, k), sem unidade
  RAS mm  -> mundo fisico do NIfTI (affine), em milimetros
  glTF m  -> mundo do visualizador (Y para cima, Z para frente), em metros

Nada aqui assume affine diagonal: usamos a matriz 3x3 completa.
"""

from __future__ import annotations

import numpy as np

# Rotacao pura (det +1) que leva RAS -> convencao glTF.
RAS_PARA_GLTF: np.ndarray = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
# Rotacao => inversa e a transposta.
GLTF_PARA_RAS: np.ndarray = RAS_PARA_GLTF.T

MM_PARA_M: float = 0.001
M_PARA_MM: float = 1000.0


def _pontos(pts: np.ndarray) -> np.ndarray:
    """Valida e normaliza a entrada para float (N,3)."""
    arr = np.asarray(pts, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"esperado array (N,3), recebido {arr.shape}")
    return arr


def zooms_de(affine: np.ndarray) -> np.ndarray:
    """Tamanho do voxel em mm por eixo (norma das colunas da parte linear)."""
    return np.linalg.norm(np.asarray(affine, dtype=np.float64)[:3, :3], axis=0)


def voxel_para_ras_mm(pts_voxel: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """Indice de voxel -> mm no espaco RAS do NIfTI."""
    aff = np.asarray(affine, dtype=np.float64)
    return _pontos(pts_voxel) @ aff[:3, :3].T + aff[:3, 3]


def ras_mm_para_voxel(pts_mm: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """mm RAS -> indice de voxel (continuo, sem arredondar)."""
    inv = np.linalg.inv(np.asarray(affine, dtype=np.float64))
    return _pontos(pts_mm) @ inv[:3, :3].T + inv[:3, 3]


def ras_mm_para_gltf_m(pts_mm: np.ndarray) -> np.ndarray:
    """mm RAS -> metros no espaco glTF."""
    return (_pontos(pts_mm) @ RAS_PARA_GLTF.T) * MM_PARA_M


def gltf_m_para_ras_mm(pts_gltf: np.ndarray) -> np.ndarray:
    """metros glTF -> mm RAS."""
    return (_pontos(pts_gltf) * M_PARA_MM) @ RAS_PARA_GLTF


def voxel_para_gltf_m(pts_voxel: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """Indice de voxel -> metros glTF."""
    return ras_mm_para_gltf_m(voxel_para_ras_mm(pts_voxel, affine))


def gltf_m_para_voxel(pts_gltf: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """metros glTF -> indice de voxel (continuo)."""
    return ras_mm_para_voxel(gltf_m_para_ras_mm(pts_gltf), affine)


def _round_trip(nome: str, affine: np.ndarray, rng: np.random.Generator) -> None:
    pts_vox = rng.uniform(0.0, 256.0, size=(5000, 3))
    volta = gltf_m_para_voxel(voxel_para_gltf_m(pts_vox, affine), affine)
    erro_vox = np.abs(volta - pts_vox).max()

    pts_mm = voxel_para_ras_mm(pts_vox, affine)
    erro_mm = np.abs(gltf_m_para_ras_mm(ras_mm_para_gltf_m(pts_mm)) - pts_mm).max()

    print(f"[{nome}]")
    print(f"  zooms (mm)              : {np.round(zooms_de(affine), 6)}")
    print(f"  det(3x3)                : {np.linalg.det(np.asarray(affine)[:3, :3]):.6f}")
    print(f"  erro max voxel->gltf->voxel : {erro_vox:.3e}")
    print(f"  erro max mm->gltf->mm       : {erro_mm:.3e}")
    assert erro_vox < 1e-6 and erro_mm < 1e-6, "round-trip fora da tolerancia"


if __name__ == "__main__":
    from pathlib import Path

    import nibabel as nib

    rng = np.random.default_rng(0)

    caminho = Path(__file__).resolve().parents[2] / ".clinica-dados" / "torax-alta_masks" / "heart.nii.gz"
    affine_real = nib.load(str(caminho)).affine
    print(f"affine real ({caminho.name}):\n{np.round(affine_real, 6)}")
    _round_trip("affine real", affine_real, rng)

    # Affine obliqua sintetica: rotacao de 15 graus em torno de X, spacing anisotropico.
    t = np.deg2rad(15.0)
    rot = np.array([[1.0, 0.0, 0.0], [0.0, np.cos(t), -np.sin(t)], [0.0, np.sin(t), np.cos(t)]])
    affine_obliqua = np.eye(4)
    affine_obliqua[:3, :3] = rot @ np.diag([0.7, 0.7, 2.5])
    affine_obliqua[:3, 3] = [-180.5, 12.25, -400.75]
    print(f"\naffine obliqua sintetica:\n{np.round(affine_obliqua, 6)}")
    _round_trip("affine obliqua 15 graus", affine_obliqua, rng)

    print("\nOK: round-trips dentro da tolerancia.")
