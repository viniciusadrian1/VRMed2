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
# Filtro no domínio da MALHA (depois da extração). "taubin" é o histórico.
MESH_SMOOTHERS = ("taubin", "windowed_sinc", "none")


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


def _suavizar_windowed_sinc(malha: trimesh.Trimesh, ws_iters: int, ws_pass_band: float) -> None:
    """vtkWindowedSincPolyDataFilter na malha, IN-PLACE (só move vértices).

    ESPAÇO: roda em **metros / eixos glTF**, exatamente na fatia do pipeline que o
    Taubin ocupa (depois de `trimesh.Trimesh(..., process=True)`, antes de
    `fix_normals` e do afastamento). Escolha deliberada: assim a única diferença
    entre `mesh_smoothing="taubin"` e `"windowed_sinc"` é o filtro em si — mesma
    entrada, mesma posição, mesmo pós-processamento.

    O filtro é sensível à escala das coordenadas e aqui elas são pequenas (uma
    aorta tem ~0,1 em metros). `NormalizeCoordinatesOn()` normaliza a bounding box
    antes de suavizar, que é a mitigação recomendada pela própria doc do VTK — mas
    fica registrado que o espaço de execução é METROS glTF, não voxel nem mm.

    Origem dos números (fixos, não ajustados para favorecer resultado):
    `iterations=20` e `pass_band=0.1` são os valores do exemplo canônico da
    documentação do vtkWindowedSincPolyDataFilter (a doc recomenda passband na
    faixa de 0,1 e poucas dezenas de iterações; acima disso o ganho satura e o
    encolhimento aparece). `FeatureEdgeSmoothingOff`, `BoundarySmoothingOff` e
    `NonManifoldSmoothingOn` também vêm da doc: não inventar aresta de feature em
    isosuperfície, não mexer na borda aberta (tampa do FOV) e não rasgar junção
    não-manifold. Os mesmos 20/0,1 já eram usados no ramo `flying_edges`.

    Topologia é preservada (o filtro só desloca pontos), então nº de triângulos e
    ordem dos vértices saem iguais — a guarda abaixo falha alto se isso mudar.
    """
    import vtk
    from vtk.util import numpy_support

    faces = np.ascontiguousarray(malha.faces, dtype=np.int64)
    pontos = vtk.vtkPoints()
    pontos.SetData(
        numpy_support.numpy_to_vtk(np.ascontiguousarray(malha.vertices, dtype=np.float64), deep=True)
    )
    celulas = vtk.vtkCellArray()  # API VTK 9: (offsets, connectivity)
    celulas.SetData(
        numpy_support.numpy_to_vtkIdTypeArray(np.arange(len(faces) + 1, dtype=np.int64) * 3, deep=True),
        numpy_support.numpy_to_vtkIdTypeArray(faces.ravel(), deep=True),
    )
    pd = vtk.vtkPolyData()
    pd.SetPoints(pontos)
    pd.SetPolys(celulas)

    sinc = vtk.vtkWindowedSincPolyDataFilter()
    sinc.SetInputData(pd)
    sinc.SetNumberOfIterations(int(ws_iters))
    sinc.SetPassBand(float(ws_pass_band))
    sinc.NormalizeCoordinatesOn()
    sinc.FeatureEdgeSmoothingOff()
    sinc.BoundarySmoothingOff()
    sinc.NonManifoldSmoothingOn()
    sinc.Update()

    novos, _f = _do_polydata(sinc.GetOutput())
    if len(novos) != len(malha.vertices):
        raise RuntimeError(
            f"windowed_sinc mudou a topologia: {len(malha.vertices)} → {len(novos)} vértices"
        )
    malha.vertices = novos


