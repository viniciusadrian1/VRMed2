"""
VRMED Reconstruction Benchmark — runner.

Para cada par (estrutura x pipeline) reconstrói a superfície com
`scripts.geometry.reconstruction.reconstruct_surface`, mede com
`scripts.validation.mesh_metrics.comparar_mascara_malha` e grava
benchmark.json / benchmark.csv / summary.md.

O summary agrega POR FAIXA DE ESCALA (grande / médio / pequeno pelo volume da máscara),
não por média global: numa caixa torácica o coração e os lobos dominam a média e escondem
o colapso da traqueia/esôfago/vasinhos, que é justamente onde os pipelines se diferenciam.

Uso:
  python scripts/validation/benchmark.py \
      --masks .clinica-dados/torax-alta_masks \
      --pipelines marching_cubes,surface_nets,flying_edges,sdf \
      --out .clinica-dados/benchmark
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

import nibabel as nib
import numpy as np

# Faixas de escala pelo volume da máscara (ml = cm³).
FAIXA_GRANDE = "grande (>100 cm3)"
FAIXA_MEDIO = "medio (1-100 cm3)"
FAIXA_PEQUENO = "pequeno (<1 cm3)"
ORDEM_FAIXAS = (FAIXA_GRANDE, FAIXA_MEDIO, FAIXA_PEQUENO)

COLUNAS = (
    "case", "estrutura", "faixa", "pipeline", "tipo_referencia", "spacing_mm",
    "tempo_s", "volume_malha_ml", "volume_mascara_ml", "volume_error_pct",
    "area_superficie_mm2", "triangle_count", "vertex_count",
    "watertight", "n_componentes", "euler_number",
    "hd95_mm", "assd_mm", "dice", "tamanho_glb_mb", "erro",
)

# Guardrail 1: estes casos comparam pipelines entre si contra a MÁSCARA de entrada.
# Não existe ground truth clínico aqui — Dice/HD95/ASSD medem reconstrução, não segmentação.
TIPO_REFERENCIA = "benchmark_interno"

# Métricas agregadas no summary, na ordem em que aparecem na tabela.
METRICAS = (
    "dice", "hd95_mm", "assd_mm", "volume_error_pct", "area_superficie_mm2",
    "triangle_count", "vertex_count", "n_componentes", "euler_number", "tamanho_glb_mb",
)
# nome em comparar_mascara_malha -> nome da coluna
DE_METRICS = {
    "dice": "dice", "hd95_mm": "hd95_mm", "assd_mm": "assd_mm",
    "volume_mask_ml": "volume_mascara_ml", "volume_mesh_ml": "volume_malha_ml",
    "volume_error_pct": "volume_error_pct",
}


def zooms_de(affine: np.ndarray) -> np.ndarray:
    """Tamanho físico do voxel em mm (norma das colunas da parte linear)."""
    return np.linalg.norm(affine[:3, :3], axis=0)


def faixa_de_escala(volume_ml: float) -> str:
    if volume_ml > 100.0:
        return FAIXA_GRANDE
    if volume_ml >= 1.0:
        return FAIXA_MEDIO
    return FAIXA_PEQUENO


def volume_mascara_ml(mask: np.ndarray, affine: np.ndarray) -> float:
    """Volume da máscara em ml, sempre com spacing físico — nunca contagem de voxel."""
    return float(mask.sum()) * float(np.prod(zooms_de(affine))) / 1000.0


def _finito(v: Any) -> float | None:
    """None para NaN/inf: mediana e tabela ignoram; um NaN contamina a mediana inteira."""
    if v is None:
        return None
    v = float(v)
    return v if np.isfinite(v) else None


def tamanho_glb_mb(mesh) -> float:
    """Peso de entrega: exporta para um GLB temporário, mede o arquivo e apaga.

    É o único número que responde "isso cabe no navegador"; sem Draco e sem
    quantização — é o custo bruto da malha, não o do asset final.
    """
    import trimesh

    with tempfile.TemporaryDirectory() as tmp:
        destino = Path(tmp) / "bench.glb"
        trimesh.Scene(mesh).export(destino)
        return round(destino.stat().st_size / 1e6, 4)


def metricas_de_malha(mesh) -> dict[str, Any]:
    """Métricas da MALHA em si (topologia/tamanho), separadas do erro geométrico.

    Guardrail 2: nada aqui entra no Dice/HD95 — malha rachada e malha grande são
    problemas diferentes e ficam em colunas diferentes.
    """
    return {
        # a malha está em METROS: m2 -> mm2
        "area_superficie_mm2": round(float(mesh.area) * 1e6, 3),
        "triangle_count": int(len(mesh.faces)),
        "vertex_count": int(len(mesh.vertices)),
        "watertight": bool(mesh.is_watertight),
        "n_componentes": int(mesh.body_count),
        "euler_number": int(mesh.euler_number),
        "tamanho_glb_mb": tamanho_glb_mb(mesh),
    }


def estruturas_de(dir_masks: Path) -> list[tuple[str, Path]]:
    return sorted((p.name.split(".nii")[0], p) for p in dir_masks.glob("*.nii*"))


def rodar(dir_masks: Path, pipelines: Iterable[str]) -> list[dict[str, Any]]:
    """Roda todos os pares (estrutura x pipeline). Falha de um par vira linha com `erro`."""
    from scripts.geometry.reconstruction import reconstruct_surface
    from scripts.validation.mesh_metrics import comparar_mascara_malha

    caso = dir_masks.name.removesuffix("_masks")
    linhas: list[dict[str, Any]] = []

    for estrutura, caminho in estruturas_de(dir_masks):
        img = nib.load(caminho)
        mask = np.asarray(img.dataobj) > 0.5
        affine = img.affine
        if not mask.any():
            print(f"  [pulado] {estrutura}: máscara vazia", file=sys.stderr)
            continue

        vol_mask = volume_mascara_ml(mask, affine)
        faixa = faixa_de_escala(vol_mask)
        spacing = [round(float(z), 4) for z in zooms_de(affine)]

        for pipeline in pipelines:
            linha: dict[str, Any] = {c: None for c in COLUNAS}
            linha.update({
                "case": caso, "estrutura": estrutura, "faixa": faixa, "pipeline": pipeline,
                "tipo_referencia": TIPO_REFERENCIA, "spacing_mm": spacing,
                "volume_mascara_ml": round(vol_mask, 4),
            })
            t0 = time.perf_counter()
            try:
                resultado = reconstruct_surface(mask, affine, method=pipeline)
                linha["tempo_s"] = round(time.perf_counter() - t0, 4)
                if resultado is None:  # estrutura abaixo do mínimo de voxels
                    raise RuntimeError("reconstruct_surface devolveu None (máscara pequena demais)")
                malha = resultado.mesh
                linha.update(metricas_de_malha(malha))
                metricas = comparar_mascara_malha(mask, malha, affine)
                for origem, coluna in DE_METRICS.items():
                    linha[coluna] = _finito(metricas.get(origem))
            except Exception as exc:  # um pipeline que quebra não derruba a matriz inteira
                linha["tempo_s"] = round(time.perf_counter() - t0, 4)
                linha["erro"] = f"{type(exc).__name__}: {exc}"
                print(f"  [erro] {estrutura} x {pipeline}: {linha['erro']}", file=sys.stderr)
            linhas.append(linha)
            print(
                f"  {estrutura:28s} {pipeline:16s} dice={_fmt(linha['dice'])} "
                f"hd95={_fmt(linha['hd95_mm'], 2)} assd={_fmt(linha['assd_mm'])} "
                f"tris={linha['triangle_count']} comp={linha['n_componentes']} "
                f"wt={linha['watertight']} glb={_fmt(linha['tamanho_glb_mb'], 2)}MB "
                f"t={_fmt(linha['tempo_s'], 2)}s"
            )
    return linhas


def _fmt(v: Any, casas: int = 3) -> str:
    if v is None:
        return "-"
    return f"{v:.{casas}f}" if isinstance(v, float) else str(v)


def _mediana(valores: list[Any]) -> float | None:
    limpos = [v for v in valores if v is not None]
    return statistics.median(limpos) if limpos else None


def montar_summary(linhas: list[dict[str, Any]], pipelines: list[str]) -> str:
    casos = sorted({l["case"] for l in linhas})
    out = ["# VRMED Reconstruction Benchmark", ""]
    out.append(
        f"Caso(s): {', '.join(casos)} — {len({l['estrutura'] for l in linhas})} estruturas, "
        f"{len(pipelines)} pipelines, {len(linhas)} pares."
    )
    out.append("")
    out.append(
        "Agregado por faixa de escala (mediana). A média global esconde o colapso das "
        "estruturas pequenas, por isso a separação. Distâncias em mm físicos."
    )
    out.append("")
    out += [
        f"**tipo_referencia: `{TIPO_REFERENCIA}`.** Dice / HD95 / ASSD aqui são medidos contra a"
        " MÁSCARA de entrada rasterizada de volta na mesma grade — ou seja, medem apenas o erro"
        " de RECONSTRUÇÃO. NÃO são ground truth clínico e não dizem nada sobre a qualidade da"
        " segmentação: uma máscara errada com reconstrução perfeita dá Dice ~1 aqui.",
        "",
        "Cada erro fica na sua coluna, sem nota agregada: reconstrução (dice/hd95/assd/volume),"
        " topologia (watertight/n_componentes/euler_number), custo de entrega"
        " (triangle_count/vertex_count/tamanho_glb_mb, GLB sem Draco) e tempo.",
        "",
        "`watertight` é contagem de malhas fechadas / malhas ok, não mediana."
        " `n_componentes` > 1 = corpos desconexos (ilhas). Euler = 2 por componente fechado sem alça.",
        "",
    ]

    for faixa in ORDEM_FAIXAS:
        da_faixa = [l for l in linhas if l["faixa"] == faixa]
        if not da_faixa:
            continue
        estruturas = sorted({l["estrutura"] for l in da_faixa})
        out += [
            f"## {faixa}", "",
            f"Estruturas ({len(estruturas)}): {', '.join(estruturas)}", "",
            "| pipeline | n | dice | hd95_mm | assd_mm | volume_error_% | area_mm2 | tris | verts |"
            " watertight | n_comp | euler | glb_mb | tempo_s | falhas |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for pipeline in pipelines:
            do_par = [l for l in da_faixa if l["pipeline"] == pipeline]
            if not do_par:
                continue
            ok = [l for l in do_par if l["erro"] is None]
            med = {m: _mediana([l[m] for l in ok]) for m in METRICAS}
            n_wt = sum(1 for l in ok if l["watertight"])
            out.append(
                f"| {pipeline} | {len(ok)} | {_fmt(med['dice'], 4)} | {_fmt(med['hd95_mm'], 2)} | "
                f"{_fmt(med['assd_mm'])} | {_fmt(med['volume_error_pct'], 2)} | "
                f"{_fmt(med['area_superficie_mm2'], 0)} | {_fmt(med['triangle_count'], 0)} | "
                f"{_fmt(med['vertex_count'], 0)} | {n_wt}/{len(ok)} | "
                f"{_fmt(med['n_componentes'], 0)} | {_fmt(med['euler_number'], 0)} | "
                f"{_fmt(med['tamanho_glb_mb'], 3)} | "
                f"{_fmt(_mediana([l['tempo_s'] for l in ok]), 2)} | {len(do_par) - len(ok)} |"
            )
        out.append("")
    return "\n".join(out)


def gravar(linhas: list[dict[str, Any]], pipelines: list[str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "benchmark.json").write_text(
        json.dumps({"pipelines": pipelines, "resultados": linhas}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with (out_dir / "benchmark.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        for l in linhas:
            w.writerow({**l, "spacing_mm": "x".join(f"{z:g}" for z in l["spacing_mm"])})
    (out_dir / "summary.md").write_text(montar_summary(linhas, pipelines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="VRMED Reconstruction Benchmark")
    ap.add_argument("--masks", required=True, type=Path, help="diretório *_masks com os .nii.gz")
    ap.add_argument("--pipelines", default="marching_cubes,surface_nets,flying_edges,sdf")
    ap.add_argument("--out", required=True, type=Path, help="diretório de saída")
    args = ap.parse_args(argv)

    if not args.masks.is_dir():
        print(f"erro: --masks não é um diretório: {args.masks}", file=sys.stderr)
        return 2

    pipelines = [p.strip() for p in args.pipelines.split(",") if p.strip()]
    if not pipelines:
        print("erro: --pipelines vazio", file=sys.stderr)
        return 2

    try:
        linhas = rodar(args.masks, pipelines)
    except ImportError as exc:
        print(
            f"erro: dependência do benchmark ainda não disponível ({exc}).\n"
            "  Este runner precisa de scripts/geometry/reconstruction.py (reconstruct_surface) e\n"
            "  scripts/validation/mesh_metrics.py (comparar_mascara_malha). Nada foi gravado.",
            file=sys.stderr,
        )
        return 3

    if not linhas:
        print(f"erro: nenhuma máscara utilizável em {args.masks}", file=sys.stderr)
        return 2

    gravar(linhas, pipelines, args.out)
    print()
    print(montar_summary(linhas, pipelines))
    print(f"gravado em: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    # rodado como script, o sys.path recebe scripts/validation/, não a raiz do repo
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    raise SystemExit(main())
