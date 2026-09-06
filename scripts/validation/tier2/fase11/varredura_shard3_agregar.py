"""Shard 3 — junta o lado IDC e o lado NBIA num unico shard_3.json.

Por colecao: uniao COMPLETA dos nomes (ROIName do RTSTRUCT, CodeMeaning do SEG
pelo indice do IDC, SegmentLabel do SEG lido do arquivo), o UID de onde cada
nome veio, a cobertura exata de cada fonte e o veredito TRI-ESTADO.

Nome com muitas series guarda os 3 primeiros SeriesInstanceUID + a contagem
total: o vinculo nome->UID fica rastreavel sem copiar o catalogo inteiro. O
limite esta escrito no proprio JSON, em `limite_de_uid`.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
from scripts.validation.tier2 import interobservador as I  # noqa: E402

VARR = RAIZ / ".clinica-dados/fase11/varredura"
MAX_UID = 3

U38 = {"CC-Radiomics-Phantom", "CPTAC-PDA", "CT4Harmonization-Multicentric",
       "FDG-PET-CT-Lesions", "Lung Phantom", "NLST", "PSMA-PET-CT-Lesions",
       "QIBA CT-1C", "Soft-tissue-Sarcoma"}
U59 = {"ACRIN-6698", "ARAR0331", "Adrenal-ACC-Ki67-Seg", "CALGB50303", "CPTAC-CCRCC",
       "CT-Phantom4Radiomics", "Duke-Breast-Cancer-MRI", "ISPY1", "Lung Phantom",
       "NLST", "PROSTATEx", "Prostate-Anatomical-Edge-Cases", "RIDER Lung CT",
       "Soft-tissue-Sarcoma"}


def _censo_1a_onda() -> dict[str, dict]:
    fora = {}
    for i in range(4):
        d = json.loads((RAIZ / f".clinica-dados/fase11/censo/shard_{i}.json").read_text(
            encoding="utf-8"))
        for c in d["colecoes"]:
            fora[c["colecao"]] = c
    return fora


def _pareado_nbia(lidos: list[dict]) -> dict:
    """Mesmo nome em >= 2 arquivos da MESMA CT (ou mesmo frame of reference)."""
    por_ct: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for r in lidos:
        alvo = r.get("serie_referenciada") or r.get("frame_of_reference_uid")
        if not alvo:
            continue
        c = r["classificacao"]
        fora = set(c["consenso"]) | set(c["automaticos"])
        for n in r.get("rois", []):
            if n not in fora:
                por_ct[str(alvo)][I._norm(n)].add(r.get("series_uid"))
    achados = [
        {"alvo": ct,
         "nomes_repetidos": {n: len(u) for n, u in nomes.items() if len(u) >= 2},
         "esofago_repetido": sorted(n for n, u in nomes.items() if len(u) >= 2
                                    and I.CRIVO_ESOFAGO.search(n)
                                    and not I.CRIVO_TUMOR.search(n))}
        for ct, nomes in por_ct.items() if any(len(u) >= 2 for u in nomes.values())
    ]
    return {"n_alvos_com_ancora": len(por_ct),
            "n_alvos_com_nome_repetido": len(achados),
            "n_alvos_com_esofago_repetido": sum(1 for a in achados if a["esofago_repetido"]),
            "exemplos": achados[:3]}


def _uids_do_idc() -> set[str]:
    """UID de todo contorno que o indice do IDC conhece.

    Serve para NAO assumir que o IDC cobre a colecao da TCIA so porque tem mais
    series: em NLST o IDC tem 128.835 SEG e NENHUM deles e um dos 2.004 SEG da
    colecao da TCIA (sao analysis results de terceiros sobre as mesmas CT).
    """
    import idc_index_data as D
    import pandas as pd

    mi = pd.read_parquet(D.IDC_INDEX_PARQUET_FILEPATH,
                         columns=["SeriesInstanceUID", "Modality"])
    return set(mi[mi.Modality.isin(["RTSTRUCT", "SEG"])].SeriesInstanceUID)


def _cobertura_do_shard(saida: dict) -> dict:
    """Cobertura de NOMES sobre o universo da API da TCIA, sem contar duas vezes.

    Uma colecao so conta como COMPLETA quando a checagem empirica mostrou que as
    series lidas na NBIA existem no indice do IDC (senao o catalogo do IDC e
    outro conjunto de series e nao cobre a colecao).
    """
    completas, amostradas, total = [], [], 0
    n_completo = n_amostra = 0
    for k, c in saida.items():
        api = sum(v for kk, v in (c["series_por_modalidade_api"] or {}).items()
                  if kk in ("RTSTRUCT", "SEG"))
        total += api
        chk = c["cobertura"].get("checagem_idc_cobre_tcia") or {}
        cobre = bool(chk.get("de")) and chk["series_lidas_na_nbia_que_existem_no_indice_do_idc"] == chk["de"]
        if cobre and (c["cobertura"]["idc"].get("total_de_contornos_no_idc") or 0) >= api:
            completas.append(k)
            n_completo += api
        else:
            amostradas.append({"colecao": k, "lidos": c["cobertura"]["nbia"]["lidos"],
                               "de": api,
                               "fracao": round(c["cobertura"]["nbia"]["lidos"] / api, 4)
                               if api else None})
            n_amostra += c["cobertura"]["nbia"]["lidos"]
    return {
        "series_de_contorno_na_api_tcia": total,
        "colecoes_com_nomes_completos": completas,
        "series_com_nomes_completos": n_completo,
        "colecoes_por_amostra_declarada": amostradas,
        "series_lidas_por_amostra": n_amostra,
        "cobertura_de_nomes_pct": round(100 * (n_completo + n_amostra) / total, 1)
        if total else None,
        "arquivos_dicom_abertos_na_nbia": sum(
            c["cobertura"]["nbia"]["lidos"] for c in saida.values()),
        "series_lidas_no_indice_do_idc": sum(
            c["cobertura"]["idc"]["lidos"] for c in saida.values()),
    }


def main() -> int:
    censo1 = _censo_1a_onda()
    idc = json.loads((VARR / "idc_shard3.json").read_text(encoding="utf-8"))
    uids_idc = _uids_do_idc()
    saida = {}

    for nome in sorted(U38 | U59):
        c1 = censo1.get(nome, {})
        col = {
            "colecao": nome,
            "no_universo": ("CT+contorno (38) e contorno (59)"
                            if nome in U38 and nome in U59 else
                            "CT+contorno (38)" if nome in U38 else "contorno (59)"),
            "series_por_modalidade_api": c1.get("series_por_modalidade"),
            "n_casos_api": c1.get("n_casos"),
            "n_estudos_api": c1.get("n_estudos"),
            "contornos_por_estudo_api": (c1.get("contornos_por_estudo") or {}).get(
                "distribuicao"),
            "licencas_lidas_da_api": c1.get("licencas_lidas_da_api"),
            "veredito_1a_onda": c1.get("veredito_instrumento"),
        }
        nomes_uid: dict = {}
        cobertura, deteccoes = {}, {}

        def _add(n, uid, modalidade, fonte):
            d = nomes_uid.setdefault(n, {"n_series": 0, "uids": [], "modalidades": set(),
                                         "fontes": set()})
            d["n_series"] += 1
            d["modalidades"].add(modalidade)
            d["fontes"].add(fonte)
            if len(d["uids"]) < MAX_UID:
                d["uids"].append(uid)

        # --- lado IDC (catalogo inteiro, sem baixar DICOM)
        b = idc.get(nome, {})
        if b.get("no_idc"):
            for n, d in b["nomes"].items():
                for u in d["uids_de_origem"]:
                    _add(n, u, "/".join(d["modalidades"]), "IDC v24 (indice)")
                nomes_uid[n]["n_series"] = d["n_series"]
            n_api = sum(v for k, v in (c1.get("series_por_modalidade") or {}).items()
                        if k in ("RTSTRUCT", "SEG"))
            cobertura["idc"] = {
                "lidos": b["n_registros"],
                "total_de_contornos_no_idc": b["n_series_contorno_no_idc"],
                "total_de_contornos_na_api_tcia": n_api or None,
                "fracao_lida_do_idc": (round(b["n_registros"] / b["n_series_contorno_no_idc"], 4)
                                       if b["n_series_contorno_no_idc"] else None),
                "regra": "UNIAO COMPLETA do indice publico do IDC v24 (todas as series)",
                "roi_colapsados_por_distinct": b["roi_colapsados_por_distinct"],
                "algoritmos_declarados_f2": b["algoritmos_declarados_f2"],
                "analysis_results": b["analysis_results"],
                "licencas_idc": b["licencas"],
                "ressalvas": [
                    "ROINames do rtstruct_index e DISTINCT por serie; o excedente aparece "
                    "em roi_colapsados_por_distinct (0 = nenhum nome repetido escondido)",
                    "seg_index NAO tem SegmentLabel: pelo IDC o nome de SEG e o CodeMeaning "
                    "do SegmentedPropertyType — o rotulo livre so sai abrindo o arquivo",
                    "o IDC inclui analysis results de terceiros que a colecao TCIA nao tem",
                ],
            }
            deteccoes["d3_intersecao_idc"] = b["d3_intersecao"]
            deteccoes["d3_pareado_idc"] = b["d3_pareado"]
        else:
            cobertura["idc"] = {"lidos": 0,
                                "regra": "colecao AUSENTE do IDC v24 — so NBIA"}

        # --- lado NBIA (abre o arquivo: SegmentLabel, algoritmo, referencias)
        f = VARR / "nbia" / (I._slug(nome) + ".json")
        if f.exists():
            reg = json.loads(f.read_text(encoding="utf-8"))
            lidos = [r for r in reg.get("contornos_lidos", []) if "classificacao" in r]
            for r in lidos:
                fonte = ("SegmentLabel (arquivo DICOM SEG)" if r.get("segmentos")
                         else "ROIName (arquivo DICOM RTSTRUCT)")
                for n in r.get("rois", []):
                    _add(n, r.get("series_uid"), r.get("modality"), fonte)
            cobertura["nbia"] = (reg.get("cobertura") or {}) | {
                "veredito_do_instrumento_nesta_amostra": reg.get("veredito_instrumento"),
                "erros": sum(1 for r in reg.get("contornos_lidos", []) if "erro" in r),
                "segundos": reg.get("segundos"),
            }
            deteccoes["d3_intersecao_nbia"] = {
                "n_grupos": len((reg.get("resumo") or {}).get("entre_arquivos", [])),
                "exemplos": (reg.get("resumo") or {}).get("entre_arquivos", [])[:2],
            }
            deteccoes["d3_pareado_nbia"] = _pareado_nbia(lidos)
            hit = sum(1 for r in lidos if r.get("series_uid") in uids_idc)
            cobertura["checagem_idc_cobre_tcia"] = {
                "series_lidas_na_nbia_que_existem_no_indice_do_idc": hit,
                "de": len(lidos),
                "leitura": ("o IDC contem as MESMAS series da colecao da TCIA: a leitura "
                            "de catalogo vale como cobertura de nomes"
                            if lidos and hit == len(lidos) else
                            "o IDC NAO contem as series desta colecao da TCIA (sao outras "
                            "series): a cobertura desta colecao e a da amostra NBIA"),
            }
            col["algoritmos_seg_lidos_do_arquivo_f2"] = (
                reg.get("resumo") or {}).get("algoritmos_seg_f2")
            col["observador_dentro_do_arquivo_nbia"] = (
                reg.get("resumo") or {}).get("familias_de_observador")
        else:
            cobertura["nbia"] = {"lidos": 0, "regra": "nao lido pela NBIA neste shard"}

        # --- as tres deteccoes sobre a UNIAO dos nomes
        uniao = sorted(nomes_uid)
        classif = I.classificar_rois(uniao)
        col["nomes"] = {
            n: {"n_series": d["n_series"], "uids_de_origem": d["uids"],
                "modalidades": sorted(x for x in d["modalidades"] if x),
                "fonte_do_nome": sorted(d["fontes"])}
            for n, d in sorted(nomes_uid.items())
        }
        col["limite_de_uid"] = (f"ate {MAX_UID} SeriesInstanceUID por nome + a contagem "
                               "total de series em que o nome aparece")
        col["n_nomes_distintos"] = len(uniao)
        col["cobertura"] = cobertura
        col["esofago"] = {"oar_f5": classif["esofago_oar"],
                          "tumor_ou_sitio_f5": classif["esofago_tumor"]}
        col["observador_dentro_do_arquivo"] = classif["padrao_observador"]
        col["familias_ambiguas"] = classif["familias_ambiguas"]
        col["familias_descartadas"] = classif["familias_descartadas"]
        col["consenso_g2"] = classif["consenso"]
        col["automaticos_g3"] = classif["automaticos"]
        col["entre_arquivos_d3"] = deteccoes

        n_lidos = cobertura["idc"]["lidos"] + cobertura["nbia"]["lidos"]
        d3 = any(v.get("n_grupos") for k, v in deteccoes.items() if k.startswith("d3_inter"))
        d3 = d3 or any(v.get("n_alvos_com_nome_repetido") or v.get("n_cts_com_nome_repetido")
                       for k, v in deteccoes.items() if k.startswith("d3_par"))
        tem_esof = None if n_lidos == 0 else bool(classif["esofago_oar"])
        mult = None if n_lidos == 0 else bool(classif["padrao_observador"] or d3)
        col["resumo"] = {
            "n_leituras_de_contorno": n_lidos,
            "n_leituras_por_fonte": {"idc": cobertura["idc"]["lidos"],
                                     "nbia": cobertura["nbia"]["lidos"]},
            "leitura_nao_e_serie_distinta": ("uma serie coberta pelas DUAS fontes conta "
                                             "duas vezes; a cobertura por fonte esta em "
                                             "`cobertura`"),
            "tem_esofago": tem_esof,
            "multiplos_observadores": mult,
            "n_observadores_hipotese": classif["n_observadores_hipotese"],
            "tri_estado": "true/false/null — null e NAO MEDIDO, nunca ausencia (D6)",
        }
        if tem_esof is None or mult is None:
            col["veredito_instrumento"] = ("INCONCLUSIVO — nada lido (NAO MEDIDO nao e "
                                           "negativo)")
        else:
            I.exigir_tri_estado(tem_esof, "tem_esofago")
            I.exigir_tri_estado(mult, "multiplos_observadores")
            col["veredito_instrumento"] = {
                (True, True): "CANDIDATO — esofago E indicio de multiplos contornos do mesmo objeto",
                (True, False): "esofago SEM indicio de multiplos observadores (F1 nao satisfeito)",
                (False, True): "indicio de multiplos contornos do mesmo objeto SEM esofago (falha F5)",
                (False, False): "nem esofago nem indicio de multiplos observadores",
            }[(tem_esof, mult)]
            if classif["familias_ambiguas"] and not mult:
                col["veredito_instrumento"] += (" — MAS ha familia AMBIGUA registrada: "
                                                "ambiguo NAO e negativo")

        # F2 pelo campo DECLARADO (SegmentAlgorithmType / ROIGenerationAlgorithm), nao
        # pelo nome. g3 do instrumento so olha o NOME; um par 100% AUTOMATIC passa por ele.
        par = (deteccoes.get("d3_pareado_idc") or {})
        declarados = dict(par.get("f2_declarado_dos_arquivos_do_par_de_esofago") or {})
        if not declarados:  # sem par de esofago: cai para a distribuicao da colecao
            declarados = dict(cobertura["idc"].get("algoritmos_declarados_f2") or {})
            for a, n in (col.get("algoritmos_seg_lidos_do_arquivo_f2") or {}).items():
                declarados[a] = declarados.get(a, 0) + n
        else:
            col["pipelines_do_par_de_esofago"] = par.get("pipelines_do_par_de_esofago")
        uteis = {a: n for a, n in declarados.items() if not a.startswith("(")}
        if uteis and mult:
            so_maquina = set(uteis) <= {"AUTOMATIC", "SEMIAUTOMATIC", "SEMIAUTOMATED"}
            col["f2_pelo_campo_declarado"] = {
                "distribuicao": declarados,
                "so_saida_de_maquina": so_maquina,
                "leitura": ("F2 CAI pelo campo declarado: nenhum contorno se declara MANUAL "
                            "— saida de modelo/semiautomatico nao e observador humano "
                            "independente (Parte C)") if so_maquina else
                           ("ha contorno declarado MANUAL; F2 nao cai pelo campo, "
                            "confirmar independencia na fonte primaria"),
            }
            if so_maquina:
                col["veredito_instrumento"] += (
                    " — ELIMINADO por F2 pelo campo declarado (nenhum MANUAL)")
        saida[nome] = col

    doc = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "shard": "3/4",
        "universo": {
            "definicao_do_enunciado": "colecoes do censo da 1a onda com CT E (RTSTRUCT OU SEG)",
            "medido_literalmente_ct_e_contorno": 38,
            "medido_so_com_contorno": 59,
            "por_que_os_dois": ("o enunciado diz '~59', que e o numero de colecoes COM "
                                "CONTORNO (o filtro literal CT E contorno da 38). Para nao "
                                "perder colecao por leitura de enunciado, este shard varreu "
                                "a UNIAO dos dois i%4==3."),
            "colecoes_do_shard": sorted(U38 | U59),
            "n_colecoes": len(U38 | U59),
        },
        "fontes": {
            "idc": "indice publico IDC v24 (rtstruct_index + seg_index), HTTPS anonimo",
            "nbia": "API NBIA + pydicom, via scripts/validation/tier2/interobservador.py",
        },
        "cobertura_do_shard": _cobertura_do_shard(saida),
        "colecoes": saida,
    }
    destino = VARR / "shard_3.json"
    destino.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("gravado", destino, destino.stat().st_size // 1024, "KB")
    for n, c in saida.items():
        print(f"{n:32s} nomes={c['n_nomes_distintos']:5d} lidos={c['resumo']['n_leituras_de_contorno']:7d} "
              f"esof={c['resumo']['tem_esofago']} mult={c['resumo']['multiplos_observadores']} "
              f"| {c['veredito_instrumento'][:58]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
