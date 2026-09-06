"""Fichas de fonte primaria da Fase 11-B: metadados da API + leitura do arquivo.

Uso:
  python -m scripts.validation.tier2.fichas_fase11b censo <Colecao>
      -> getSeries da colecao inteira, salva bruto e imprime o agregado que
         responde F1 por CONSTRUCAO: quantas series de contorno por estudo,
         por caso, e quantas series de imagem cada contorno pode referenciar.
  python -m scripts.validation.tier2.fichas_fase11b abrir <Colecao> [n]
      -> baixa ate n series de contorno (estratificado: 1 por PatientID, os
         casos com MAIS contornos primeiro) e imprime ROIName / SegmentLabel
         com o SeriesInstanceUID de origem.

Nada aqui decide veredito: imprime medida. O veredito vai na ficha, a mao.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
from scripts.validation.tier2 import tcia  # noqa: E402

DL = RAIZ / ".clinica-dados/fase11/fichas/_dl"
BRUTO = RAIZ / ".clinica-dados/fase11/fichas/_bruto"
CONTORNO = ("RTSTRUCT", "SEG")


def _series(colecao: str) -> list[dict]:
    BRUTO.mkdir(parents=True, exist_ok=True)
    cache = BRUTO / (colecao.replace(" ", "_").replace("/", "_") + "_series.json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    s = tcia.listar_series(colecao)
    cache.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    return s


def censo(colecao: str) -> dict:
    s = _series(colecao)
    por_mod = collections.Counter(x.get("Modality") for x in s)
    cont = [x for x in s if x.get("Modality") in CONTORNO]
    img = [x for x in s if x.get("Modality") not in CONTORNO]
    por_estudo = collections.Counter(x["StudyInstanceUID"] for x in cont)
    por_caso = collections.Counter(x["PatientID"] for x in cont)
    img_por_estudo = collections.Counter(x["StudyInstanceUID"] for x in img)
    lic = {(x.get("LicenseName"), x.get("LicenseURI"), x.get("CollectionURI")) for x in s}
    reg = {
        "colecao": colecao,
        "series_totais": len(s),
        "por_modalidade": dict(por_mod),
        "casos_distintos": len({x["PatientID"] for x in s}),
        "estudos_distintos": len({x["StudyInstanceUID"] for x in s}),
        "contornos": len(cont),
        "estudos_com_contorno": len(por_estudo),
        "casos_com_contorno": len(por_caso),
        "contornos_por_estudo": dict(collections.Counter(por_estudo.values())),
        "contornos_por_caso": dict(collections.Counter(por_caso.values())),
        "imagens_por_estudo": dict(collections.Counter(img_por_estudo.values())),
        "estudos_com_mais_de_um_contorno": [u for u, n in por_estudo.items() if n > 1][:20],
        "casos_com_mais_de_um_contorno": [p for p, n in por_caso.items() if n > 1][:20],
        "licencas": [dict(zip(("nome", "uri", "collection_uri"), t)) for t in sorted(lic, key=str)],
        "third_party": dict(collections.Counter(x.get("ThirdPartyAnalysis") for x in s)),
        "descricoes_de_contorno": dict(collections.Counter(x.get("SeriesDescription") for x in cont).most_common(30)),
        "fabricantes_de_contorno": {
            " | ".join(str(v) for v in k): n
            for k, n in collections.Counter(
                (x.get("Manufacturer"), x.get("ManufacturerModelName"), x.get("SoftwareVersions"))
                for x in cont
            ).most_common(10)
        },
    }
    return reg


def _rois(caminho: Path) -> dict:
    """ROIName (RTSTRUCT) ou SegmentLabel + tipo codificado (SEG), do arquivo."""
    import pydicom

    d = pydicom.dcmread(str(caminho), stop_before_pixels=True)
    mod = str(getattr(d, "Modality", ""))
    out = {"Modality": mod, "SeriesInstanceUID": str(getattr(d, "SeriesInstanceUID", "")),
           "StudyInstanceUID": str(getattr(d, "StudyInstanceUID", "")),
           "PatientID": str(getattr(d, "PatientID", "")),
           "SeriesDescription": str(getattr(d, "SeriesDescription", "")),
           "StructureSetLabel": str(getattr(d, "StructureSetLabel", "")),
           "ContentCreatorName": str(getattr(d, "ContentCreatorName", "")),
           "OperatorsName": str(getattr(d, "OperatorsName", "")),
           "InstitutionName": str(getattr(d, "InstitutionName", "")),
           "referencia": [], "rois": []}
    if mod == "RTSTRUCT":
        for roi in getattr(d, "StructureSetROISequence", []):
            out["rois"].append({
                "ROIName": str(getattr(roi, "ROIName", "")),
                "ROINumber": str(getattr(roi, "ROINumber", "")),
                "ROIGenerationAlgorithm": str(getattr(roi, "ROIGenerationAlgorithm", "")),
            })
        for f in getattr(d, "ReferencedFrameOfReferenceSequence", []):
            for st in getattr(f, "RTReferencedStudySequence", []):
                for se in getattr(st, "RTReferencedSeriesSequence", []):
                    out["referencia"].append(str(getattr(se, "SeriesInstanceUID", "")))
    elif mod == "SEG":
        for seg in getattr(d, "SegmentSequence", []):
            tipo = getattr(seg, "SegmentedPropertyTypeCodeSequence", [None])
            tipo = getattr(tipo[0], "CodeMeaning", "") if tipo and tipo[0] is not None else ""
            out["rois"].append({
                "SegmentLabel": str(getattr(seg, "SegmentLabel", "")),
                "SegmentNumber": str(getattr(seg, "SegmentNumber", "")),
                "SegmentAlgorithmType": str(getattr(seg, "SegmentAlgorithmType", "")),
                "SegmentAlgorithmName": str(getattr(seg, "SegmentAlgorithmName", "")),
                "SegmentDescription": str(getattr(seg, "SegmentDescription", "")),
                "SegmentedPropertyType": str(tipo),
            })
        for r in getattr(d, "ReferencedSeriesSequence", []):
            out["referencia"].append(str(getattr(r, "SeriesInstanceUID", "")))
    return out


def abrir(colecao: str, n: int = 12) -> list[dict]:
    s = _series(colecao)
    cont = [x for x in s if x.get("Modality") in CONTORNO]
    por_caso = collections.Counter(x["PatientID"] for x in cont)
    # casos com mais contornos primeiro; dentro do caso, todos os contornos
    cont.sort(key=lambda x: (-por_caso[x["PatientID"]], x["PatientID"], x["SeriesInstanceUID"]))
    escolhidos, vistos = [], collections.Counter()
    limite_por_caso = 4 if max(por_caso.values(), default=1) > 1 else 1
    for x in cont:
        if vistos[x["PatientID"]] >= limite_por_caso:
            continue
        vistos[x["PatientID"]] += 1
        escolhidos.append(x)
        if len(escolhidos) >= n:
            break
    saida = []
    raiz = DL / colecao.replace(" ", "_")
    for x in escolhidos:
        destino = raiz / x["SeriesInstanceUID"]
        tcia.baixar_serie(x, destino)
        for dcm in sorted(destino.glob("*.dcm")):
            r = _rois(dcm)
            r["arquivo"] = str(dcm)
            r["api_PatientID"] = x["PatientID"]
            r["api_StudyInstanceUID"] = x["StudyInstanceUID"]
            saida.append(r)
    return saida


if __name__ == "__main__":
    cmd, col = sys.argv[1], sys.argv[2]
    if cmd == "censo":
        print(json.dumps(censo(col), ensure_ascii=False, indent=1))
    elif cmd == "abrir":
        print(json.dumps(abrir(col, int(sys.argv[3]) if len(sys.argv) > 3 else 12),
                         ensure_ascii=False, indent=1))
    else:
        raise SystemExit("censo|abrir")
