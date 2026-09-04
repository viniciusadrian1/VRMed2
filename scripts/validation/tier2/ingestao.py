"""Ingestao Tier2 de UM caso do LCTSC: TCIA -> GT NIfTI -> TotalSegmentator -> Parte K.

Ordem que faz predicao e GT compartilharem a grade POR CONSTRUCAO:
  1. baixa a serie CT e a serie RTSTRUCT do caso (cache em disco);
  2. LE os nomes reais das ROIs do RTSTRUCT (nunca assume os da literatura);
  3. converte o RTSTRUCT com dcmrtstruct2nii, que grava as mascaras E o
     `image.nii.gz` da serie de referencia;
  4. roda o TotalSegmentator sobre EXATAMENTE esse `image.nii.gz` — nao sobre
     uma conversao paralela;
  5. Parte K: verifica a grade de cada par (predicao, GT) e o teste de inversao
     de eixo;
  6. grava manifesto.json.

Este script NAO calcula metricas de acuracia — so ingere e prova o alinhamento.

Uso:
  python -m scripts.validation.tier2.ingestao --caso LCTSC-Train-S1-001
"""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

from ...clinica.segmentacao import rodar_segmentacao  # mesmas opcoes da producao
from . import geometria, mapeamento, rtstruct as rtst, tcia

COLECAO = "LCTSC"
RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
PACOTES = ("numpy", "scipy", "nibabel", "SimpleITK", "pydicom", "dcmrtstruct2nii", "TotalSegmentator")


def _versoes() -> dict[str, str]:
    return {p: version(p) for p in PACOTES}


def _serie(series: list[dict], modalidade: str) -> dict:
    achadas = [s for s in series if s.get("Modality") == modalidade]
    if len(achadas) != 1:
        raise RuntimeError(f"esperava 1 serie {modalidade}, achei {len(achadas)}")
    return achadas[0]