def _finalizar(
    verts_vox: np.ndarray,
    faces: np.ndarray,
    affine: np.ndarray,
    *,
    suavizar_malha: bool,
    taubin_iters: int,
    offset_mm: float,
    mesh_smoothing: str = "taubin",
    ws_iters: int = 20,
    ws_pass_band: float = 0.1,
) -> tuple[trimesh.Trimesh, int]:
    """Índice de voxel → mm RAS → glTF(m), + suavização de malha/normais/afastamento.

    `mesh_smoothing` escolhe o filtro no domínio da MALHA: "taubin" (histórico),
    "windowed_sinc" ou "none". Só atua quando `suavizar_malha` é True.

    Levanta SuperficieVazia quando não sobrou geometria (estrutura dissolvida
    pela suavização) — quem chama traduz para "ausente" em vez de quebrar.
    """
    if len(faces) == 0 or len(verts_vox) == 0:
        raise SuperficieVazia("isosuperfície vazia: a estrutura não sobreviveu à suavização")
    verts_mm = verts_vox @ affine[:3, :3].T + affine[:3, 3]
    malha = trimesh.Trimesh(vertices=(verts_mm @ RAS_PARA_GLTF.T) * MM_PARA_M, faces=faces, process=True)
    tris_brutos = len(malha.faces)
    if suavizar_malha and mesh_smoothing == "windowed_sinc":
        _suavizar_windowed_sinc(malha, ws_iters, ws_pass_band)
    elif suavizar_malha and mesh_smoothing == "taubin" and taubin_iters > 0:
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
    mesh_smoothing: str = "taubin",
    ws_iters: int = 20,
    ws_pass_band: float = 0.1,
) -> ResultadoSuperficie | None:
    """Máscara binária → superfície em metros/eixos glTF. None se < 50 voxels.

    smoothing: "auto" (o suavizador natural do método), "none", "taubin" ou
    "windowed_sinc" — atua no CAMPO/extrator (só muda algo no flying_edges).

    mesh_smoothing: filtro no domínio da MALHA, depois da extração.
    "taubin" (DEFAULT, comportamento histórico byte a byte), "windowed_sinc"
    (vtkWindowedSincPolyDataFilter, ver `_suavizar_windowed_sinc` para espaço e
    origem dos números) ou "none". Vale onde o pipeline já suavizava a malha —
    `marching_cubes`, `sdf` e `flying_edges` com `smoothing="taubin"`; o
    `surface_nets` continua sem suavização de malha (ele tem a dele, embutida).
    `ws_iters`/`ws_pass_band` são os parâmetros do WindowedSinc: 20 e 0,1, valores
    conservadores da documentação do VTK, fixos, não ajustados por resultado.

    Devolve None também quando a estrutura NÃO SOBREVIVE à suavização (vaso fino
    dissolvido: o campo nunca alcança `level`). É perda total, não erro de
    programação — por isso vira "ausente" e não exceção.
    """
    try:
        return _reconstruir(
            mask, affine, method=method, smoothing=smoothing, sigma_mm=sigma_mm,
            taubin_iters=taubin_iters, offset_mm=offset_mm, level=level,
            mesh_smoothing=mesh_smoothing, ws_iters=ws_iters, ws_pass_band=ws_pass_band,
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
    mesh_smoothing: str,
    ws_iters: int,
    ws_pass_band: float,
) -> ResultadoSuperficie | None:
    if method not in METODOS:
        raise ValueError(f"método desconhecido: {method!r} (use um de {METODOS})")
    if mesh_smoothing not in MESH_SMOOTHERS:
        raise ValueError(f"mesh_smoothing desconhecido: {mesh_smoothing!r} (use um de {MESH_SMOOTHERS})")
    mask = np.asarray(mask) > 0.5
    if int(mask.sum()) < MIN_VOXELS:
        return None

    zooms = zooms_de(affine)
    if sigma_mm is None:
        sigma_mm = _sigma_padrao(zooms)
    suave = smoothing != "none"
    t0 = time.perf_counter()
    # `suav` viaja junto para o _finalizar: o filtro de malha e seus parâmetros.
    suav = {"mesh_smoothing": mesh_smoothing, "ws_iters": ws_iters, "ws_pass_band": ws_pass_band}
    params: dict[str, Any] = {
        "sigma_mm": float(sigma_mm),
        "level": float(level),
        "offset_mm": float(offset_mm),
        # mesh_smoothing/taubin_iters registram o que RODOU, não o que foi pedido
        # (cada ramo corrige abaixo quando não aplica suavização de malha).
        "mesh_smoothing": mesh_smoothing if suave else "none",
        "taubin_iters": int(taubin_iters) if suave and mesh_smoothing == "taubin" else 0,
        "ws_iters": int(ws_iters),
        "ws_pass_band": float(ws_pass_band),
        "zooms_mm": [float(z) for z in zooms],
    }

    if method == "marching_cubes":
        from skimage import measure

        campo = _campo_suavizado(mask, zooms, sigma_mm)
        verts, faces, _n, _v = measure.marching_cubes(campo, level=level)
        verts = verts - 1.0  # desfaz o pad
        malha, tris = _finalizar(
            verts, faces, affine, suavizar_malha=suave, taubin_iters=taubin_iters,
            offset_mm=offset_mm, **suav
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
            pontos - 1.0, faces, affine, suavizar_malha=False, taubin_iters=0, offset_mm=offset_mm
        )
        params["taubin_iters"] = 0
        params["mesh_smoothing"] = "none"  # a suavização do SurfaceNets é do extrator

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
            # Este sinc é do EXTRATOR: roda na polydata em coordenada de VOXEL e
            # com as opções default do VTK (boundary ON, non-manifold OFF) — não
            # confundir com _suavizar_windowed_sinc, que é no domínio da malha.
            sinc = vtk.vtkWindowedSincPolyDataFilter()
            sinc.SetInputData(saida)
            sinc.SetNumberOfIterations(int(ws_iters))
            sinc.SetPassBand(float(ws_pass_band))
            sinc.NormalizeCoordinatesOn()
            sinc.Update()
            saida = sinc.GetOutput()
        pontos, faces = _do_polydata(saida)
        taubin_extra = suave and smoothing == "taubin"
        malha, tris = _finalizar(
            pontos - 1.0,
            faces,
            affine,
            suavizar_malha=taubin_extra,
            taubin_iters=taubin_iters,
            offset_mm=offset_mm,
            **suav,
        )
        params["taubin_iters"] = int(taubin_iters) if taubin_extra and mesh_smoothing == "taubin" else 0
        params["mesh_smoothing"] = mesh_smoothing if taubin_extra else "none"

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
            verts, faces, affine, suavizar_malha=suave, taubin_iters=taubin_iters,
            offset_mm=offset_mm, **suav
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


