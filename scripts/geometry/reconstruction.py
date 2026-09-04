"""
Fase 1 — extração de superfície: 4 métodos comparáveis atrás de uma API só.

Todos devolvem a malha em METROS nos eixos glTF (mesma convenção de
`scripts/clinica/malha.py`), então volume, centróide e contagem de triângulos
podem ser comparados lado a lado.

- "marching_cubes": baseline A, reproduz `malha_de_volume` (gaussiana na ocupação
  + skimage + Taubin).
- "surface_nets": vtkSurfaceNets3D sobre o rótulo, sem borrar a ocupação.
- "flying_edges": vtkFlyingEdges3D no mesmo campo suavizado do baseline.
- "sdf": suaviza o zero-level-set de uma SDF em mm em vez de borrar a ocupação.

Sem claim clínico: são variações geométricas para medir, não para diagnosticar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import trimesh

# Idênticas às de scripts/clinica/malha.py — rotação pura RAS→glTF, det +1.
RAS_PARA_GLTF = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
MM_PARA_M = 0.001

MIN_VOXELS = 50  # abaixo disso é ruído/estrutura ausente
METODOS = ("marching_cubes", "surface_nets", "flying_edges", "sdf")


class SuperficieVazia(RuntimeError):
    """A extração não produziu geometria (estrutura fina dissolvida pela suavização)."""


@dataclass
class ResultadoSuperficie:
    """Malha em metros/eixos glTF + a receita que a produziu."""

    mesh: trimesh.Trimesh
    tris_brutos: int  # triângulos antes da suavização (depois do process=True)
    metodo: str
    suavizacao: str
    params: dict[str, Any] = field(default_factory=dict)
    tempo_s: float = 0.0


def zooms_de(affine: np.ndarray) -> np.ndarray:
    return np.linalg.norm(affine[:3, :3], axis=0)


def _sigma_padrao(zooms: np.ndarray) -> float:
    return max(0.6, 0.5 * float(zooms.max()))


def _campo_suavizado(mask: np.ndarray, zooms: np.ndarray, sigma_mm: float) -> np.ndarray:
    """Ocupação padded 1 voxel e borrada — o pad fecha a estrutura cortada pelo FOV."""
    from scipy import ndimage

    return ndimage.gaussian_filter(np.pad(mask.astype(np.float32), 1), sigma=sigma_mm / zooms, mode="constant")


def _finalizar(
    verts_vox: np.ndarray,
    faces: np.ndarray,
    affine: np.ndarray,
    *,
    suavizar_taubin: bool,
    taubin_iters: int,
    offset_mm: float,
) -> tuple[trimesh.Trimesh, int]:
    """Índice de voxel → mm RAS → glTF(m), + Taubin/normais/afastamento.

    Levanta SuperficieVazia quando não sobrou geometria (estrutura dissolvida
    pela suavização) — quem chama traduz para "ausente" em vez de quebrar.
    """
    if len(faces) == 0 or len(verts_vox) == 0:
        raise SuperficieVazia("isosuperfície vazia: a estrutura não sobreviveu à suavização")
    verts_mm = verts_vox @ affine[:3, :3].T + affine[:3, 3]
    malha = trimesh.Trimesh(vertices=(verts_mm @ RAS_PARA_GLTF.T) * MM_PARA_M, faces=faces, process=True)
    tris_brutos = len(malha.faces)
    if suavizar_taubin and taubin_iters > 0:
        # nu POSITIVO é o unshrink no trimesh; iterações pares = shrink+inflate.
        trimesh.smoothing.filter_taubin(malha, lamb=0.5, nu=0.53, iterations=taubin_iters)
    malha.fix_normals(multibody=True)  # marching cubes sai com normal para dentro
    if offset_mm > 0:
        malha.vertices = malha.vertices - malha.vertex_normals * (offset_mm * MM_PARA_M)
    return malha, tris_brutos


def _para_vtk_image(campo: np.ndarray):
    """numpy (i,j,k) → vtkImageData com spacing 1 e origem 0 (coordenada = índice de voxel)."""
    import vtk
    from vtk.util import numpy_support

    img = vtk.vtkImageData()
    img.SetDimensions(*campo.shape)
    img.SetSpacing(1.0, 1.0, 1.0)
    img.SetOrigin(0.0, 0.0, 0.0)
    # VTK varre x primeiro; ravel em ordem F casa com SetDimensions(i,j,k).
    arr = numpy_support.numpy_to_vtk(np.ascontiguousarray(campo.ravel(order="F")), deep=True)
    arr.SetName("campo")
    img.GetPointData().SetScalars(arr)
    return img


def _do_polydata(pd) -> tuple[np.ndarray, np.ndarray]:
    from vtk.util import numpy_support

    # Isosuperfície vazia (estrutura dissolvida pela suavização, p.ex. um vaso
    # fino): o VTK devolve polydata sem pontos e GetPoints() vira None. Sem esta
    # guarda o filtro estourava AttributeError em vez de reportar "ausente".
    pontos_vtk = pd.GetPoints()
    if pontos_vtk is None or pd.GetNumberOfPolys() == 0:
        return np.empty((0, 3), dtype=np.float64), np.empty((0, 3), dtype=np.int64)

    pontos = numpy_support.vtk_to_numpy(pontos_vtk.GetData()).astype(np.float64)
    conect = numpy_support.vtk_to_numpy(pd.GetPolys().GetConnectivityArray())
    return pontos, conect.reshape(-1, 3)


def reconstruct_surface(
    mask: np.ndarray,
    affine: np.ndarray,
    *,
    method: str = "marching_cubes",
    smoothing: str = "auto",
    sigma_mm: float | None = None,
    taubin_iters: int = 4,
    offset_mm: float = 0.0,
    level: float = 0.5,
) -> ResultadoSuperficie | None:
    """Máscara binária → superfície em metros/eixos glTF. None se < 50 voxels.

    smoothing: "auto" (o suavizador natural do método), "none", "taubin" ou
    "windowed_sinc" (só muda algo no flying_edges).

    Devolve None também quando a estrutura NÃO SOBREVIVE à suavização (vaso fino
    dissolvido: o campo nunca alcança `level`). É perda total, não erro de
    programação — por isso vira "ausente" e não exceção.
    """
    try:
        return _reconstruir(
            mask, affine, method=method, smoothing=smoothing, sigma_mm=sigma_mm,
            taubin_iters=taubin_iters, offset_mm=offset_mm, level=level,
        )
    except SuperficieVazia:
        return None
    except ValueError as e:
        # skimage: "Surface level must be within volume data range" = mesmo caso.
        if "within volume data range" in str(e):
            return None
        raise


def _reconstruir(
    mask: np.ndarray,
    affine: np.ndarray,
    *,
    method: str,
    smoothing: str,
    sigma_mm: float | None,
    taubin_iters: int,
    offset_mm: float,
    level: float,
) -> ResultadoSuperficie | None:
    if method not in METODOS:
        raise ValueError(f"método desconhecido: {method!r} (use um de {METODOS})")
    mask = np.asarray(mask) > 0.5
    if int(mask.sum()) < MIN_VOXELS:
        return None

    zooms = zooms_de(affine)
    if sigma_mm is None:
        sigma_mm = _sigma_padrao(zooms)
    suave = smoothing != "none"
    t0 = time.perf_counter()
    params: dict[str, Any] = {
        "sigma_mm": float(sigma_mm),
        "level": float(level),
        "offset_mm": float(offset_mm),
        "taubin_iters": int(taubin_iters) if suave else 0,
        "zooms_mm": [float(z) for z in zooms],
    }

    if method == "marching_cubes":
        from skimage import measure

        campo = _campo_suavizado(mask, zooms, sigma_mm)
        verts, faces, _n, _v = measure.marching_cubes(campo, level=level)
        verts = verts - 1.0  # desfaz o pad
        malha, tris = _finalizar(
            verts, faces, affine, suavizar_taubin=suave, taubin_iters=taubin_iters, offset_mm=offset_mm
        )

    elif method == "surface_nets":
        import vtk

        params.pop("sigma_mm")  # sem gaussiana: o SurfaceNets trabalha no rótulo
        rotulos = np.pad(mask, 1).astype(np.uint8)  # pad fecha a tampa no fim do FOV
        redes = vtk.vtkSurfaceNets3D()
        redes.SetInputData(_para_vtk_image(rotulos))
        redes.SetOutputMeshTypeToTriangles()
        redes.SetBackgroundLabel(0)
        redes.SetValue(0, 1)  # extrai o rótulo 1
        if suave:
            suavizador = redes.GetSmoother()
            params["sn_smoothing_iters"] = int(suavizador.GetNumberOfIterations())
            params["sn_constraint_auto"] = bool(redes.GetAutomaticSmoothingConstraints())
        else:
            redes.SmoothingOff()
        redes.Update()
        pontos, faces = _do_polydata(redes.GetOutput())
        # spacing 1 + origem 0 ⇒ os pontos já são índice de voxel; -1 desfaz o pad.
        malha, tris = _finalizar(
            pontos - 1.0, faces, affine, suavizar_taubin=False, taubin_iters=0, offset_mm=offset_mm
        )
        params["taubin_iters"] = 0

    elif method == "flying_edges":
        import vtk

        campo = _campo_suavizado(mask, zooms, sigma_mm)
        arestas = vtk.vtkFlyingEdges3D()
        arestas.SetInputData(_para_vtk_image(campo))
        arestas.SetValue(0, level)
        arestas.ComputeNormalsOff()
        arestas.ComputeGradientsOff()
        arestas.Update()
        saida = arestas.GetOutput()
        if smoothing in ("auto", "windowed_sinc"):
            sinc = vtk.vtkWindowedSincPolyDataFilter()
            sinc.SetInputData(saida)
            sinc.SetNumberOfIterations(20)
            sinc.SetPassBand(0.1)
            sinc.NormalizeCoordinatesOn()
            sinc.Update()
            saida = sinc.GetOutput()
            params.update(ws_iters=20, ws_pass_band=0.1)
        pontos, faces = _do_polydata(saida)
        taubin_extra = suave and smoothing == "taubin"
        malha, tris = _finalizar(
            pontos - 1.0,
            faces,
            affine,
            suavizar_taubin=taubin_extra,
            taubin_iters=taubin_iters,
            offset_mm=offset_mm,
        )
        params["taubin_iters"] = int(taubin_iters) if taubin_extra else 0

    else:  # "sdf"
        from scipy import ndimage
        from skimage import measure

        m = np.pad(mask, 1)
        # SDF em mm (sampling físico): negativa dentro, positiva fora.
        dentro = ndimage.distance_transform_edt(m, sampling=zooms)
        fora = ndimage.distance_transform_edt(~m, sampling=zooms)
        sdf = (fora - dentro).astype(np.float32)
        # Gaussiana LEVE na SDF: suaviza o zero-level-set sem borrar a ocupação.
        sdf = ndimage.gaussian_filter(sdf, sigma=sigma_mm / zooms, mode="nearest")
        verts, faces, _n, _v = measure.marching_cubes(sdf, level=0.0)
        verts = verts - 1.0
        malha, tris = _finalizar(
            verts, faces, affine, suavizar_taubin=suave, taubin_iters=taubin_iters, offset_mm=offset_mm
        )
        params["level"] = 0.0  # o level da máscara não se aplica: o corte é o zero da SDF

    return ResultadoSuperficie(
        mesh=malha,
        tris_brutos=tris,
        metodo=method,
        suavizacao=smoothing,
        params=params,
        tempo_s=time.perf_counter() - t0,
    )


def volume_ml(malha: trimesh.Trimesh) -> float:
    return abs(float(malha.volume)) * 1e6  # m³ → mL


def centroide_mm(malha: trimesh.Trimesh) -> np.ndarray:
    """Centróide da malha de volta em mm RAS (transposta = inversa da rotação)."""
    return (np.asarray(malha.centroid) / MM_PARA_M) @ RAS_PARA_GLTF


def _demo() -> None:
    """Compara os 4 métodos em dados reais. Roda: python -m scripts.geometry.reconstruction"""
    from pathlib import Path

    import nibabel as nib

    base = Path(__file__).resolve().parents[2] / ".clinica-dados" / "torax-alta_masks"
    for nome in ("aorta", "heart"):
        img = nib.load(str(base / f"{nome}.nii.gz"))
        mask = np.asarray(img.dataobj) > 0.5
        affine = img.affine
        zooms = zooms_de(affine)
        vol_mascara = float(mask.sum()) * float(np.prod(zooms)) / 1000.0
        print(f"\n=== {nome}  voxels={int(mask.sum())}  zooms={np.round(zooms, 3).tolist()} mm")
        print(f"    volume da máscara = {vol_mascara:.1f} mL")
        print(f"{'metodo':<16}{'tris':>8}{'volume_mL':>12}{'tempo_s':>9}   centroide_mm")
        ref = None
        for metodo in METODOS:
            r = reconstruct_surface(mask, affine, method=metodo)
            assert r is not None
            c = centroide_mm(r.mesh)
            if ref is None:
                ref = c
            print(
                f"{metodo:<16}{len(r.mesh.faces):>8}{volume_ml(r.mesh):>12.1f}{r.tempo_s:>9.2f}   "
                f"[{c[0]:7.2f} {c[1]:7.2f} {c[2]:7.2f}]  Δref={np.linalg.norm(c - ref):.2f} mm"
            )
        # Aceite: o SurfaceNets tem que cair dentro de ~1 voxel do baseline.
        r_mc = reconstruct_surface(mask, affine, method="marching_cubes")
        r_sn = reconstruct_surface(mask, affine, method="surface_nets")
        assert r_mc is not None and r_sn is not None
        d = float(np.linalg.norm(centroide_mm(r_mc.mesh) - centroide_mm(r_sn.mesh)))
        assert d <= float(zooms.max()), f"centróides divergem {d:.2f} mm (> 1 voxel)"
        print(f"    aceite surface_nets vs marching_cubes: {d:.2f} mm <= 1 voxel ({zooms.max():.2f} mm) OK")
    assert reconstruct_surface(np.zeros((10, 10, 10), bool), np.eye(4)) is None


if __name__ == "__main__":
    _demo()
