"""Qualidade TOPOLOGICA da malha e CONTINUIDADE de estruturas tubulares.

Duas perguntas que Dice/HD95 nao respondem:
  1. a malha e utilizavel (fechada, um corpo so, sem aresta nao-manifold)?
     -> `qualidade_topologica` — nao mede fidelidade, mede sanidade.
  2. o vaso continuou INTEIRO ao virar malha, ou fragmentou/sumiu?
     -> `continuidade_vaso` (na mascara) e `comparar_continuidade` (mascara x
        malha rasterizada). Um vaso que quebra em 3 pedacos pode ter Dice alto
        e ainda assim ser inutil para navegacao/planejamento.

Nada aqui e claim clinico: e controle de qualidade geometrico sobre a MESMA
grade de voxel (referencia = a propria mascara, tipo "benchmark_interno").
"""

from __future__ import annotations

import numpy as np
import trimesh
from scipy import ndimage
from skimage.morphology import skeletonize

from ..geometry.coordinates import zooms_de
from .mesh_metrics import voxelizar_malha, volume_ml

# 26-conexo: dois voxels que se tocam so pelo vertice ainda sao o mesmo vaso.
# Com 6-conexo uma escada diagonal de 1 voxel ja contaria como fragmentacao.
CONECTIVIDADE = np.ones((3, 3, 3), dtype=bool)


def qualidade_topologica(mesh: trimesh.Trimesh) -> dict:
    """Sanidade topologica da malha (nao mede fidelidade geometrica)."""
    arestas = np.sort(mesh.edges, axis=1)
    _unicas, contagem = np.unique(arestas, axis=0, return_counts=True)
    # aresta sa aparece em exatamente 2 faces; 1 = borda aberta, >=3 = nao-manifold
    n_nao_manifold = int((contagem != 2).sum())

    areas = np.asarray(mesh.area_faces, dtype=float)
    # degenerada = area desprezivel FRENTE A ESCALA DA MALHA (limiar absoluto em
    # metros classificaria tudo como degenerado numa malha de 5 mm).
    mediana = float(np.median(areas)) if len(areas) else 0.0
    n_degeneradas = int((areas <= 1e-8 * mediana).sum()) if mediana > 0 else len(areas)

    n_isolados = int(len(mesh.vertices) - len(np.unique(mesh.faces)))
    watertight = bool(mesh.is_watertight)

    return {
        "watertight": watertight,
        "n_componentes": int(mesh.body_count),
        "euler_number": int(mesh.euler_number),
        "n_arestas_nao_manifold": n_nao_manifold,
        "n_faces_degeneradas": n_degeneradas,
        "n_vertices_isolados": n_isolados,
        "normais_consistentes": bool(mesh.is_winding_consistent),
        "area_mm2": round(float(mesh.area) * 1e6, 3),  # m2 -> mm2
        "volume_ml_se_watertight": round(volume_ml(mesh), 4) if watertight else None,
    }


def continuidade_vaso(mask: np.ndarray, zooms: np.ndarray) -> dict:
    """Continuidade de estrutura tubular: quantos pedacos e qual o comprimento.

    `comprimento_esqueleto_mm` e APROXIMADO: soma dos voxels do esqueleto x
    spacing medio. Subestima trecho diagonal (passo real ate sqrt(3)x maior) e
    so serve para COMPARAR duas versoes da mesma estrutura na mesma grade.
    skimage >= 0.26 removeu `skeletonize_3d`; `skeletonize` trata 3D nativamente.
    """
    mask = np.asarray(mask) > 0.5
    zooms = np.asarray(zooms, dtype=float)
    total = int(mask.sum())
    if total == 0:
        return {"n_componentes": 0, "fracao_maior_componente": 0.0, "comprimento_esqueleto_mm": 0.0}

    rotulos, n = ndimage.label(mask, structure=CONECTIVIDADE)
    tamanhos = np.bincount(rotulos.ravel())[1:]
    esqueleto = skeletonize(mask)
    passo_mm = float(np.mean(zooms))

    return {
        "n_componentes": int(n),
        "fracao_maior_componente": round(float(tamanhos.max()) / total, 5),
        "comprimento_esqueleto_mm": round(float(esqueleto.sum()) * passo_mm, 2),
    }


