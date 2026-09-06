"""Varredura completa (shard 3) pelo indice publico do IDC v24.

Le ROINames (RTSTRUCT) e CodeMeanings de propriedade (SEG) de TODAS as series
das colecoes atribuidas, sem baixar DICOM. Reusa o instrumento consertado:
classificar_rois e detectar_entre_arquivos.

DUAS RESSALVAS QUE MUDAM O QUE SE PODE AFIRMAR:
 1. seg_index NAO tem SegmentLabel — so o CodeMeaning do SegmentedPropertyType.
    O rotulo livre (onde moraria 'Obs1'/'Obs2') exige abrir o arquivo.
 2. `segmented_SeriesInstanceUID` vem NaN em parte dos SEG. NaN virando a string
    'nan' agruparia TUDO como se apontasse para a mesma CT — falso positivo de
    D3. Aqui NaN vira None, e sem ancora o detector se abstem (que e o certo).

D3 sai em DUAS leituras, de proposito:
 - `intersecao` (a do instrumento): nome presente em TODOS os arquivos do grupo;
 - `pareado`: nome presente em >= 2 arquivos do grupo. Um terceiro arquivo
   derivado no mesmo grupo zera a intersecao e apaga um par que existe.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
from scripts.validation.tier2.interobservador import (  # noqa: E402
    CRIVO_ESOFAGO,
    CRIVO_TUMOR,
    _norm,
    classificar_rois,
    detectar_entre_arquivos,
)

CACHE = Path("C:/Users/vinic/AppData/Local/IDC/idc_index_data/24.2.2")
SAIDA = RAIZ / ".clinica-dados/fase11/varredura/idc_shard3.json"
MAX_UID = 3

MAPA = {
    "ACRIN-6698": "acrin_6698",
    "ARAR0331": None,
    "Adrenal-ACC-Ki67-Seg": "adrenal_acc_ki67_seg",
    "CALGB50303": None,
    "CC-Radiomics-Phantom": "cc_radiomics_phantom",
    "CPTAC-CCRCC": "cptac_ccrcc",
    "CPTAC-PDA": "cptac_pda",
    "CT-Phantom4Radiomics": "ct_phantom4radiomics",
    "CT4Harmonization-Multicentric": "ct4harmonization_multicentric",
    "Duke-Breast-Cancer-MRI": "duke_breast_cancer_mri",
    "FDG-PET-CT-Lesions": None,
    "ISPY1": "ispy1",
    "Lung Phantom": "lung_phantom",
    "NLST": "nlst",
    "PROSTATEx": "prostatex",
    "PSMA-PET-CT-Lesions": "psma_pet_ct_lesions",
    "Prostate-Anatomical-Edge-Cases": "prostate_anatomical_edge_cases",
    "QIBA CT-1C": "qiba_ct_1c",
    "RIDER Lung CT": "rider_lung_ct",
    "Soft-tissue-Sarcoma": "soft_tissue_sarcoma",
}


def _lista(v) -> list[str]:
    if v is None:
        return []
    try:
        return [str(x) for x in v if str(x)]
    except TypeError:
        return [str(v)]


def _uid(v) -> str | None:
    """NaN/'nan'/'' -> None. Sem isto, D3 agrupa tudo pela mesma chave falsa."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "none") else None


def _pareado(registros: list[dict]) -> dict:
    """Mesmo nome em >= 2 arquivos da MESMA CT (mais frouxo que a intersecao)."""
    por_ct: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    quem: dict[str, dict] = {r["series_uid"]: r for r in registros}
    for r in registros:
        alvo = r.get("serie_referenciada")
        if not alvo:
            continue
        c = r["classificacao"]
        fora = set(c["consenso"]) | set(c["automaticos"])
        for n in r.get("rois", []):
            if n not in fora:
                por_ct[alvo][_norm(n)].add(r["series_uid"])

    # F2 do PAR de esofago pelo campo DECLARADO, nao pelo nome: g3 do instrumento
    # so olha nome, entao um par 100% AUTOMATIC passa por ele sem ser marcado.
    f2 = Counter()
    pipelines = Counter()
    for ct, nomes in por_ct.items():
        for n, uids in nomes.items():
            if len(uids) < 2 or not CRIVO_ESOFAGO.search(n) or CRIVO_TUMOR.search(n):
                continue
            for u in uids:
                r = quem[u]
                f2[r.get("algorithm_type") or "(vazio)"] += 1
                pipelines[f"{r.get('analysis_result_id') or '(colecao)'} | "
                          f"{r.get('algorithm_name') or ''}"] += 1

    achados = []
    for ct, nomes in por_ct.items():
        rep = {n: sorted(u) for n, u in nomes.items() if len(u) >= 2}
        if not rep:
            continue
        achados.append({
            "ct_referenciada": ct,
            "nomes_repetidos": {n: {"n_arquivos": len(u), "series": u[:MAX_UID]}
                                for n, u in rep.items()},
            "esofago_repetido": sorted(n for n in rep
                                       if CRIVO_ESOFAGO.search(n) and not CRIVO_TUMOR.search(n)),
        })
    return {
        "n_cts_com_ancora": len(por_ct),
        "n_cts_com_nome_repetido": len(achados),
        "n_cts_com_esofago_repetido": sum(1 for a in achados if a["esofago_repetido"]),
        "f2_declarado_dos_arquivos_do_par_de_esofago": dict(f2),
        "pipelines_do_par_de_esofago": dict(pipelines.most_common(6)),
        "exemplos": sorted(achados, key=lambda a: -len(a["nomes_repetidos"]))[:5],
    }