def _autoteste() -> None:
    """Suavização de malha: default intacto + sanidade do WindowedSinc.

    Roda sem dado real (fantoma analítico):
        python -m scripts.geometry.reconstruction --autoteste
    """
    from ..validation.phantom import esfera

    mask, affine = esfera(20.0, spacing=(1.0, 1.0, 1.0))
    base = dict(method="marching_cubes", sigma_mm=0.0, taubin_iters=4)
    print(f"esfera d=20 mm, spacing 1 mm, voxels={int(mask.sum())}")

    # 1. O default não mudou: omitir mesh_smoothing == pedir "taubin".
    r_default = reconstruct_surface(mask, affine, **base)
    r_taubin = reconstruct_surface(mask, affine, **base, mesh_smoothing="taubin")
    assert r_default is not None and r_taubin is not None
    v_def, v_tau = r_default.mesh.vertices, r_taubin.mesh.vertices
    assert v_def.shape == v_tau.shape, f"shapes divergem: {v_def.shape} vs {v_tau.shape}"
    assert np.array_equal(v_def, v_tau), "default != mesh_smoothing='taubin' — o default MUDOU"
    assert np.allclose(v_def, v_tau, rtol=0, atol=0)
    print(f"1) default == mesh_smoothing='taubin': {len(v_def)} vértices idênticos bit a bit  OK")
    print(f"   params: {r_default.params['mesh_smoothing']=} {r_default.params['taubin_iters']=} "
          f"{r_default.params['ws_iters']=} {r_default.params['ws_pass_band']=}")

    # 2. WindowedSinc: mesma topologia, volume na mesma ordem (sanidade, não critério).
    r_ws = reconstruct_surface(mask, affine, **base, mesh_smoothing="windowed_sinc")
    assert r_ws is not None
    assert len(r_ws.mesh.faces) == len(r_taubin.mesh.faces), "windowed_sinc mudou a contagem de triângulos"
    d_vol = abs(volume_ml(r_ws.mesh) - volume_ml(r_taubin.mesh)) / volume_ml(r_taubin.mesh)
    assert d_vol < 0.20, f"volume do windowed_sinc {d_vol:.1%} fora dos 20% do taubin"
    print(f"2) windowed_sinc: tris={len(r_ws.mesh.faces)} (== taubin), "
          f"volume {volume_ml(r_ws.mesh):.2f} mL vs taubin {volume_ml(r_taubin.mesh):.2f} mL "
          f"(Δ {d_vol:.2%} < 20%)  OK")
    print(f"   params: {r_ws.params['mesh_smoothing']=} {r_ws.params['ws_iters']=} "
          f"{r_ws.params['ws_pass_band']=}")

    # 3. "none" não aplica Taubin: a escada da máscara permanece ⇒ área MAIOR.
    r_none = reconstruct_surface(mask, affine, **base, mesh_smoothing="none")
    assert r_none is not None
    a_none, a_tau = float(r_none.mesh.area), float(r_taubin.mesh.area)
    assert a_none > a_tau, f"area none={a_none:.6f} não é maior que taubin={a_tau:.6f}"
    print(f"3) mesh_smoothing='none' (taubin_iters=4 ignorado): área {a_none:.6f} > "
          f"taubin {a_tau:.6f} m²  OK")
    print(f"   params: {r_none.params['mesh_smoothing']=} {r_none.params['taubin_iters']=}")

    # 4. SuperficieVazia → None continua valendo, nas três variantes.
    vazio = np.zeros((10, 10, 10), bool)
    for ms in MESH_SMOOTHERS:
        assert reconstruct_surface(vazio, np.eye(4), mesh_smoothing=ms) is None
    print(f"4) máscara vazia → None em {list(MESH_SMOOTHERS)}  OK")
    print("autoteste OK")


if __name__ == "__main__":
    import sys

    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        _demo()