def comparar_continuidade(mask_ref: np.ndarray, mesh: trimesh.Trimesh, affine: np.ndarray) -> dict:
    """Detecta vaso que FRAGMENTOU ou sumiu ao virar malha.

    Rasteriza a malha na mesma grade da mascara e compara a continuidade das
    duas. `delta_componentes > 0` = fragmentou; `fracao_maior_componente` caindo
    = perdeu um ramo; comprimento de esqueleto caindo = encurtou/afinou.
    """
    mask_ref = np.asarray(mask_ref) > 0.5
    zooms = zooms_de(affine)
    rasterizada = voxelizar_malha(mesh, mask_ref.shape, affine)

    ref = continuidade_vaso(mask_ref, zooms)
    mal = continuidade_vaso(rasterizada, zooms)
    comp_ref = ref["comprimento_esqueleto_mm"]
    return {
        "mascara": ref,
        "malha": mal,
        "delta_componentes": mal["n_componentes"] - ref["n_componentes"],
        "delta_comprimento_pct": (
            round((mal["comprimento_esqueleto_mm"] - comp_ref) / comp_ref * 100.0, 2) if comp_ref else float("nan")
        ),
        "fragmentou": mal["n_componentes"] > ref["n_componentes"],
        "sumiu": mal["n_componentes"] == 0,
        "referencia": "benchmark_interno",  # a mascara nao e ground truth clinico
    }


def _demo() -> None:
    import json
    from pathlib import Path

    import nibabel as nib

    from ..geometry.reconstruction import reconstruct_surface
    from .phantom import tubo_fino

    raiz = Path(__file__).resolve().parents[2] / ".clinica-dados" / "torax-alta_masks"
    casos: list[tuple[str, np.ndarray, np.ndarray]] = []
    for nome in ("aorta", "trachea"):
        img = nib.load(str(raiz / f"{nome}.nii.gz"))
        casos.append((nome, np.asarray(img.dataobj) > 0.5, img.affine))
    mask_tubo, aff_tubo = tubo_fino(3.0, 40.0, spacing=(0.7, 0.7, 0.7))
    casos.append(("fantoma_tubo_3mm", mask_tubo, aff_tubo))

    for nome, mask, affine in casos:
        zooms = zooms_de(affine)
        base = continuidade_vaso(mask, zooms)
        print(f"\n=== {nome} shape={mask.shape} voxels={int(mask.sum())} zooms={np.round(zooms, 3).tolist()}")
        print("  mascara:", json.dumps(base))
        for metodo in ("marching_cubes", "surface_nets"):
            r = reconstruct_surface(mask, affine, method=metodo)
            if r is None:
                print(f"  [{metodo}] AUSENTE (estrutura nao sobreviveu)")
                continue
            print(f"  [{metodo}] topologia:", json.dumps(qualidade_topologica(r.mesh)))
            c = comparar_continuidade(mask, r.mesh, affine)
            print(f"  [{metodo}] continuidade:", json.dumps({k: v for k, v in c.items() if k != "mascara"}))

    # check minimo: esfera de trimesh e sa; um tubo inteiro nao tem 2 componentes
    q = qualidade_topologica(trimesh.creation.icosphere(subdivisions=2, radius=0.01))
    assert q["watertight"] and q["n_componentes"] == 1 and q["n_arestas_nao_manifold"] == 0, q
    assert continuidade_vaso(mask_tubo, zooms_de(aff_tubo))["n_componentes"] == 1
    print("\nOK: checks minimos passaram")


if __name__ == "__main__":
    _demo()
