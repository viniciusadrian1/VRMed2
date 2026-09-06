"""Fase 20 — a anotacao de esofago e HUMANA? Medido, nao pesquisado.

O QUE ESTE MODULO DESCOBRIU QUE MUDA A FASE
O `rtstruct_index` do IDC nao traz so `ROINames`. Ele traz tambem:

  ROIGenerationAlgorithms   -> a tag DICOM (3006,0036) ROIGenerationAlgorithm,
                               cujos valores validos no padrao sao AUTOMATIC,
                               SEMIAUTOMATIC e MANUAL;
  RTROIInterpretedTypes     -> a tag (3006,00A4) RTROIInterpretedType, que diz se a
                               ROI e ORGAN, PTV, GTV, EXTERNAL, etc.;
  referenced_SeriesInstanceUID -> a serie de CT que o contorno descreve.

Ou seja: a pergunta que decide a elegibilidade de um dataset — "a mascara e contorno
humano ou saida de modelo?" — tem resposta LEGIVEL POR MAQUINA para as 908 RTSTRUCT
com esofago-orgao, sem baixar um byte de imagem.

E `referenced_SeriesInstanceUID` liga a mascara a imagem POR IDENTIFICADOR, nao por
nome de arquivo. E a prioridade 2 da Fase 20.1 ("DICOM completo + mascara vinculada
por identificadores") satisfeita por construcao no canal DICOM.

CUIDADO QUE O MODULO TOMA
A tag e DECLARATIVA: ela diz o que o autor do arquivo escreveu, nao o que ele fez.
Um RTSTRUCT sem a tag, ou com string vazia, e UNKNOWN — nunca "manual por omissao".
E MANUAL declarado nao exclui pre-anotacao por modelo corrigida a mao: a circularidade
de anotacao que a Fase 16 encontrou no TotalSegmentator seria invisivel aqui tambem.

  python -m scripts.validation.fase20.proveniencia_roi --autoteste
  python -m scripts.validation.fase20.proveniencia_roi
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import idc_esofago as ie  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase20"

RT_INDEX = (Path(os.path.expanduser("~")) / "AppData" / "Local" / "IDC"
            / "idc_index_data" / "24.2.2" / "rtstruct_index.parquet")

# Valores da tag (3006,0036) segundo o padrao DICOM. Qualquer outra coisa e
# vocabulario livre do fabricante e cai em OUTRO — nunca em MANUAL por simpatia.
PADRAO = ("AUTOMATIC", "SEMIAUTOMATIC", "MANUAL")


def _rt() -> pd.DataFrame:
    return pd.read_parquet(RT_INDEX)


def _ix() -> pd.DataFrame:
    import idc_index_data
    return pd.read_parquet(Path(os.path.dirname(idc_index_data.__file__)) / "idc_index.parquet")


def _lista(v) -> list:
    """O parquet guarda listas como ndarray; normaliza para lista de str."""
    if v is None:
        return []
    try:
        return [str(x) for x in list(v)]
    except TypeError:
        return [str(v)]


def algoritmo_do_esofago(nomes, algos) -> list:
    """Algoritmos declarados APENAS para as ROIs que sao esofago-orgao.

    Alinhar por indice e o ponto delicado: `ROINames` e `ROIGenerationAlgorithms` sao
    listas paralelas. Se os comprimentos divergirem, nao ha alinhamento confiavel e o
    caso vira DESALINHADO em vez de um palpite.
    """
    nomes, algos = _lista(nomes), _lista(algos)
    idx = [i for i, n in enumerate(nomes) if ie._nomes_de_esofago([n])]
    if not idx:
        return []
    if len(algos) != len(nomes):
        return ["DESALINHADO"] * len(idx)
    return [(algos[i].strip().upper() or "VAZIO") for i in idx]


# PRV = Planning Risk Volume: o orgao dilatado por uma margem de incerteza. Sob a
# ESOPHAGUS_ONTOLOGY_V1 ele NAO e o alvo — e um objeto maior, por construcao.
PADRAO_PRV = re.compile(r"\bprv\b|_prv|prv_|planning\s*risk", re.IGNORECASE)


def contar_prv(nomes) -> int:
    """Quantos nomes que o crivo aceita como esofago sao, na verdade, PRV."""
    return sum(1 for n in _lista(nomes)
               if ie._nomes_de_esofago([n]) and PADRAO_PRV.search(str(n)))


def classificar(a: str) -> str:
    if a == "MANUAL":
        return "MANUAL"
    if a in ("AUTOMATIC", "SEMIAUTOMATIC"):
        return a
    if a in ("VAZIO", "DESALINHADO", "NAN", "NONE"):
        return "UNKNOWN"
    return "OUTRO"


def medir() -> dict:
    rt = _rt()
    ix = _ix()
    col = ix.drop_duplicates("SeriesInstanceUID").set_index("SeriesInstanceUID")

    linhas = []
    for _, r in rt.iterrows():
        nomes = _lista(r["ROINames"])
        if not ie._nomes_de_esofago(nomes):
            continue
        uid = r["SeriesInstanceUID"]
        meta = col.loc[uid] if uid in col.index else None
        ref = r.get("referenced_SeriesInstanceUID")
        ref = None if ref is None or str(ref) == "nan" else str(ref)
        algos = [classificar(a) for a in algoritmo_do_esofago(r["ROINames"],
                                                              r["ROIGenerationAlgorithms"])]
        linhas.append({
            "SeriesInstanceUID": uid,
            "colecao": None if meta is None else str(meta["collection_id"]),
            "PatientID": None if meta is None else str(meta["PatientID"]),
            "StudyInstanceUID": None if meta is None else str(meta["StudyInstanceUID"]),
            "licenca": None if meta is None else str(meta["license_short_name"]),
            "referenced_SeriesInstanceUID": ref,
            "ct_referenciada_no_indice": bool(ref is not None and ref in col.index),
            "n_rois": int(r["total_rois"]),
            "algoritmos_do_esofago": algos,
            "algoritmo": (Counter(algos).most_common(1)[0][0] if algos else "SEM_ROI"),
            "tipos_interpretados": _lista(r["RTROIInterpretedTypes"])[:8],
            "n_prv": contar_prv(r["ROINames"]),
        })
    return {"linhas": linhas, "n_rtstruct_total": int(len(rt))}


def agregar(linhas) -> dict:
    df = pd.DataFrame(linhas)
    por_col = {}
    for c, g in df.groupby("colecao", dropna=False):
        por_col[str(c)] = {
            "rtstruct_com_esofago": int(len(g)),
            "sujeitos_distintos": int(g["PatientID"].nunique()),
            "estudos_distintos": int(g["StudyInstanceUID"].nunique()),
            "algoritmo": g["algoritmo"].value_counts().to_dict(),
            "licencas": g["licenca"].value_counts().to_dict(),
            "ct_referenciada_resolvida": int(g["ct_referenciada_no_indice"].sum()),
            "ct_referenciada_de": int(len(g)),
        }
    return {
        "total_rtstruct_com_esofago": int(len(df)),
        "sujeitos_distintos_total": int(df["PatientID"].nunique()),
        "algoritmo_global": df["algoritmo"].value_counts().to_dict(),
        "rtstruct_com_prv": int((df["n_prv"] > 0).sum()) if "n_prv" in df else 0,
        "por_colecao": por_col,
    }


def autoteste() -> int:
    falhas = []

    # alinhamento normal
    nomes = ["Lung_L", "Esophagus", "Heart"]
    algos = ["MANUAL", "AUTOMATIC", "MANUAL"]
    got = algoritmo_do_esofago(nomes, algos)
    if got != ["AUTOMATIC"]:
        falhas.append("nao pegou o algoritmo da ROI certa: " + str(got))

    # O crivo de esofago e o MESMO da Fase 11 — nao uma segunda copia. Isso inclui
    # herdar os limites dele, e este teste DOCUMENTA um que o autoteste descobriu:
    # o crivo aceita "Esophagus_PRV". PRV e Planning Risk Volume — o orgao expandido
    # por uma margem, ou seja, OUTRO objeto sob a ESOPHAGUS_ONTOLOGY_V1. O crivo
    # publicado exclui tumor, nao exclui margem de planejamento.
    # NAO corrigimos o crivo aqui: ele e instrumento auditado e o numero 908 esta
    # publicado. O que fazemos e MEDIR quantos PRV existem entre os 908 (ver
    # `contar_prv`) e reportar. Trocar o crivo em silencio mudaria um numero publicado.
    if not algoritmo_do_esofago(["Esophagus_PRV"], ["MANUAL"]):
        falhas.append("o crivo deixou de aceitar PRV — o numero 908 da Fase 11 mudou; "
                      "isso pode ser correto, mas exige nova versao, nao edicao silenciosa")
    if algoritmo_do_esofago(["GTV_esophagus"], ["MANUAL"]):
        falhas.append("GTV foi tratado como esofago-orgao")

    # e a medicao do PRV tem de saber contar
    if contar_prv(["Esophagus", "Esophagus_PRV", "esophagus prv", "Lung_L"]) != 2:
        falhas.append("contagem de PRV errada: " + str(contar_prv(["Esophagus_PRV"])))
    if contar_prv(["Esophagus"]) != 0:
        falhas.append("orgao puro foi contado como PRV")

    # CONTROLE: listas de comprimento diferente nao podem virar palpite
    d = algoritmo_do_esofago(["A", "Esophagus"], ["MANUAL"])
    if d != ["DESALINHADO"]:
        falhas.append("desalinhamento virou palpite: " + str(d))

    # classificacao: so MANUAL e MANUAL; vazio e UNKNOWN, nunca manual por omissao
    for v, esp in (("MANUAL", "MANUAL"), ("AUTOMATIC", "AUTOMATIC"),
                   ("SEMIAUTOMATIC", "SEMIAUTOMATIC"), ("VAZIO", "UNKNOWN"),
                   ("DESALINHADO", "UNKNOWN"), ("EclipseSmartSegmentation", "OUTRO")):
        if classificar(v) != esp:
            falhas.append("classificar(%r) deu %r, esperado %r" % (v, classificar(v), esp))

    # controle NEGATIVO explicito: string vazia NAO pode virar MANUAL
    if classificar("VAZIO") == "MANUAL":
        falhas.append("ausencia da tag virou MANUAL — o pior erro possivel aqui")

    # agregacao: sujeitos distintos, nao series
    linhas = [
        {"colecao": "c", "PatientID": "p1", "StudyInstanceUID": "s1", "licenca": "CC BY 4.0",
         "algoritmo": "MANUAL", "ct_referenciada_no_indice": True},
        {"colecao": "c", "PatientID": "p1", "StudyInstanceUID": "s2", "licenca": "CC BY 4.0",
         "algoritmo": "MANUAL", "ct_referenciada_no_indice": False},
        {"colecao": "c", "PatientID": "p2", "StudyInstanceUID": "s3", "licenca": "CC BY 4.0",
         "algoritmo": "AUTOMATIC", "ct_referenciada_no_indice": True},
    ]
    ag = agregar(linhas)
    if ag["total_rtstruct_com_esofago"] != 3:
        falhas.append("total errado")
    if ag["sujeitos_distintos_total"] != 2:
        falhas.append("sujeitos distintos errado: contou series como casos")
    if ag["por_colecao"]["c"]["ct_referenciada_resolvida"] != 2:
        falhas.append("ligacao mascara-imagem contada errado")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste proveniencia_roi: %d verificacoes, %d falhas" % (14, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    if not RT_INDEX.exists():
        print("rtstruct_index ausente:", RT_INDEX)
        return 1

    r = medir()
    linhas = r["linhas"]
    ag = agregar(linhas)

    print("RTSTRUCT com esofago-ORGAO: %d de %d no indice"
          % (ag["total_rtstruct_com_esofago"], r["n_rtstruct_total"]))
    print("SUJEITOS DISTINTOS com contorno de esofago: %d"
          % ag["sujeitos_distintos_total"])
    print("dos quais com nome de PRV (margem de planejamento, NAO o orgao): %d"
          % ag["rtstruct_com_prv"])
    print()
    print("ROIGenerationAlgorithm DECLARADO para a ROI de esofago — global:")
    for k, v in sorted(ag["algoritmo_global"].items(), key=lambda x: -x[1]):
        print("   %-15s %5d" % (k, v))
    print()
    print("%-20s %8s %9s %10s  %-28s %s"
          % ("colecao", "rtstruct", "SUJEITOS", "CT ligada", "algoritmo declarado", "licenca"))
    for c, g in sorted(ag["por_colecao"].items(), key=lambda x: -x[1]["rtstruct_com_esofago"]):
        print("%-20s %8d %9d %6d/%-4d  %-28s %s"
              % (c, g["rtstruct_com_esofago"], g["sujeitos_distintos"],
                 g["ct_referenciada_resolvida"], g["ct_referenciada_de"],
                 ",".join("%s=%d" % (k, v) for k, v in g["algoritmo"].items())[:28],
                 ",".join(str(k) for k in g["licencas"])))

    SAIDA.mkdir(parents=True, exist_ok=True)
    doc = {
        "fase": 20,
        "fonte": str(RT_INDEX),
        "pergunta": "a ROI de esofago foi declarada MANUAL, AUTOMATIC ou SEMIAUTOMATIC?",
        "tag_dicom": "(3006,0036) ROIGenerationAlgorithm",
        "limites_declarados": [
            "a tag e DECLARATIVA: diz o que o autor escreveu, nao o que ele fez",
            "ausencia da tag e UNKNOWN, nunca MANUAL por omissao",
            "MANUAL declarado NAO exclui pre-anotacao por modelo corrigida a mao — foi "
            "exatamente essa a circularidade que a Fase 16 encontrou no TotalSegmentator, "
            "e ela seria invisivel aqui tambem",
            "o crivo de nome de esofago e o MESMO da Fase 11 (idc_esofago._nomes_de_esofago)",
        ],
        "agregado": ag,
    }
    (SAIDA / "proveniencia_roi.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")

    campos = ["colecao", "PatientID", "StudyInstanceUID", "SeriesInstanceUID",
              "referenced_SeriesInstanceUID", "ct_referenciada_no_indice",
              "licenca", "n_rois", "algoritmo"]
    with (SAIDA / "proveniencia_roi.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            w.writerow({k: l.get(k, "") for k in campos})
    print("\nescrito:", SAIDA / "proveniencia_roi.json", "e .csv (%d linhas)" % len(linhas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
