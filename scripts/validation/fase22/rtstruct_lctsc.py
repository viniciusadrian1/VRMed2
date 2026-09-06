"""Fase 22 — o que os 60 RTSTRUCT do LCTSC dizem sobre si mesmos.

POR QUE ESTE MODULO EXISTE
O critico da Fase 20 apontou a lacuna mais incomoda do projeto: em 21 fases,
NINGUEM abriu um unico arquivo RTSTRUCT DICOM. Todo o censo (19.358 RTSTRUCT, 908
com esofago) e metadado de INDICE. E o LCTSC — a coorte que o VRmed usa, com split
congelado — nunca teve seus arquivos lidos.

O que so aparece abrindo o arquivo:
  ROIName exato, RTROIInterpretedType, ROIGenerationAlgorithm, ContentCreatorName,
  StructureSetLabel, o software que escreveu, e a EXTENSAO REAL do contorno em z.

A EXTENSAO E O PONTO. A Fase 21 deixou aberta uma contradicao: o SegTHOR foi
reprovado por comecar na 4a vertebra CERVICAL, e um avaliador disse que o LCTSC
teria extensao comparavel. O artigo pode nao declarar nada — mas o ARQUIVO declara
onde o contorno realmente comeca e acaba. Isso e medivel aqui, sem fonte externa.

ACHADO QUE ESTE MODULO REGISTRA CONTRA O PROPRIO PROJETO
`Manufacturer` dos 60 RTSTRUCT do LCTSC e `Plastimatch`. Na Fase 20 eu usei
`Manufacturer = Plastimatch` como SINAL DE GERACAO AUTOMATICA ao avaliar o
STOPSTORM. O LCTSC e contorno clinico humano de radioterapia e tambem diz
Plastimatch — porque a tag nomeia o software que ESCREVEU o arquivo, nao quem
desenhou o contorno. O sinal era fraco e fica registrado como tal.

  python -m scripts.validation.fase22.rtstruct_lctsc --autoteste
  python -m scripts.validation.fase22.rtstruct_lctsc
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import idc_esofago as ie  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
LCTSC = RAIZ / ".clinica-dados" / "tier2" / "lctsc"
SAIDA = RAIZ / "docs" / "overnight" / "phase22"

# Tags de autoria que o padrao DICOM oferece para um structure set. Se todas
# estiverem vazias, a autoria NAO esta no arquivo — e isso e um achado, nao um
# problema de leitura.
TAGS_AUTORIA = ("ContentCreatorName", "ReviewerName", "ReviewDate",
                "ApprovalStatus", "OperatorsName", "InstitutionName",
                "StationName", "Manufacturer", "ManufacturerModelName",
                "SoftwareVersions", "StructureSetLabel", "StructureSetName",
                "StructureSetDescription")


def _v(ds, nome):
    v = getattr(ds, nome, None)
    return "" if v is None else str(v).strip()


def medir_caso(caminho: Path) -> dict:
    import pydicom
    ds = pydicom.dcmread(str(caminho), stop_before_pixels=True, force=True)

    rois = []
    for r in getattr(ds, "StructureSetROISequence", []):
        rois.append({
            "numero": int(r.ROINumber),
            "nome": str(r.ROIName),
            "algoritmo": _v(r, "ROIGenerationAlgorithm"),
            "descricao": _v(r, "ROIDescription"),
        })
    tipos = {}
    for o in getattr(ds, "RTROIObservationsSequence", []):
        tipos[int(o.ReferencedROINumber)] = {
            "interpreted_type": _v(o, "RTROIInterpretedType"),
            "interpreter": _v(o, "ROIInterpreter"),
            "observation_label": _v(o, "ROIObservationLabel"),
        }

    # geometria dos contornos, por ROI
    geo = {}
    for c in getattr(ds, "ROIContourSequence", []):
        seq = getattr(c, "ContourSequence", [])
        zs = sorted({round(float(s.ContourData[2]), 3) for s in seq
                     if len(getattr(s, "ContourData", [])) >= 3})
        # ContourImageSequence e Tipo 3 (opcional): sem ele nao da para ligar cada
        # contorno a uma instancia de imagem. E exatamente o que o critico da Fase 20
        # pediu para verificar.
        com_img = sum(1 for s in seq if getattr(s, "ContourImageSequence", None))
        geo[int(c.ReferencedROINumber)] = {
            "n_contornos": len(seq),
            "n_fatias": len(zs),
            "z_min": zs[0] if zs else None,
            "z_max": zs[-1] if zs else None,
            "extensao_mm": round(zs[-1] - zs[0], 2) if len(zs) >= 2 else 0.0,
            "contornos_com_ContourImageSequence": com_img,
        }

    nomes = [r["nome"] for r in rois]
    eso = ie._nomes_de_esofago(nomes)
    n_eso = next((r["numero"] for r in rois if r["nome"] in eso), None)

    # extensao de OUTRAS estruturas, para dar escala: o esofago sozinho nao diz nada
    ref = {}
    for r in rois:
        g = geo.get(r["numero"], {})
        ref[r["nome"]] = {"n_fatias": g.get("n_fatias"), "z_min": g.get("z_min"),
                          "z_max": g.get("z_max"), "extensao_mm": g.get("extensao_mm")}

    autoria = {t: _v(ds, t) for t in TAGS_AUTORIA}
    return {
        "caso": caminho.parents[1].name,
        "instituicao_rotulo": caminho.parents[1].name.split("-")[2]
        if len(caminho.parents[1].name.split("-")) > 2 else "?",
        "n_rois": len(rois),
        "rois": nomes,
        "esofago_nome": eso[0] if eso else None,
        "esofago_algoritmo": next((r["algoritmo"] for r in rois if r["nome"] in eso), ""),
        "esofago_tipo": (tipos.get(n_eso, {}).get("interpreted_type", "")
                         if n_eso is not None else ""),
        "esofago_interpreter": (tipos.get(n_eso, {}).get("interpreter", "")
                                if n_eso is not None else ""),
        "algoritmos_todos": dict(Counter(r["algoritmo"] or "VAZIO" for r in rois)),
        "tipos_todos": dict(Counter(v["interpreted_type"] or "VAZIO"
                                    for v in tipos.values())),
        "autoria": autoria,
        "geometria_por_estrutura": ref,
        "esofago": ref.get(eso[0]) if eso else None,
        "study_uid": _v(ds, "StudyInstanceUID"),
        "series_uid": _v(ds, "SeriesInstanceUID"),
        "patient_id": _v(ds, "PatientID"),
        "referenced_ct_uid": _referenciada(ds),
    }


def _referenciada(ds) -> str:
    try:
        s = (ds.ReferencedFrameOfReferenceSequence[0]
             .RTReferencedStudySequence[0].RTReferencedSeriesSequence[0])
        return str(s.SeriesInstanceUID)
    except Exception:  # noqa: BLE001
        return ""


def agregar(linhas) -> dict:
    com_eso = [l for l in linhas if l["esofago"]]
    ext = [l["esofago"]["extensao_mm"] for l in com_eso if l["esofago"]["extensao_mm"]]
    fat = [l["esofago"]["n_fatias"] for l in com_eso]

    # A comparacao que da escala: onde o esofago comeca em relacao ao topo do
    # PULMAO do mesmo caso. Se o contorno subisse ao pescoco, comecaria BEM acima
    # do apice pulmonar. Isso e medivel sem nenhuma fonte externa.
    rel = []
    for l in com_eso:
        g = l["geometria_por_estrutura"]
        pulmoes = [g[k] for k in g if k.lower().startswith("lung") and g[k]["z_max"] is not None]
        if not pulmoes or l["esofago"]["z_max"] is None:
            continue
        topo_pulmao = max(p["z_max"] for p in pulmoes)
        base_pulmao = min(p["z_min"] for p in pulmoes)
        rel.append({
            "caso": l["caso"],
            "eso_z_max_menos_topo_pulmao": round(l["esofago"]["z_max"] - topo_pulmao, 2),
            "eso_z_min_menos_base_pulmao": round(l["esofago"]["z_min"] - base_pulmao, 2),
        })

    acima = [r["eso_z_max_menos_topo_pulmao"] for r in rel]
    abaixo = [r["eso_z_min_menos_base_pulmao"] for r in rel]

    autor_vazio = {}
    for t in TAGS_AUTORIA:
        vazios = sum(1 for l in linhas if not l["autoria"].get(t))
        autor_vazio[t] = {"vazio_em": vazios, "de": len(linhas),
                          "valores": sorted({l["autoria"].get(t) for l in linhas
                                             if l["autoria"].get(t)})[:3]}

    return {
        "n_casos": len(linhas),
        "com_esofago": len(com_eso),
        "nomes_de_esofago": dict(Counter(l["esofago_nome"] for l in com_eso)),
        "roi_sets_distintos": dict(Counter(tuple(sorted(l["rois"])) for l in linhas)).__len__(),
        "algoritmo_do_esofago": dict(Counter(l["esofago_algoritmo"] or "VAZIO" for l in com_eso)),
        "tipo_interpretado_do_esofago": dict(Counter(l["esofago_tipo"] or "VAZIO" for l in com_eso)),
        "extensao_esofago_mm": {
            "min": min(ext) if ext else None, "mediana": float(np.median(ext)) if ext else None,
            "max": max(ext) if ext else None} if ext else {},
        "fatias_esofago": {"min": min(fat), "mediana": float(np.median(fat)),
                           "max": max(fat)} if fat else {},
        "esofago_vs_pulmao": {
            "n": len(rel),
            "acima_do_topo_do_pulmao_mm": {
                "min": round(min(acima), 2), "mediana": round(float(np.median(acima)), 2),
                "max": round(max(acima), 2),
                "casos_acima_do_topo": sum(1 for a in acima if a > 0)} if acima else {},
            "abaixo_da_base_do_pulmao_mm": {
                "min": round(min(abaixo), 2), "mediana": round(float(np.median(abaixo)), 2),
                "max": round(max(abaixo), 2),
                "casos_abaixo_da_base": sum(1 for a in abaixo if a < 0)} if abaixo else {},
        },
        "tags_de_autoria": autor_vazio,
        "ct_referenciada_resolvida": sum(1 for l in linhas if l["referenced_ct_uid"]),
        "contour_image_sequence": {
            "casos_com_pelo_menos_um": sum(
                1 for l in linhas
                if any(v.get("n_fatias") for v in l["geometria_por_estrutura"].values())),
        },
    }


def autoteste() -> int:
    falhas = []
    # _v nunca pode inventar valor
    class _D:
        A = "  x  "
    if _v(_D(), "A") != "x":
        falhas.append("_v nao normalizou espacos")
    if _v(_D(), "NAO_EXISTE") != "":
        falhas.append("_v inventou valor para tag ausente")

    # o crivo de esofago e o do projeto, nao uma copia
    if ie._nomes_de_esofago(["Esophagus"]) != ["Esophagus"]:
        falhas.append("crivo de esofago mudou")
    if ie._nomes_de_esofago(["Lung_L", "Heart", "SpinalCord"]):
        falhas.append("crivo aceitou estrutura que nao e esofago")

    # agregacao: extensao e por ROI, e o relativo ao pulmao tem de ter sinal certo
    linhas = [{
        "caso": "c1", "rois": ["Esophagus", "Lung_L"], "esofago_nome": "Esophagus",
        "esofago_algoritmo": "", "esofago_tipo": "ORGAN", "referenced_ct_uid": "1.2.3",
        "autoria": {t: "" for t in TAGS_AUTORIA},
        "esofago": {"n_fatias": 50, "z_min": -100.0, "z_max": 50.0, "extensao_mm": 150.0},
        "geometria_por_estrutura": {
            "Esophagus": {"n_fatias": 50, "z_min": -100.0, "z_max": 50.0, "extensao_mm": 150.0},
            "Lung_L": {"n_fatias": 60, "z_min": -120.0, "z_max": 40.0, "extensao_mm": 160.0}},
    }]
    ag = agregar(linhas)
    if ag["com_esofago"] != 1:
        falhas.append("agregacao nao achou o esofago")
    r = ag["esofago_vs_pulmao"]["acima_do_topo_do_pulmao_mm"]
    # esofago vai ate z=50, pulmao ate z=40 -> esofago 10 mm ACIMA do topo do pulmao
    if r["mediana"] != 10.0 or r["casos_acima_do_topo"] != 1:
        falhas.append("relacao esofago-pulmao calculada errado: " + str(r))
    r2 = ag["esofago_vs_pulmao"]["abaixo_da_base_do_pulmao_mm"]
    # esofago comeca em -100, pulmao em -120 -> esofago 20 mm ACIMA da base (nao abaixo)
    if r2["mediana"] != 20.0 or r2["casos_abaixo_da_base"] != 0:
        falhas.append("relacao caudal calculada errado: " + str(r2))

    # CONTROLE: tag de autoria vazia tem de ser contada como vazia
    if ag["tags_de_autoria"]["ContentCreatorName"]["vazio_em"] != 1:
        falhas.append("tag vazia nao foi contada")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste rtstruct_lctsc: %d verificacoes, %d falhas" % (9, len(falhas)))
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

    arquivos = sorted(glob.glob(str(LCTSC / "*" / "rtstruct" / "*.dcm")))
    if not arquivos:
        print("nenhum RTSTRUCT em", LCTSC)
        return 1
    linhas = [medir_caso(Path(f)) for f in arquivos]
    ag = agregar(linhas)

    print("RTSTRUCT do LCTSC abertos: %d  |  com esofago: %d"
          % (ag["n_casos"], ag["com_esofago"]))
    print("nome da ROI de esofago:", ag["nomes_de_esofago"])
    print("ROIGenerationAlgorithm do esofago:", ag["algoritmo_do_esofago"])
    print("RTROIInterpretedType do esofago:", ag["tipo_interpretado_do_esofago"])
    print("CT referenciada por UID: %d/%d" % (ag["ct_referenciada_resolvida"], ag["n_casos"]))
    print()
    print("TAGS DE AUTORIA — o que o arquivo declara sobre quem contornou")
    for t, v in ag["tags_de_autoria"].items():
        estado = "VAZIA em %d/%d" % (v["vazio_em"], v["de"])
        print("  %-26s %-16s %s" % (t, estado, v["valores"] if v["valores"] else ""))
    print()
    e = ag["extensao_esofago_mm"]
    f = ag["fatias_esofago"]
    print("EXTENSAO DO CONTORNO DE ESOFAGO (medida no arquivo, nao no artigo)")
    print("  extensao em z: min %.1f  mediana %.1f  max %.1f mm"
          % (e["min"], e["mediana"], e["max"]))
    print("  fatias:        min %d  mediana %.0f  max %d" % (f["min"], f["mediana"], f["max"]))
    print()
    rp = ag["esofago_vs_pulmao"]
    print("O ESOFAGO SOBE ACIMA DO PULMAO? (a pergunta da contradicao SegTHOR x LCTSC)")
    print("  n comparaveis: %d" % rp["n"])
    ac = rp["acima_do_topo_do_pulmao_mm"]
    print("  topo do esofago menos topo do pulmao: min %.1f  mediana %.1f  max %.1f mm"
          % (ac["min"], ac["mediana"], ac["max"]))
    print("  casos em que o esofago sobe ACIMA do apice pulmonar: %d/%d"
          % (ac["casos_acima_do_topo"], rp["n"]))
    ab = rp["abaixo_da_base_do_pulmao_mm"]
    print("  base do esofago menos base do pulmao: min %.1f  mediana %.1f  max %.1f mm"
          % (ab["min"], ab["mediana"], ab["max"]))
    print("  casos em que o esofago desce ABAIXO da base pulmonar: %d/%d"
          % (ab["casos_abaixo_da_base"], rp["n"]))

    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "rtstruct_lctsc.json").write_text(json.dumps({
        "fase": 22,
        "pergunta": ("o que os 60 RTSTRUCT do LCTSC declaram sobre definicao e autoria "
                     "do contorno de esofago — lido no arquivo, nao no artigo"),
        "limite_declarado": (
            "extensao em z e do CONTORNO, nao da anatomia. Ela diz onde o anotador "
            "parou, que e exatamente o que a ESOPHAGUS_ONTOLOGY_V1 chama de 'herdada "
            "do GT'. Nao converte em capacidade de localizar marco anatomico."
        ),
        "agregado": ag, "casos": linhas,
    }, indent=1, ensure_ascii=False), encoding="utf-8")

    campos = ["caso", "esofago_nome", "esofago_algoritmo", "esofago_tipo",
              "n_rois", "patient_id", "study_uid", "series_uid", "referenced_ct_uid"]
    with (SAIDA / "rtstruct_lctsc.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos + ["eso_fatias", "eso_extensao_mm"],
                           extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            row = {k: l.get(k, "") for k in campos}
            row["eso_fatias"] = (l["esofago"] or {}).get("n_fatias", "")
            row["eso_extensao_mm"] = (l["esofago"] or {}).get("extensao_mm", "")
            w.writerow(row)
    print("\nescrito:", SAIDA / "rtstruct_lctsc.json", "e .csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
