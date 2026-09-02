#!/usr/bin/env python
"""
preparar-caso — Etapas 1 e 2 do pipeline clínico + QA (ainda sem malha).

  TC (pasta DICOM | .nrrd | .nii.gz)
    → .clinica-dados/<slug>/ct.nii.gz      HU, espaçamento real, entrada validada
    → .clinica-dados/<slug>/masks/         TotalSegmentator, uma máscara por estrutura
    → tabela de volumes/componentes        + .clinica-dados/<slug>/qa/*.png (máscaras sobre a TC)
    → .clinica-dados/<slug>/relatorio.json

A malha continua em tc-para-vrmed.py (--input ct.nii.gz --masks-dir masks/).

Uso:
  .venv-pipeline/Scripts/python scripts/preparar-caso.py --input exame/ --slug cta-cardio --preset cardiaco
      [--tarefas heartchambers_highres] [--fast] [--reusar-mascaras] [--janela cardiaco] [--forcar]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clinica import ingestao, metricas, qa, segmentacao  # noqa: E402

JANELA_POR_PRESET = {"cardiaco": "cardiaco", "abdomen": "abdome"}


def log(msg: str) -> None:
    print(f"[preparar-caso] {msg}", flush=True)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # console do Windows em cp1252
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", required=True, help="pasta DICOM ou arquivo .nrrd/.nii/.nii.gz")
    parser.add_argument("--slug", required=True, help="nome do caso (pasta em --dados)")
    parser.add_argument("--preset", default="torax", choices=list(segmentacao.PRESETS))
    parser.add_argument(
        "--tarefas",
        default="",
        help="tarefas extras do TotalSegmentator, separadas por vírgula (ex.: heartchambers_highres)",
    )
    parser.add_argument("--fast", action="store_true", help="modo rápido 3 mm (só para preview)")
    parser.add_argument("--dados", default=".clinica-dados", help="raiz dos dados (gitignored)")
    parser.add_argument(
        "--reusar-mascaras",
        action="store_true",
        help="pula ingestão e segmentação se ct.nii.gz e masks/ já existirem",
    )
    parser.add_argument("--janela", default=None, choices=list(qa.JANELAS), help="janela HU dos PNGs")
    parser.add_argument("--serie", default=None, help="SeriesInstanceUID, se a pasta tiver várias séries")
    parser.add_argument("--forcar", action="store_true", help="segue mesmo se não parecer HU")
    args = parser.parse_args()

    entrada = Path(args.input)
    pasta = Path(args.dados) / args.slug
    ct = pasta / "ct.nii.gz"
    masks = pasta / "masks"
    relatorio: dict = {
        "slug": args.slug,
        "preset": args.preset,
        "enquadramento": "visualização educacional — não substitui laudo",
        "etapas_s": {},
    }
    inicio = time.time()

    # ----- 1. Ingestão -----
    if args.reusar_mascaras and ct.exists():
        log(f"reusando {ct}")
    else:
        if not entrada.exists():
            log(f"ERRO: entrada não existe: {entrada}")
            return 1
        try:
            info = ingestao.ingerir(entrada, ct, serie=args.serie, forcar=args.forcar, log=log)
        except ingestao.EntradaInvalida as erro:
            log(f"ERRO: {erro}")
            return 1
        relatorio["ingestao"] = info
        relatorio["etapas_s"]["ingestao"] = info["tempo_s"]
        log(
            f"ct: {info['shape_xyz']} voxels, spacing {info['spacing_mm']} mm, "
            f"HU {info['hu_min']:.0f}..{info['hu_max']:.0f} ({info['tempo_s']} s)"
        )

    # ----- 2. Segmentação -----
    estruturas = segmentacao.PRESETS[args.preset]
    if args.reusar_mascaras and any(masks.glob("*.nii.gz")):
        log(f"reusando máscaras de {masks}")
        relatorio["segmentacao"] = segmentacao.info_segmentacao(masks)
    else:
        seg = segmentacao.rodar_segmentacao(ct, masks, estruturas, fast=args.fast, log=log)
        relatorio["segmentacao"] = seg
        relatorio["etapas_s"]["segmentacao"] = seg["tempo_s"]
        log(f"segmentação: {seg['tempo_s']} s (TotalSegmentator {seg['totalsegmentator_versao']})")

    extras: dict[str, dict] = {}
    for tarefa in [t.strip() for t in args.tarefas.split(",") if t.strip()]:
        destino = masks / tarefa
        if args.reusar_mascaras and any(destino.glob("*.nii.gz")):
            extras[tarefa] = segmentacao.info_segmentacao(destino) or {}
            continue
        try:
            extras[tarefa] = segmentacao.rodar_segmentacao(
                ct, destino, None, fast=args.fast, task=tarefa, log=log
            )
        except segmentacao.LicencaAusente as erro:
            log(f"AVISO: {erro} — tarefa {tarefa} pulada")
            extras[tarefa] = {"pulada": str(erro)}
    if extras:
        relatorio["tarefas_extras"] = extras

    # ----- 3. Métricas (medida automática; enquadramento educacional) -----
    tab = metricas.tabela(masks, estruturas)
    relatorio["estruturas"] = tab
    print(f"\n## {args.slug} — tarefa total\n{metricas.formatar_markdown(tab)}\n")
    for tarefa in extras:
        if any((masks / tarefa).glob("*.nii.gz")):
            tab_extra = metricas.tabela(masks / tarefa)
            relatorio.setdefault("estruturas_extras", {})[tarefa] = tab_extra
            print(f"## {tarefa}\n{metricas.formatar_markdown(tab_extra)}\n")

    # ----- 4. QA visual -----
    janela = qa.JANELAS[args.janela or JANELA_POR_PRESET.get(args.preset, "torax")]
    relatorio["qa"] = qa.sobrepor(ct, masks, pasta / "qa", janela=janela, estruturas=estruturas, log=log)
    for tarefa in extras:
        if any((masks / tarefa).glob("*.nii.gz")):
            relatorio.setdefault("qa_extras", {})[tarefa] = qa.sobrepor(
                ct, masks / tarefa, pasta / "qa" / tarefa, janela=janela, log=log
            )
    log(f"QA: {relatorio['qa']['mosaico']}")

    relatorio["tempo_total_s"] = round(time.time() - inicio, 1)
    (pasta / "relatorio.json").write_text(
        json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log(f"relatório: {pasta / 'relatorio.json'} ({relatorio['tempo_total_s']} s no total)")
    log(
        "próximo passo (malha): python scripts/tc-para-vrmed.py "
        f"--input {ct} --masks-dir {masks} --structures {args.preset} "
        f"--output .clinica-dados/{args.slug}/{args.slug}-sem-draco.glb --report .clinica-dados/{args.slug}/malha.json"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
