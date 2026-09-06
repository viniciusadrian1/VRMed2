"""SegmentLabel / ROIName LIDOS DO ARQUIVO em uma arvore ja baixada.

O indice do IDC nao tem SegmentLabel — o rotulo livre, unico lugar onde um
'Obs1'/'Reader2'/'nodule - reader A' apareceria. Este script varre um diretorio
de series (cada subdiretorio = SeriesInstanceUID, com _tcia_serie.json) e
agrega os rotulos reais, com o UID de origem.

Uso: python -m scripts.validation.tier2.fichas_fase11b_rotulos <dir> [saida.json]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
from scripts.validation.tier2.fichas_fase11b import _rois  # noqa: E402


def varrer(raiz: Path) -> dict:
    series, erros = [], []
    for dcm in sorted(raiz.rglob("*.dcm")):
        try:
            r = _rois(dcm)
        except Exception as e:  # noqa: BLE001
            erros.append({"arquivo": str(dcm), "erro": f"{type(e).__name__}: {e}"})
            continue
        r["arquivo"] = str(dcm)
        series.append(r)

    rot = collections.Counter()
    tipos = collections.Counter()
    algo = collections.Counter()
    nome_algo = collections.Counter()
    creator = collections.Counter()
    desc = collections.Counter()
    por_ct = collections.defaultdict(set)
    n_seg = collections.Counter()
    for r in series:
        creator[r["ContentCreatorName"] + " | " + r["OperatorsName"] + " | " + r["InstitutionName"]] += 1
        desc[r["SeriesDescription"] + " | " + r["StructureSetLabel"]] += 1
        n_seg[len(r["rois"])] += 1
        for a in r["referencia"]:
            por_ct[a].add(r["SeriesInstanceUID"])
        for x in r["rois"]:
            rot[x.get("SegmentLabel") or x.get("ROIName", "")] += 1
            tipos[x.get("SegmentedPropertyType", "")] += 1
            algo[x.get("SegmentAlgorithmType") or x.get("ROIGenerationAlgorithm", "")] += 1
            nome_algo[x.get("SegmentAlgorithmName", "")] += 1

    multi = {k: sorted(v)[:6] for k, v in por_ct.items() if len(v) > 1}
    return {
        "diretorio": str(raiz),
        "series_lidas": len(series),
        "erros": erros[:10],
        "rotulos_livres": dict(rot.most_common(80)),
        "rotulos_distintos": len(rot),
        "tipos_codificados": dict(tipos.most_common(20)),
        "algoritmo_declarado": dict(algo),
        "nome_do_algoritmo": dict(nome_algo.most_common(15)),
        "criador_operador_instituicao": dict(creator.most_common(15)),
        "descricao_e_label": dict(desc.most_common(15)),
        "segmentos_por_arquivo": {str(k): v for k, v in sorted(n_seg.items())},
        "series_de_imagem_com_mais_de_um_contorno": len(multi),
        "exemplos_ct_com_varios_contornos": dict(list(multi.items())[:5]),
        "ct_referenciadas_distintas": len(por_ct),
    }


if __name__ == "__main__":
    reg = varrer(Path(sys.argv[1]))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(reg, ensure_ascii=False, indent=1))
