"""Cobertura 100% de ROIName / tipo de segmento pelo indice do IDC v24.2.2.

Cruza os SeriesInstanceUID de contorno que a API do TCIA devolveu (arquivo
bruto de fichas_fase11b) com rtstruct_index / seg_index do idc-index local.
Declara SEMPRE a cobertura: uid_da_api que o indice nao tem vira `ausentes`,
nunca vira negativo.

RESSALVA (a mesma do shard 3): seg_index NAO tem SegmentLabel, so o CodeMeaning
do SegmentedPropertyType. Rotulo livre ('Obs1') exige abrir o arquivo.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
BRUTO = RAIZ / ".clinica-dados/fase11/fichas/_bruto"
IDC = Path("C:/Users/vinic/AppData/Local/IDC/idc_index_data/24.2.2")


def _lista(v) -> list[str]:
    """Escalar vira lista de UM item — str e iteravel, e iterar caracteres
    transformaria 'MANUAL' em M/A/N/U/A/L (bug real, visto na 1a rodada)."""
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v else []
    try:
        return [str(x) for x in v]
    except TypeError:
        return [str(v)]


def cruzar(colecao: str) -> dict:
    series = json.loads((BRUTO / (colecao.replace(" ", "_") + "_series.json")).read_text("utf-8"))
    cont = [x for x in series if x.get("Modality") in ("RTSTRUCT", "SEG")]
    uids = {x["SeriesInstanceUID"]: x for x in cont}
    rt = pd.read_parquet(IDC / "rtstruct_index.parquet")
    sg = pd.read_parquet(IDC / "seg_index.parquet")
    rt = rt[rt.SeriesInstanceUID.isin(uids)]
    sg = sg[sg.SeriesInstanceUID.isin(uids)]
    achados = set(rt.SeriesInstanceUID) | set(sg.SeriesInstanceUID)

    nomes = collections.Counter()
    algos = collections.Counter()
    por_serie_eso = collections.Counter()
    ref = collections.Counter()
    for _, r in rt.iterrows():
        ns = _lista(r.ROINames)
        gs = _lista(r.ROIGenerationAlgorithms)
        nomes.update(ns)
        algos.update(gs if gs else ["(vazio)"])
        por_serie_eso[sum(1 for n in ns if "esoph" in n.lower())] += 1
        ref[str(r.referenced_SeriesInstanceUID)] += 1
    for _, r in sg.iterrows():
        ns = _lista(r.SegmentedPropertyType_CodeMeanings)
        nomes.update(ns)
        algos.update(_lista(r.AlgorithmType) or ["(vazio)"])
        por_serie_eso[sum(1 for n in ns if "esoph" in n.lower())] += 1
        ref[str(r.segmented_SeriesInstanceUID)] += 1

    return {
        "colecao": colecao,
        "contornos_na_api": len(uids),
        "cobertos_pelo_idc": len(achados),
        "ausentes_do_idc": len(uids) - len(achados),
        "rtstruct_no_idc": int(len(rt)),
        "seg_no_idc": int(len(sg)),
        "nomes_distintos": len(nomes),
        "nomes": dict(nomes.most_common(60)),
        # ATENCAO: ROIGenerationAlgorithms do indice vem DEDUPLICADO por serie —
        # nao e paralelo a ROINames. Da para dizer "esta serie tem algum ROI
        # AUTOMATIC", nunca "o esofago DESTA serie e AUTOMATIC". Isso exige abrir.
        "algoritmos_por_serie_deduplicado": dict(algos),
        "esofagos_por_serie": {str(k): v for k, v in sorted(por_serie_eso.items())},
        "series_de_imagem_referenciadas_mais_de_uma_vez": {
            k: v for k, v in ref.most_common(10) if v > 1
        },
        "n_referencias_distintas": len(ref),
    }


if __name__ == "__main__":
    print(json.dumps(cruzar(sys.argv[1]), ensure_ascii=False, indent=1))