def main() -> int:
    import idc_index_data as D

    mi = pd.read_parquet(
        D.IDC_INDEX_PARQUET_FILEPATH,
        columns=["collection_id", "analysis_result_id", "PatientID", "SeriesInstanceUID",
                 "StudyInstanceUID", "Modality", "license_short_name"],
    )
    rt = pd.read_parquet(CACHE / "rtstruct_index.parquet").set_index("SeriesInstanceUID")
    sg = pd.read_parquet(CACHE / "seg_index.parquet").set_index("SeriesInstanceUID")

    saida = {}
    for tcia, cid in MAPA.items():
        if cid is None:
            saida[tcia] = {"colecao": tcia, "no_idc": False,
                           "motivo": "colecao nao existe no IDC v24; varrer pela NBIA"}
            print(f"{tcia:34s} AUSENTE do IDC", flush=True)
            continue
        sub = mi[(mi.collection_id == cid) & (mi.Modality.isin(["RTSTRUCT", "SEG"]))]
        registros, nomes_uid = [], {}
        algos_f2: Counter = Counter()
        colapsados = 0
        for r in sub.itertuples():
            uid = r.SeriesInstanceUID
            if r.Modality == "RTSTRUCT":
                if uid not in rt.index:
                    continue
                row = rt.loc[uid]
                nomes = _lista(row.ROINames)
                tot = int(row.total_rois) if pd.notna(row.total_rois) else None
                colapsados += max(0, (tot or 0) - len(nomes))
                reg = {"modality": "RTSTRUCT",
                       "serie_referenciada": _uid(row.referenced_SeriesInstanceUID),
                       "total_rois": tot,
                       "algorithm_type": ",".join(_lista(row.ROIGenerationAlgorithms)),
                       "fonte_do_nome": "IDC rtstruct_index.ROINames (DISTINCT por serie)"}
                algos_f2.update(_lista(row.ROIGenerationAlgorithms) or ["(vazio no indice)"])
            else:
                if uid not in sg.index:
                    continue
                row = sg.loc[uid]
                nomes = _lista(row.SegmentedPropertyType_CodeMeanings)
                reg = {"modality": "SEG",
                       "serie_referenciada": _uid(row.segmented_SeriesInstanceUID),
                       "total_rois": (int(row.total_segments)
                                      if pd.notna(row.total_segments) else None),
                       "algorithm_name": str(row.AlgorithmName or ""),
                       "algorithm_type": str(row.AlgorithmType or ""),
                       "fonte_do_nome": ("IDC seg_index.SegmentedPropertyType_CodeMeanings "
                                         "(CODIGO, nao SegmentLabel)")}
                algos_f2.update([str(row.AlgorithmType or "(vazio)")])
            reg |= {"case_id": r.PatientID, "series_uid": uid,
                    "study_uid": r.StudyInstanceUID, "rois": nomes,
                    "frame_of_reference_uid": None,
                    "analysis_result_id": str(r.analysis_result_id or ""),
                    "licenca": str(r.license_short_name or "")}
            reg["classificacao"] = classificar_rois(nomes)
            registros.append(reg)
            for n in nomes:
                d = nomes_uid.setdefault(n, {"n_series": 0, "uids": [], "modalidades": set()})
                d["n_series"] += 1
                d["modalidades"].add(r.Modality)
                if len(d["uids"]) < MAX_UID:
                    d["uids"].append(uid)

        entre = detectar_entre_arquivos(registros)
        uniao = sorted(nomes_uid)
        cl = classificar_rois(uniao)
        saida[tcia] = {
            "colecao": tcia, "no_idc": True, "collection_id": cid,
            "n_registros": len(registros),
            "n_series_contorno_no_idc": int(len(sub)),
            "n_casos": int(sub.PatientID.nunique()),
            "n_estudos": int(sub.StudyInstanceUID.nunique()),
            "modalidades": dict(Counter(r["modality"] for r in registros)),
            "nomes": {n: {"n_series": d["n_series"], "uids_de_origem": d["uids"],
                          "modalidades": sorted(d["modalidades"])}
                      for n, d in sorted(nomes_uid.items())},
            "n_nomes_distintos": len(uniao),
            "roi_colapsados_por_distinct": colapsados,
            "algoritmos_declarados_f2": dict(algos_f2.most_common()),
            "licencas": sorted({r["licenca"] for r in registros if r["licenca"]}),
            "analysis_results": dict(Counter(r["analysis_result_id"] for r in registros)),
            "classificacao_da_uniao": cl,
            "d3_intersecao": {"n_grupos": len(entre), "exemplos": entre[:3],
                              "n_grupos_com_esofago": sum(1 for a in entre
                                                          if a["esofago_repetido"])},
            "d3_pareado": _pareado(registros),
        }
        c = saida[tcia]
        print(f"{tcia:34s} regs={len(registros):6d} nomes={len(uniao):4d} "
              f"esof={cl['esofago_oar'][:2]} fam={len(cl['padrao_observador'])} "
              f"d3int={c['d3_intersecao']['n_grupos']} "
              f"d3par={c['d3_pareado']['n_cts_com_nome_repetido']} "
              f"(esof {c['d3_pareado']['n_cts_com_esofago_repetido']})", flush=True)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print("gravado", SAIDA, SAIDA.stat().st_size // 1024, "KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
