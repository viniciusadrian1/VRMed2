"""Validacao geometrica de malhas: MASCARA -> MALHA e MASTER -> DERIVADO.

Duas perguntas diferentes:
  1. a reconstrucao (marching cubes + suavizacao) e fiel a mascara?
     -> `comparar_mascara_malha`: rasteriza a malha de volta para a MESMA grade
        da mascara e reaproveita as metricas de segmentacao (Dice/HD95/ASSD).
  2. a decimacao/otimizacao estragou a malha?
     -> `comparar_malhas`: distancia ponto-superficie nos dois sentidos.

Toda distancia sai em mm fisicos; nada e medido em indice de voxel.
Nao ha claim clinico aqui: e controle de qualidade geometrico.
"""

from __future__ import annotations

import numpy as np
import trimesh

from ..geometry.coordinates import gltf_m_para_voxel, zooms_de
from .segmentation_metrics import compare_masks

AMOSTRAS_PADRAO = 20_000


def voxelizar_malha(mesh: trimesh.Trimesh, shape: tuple[int, int, int], affine: np.ndarray) -> np.ndarray:
    """Rasteriza a malha (metros, eixos glTF) de volta para a grade da mascara.

    Os vertices voltam para INDICE DE VOXEL pelas convencoes do projeto e o
    preenchimento e feito pelo vtkPolyDataToImageStencil, que resolve dentro/fora
    por interseccao de raios — nao depende de flood fill 6-conexo, que vaza em
    casca fina de marching cubes.
    """
    import vtk
    from vtk.util import numpy_support as vtknp

    verts = np.ascontiguousarray(gltf_m_para_voxel(mesh.vertices, affine))
    faces = np.asarray(mesh.faces, dtype=np.int64)

    pontos = vtk.vtkPoints()
    pontos.SetData(vtknp.numpy_to_vtk(verts, deep=True))
    celulas = vtk.vtkCellArray()
    celulas.SetData(3, vtknp.numpy_to_vtkIdTypeArray(np.ascontiguousarray(faces).ravel(), deep=True))
    poly = vtk.vtkPolyData()
    poly.SetPoints(pontos)
    poly.SetPolys(celulas)

    stencil = vtk.vtkPolyDataToImageStencil()
    stencil.SetInputData(poly)
    stencil.SetOutputOrigin(0.0, 0.0, 0.0)  # centro do voxel [0,0,0] na origem
    stencil.SetOutputSpacing(1.0, 1.0, 1.0)  # espaco de indice: pitch 1
    stencil.SetOutputWholeExtent(0, shape[0] - 1, 0, shape[1] - 1, 0, shape[2] - 1)
    stencil.SetTolerance(0.0)  # sem tolerancia = decisao pelo raio, sem engordar
    stencil.Update()

    imagem = vtk.vtkImageStencilToImage()
    imagem.SetInputConnection(stencil.GetOutputPort())
    imagem.SetInsideValue(1)
    imagem.SetOutsideValue(0)
    imagem.SetOutputScalarTypeToUnsignedChar()
    imagem.Update()

    bruto = vtknp.vtk_to_numpy(imagem.GetOutput().GetPointData().GetScalars())
    # VTK guarda x variando mais rapido; o array NIfTI e (i, j, k).
    return bruto.reshape(shape[::-1]).transpose(2, 1, 0).astype(bool)


def volume_ml(mesh: trimesh.Trimesh) -> float:
    """Volume fechado da malha em mL (a malha esta em metros)."""
    return abs(float(mesh.volume)) * 1e6  # m3 -> mL


def _erro_pct(medido: float, referencia: float) -> float:
    return float("nan") if referencia == 0 else (medido - referencia) / referencia * 100.0


def comparar_mascara_malha(mask: np.ndarray, mesh: trimesh.Trimesh, affine: np.ndarray) -> dict:
    """Erro da RECONSTRUCAO: mascara original x malha rasterizada na mesma grade."""
    mask = np.asarray(mask) > 0.5
    zooms = zooms_de(affine)
    rasterizada = voxelizar_malha(mesh, mask.shape, affine)
    # a malha e a "predicao", a mascara e a referencia
    metricas = compare_masks(rasterizada, mask, zooms)

    v_mask = float(mask.sum()) * float(np.prod(zooms)) / 1000.0
    v_mesh = volume_ml(mesh)
    return {
        "dice": round(metricas["dice"], 4),
        "hd95_mm": round(metricas["hd95_mm"], 4),
        "assd_mm": round(metricas["assd_mm"], 4),
        "volume_mask_ml": round(v_mask, 3),
        "volume_mesh_ml": round(v_mesh, 3),
        "volume_error_pct": round(_erro_pct(v_mesh, v_mask), 3),
    }


def _distancias_mm(origem: trimesh.Trimesh, alvo: trimesh.Trimesh, n: int, rng) -> np.ndarray:
    """Distancia ponto-superficie (mm) de n pontos amostrados em `origem` ate `alvo`."""
    pontos, _ = trimesh.sample.sample_surface(origem, n, seed=int(rng.integers(1 << 31)))
    _fechado, dist_m, _tid = trimesh.proximity.closest_point(alvo, pontos)
    return np.asarray(dist_m) * 1000.0  # metros -> mm


def comparar_malhas(
    master: trimesh.Trimesh, derivado: trimesh.Trimesh, amostras: int = AMOSTRAS_PADRAO, semente: int = 0
) -> dict:
    """Erro da DECIMACAO/otimizacao: distancia simetrica master x derivado."""
    rng = np.random.default_rng(semente)
    d1 = _distancias_mm(master, derivado, amostras, rng)
    d2 = _distancias_mm(derivado, master, amostras, rng)
    todas = np.concatenate([d1, d2])

    v_master, v_derivado = volume_ml(master), volume_ml(derivado)
    tris_master, tris_derivado = len(master.faces), len(derivado.faces)
    return {
        "hausdorff_mm": round(float(todas.max()), 4),
        "rms_mm": round(float(np.sqrt(np.mean(todas**2))), 4),
        "volume_error_pct": round(_erro_pct(v_derivado, v_master), 3),
        "reducao_tris_pct": round((1.0 - tris_derivado / tris_master) * 100.0, 2),
        "tris_master": tris_master,
        "tris_derivado": tris_derivado,
    }


if __name__ == "__main__":
    import json
    from pathlib import Path

    import fast_simplification
    import nibabel as nib

    from ..clinica.malha import malha_de_volume

    caminho = Path(__file__).resolve().parents[2] / ".clinica-dados" / "torax-alta_masks" / "heart.nii.gz"
    img = nib.load(str(caminho))
    mask = np.asarray(img.dataobj) > 0.5
    malha, _tris_brutos = malha_de_volume(mask, img.affine, afastamento_mm=0.0)

    print(f"mascara {caminho.name}: shape={mask.shape} voxels={int(mask.sum())} tris={len(malha.faces)}")
    r = comparar_mascara_malha(mask, malha, img.affine)
    print("mascara x malha:", json.dumps(r, indent=2))
    assert r["dice"] > 0.9, f"Dice {r['dice']} < 0.9 — conversao de coordenadas errada"

    v, f = fast_simplification.simplify(
        malha.vertices.astype(np.float32), malha.faces.astype(np.int64), target_count=int(len(malha.faces) * 0.3)
    )
    derivado = trimesh.Trimesh(vertices=v, faces=f, process=True)
    print("master x derivado:", json.dumps(comparar_malhas(malha, derivado), indent=2))
