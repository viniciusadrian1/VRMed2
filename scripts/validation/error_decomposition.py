"""Decomposicao de erro (guardrail 5): quatro erros MEDIDOS SEPARADAMENTE.

O pipeline TC -> mascara -> malha -> GLB acumula quatro perdas de natureza
diferente. Elas NAO sao somadas nem agregadas num indice unico — cada bloco do
dicionario de saida traz suas proprias metricas e o seu `tipo_referencia`:

  A) segmentacao  : mascara predita x ground truth INDEPENDENTE (rotulado por
                    humano, fora deste repositorio). Hoje AUSENTE: o bloco sai
                    {"disponivel": False}. Usar a propria mascara como GT daria
                    Dice 1.0 e seria uma mentira — nunca fazemos isso.
  B) reconstrucao : mascara -> MASTER mesh (sem decimacao), rasterizando a malha
                    de volta para a grade da mascara. tipo_referencia interno.
  C) simplificacao: MASTER -> DERIVED (decimado), distancia superficie-superficie.
  D) compressao   : GLB cru -> GLB com Draco. Mede bytes e, quando possivel, o
                    desvio geometrico. O trimesh NAO decodifica Draco: se a
                    releitura vier degenerada reportamos "nao verificavel com
                    trimesh" em vez de imprimir um numero errado.

Uso:
  python -m scripts.validation.error_decomposition --masks .clinica-dados/torax-alta_masks \
      --estruturas heart,trachea
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from ..geometry.reconstruction import reconstruct_surface
from .mesh_metrics import comparar_malhas, comparar_mascara_malha, volume_ml
from .segmentation_metrics import compare_masks

FRACAO_DECIMACAO_PADRAO = 0.3  # ponytail: default unico; passe alvo_tris para outro alvo

INDISPONIVEL_GT = {
    "disponivel": False,
    "motivo": "sem ground truth independente no repositorio",
    "tipo_referencia": "ground_truth_independente",
}


def _stats_malha(mesh: trimesh.Trimesh) -> dict[str, Any]:
    """Antes/depois quantitativo de qualquer transformacao destrutiva."""
    return {
        "tris": int(len(mesh.faces)),
        "vertices": int(len(mesh.vertices)),
        "volume_ml": round(volume_ml(mesh), 4),
        "area_cm2": round(float(mesh.area) * 1e4, 4),  # m2 -> cm2
    }


# ------------------------------------------------------------------ A) segmentacao


def erro_segmentacao(pred_path: str | Path | None, gt_path: str | Path | None) -> dict[str, Any]:
    """Mascara predita x ground truth INDEPENDENTE. Sem GT: bloco indisponivel."""
    if gt_path is None or pred_path is None:
        return dict(INDISPONIVEL_GT)
    import nibabel as nib

    pred_img, gt_img = nib.load(str(pred_path)), nib.load(str(gt_path))
    pred = np.asarray(pred_img.dataobj) > 0.5
    gt = np.asarray(gt_img.dataobj) > 0.5
    if pred.shape != gt.shape:
        return {
            "disponivel": False,
            "motivo": f"grades diferentes: pred {pred.shape} vs gt {gt.shape}",
            "tipo_referencia": "ground_truth_independente",
        }
    spacing = np.linalg.norm(gt_img.affine[:3, :3], axis=0)
    return {
        "disponivel": True,
        "tipo_referencia": "ground_truth_independente",
        "pred": str(pred_path),
        "ground_truth": str(gt_path),
        **{k: round(float(v), 4) for k, v in compare_masks(pred, gt, spacing).items()},
    }


# ---------------------------------------------------------------- B) reconstrucao


def erro_reconstrucao(mask: np.ndarray, affine: np.ndarray, master: trimesh.Trimesh) -> dict[str, Any]:
    """Mascara -> MASTER: a malha rasterizada de volta bate com a mascara?"""
    return {
        "disponivel": True,
        "tipo_referencia": "benchmark_interno",
        "referencia": "mascara de entrada (mesma grade)",
        "master": _stats_malha(master),
        **comparar_mascara_malha(mask, master, affine),
    }


# --------------------------------------------------------------- C) simplificacao


def erro_simplificacao(master: trimesh.Trimesh, alvo_tris: int | None = None) -> dict[str, Any]:
    """MASTER -> DERIVED (decimado). Devolve tambem o derivado, para o bloco D."""
    import fast_simplification

    alvo = int(alvo_tris or len(master.faces) * FRACAO_DECIMACAO_PADRAO)
    alvo = max(4, min(alvo, len(master.faces)))
    v, f = fast_simplification.simplify(
        master.vertices.astype(np.float32), master.faces.astype(np.int64), target_count=alvo
    )
    derivado = trimesh.Trimesh(vertices=v, faces=f, process=True)
    return {
        "disponivel": True,
        "tipo_referencia": "benchmark_interno",
        "referencia": "malha MASTER (sem decimacao)",
        "alvo_tris": alvo,
        "antes": _stats_malha(master),
        "depois": _stats_malha(derivado),
        **comparar_malhas(master, derivado),
    }, derivado


# ------------------------------------------------------------------ D) compressao


def _npx() -> str | None:
    return shutil.which("npx") or shutil.which("npx.cmd")


def _degenerada(mesh: trimesh.Trimesh) -> bool:
    """Draco lido pelo trimesh vira zeros: sem faces, sem area ou sem extensao."""
    return len(mesh.faces) == 0 or float(mesh.area) <= 0.0 or not np.any(np.asarray(mesh.extents) > 1e-9)


def erro_compressao(derivado: trimesh.Trimesh) -> dict[str, Any]:
    """GLB cru -> GLB com Draco: bytes sempre; geometria so se for verificavel."""
    npx = _npx()
    if npx is None:
        return {"disponivel": False, "motivo": "npx nao encontrado no PATH", "tipo_referencia": "benchmark_interno"}

    with tempfile.TemporaryDirectory() as tmp:
        cru = Path(tmp) / "cru.glb"
        comprimido = Path(tmp) / "draco.glb"
        cru.write_bytes(trimesh.Scene(derivado).export(file_type="glb"))
        try:
            proc = subprocess.run(
                [npx, "--no-install", "gltf-transform", "draco", str(cru), str(comprimido)],
                capture_output=True, text=True, timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return {"disponivel": False, "motivo": f"falha ao rodar gltf-transform: {e}",
                    "tipo_referencia": "benchmark_interno"}
        if proc.returncode != 0 or not comprimido.exists():
            motivo = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:] or ["erro desconhecido"]
            return {"disponivel": False, "motivo": f"gltf-transform draco falhou: {motivo[0]}",
                    "tipo_referencia": "benchmark_interno"}

        bytes_antes, bytes_depois = cru.stat().st_size, comprimido.stat().st_size
        antes = trimesh.load(str(cru), force="mesh", process=False)
        depois = trimesh.load(str(comprimido), force="mesh", process=False)

        saida: dict[str, Any] = {
            "disponivel": True,
            "tipo_referencia": "benchmark_interno",
            "referencia": "GLB sem compressao (mesma malha DERIVED)",
            "bytes_antes": int(bytes_antes),
            "bytes_depois": int(bytes_depois),
            "reducao_bytes_pct": round((1.0 - bytes_depois / bytes_antes) * 100.0, 2),
        }
        if _degenerada(depois) or _degenerada(antes):
            saida["desvio_geometrico"] = {
                "verificavel": False,
                "motivo": "nao verificavel com trimesh: o trimesh nao decodifica Draco (releitura degenerada)",
                "tris_relidos": int(len(depois.faces)),
            }
        else:
            saida["desvio_geometrico"] = {"verificavel": True, **comparar_malhas(antes, depois)}
        return saida


# ------------------------------------------------------------------------- API


def decompor_erros(
    mask: np.ndarray,
    affine: np.ndarray,
    nome_estrutura: str,
    *,
    metodo: str = "marching_cubes",
    alvo_tris: int | None = None,
    gt_path: str | Path | None = None,
    pred_path: str | Path | None = None,
) -> dict[str, Any]:
    """Os quatro erros, cada um com seu proprio dict e tipo_referencia.

    NAO existe metrica agregada dos quatro: somar erro de segmentacao com erro de
    compressao nao tem significado fisico.
    """
    saida: dict[str, Any] = {
        "estrutura": nome_estrutura,
        "metodo": metodo,
        "A_segmentacao": erro_segmentacao(pred_path, gt_path),
    }
    r = reconstruct_surface(mask, affine, method=metodo)
    if r is None:
        ausente = {"disponivel": False, "motivo": "estrutura ausente ou dissolvida na reconstrucao",
                   "tipo_referencia": "benchmark_interno"}
        return {**saida, "B_reconstrucao": dict(ausente), "C_simplificacao": dict(ausente),
                "D_compressao": dict(ausente)}

    saida["B_reconstrucao"] = erro_reconstrucao(mask, affine, r.mesh)
    bloco_c, derivado = erro_simplificacao(r.mesh, alvo_tris)
    saida["C_simplificacao"] = bloco_c
    saida["D_compressao"] = erro_compressao(derivado)
    return saida


# ------------------------------------------------------------------------- CLI


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Decomposicao de erro do pipeline (4 erros separados).")
    p.add_argument("--masks", default=".clinica-dados/torax-alta_masks", help="diretorio com as mascaras NIfTI")
    p.add_argument("--estruturas", default="heart,trachea", help="nomes separados por virgula")
    p.add_argument("--metodo", default="marching_cubes")
    p.add_argument("--alvo-tris", type=int, default=None)
    p.add_argument("--gt", default=None, help="NIfTI de ground truth INDEPENDENTE (bloco A)")
    args = p.parse_args(argv)

    import nibabel as nib

    base = Path(args.masks)
    resultados = []
    for nome in [s.strip() for s in args.estruturas.split(",") if s.strip()]:
        caminho = base / f"{nome}.nii.gz"
        img = nib.load(str(caminho))
        mask = np.asarray(img.dataobj) > 0.5
        resultados.append(
            decompor_erros(mask, img.affine, nome, metodo=args.metodo,
                           alvo_tris=args.alvo_tris, gt_path=args.gt, pred_path=caminho)
        )
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
    return 0


def _autoteste() -> None:
    """Sanidade: os 4 blocos existem, tem tipo_referencia, A indisponivel sem GT e nada agregado."""
    from .phantom import esfera

    mask, affine = esfera(diametro_mm=24.0)
    r = decompor_erros(mask, affine, "esfera_phantom")
    chaves = ("A_segmentacao", "B_reconstrucao", "C_simplificacao", "D_compressao")
    assert set(chaves) <= set(r), r.keys()
    assert all("tipo_referencia" in r[k] for k in chaves), r
    assert r["A_segmentacao"] == INDISPONIVEL_GT, r["A_segmentacao"]
    assert not any("total" in k or "agregad" in k or "global" in k for k in r), r.keys()
    assert r["B_reconstrucao"]["dice"] > 0.9, r["B_reconstrucao"]
    assert r["C_simplificacao"]["depois"]["tris"] < r["C_simplificacao"]["antes"]["tris"]
    print(json.dumps(r, indent=2, ensure_ascii=False))
    print("autoteste OK")


if __name__ == "__main__":
    import sys

    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        raise SystemExit(_main())
