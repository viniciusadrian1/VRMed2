"""Fase 20 — que canal entrega IDENTIDADE, e sob que licenca, medido do indice publico.

A PERGUNTA QUE ESTE MODULO RESPONDE POR MEDICAO
A Fase 19 mediu o gargalo do dataset proprio: o esquema verifica vazamento por QUATRO
identidades (case_id, study_id, series_id, sha256 do conteudo) e um canal NIfTI so
entrega DUAS — StudyInstanceUID e SeriesInstanceUID nao existem fora do DICOM.

Logo a pergunta da Fase 20 nao e "existe esofago?" (a Fase 11 ja respondeu: 908
RTSTRUCT em 5 colecoes). E: onde o esofago existe COM identidade e COM licenca
verificavel — e quantos SUJEITOS, nao quantas series, cada colecao realmente tem.

POR QUE MEDIR EM VEZ DE PESQUISAR
`idc_index.parquet` (73 MB, ja instalado) traz, por SERIE: PatientID,
StudyInstanceUID, SeriesInstanceUID, Modality, source_DOI, series_size_MB e
**license_short_name**. Ou seja, a licenca do dado esta no indice, por serie, legivel
por maquina — nao e preciso inferir de pagina web. E a distincao serie-x-sujeito, que
a Fase 18 aprendeu a exigir, sai de um `nunique`.

O QUE ESTE MODULO NAO FAZ
Nao baixa imagem, nao ingere caso, nao classifica dataset como elegivel. Licenca
aberta e identidade presente sao condicoes NECESSARIAS; a procedencia da anotacao
(humana x saida de modelo) NAO esta no indice e continua sendo apuracao documental.

  python -m scripts.validation.fase20.censo_identidade --autoteste
  python -m scripts.validation.fase20.censo_identidade
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase20"

# As 5 colecoes com esofago-ORGAO medidas pela Fase 11 e reproduzidas hoje.
# LCTSC e NSCLC-Radiomics ja sao USADAS pelo VRmed — entram aqui para contraste,
# nunca como candidatas a desenho novo (o split delas esta congelado).
ESOFAGO = {
    "pediatric_ct_seg": "359 RTSTRUCT com esofago-orgao",
    "nsclc_radiomics": "355 — JA USADA pelo VRmed (Fase 10)",
    "4d_lung": "101",
    "lctsc": "60 — JA USADA pelo VRmed (split congelado)",
    "eay131": "33 (17 CT) — catalogo de lesao, nao OAR",
}
JA_USADAS = ("nsclc_radiomics", "lctsc")

# Licencas que permitem uso e redistribuicao com atribuicao. Nao e opiniao juridica:
# e o mesmo mapa de classes que `baseline_v1/manifesto.py` ja usa.
ABERTAS_ATRIBUICAO = ("CC BY 3.0", "CC BY 4.0", "CC-BY-3.0", "CC-BY-4.0")


def _indice() -> pd.DataFrame:
    import idc_index_data
    d = Path(os.path.dirname(idc_index_data.__file__))
    return pd.read_parquet(d / "idc_index.parquet")


def _analises() -> pd.DataFrame:
    import idc_index_data
    d = Path(os.path.dirname(idc_index_data.__file__))
    return pd.read_parquet(d / "analysis_results_index.parquet")


def medir_colecao(ix: pd.DataFrame, col: str) -> dict:
    """Serie x estudo x sujeito, licenca e modalidade de UMA colecao.

    A distincao serie-x-sujeito e o ponto: 4D-Lung tem multiplas fases respiratorias
    do MESMO sujeito. Contar series como se fossem casos infla n e, pior, espalha o
    mesmo sujeito por particoes diferentes se o split for por serie.
    """
    sub = ix[ix["collection_id"] == col]
    if sub.empty:
        return {"colecao": col, "erro": "ausente do indice"}
    ct = sub[sub["Modality"] == "CT"]
    lic = sub["license_short_name"].value_counts().to_dict()
    return {
        "colecao": col,
        "series": int(len(sub)),
        "estudos": int(sub["StudyInstanceUID"].nunique()),
        "sujeitos": int(sub["PatientID"].nunique()),
        "series_por_sujeito": round(len(sub) / max(1, sub["PatientID"].nunique()), 2),
        "series_ct": int(len(ct)),
        "sujeitos_ct": int(ct["PatientID"].nunique()),
        "series_ct_por_sujeito": round(len(ct) / max(1, ct["PatientID"].nunique()), 2),
        "modalidades": sub["Modality"].value_counts().to_dict(),
        "licencas": lic,
        "licenca_unica": len(lic) == 1,
        "licenca_aberta_atribuicao": all(k in ABERTAS_ATRIBUICAO for k in lic),
        "tamanho_GB": round(float(sub["series_size_MB"].sum()) / 1024.0, 2),
        "tamanho_ct_GB": round(float(ct["series_size_MB"].sum()) / 1024.0, 2),
        "source_DOI": sorted({str(v) for v in sub["source_DOI"].dropna().unique()})[:3],
        "derivada": bool(sub["analysis_result_id"].notna().any()),
        "body_part": sub["BodyPartExamined"].value_counts().head(4).to_dict(),
        "fabricantes": int(sub["Manufacturer"].nunique()),
        # CORRECAO: a primeira versao deste modulo leu `series_revised_idc_version`
        # como "esta serie foi revisada depois de publicada". ERRADO — o campo vem
        # preenchido em 1.032.911/1.032.911 series, ou seja, 100 %. Ele carrega a
        # VERSAO do IDC em que a serie esta corrente, nao um evento de revisao.
        # A estabilidade de identidade e medida em `estabilidade_de_uid()`, do
        # `prior_versions_index`, que e onde a pergunta tem resposta.
        "versao_corrente_min": int(sub["series_revised_idc_version"].min()),
        "versao_corrente_max": int(sub["series_revised_idc_version"].max()),
        "versao_inicial_min": int(sub["series_init_idc_version"].min()),
        "versao_inicial_max": int(sub["series_init_idc_version"].max()),
    }


def _anos(v):
    """PatientAge do DICOM vem como '006Y', '018M', '003W', '021D'. Nao adivinha."""
    m = re.match(r"^(\d{1,3})([YMWD])$", str(v).strip().upper())
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2)
    return {"Y": n, "M": n / 12.0, "W": n / 52.0, "D": n / 365.0}[u]


def demografia(ix: pd.DataFrame, col: str) -> dict:
    """Idade por SUJEITO. Existe para transformar 'e pediatrico' em medida.

    Sob a ESOPHAGUS_ONTOLOGY_V1 o alvo e o esofago TORACICO adulto: os pisos de
    resolucao da V1 foram calibrados na grade do LCTSC (0,977-1,270 mm no plano,
    parede de 3-4 mm). Um esofago de crianca de 6 anos nao e o mesmo objeto nessa
    grade — e isso e reprovacao por DEFINICAO, nao por acesso nem por licenca.

    RESSALVA MEDIDA: PatientAge vem vazio ou zerado em boa parte das colecoes; e
    artefato de anonimizacao. Onde vier, a fracao legivel entra no resultado.
    """
    sub = ix[ix["collection_id"] == col].drop_duplicates("PatientID")
    brutas = [a for a in (_anos(v) for v in sub["PatientAge"]) if a is not None]
    # '000Y' NAO e um recem-nascido: e artefato de anonimizacao. Um lactente real
    # viria em dias, semanas ou meses ('021D', '003W', '006M'), nunca em zero anos.
    # Sem esta linha o 4D-Lung — 16 sujeitos, todos 000Y, coorte de NSCLC ADULTO —
    # saia marcado PEDIATRICA, que foi exatamente o falso positivo que apareceu.
    zerados = sum(1 for a in brutas if a == 0.0)
    idades = [a for a in brutas if a > 0.0]
    if not idades:
        return {"colecao": col, "sujeitos": int(len(sub)), "idade_legivel": 0,
                "idade_zerada": int(zerados),
                "nota": ("PatientAge ausente ou zerado em %d de %d sujeitos — artefato "
                         "de anonimizacao, idade NAO avaliavel nesta colecao"
                         % (zerados, len(sub)))}
    a = np.array(idades)
    return {
        "colecao": col, "sujeitos": int(len(sub)), "idade_legivel": int(len(a)),
        "idade_zerada": int(zerados),
        "fracao_legivel": round(len(a) / max(1, len(sub)), 3),
        "idade_min": round(float(a.min()), 1),
        "idade_mediana": round(float(np.median(a)), 1),
        "idade_max": round(float(a.max()), 1),
        "menores_de_18_pct": round(100.0 * float((a < 18).mean()), 1),
        # exige tambem massa de idade utilizavel: uma colecao com 3 idades legiveis
        # de 300 sujeitos nao sustenta a afirmacao "e pediatrica"
        "pediatrica": bool((a < 18).mean() > 0.9 and len(a) >= 10
                           and len(a) / max(1, len(sub)) >= 0.2),
    }


def estabilidade_de_uid() -> dict:
    """O SeriesInstanceUID sobrevive a uma troca de versao do IDC?

    A pergunta importa para o congelamento: se um `series_id` gravado hoje deixar de
    existir amanha, ele nao serve de identidade duravel — e so o sha256 do conteudo
    sobra. E exatamente por isso que o esquema tem QUATRO chaves e nao tres.

    Medido comparando `prior_versions_index` (series de versoes anteriores) com o
    indice corrente. Um UID que estava la e nao esta aqui mudou, foi removido, ou a
    serie foi republicada sob outro identificador.
    """
    import idc_index_data
    d = Path(os.path.dirname(idc_index_data.__file__))
    ix = pd.read_parquet(d / "idc_index.parquet")
    pv = pd.read_parquet(d / "prior_versions_index.parquet")
    atual, antigo = set(ix["SeriesInstanceUID"]), set(pv["SeriesInstanceUID"])
    sumiram = antigo - atual
    return {
        "series_no_indice_corrente": int(len(ix)),
        "series_em_versoes_anteriores": int(len(antigo)),
        "uid_sobreviveu": int(len(antigo & atual)),
        "uid_sumiu": int(len(sumiram)),
        "fracao_que_sumiu": round(len(sumiram) / max(1, len(antigo)), 4),
        "leitura": (
            "UID do IDC NAO e persistente entre versoes: %d de %d series de versoes "
            "anteriores (%.1f %%) tem UID ausente do indice corrente. Logo `series_id` "
            "e identidade util para detectar vazamento HOJE, e nao e ancora duravel "
            "entre releases — o sha256 do conteudo e."
            % (len(sumiram), len(antigo), 100.0 * len(sumiram) / max(1, len(antigo)))
        ),
    }


def identidade_disponivel(ix: pd.DataFrame, col: str) -> dict:
    """As tres chaves DICOM existem e sao NAO VAZIAS para toda serie da colecao?"""
    sub = ix[ix["collection_id"] == col]
    if sub.empty:
        return {"colecao": col, "erro": "ausente"}
    out = {"colecao": col}
    for campo, rotulo in (("PatientID", "case_id"),
                          ("StudyInstanceUID", "study_id"),
                          ("SeriesInstanceUID", "series_id")):
        v = sub[campo]
        out[rotulo] = {
            "presente_em": int(v.notna().sum()),
            "de": int(len(sub)),
            "distintos": int(v.nunique()),
            "completo": bool(v.notna().all() and (v.astype(str).str.len() > 0).all()),
        }
    # SeriesInstanceUID tem de ser UNICO por serie — se nao for, o indice tem duplicata
    out["series_id"]["unico"] = bool(sub["SeriesInstanceUID"].nunique() == len(sub))
    return out


def autoteste() -> int:
    falhas = []
    # DataFrame sintetico: 2 sujeitos, 3 series, 1 deles com duas fases (o padrao 4D)
    df = pd.DataFrame({
        "collection_id": ["x", "x", "x", "y"],
        "PatientID": ["p1", "p1", "p2", "p9"],
        "StudyInstanceUID": ["s1", "s1", "s2", "s9"],
        "SeriesInstanceUID": ["a", "b", "c", "z"],
        "Modality": ["CT", "CT", "RTSTRUCT", "CT"],
        "license_short_name": ["CC BY 4.0", "CC BY 4.0", "CC BY 4.0", "CC BY-NC 4.0"],
        "series_size_MB": [1024.0, 1024.0, 1.0, 5.0],
        "source_DOI": ["10.1/x", "10.1/x", "10.1/x", "10.2/y"],
        "analysis_result_id": [None, None, None, None],
        "BodyPartExamined": ["CHEST", "CHEST", "CHEST", "HEAD"],
        "Manufacturer": ["A", "A", "A", "B"],
        "series_revised_idc_version": [5, 5, 5, 5],
        "series_init_idc_version": [1, 1, 2, 3],
    })

    m = medir_colecao(df, "x")
    if m["series"] != 3 or m["sujeitos"] != 2 or m["estudos"] != 2:
        falhas.append("contagem serie/sujeito/estudo errada: " + str(m))
    if m["series_por_sujeito"] != 1.5:
        falhas.append("series por sujeito errada: " + str(m["series_por_sujeito"]))
    # O ponto do modulo: series_ct nao pode contar o RTSTRUCT
    if m["series_ct"] != 2 or m["sujeitos_ct"] != 1:
        falhas.append("contagem de CT contaminada por RTSTRUCT: " + str(m))
    if not m["licenca_aberta_atribuicao"] or not m["licenca_unica"]:
        falhas.append("licenca aberta unica nao reconhecida: " + str(m["licencas"]))
    if m["versao_corrente_min"] != 5 or m["versao_corrente_max"] != 5:
        falhas.append("versao corrente lida errado: " + str(m))
    if abs(m["tamanho_GB"] - round(2049.0 / 1024.0, 2)) > 0.01:
        falhas.append("tamanho errado: " + str(m["tamanho_GB"]))

    # controle NEGATIVO: licenca nao-atribuicao NAO pode ser aceita como aberta
    # demografia: a fixture tem PatientAge? o autoteste do parser cobre os 4 sufixos
    for v, esperado in (("006Y", 6.0), ("018M", 1.5), ("052W", 1.0), ("365D", 1.0),
                        ("000Y", 0.0), ("", None), ("6", None), ("ABC", None)):
        got = _anos(v)
        if esperado is None and got is not None:
            falhas.append("_anos(%r) deveria ser None, deu %r" % (v, got))
        elif esperado is not None and (got is None or abs(got - esperado) > 0.01):
            falhas.append("_anos(%r) deu %r, esperado %r" % (v, got, esperado))

    m2 = medir_colecao(df, "y")
    if m2["licenca_aberta_atribuicao"]:
        falhas.append("CC BY-NC foi classificada como aberta com atribuicao")

    # controle NEGATIVO: colecao inexistente devolve erro, nao zero silencioso
    if "erro" not in medir_colecao(df, "nao_existe"):
        falhas.append("colecao inexistente nao devolveu erro")

    idn = identidade_disponivel(df, "x")
    if not idn["study_id"]["completo"] or idn["study_id"]["distintos"] != 2:
        falhas.append("identidade de estudo medida errado: " + str(idn))
    if not idn["series_id"]["unico"]:
        falhas.append("series_id unico nao reconhecido")

    # controle POSITIVO: um UID ausente tem de derrubar 'completo'
    quebrado = df.copy()
    quebrado.loc[0, "StudyInstanceUID"] = None
    if identidade_disponivel(quebrado, "x")["study_id"]["completo"]:
        falhas.append("UID ausente passou como identidade completa")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste censo_identidade: %d verificacoes, %d falhas" % (17, len(falhas)))
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

    ix = _indice()
    ar = _analises()
    print("idc_index: %d series em %d colecoes | analysis_results: %d"
          % (len(ix), ix["collection_id"].nunique(), len(ar)))
    print()

    print("AS 5 COLECOES COM ESOFAGO-ORGAO — serie x estudo x SUJEITO, e licenca")
    print("%-20s %7s %7s %8s %6s %8s %8s  %s"
          % ("colecao", "series", "estud", "SUJEIT", "s/suj", "CT", "CT_GB", "licenca"))
    medidas = []
    for col in ESOFAGO:
        m = medir_colecao(ix, col)
        if "erro" in m:
            print("%-20s %s" % (col, m["erro"]))
            medidas.append(m)
            continue
        m["ja_usada_pelo_vrmed"] = col in JA_USADAS
        m["nota_fase11"] = ESOFAGO[col]
        m.update({"identidade": identidade_disponivel(ix, col)})
        medidas.append(m)
        print("%-20s %7d %7d %8d %6.2f %8d %8.1f  %s%s"
              % (col, m["series"], m["estudos"], m["sujeitos"], m["series_por_sujeito"],
                 m["series_ct"], m["tamanho_ct_GB"], ",".join(m["licencas"]),
                 "   [JA USADA]" if col in JA_USADAS else ""))

    print()
    print("IDENTIDADE DICOM — as tres chaves que o canal NIfTI nao entrega")
    for m in medidas:
        if "identidade" not in m:
            continue
        i = m["identidade"]
        # Cada chave impressa como PRESENTE_EM/TOTAL e DISTINTOS, nas mesmas
        # colunas — misturar as duas leituras na mesma linha foi a primeira versao
        # deste print, e ela dava a impressao de PatientID faltando.
        print("  %-20s  case_id %4d/%-5d (%4d distintos) | study_id %4d/%-5d (%4d distintos)"
              " | series_id %4d/%-5d %s"
              % (m["colecao"],
                 i["case_id"]["presente_em"], i["case_id"]["de"], i["case_id"]["distintos"],
                 i["study_id"]["presente_em"], i["study_id"]["de"], i["study_id"]["distintos"],
                 i["series_id"]["presente_em"], i["series_id"]["de"],
                 "UNICO" if i["series_id"]["unico"] else "COM DUPLICATA"))

    print()
    print("DEMOGRAFIA POR SUJEITO — 'e pediatrico' vira medida")
    demo = []
    for col in ESOFAGO:
        dm = demografia(ix, col)
        demo.append(dm)
        if dm.get("idade_legivel"):
            print("  %-20s n=%-4d idade legivel %3d (%.0f%%)  min %.0f mediana %.0f max %.0f"
                  "  |  <18 anos: %.0f%%  %s"
                  % (col, dm["sujeitos"], dm["idade_legivel"], 100 * dm["fracao_legivel"],
                     dm["idade_min"], dm["idade_mediana"], dm["idade_max"],
                     dm["menores_de_18_pct"],
                     "PEDIATRICA" if dm["pediatrica"] else ""))
        else:
            print("  %-20s n=%-4d %s" % (col, dm["sujeitos"], dm["nota"]))

    est = estabilidade_de_uid()
    print()
    print("ESTABILIDADE DE IDENTIDADE ENTRE VERSOES DO IDC")
    print("  " + est["leitura"])

    print()
    print("LICENCAS EM TODO O IDC — o indice traz license_short_name por serie")
    tot = ix["license_short_name"].value_counts()
    for k, v in tot.items():
        print("  %-16s %7d series" % (k, v))

    print()
    print("ANALYSIS RESULTS — dado DERIVADO, o canal que parece perfeito e nao serve como GT")
    derivadas = ix[ix["analysis_result_id"].notna()]
    print("  series derivadas no indice: %d em %d analysis results"
          % (len(derivadas), derivadas["analysis_result_id"].nunique()))
    por_ar = derivadas.groupby("analysis_result_id").agg(
        series=("SeriesInstanceUID", "count"),
        sujeitos=("PatientID", "nunique"),
        colecoes=("collection_id", "nunique"),
    ).sort_values("series", ascending=False)
    lic_ar = ar.set_index("analysis_result_id")["license_short_name"].to_dict()
    for k, r in por_ar.head(12).iterrows():
        print("    %-32s %6d series  %5d sujeitos  %2d colecoes  %s"
              % (str(k)[:32], r["series"], r["sujeitos"], r["colecoes"],
                 lic_ar.get(k, "?")))

    SAIDA.mkdir(parents=True, exist_ok=True)
    doc = {
        "fase": 20,
        "fonte": "idc_index_data 24.2.2 — idc_index.parquet e analysis_results_index.parquet",
        "pergunta": ("onde o esofago existe COM identidade DICOM e COM licenca "
                     "verificavel, e quantos SUJEITOS (nao series) cada colecao tem"),
        "limite_declarado": (
            "licenca aberta e identidade presente sao NECESSARIAS, nunca suficientes. "
            "A procedencia da anotacao (humana x saida de modelo) NAO esta no indice."
        ),
        "n_series_indice": int(len(ix)),
        "n_colecoes": int(ix["collection_id"].nunique()),
        "licencas_globais": {str(k): int(v) for k, v in tot.items()},
        "estabilidade_de_uid": est,
        "demografia": demo,
        "colecoes_esofago": medidas,
        "analysis_results": [
            {"analysis_result_id": str(k), "series": int(r["series"]),
             "sujeitos": int(r["sujeitos"]), "colecoes": int(r["colecoes"]),
             "licenca": lic_ar.get(k, "?")}
            for k, r in por_ar.iterrows()
        ],
    }
    (SAIDA / "censo_identidade.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    campos = ["colecao", "series", "estudos", "sujeitos", "series_por_sujeito",
              "series_ct", "sujeitos_ct", "tamanho_ct_GB", "licenca_unica",
              "licenca_aberta_atribuicao", "versao_corrente_max", "ja_usada_pelo_vrmed"]
    with (SAIDA / "censo_identidade.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for m in medidas:
            if "erro" not in m:
                w.writerow({k: m.get(k, "") for k in campos})
    print("\nescrito:", SAIDA / "censo_identidade.json", "e .csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