def ingerir(caso: str, raiz: Path = RAIZ_PADRAO, task: str = "total", log=print) -> dict:
    destino = Path(raiz) / caso
    destino.mkdir(parents=True, exist_ok=True)

    # 1. metadados + download (cache: nao rebaixa o que ja esta la)
    series = tcia.listar_series(COLECAO, patient_id=caso)
    ct, rt = _serie(series, "CT"), _serie(series, "RTSTRUCT")
    if ct["StudyInstanceUID"] != rt["StudyInstanceUID"]:
        raise RuntimeError("CT e RTSTRUCT em estudos diferentes — caso inconsistente")
    log(f"caso {caso}: CT {ct['ImageCount']} imagens, RTSTRUCT de {rt.get('Manufacturer')}")
    dir_ct = tcia.baixar_serie(ct, destino / "ct")
    dir_rt = tcia.baixar_serie(rt, destino / "rtstruct")

    arquivos_rt = sorted(dir_rt.glob("*.dcm"))
    if len(arquivos_rt) != 1:
        raise RuntimeError(f"esperava 1 arquivo RTSTRUCT, achei {len(arquivos_rt)}")
    arquivo_rt = arquivos_rt[0]

    # 2. nomes REAIS das ROIs, lidos do arquivo
    rois = rtst.listar_rois(arquivo_rt)
    log(f"ROIs no RTSTRUCT ({len(rois)}): {rois}")
    esperadas = list(mapeamento.MAPA_LCTSC)
    mapeadas = {r: mapeamento.canonizar(r) for r in rois}
    divergencia = {
        "nomes_esperados_pela_literatura": esperadas,
        "nomes_reais_lidos_do_arquivo": rois,
        "nao_mapeadas": [r for r, c in mapeadas.items() if c is None],
        "canonicas_ausentes": [c for c in esperadas if c not in mapeadas.values()],
    }
    divergencia["divergiram"] = bool(
        divergencia["nao_mapeadas"] or divergencia["canonicas_ausentes"]
    )
    if divergencia["divergiram"]:
        log(f"AVISO: nomes de ROI divergiram da literatura: {divergencia}")

    # 3. RTSTRUCT -> NIfTI (foreground 255) + image.nii.gz da serie de referencia
    dir_gt = destino / "gt"
    if not (dir_gt / rtst.NOME_IMAGEM).exists():
        rtst.converter(arquivo_rt, dir_ct, dir_gt)
    convertido = {
        "imagem": dir_gt / rtst.NOME_IMAGEM,
        "mascaras": {
            p.name[len(rtst.PREFIXO_MASCARA) :].removesuffix(".nii.gz"): p
            for p in sorted(dir_gt.glob(f"{rtst.PREFIXO_MASCARA}*.nii.gz"))
        },
    }
    imagem = convertido["imagem"]
    log(f"GT: {len(convertido['mascaras'])} mascaras + {imagem.name}")

    # 4. TotalSegmentator sobre O MESMO image.nii.gz (opcoes identicas as da producao)
    dir_pred = destino / "pred_masks"
    if (dir_pred / "segmentacao.json").exists():
        info_seg = json.loads((dir_pred / "segmentacao.json").read_text(encoding="utf-8"))
        log("predicao reusada de pred_masks/segmentacao.json")
    else:
        info_seg = rodar_segmentacao(
            imagem, dir_pred, estruturas=mapeamento.roi_subset(), task=task, log=log
        )

    # 5. Parte K
    geo = {"dicom_original": geometria.metadados_dicom(dir_ct)}
    ref = geometria.descrever_nifti(imagem)
    spacing = ref["zooms_mm"]
    pares = {}
    for nome_real, canonica in mapeadas.items():
        if canonica is None:
            continue
        alvos = mapeamento.MAPA_LCTSC[canonica]
        caminho_gt = convertido["mascaras"].get(nome_real)
        if caminho_gt is None:
            raise FileNotFoundError(f"dcmrtstruct2nii nao gravou mascara para a ROI {nome_real}")
        pred, caminho_pred = mapeamento.unir_predicao(dir_pred, alvos)
        alinhamento = geometria.verificar_alinhamento(caminho_pred, caminho_gt)
        gt = rtst.carregar_mascara(caminho_gt)
        pares[nome_real] = {
            "canonica": canonica,
            "estruturas_totalsegmentator": list(alvos),
            "uniao_de_lobos": len(alvos) > 1,
            "gt": str(caminho_gt),
            "alinhamento": alinhamento,
            "flip": geometria.checar_flip_eixo(pred, gt, spacing),
        }
        log(f"  {nome_real}: {alinhamento['veredito']}; {pares[nome_real]['flip']['veredito']}")
    geo["referencia_nifti"] = ref
    geo["pares"] = pares

    # 6. manifesto
    manifesto = {
        "tier": "Tier2 — acuracia da SEGMENTACAO contra ground truth independente",
        "bloco_de_erro": "A (segmentacao). Nao diz nada sobre B/C/D e nao se soma a eles.",
        "dataset": COLECAO,
        "case_id": caso,
        "licenca": {**tcia.licenca(ct), "doi": "10.7937/K9/TCIA.2017.3r3fvz08"},
        "modalidades": {"imagem": ct["Modality"], "ground_truth": rt["Modality"]},
        "study_instance_uid": ct["StudyInstanceUID"],
        "series_instance_uid": {"ct": ct["SeriesInstanceUID"], "rtstruct": rt["SeriesInstanceUID"]},
        "fabricante": {"ct": ct.get("Manufacturer"), "rtstruct": rt.get("Manufacturer")},
        "software_rtstruct": rt.get("SoftwareVersions"),
        "n_imagens_ct": ct.get("ImageCount"),
        "rois_encontradas": rois,
        "mapeamento_roi": {
            r: list(mapeamento.MAPA_LCTSC[c]) for r, c in mapeadas.items() if c is not None
        },
        "divergencia_de_nomes": divergencia,
        "segmentacao": info_seg,
        "totalsegmentator_task": task,
        "spacing_mm": list(spacing),
        "shape": list(ref["shape"]),
        "orientacao": ref["orientacao"],
        "foreground_gt": 255,
        "limiar_leitura": "> 0.5",
        "versoes": _versoes(),
        "geometria": geo,
        "caminhos": {
            "ct_dicom": str(dir_ct),
            "rtstruct_dicom": str(arquivo_rt),
            "gt_nifti": str(dir_gt),
            "imagem_de_referencia": str(imagem),
            "pred_masks": str(dir_pred),
        },
    }
    saida = destino / "manifesto.json"
    saida.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"manifesto: {saida}")
    return manifesto


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ingestao Tier2 de um caso do LCTSC (TCIA).")
    p.add_argument("--caso", default="LCTSC-Train-S1-001", help="PatientID do LCTSC")
    p.add_argument("--raiz", type=Path, default=RAIZ_PADRAO)
    p.add_argument("--task", default="total", help="tarefa do TotalSegmentator")
    a = p.parse_args(argv)
    if a.caso == "LCTSC-Test-S1-101":
        raise SystemExit(
            "LCTSC-Test-S1-101 e o unico RTSTRUCT escrito por Plastimatch (round-trip extra "
            "de geometria em 2019) — escolha um LCTSC-Train-S1-*"
        )
    ingerir(a.caso, a.raiz, a.task)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
