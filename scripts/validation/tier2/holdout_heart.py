"""
Fase 7, Objetivo A — VALIDACAO no holdout da hipotese do mapeamento cardiaco.

A hipotese foi fixada na FASE 6, no conjunto de development, e esta congelada aqui:

    o objeto que o GT do LCTSC chama `Heart` e melhor representado por
    TotalSegmentator::pericardium (task trunk_cavities) do que por
    TotalSegmentator::heart (task total)

Numero de SELECAO da fase 6 (6 casos do development): dice 0,9056 contra 0,7709.
Numero de SELECAO NAO E NUMERO DE VALIDACAO. Este modulo existe para produzir o
segundo.

------------------------------------------------------------------------------
O QUE ESTE MODULO PODE E NAO PODE FAZER

PODE: medir as DUAS comparacoes ja declaradas, em validation e em test.
NAO PODE: escolher qualquer coisa a partir do que vir. A comparacao, as metricas
e os limiares estao todos fixados abaixo, ANTES da execucao. Se o resultado
contrariar a hipotese, o mapeamento antigo permanece — isso e um desfecho
previsto, nao uma falha.

O `test` e usado UMA vez, para esta hipotese, e para mais nada nesta fase.
Qualquer outra decisao (esofago, medula, modelo, dataset) fica proibida de olhar
para ele — ver docs/RELATORIO-FASE7-HOLDOUT-ESOFAGO.md.
------------------------------------------------------------------------------

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.segmentation_metrics import compare_masks  # noqa: E402
from scripts.validation.tier2 import fase5, geometria, pericardio  # noqa: E402
from scripts.validation.tier2 import rtstruct as rtst  # noqa: E402
from scripts.validation.tier2.benchmark_tier2 import recall_containment  # noqa: E402

RAIZ = Path(".clinica-dados/tier2/lctsc")
SAIDA = RAIZ / "fase7" / "holdout_heart"
NM = "nao medido"

# A COMPARACAO, congelada. Nao ha terceira opcao e nao se acrescenta variante
# depois de ver o resultado. `heart` e o mapeamento VIGENTE; `pericardium` e o
# candidato que venceu na selecao.
VIGENTE = "heart"
CANDIDATO = "pericardium"
GT_ROI = "Heart"

# Limiares herdados da fase 5, inalterados (Parte 5 da fase 7 manda usar estes).
LIMIAR_DICE = fase5.LIMIAR_MELHORIA_DICE            # 0,01
LIMIAR_REGRESSAO_DICE = fase5.LIMIAR_REGRESSAO_DICE  # 0,01
LIMIAR_HD95_MM = fase5.LIMIAR_REGRESSAO_HD95_MM      # 1,0
LIMIAR_VOLUME_PP = fase5.LIMIAR_REGRESSAO_VOLUME_PCT  # 2,0

# Metricas publicadas. Fixadas aqui: escolher metrica depois do resultado e
# p-hacking, e "nao publicar so Dice" e exigencia explicita da Parte 3.
METRICAS = ("dice", "iou", "precision_pred", "recall_gt", "hd95_mm", "assd_mm",
            "volume_error_pct", "fp_ml", "fn_ml", "erro_absoluto_ml")

COLUNAS = ("split", "case_id", "instituicao", "gt_roi_name", "variante", *METRICAS,
           "volume_pred_ml", "volume_gt_ml", "spacing_mm", "erro")


def _ml(m: np.ndarray, spacing) -> float:
    return round(float(np.asarray(m).sum()) * float(np.prod(spacing)) / 1000.0, 4)


def medir_variante(pred: np.ndarray, gt: np.ndarray, spacing) -> dict[str, Any]:
    """Todas as metricas de uma variante contra o GT. Sem escolha, so medida."""
    m = compare_masks(pred, gt, spacing)
    rc = recall_containment(pred, gt)
    fp, fn = pred & ~gt, gt & ~pred
    fp_ml, fn_ml = _ml(fp, spacing), _ml(fn, spacing)
    return {
        "dice": m["dice"], "iou": m["iou"],
        "precision_pred": rc["precision_pred"], "recall_gt": rc["recall_gt"],
        "hd95_mm": m["hd95_mm"], "assd_mm": m["assd_mm"],
        "volume_error_pct": m["volume_error_pct"],
        "fp_ml": fp_ml, "fn_ml": fn_ml,
        # erro absoluto NAO cancela: e a discordancia real, ao contrario do liquido
        "erro_absoluto_ml": round(fp_ml + fn_ml, 4),
        "volume_pred_ml": _ml(pred, spacing), "volume_gt_ml": _ml(gt, spacing),
    }


def rodar_caso(caso: str, split: str, raiz: Path = RAIZ, saida: Path = SAIDA) -> list[dict]:
    """As duas linhas de um caso: vigente e candidato, contra o mesmo GT."""
    import nibabel as nib

    dir_caso = raiz / caso
    caminho_gt = dir_caso / "gt" / f"{rtst.PREFIXO_MASCARA}{GT_ROI}.nii.gz"
    caminho_heart = dir_caso / "pred_masks" / "heart.nii.gz"

    # o pericardium e produzido em diretorio PROPRIO; o baseline nao e tocado
    dir_peri = saida / "segmentacao" / caso
    caminho_peri = dir_peri / "masks" / f"{pericardio.CLASSE}.nii.gz"
    if not caminho_peri.exists():
        pericardio.segmentar(caso, raiz=raiz, saida=saida / "segmentacao", log=lambda *a: None)

    base = {"split": split, "case_id": caso,
            "instituicao": fase5.instituicao_de(caso), "gt_roi_name": GT_ROI}

    # geometria ANTES de qualquer medida; desalinhamento ABORTA, nao vira Dice ruim
    linhas = []
    for variante, caminho in ((VIGENTE, caminho_heart), (CANDIDATO, caminho_peri)):
        linha = {c: None for c in COLUNAS}
        linha.update(base, variante=variante, erro="")
        try:
            geometria.verificar_alinhamento(caminho, caminho_gt)
        except geometria.DesalinhamentoGeometrico as e:
            linha["erro"] = f"ABORTADA: {e}"
            linhas.append(linha)
            continue
        img = nib.load(str(caminho_gt))
        spacing = tuple(float(z) for z in img.header.get_zooms()[:3])
        gt = rtst.carregar_mascara(caminho_gt)
        pred = np.asarray(nib.load(str(caminho)).dataobj) > 0.5
        linha.update(medir_variante(pred, gt, spacing))
        linha["spacing_mm"] = [round(z, 4) for z in spacing]
        linhas.append(linha)
    return linhas


# ------------------------------------------------------------------ agregacao


def _pareado(linhas: list[dict], split: str, metrica: str) -> dict[str, Any]:
    """Diferenca PAREADA candidato - vigente, por caso.

    Pareada e nao "diferenca das medianas": a fase 5 pegou um caso em que a
    mediana do Dice SOBE enquanto a mediana das diferencas pareadas e NEGATIVA,
    com 18/30 casos piorando. Mediana de medianas engana.
    """
    por_caso: dict[str, dict[str, float]] = {}
    for l in linhas:
        if l["split"] != split or l["erro"] or not isinstance(l.get(metrica), (int, float)):
            continue
        por_caso.setdefault(l["case_id"], {})[l["variante"]] = float(l[metrica])
    deltas = [(c, v[CANDIDATO] - v[VIGENTE]) for c, v in sorted(por_caso.items())
              if VIGENTE in v and CANDIDATO in v]
    if not deltas:
        return {"n": 0, "mediana_delta": NM}
    vals = [d for _c, d in deltas]
    return {
        "n": len(vals),
        "mediana_delta": round(statistics.median(vals), 4),
        "media_delta": round(statistics.fmean(vals), 4),
        "min_delta": round(min(vals), 4), "max_delta": round(max(vals), 4),
        "n_positivos": sum(1 for v in vals if v > 0),
        "n_negativos": sum(1 for v in vals if v < 0),
        "mediana_vigente": round(statistics.median(
            [por_caso[c][VIGENTE] for c, _ in deltas]), 4),
        "mediana_candidato": round(statistics.median(
            [por_caso[c][CANDIDATO] for c, _ in deltas]), 4),
        "por_caso": {c: round(d, 4) for c, d in deltas},
    }


def veredito(linhas: list[dict]) -> dict[str, Any]:
    """Aplica os criterios de promocao DECLARADOS ANTES. Nao julga no olho."""
    out: dict[str, Any] = {"criterios_declarados": {
        "limiar_dice": LIMIAR_DICE, "limiar_regressao_dice": LIMIAR_REGRESSAO_DICE,
        "limiar_hd95_mm": LIMIAR_HD95_MM, "limiar_volume_pp": LIMIAR_VOLUME_PP,
        "origem": "fase5.py — inalterados desde antes de qualquer experimento",
    }}
    for split in ("validation", "test"):
        d = _pareado(linhas, split, "dice")
        h = _pareado(linhas, split, "hd95_mm")
        a = _pareado(linhas, split, "assd_mm")
        if d.get("n", 0) == 0:
            out[split] = {"veredito": f"{NM}: sem par completo"}
            continue
        # ganho consistente = mediana das diferencas pareadas acima do limiar E
        # maioria dos casos na mesma direcao
        ganho = d["mediana_delta"] >= LIMIAR_DICE
        consistente = d["n_positivos"] > d["n_negativos"]
        # regressao de distancia: HD95 ou ASSD PIORANDO (subindo) acima do limiar
        reg_hd95 = isinstance(h.get("mediana_delta"), float) and h["mediana_delta"] > LIMIAR_HD95_MM
        out[split] = {
            "n_casos": d["n"],
            "delta_dice_mediano": d["mediana_delta"],
            "casos_melhoraram": f"{d['n_positivos']}/{d['n']}",
            "ganho_acima_do_limiar": bool(ganho),
            "direcao_consistente": bool(consistente),
            "regressao_hd95": bool(reg_hd95),
            "delta_hd95_mediano": h.get("mediana_delta"),
            "delta_assd_mediano": a.get("mediana_delta"),
            "veredito": ("PROMOVE" if (ganho and consistente and not reg_hd95)
                         else "NAO PROMOVE"),
        }
    v, t = out.get("validation", {}), out.get("test", {})
    out["decisao_final"] = (
        "PROMOVER heart -> pericardium"
        if v.get("veredito") == "PROMOVE" and t.get("veredito") == "PROMOVE"
        else "MANTER heart — a hipotese nao sobreviveu aos DOIS conjuntos"
    )
    out["regra"] = ("promove so se PROMOVE em validation E em test. Um dos dois "
                    "falhando mantem o mapeamento vigente.")
    return out


def rodar(raiz: Path = RAIZ, saida: Path = SAIDA, log=print) -> dict:
    split = fase5.carregar_split(raiz)
    linhas: list[dict] = []
    for nome in ("validation", "test"):
        for i, caso in enumerate(split[nome], 1):
            log(f"[{nome} {i}/{len(split[nome])}] {caso}")
            linhas.extend(rodar_caso(caso, nome, raiz, saida))
    r = {"hipotese": (f"GT {GT_ROI} e melhor representado por {CANDIDATO} do que por "
                      f"{VIGENTE}; fixada na fase 6 no development"),
         "numero_de_selecao_fase6": {"dice_heart": 0.7709, "dice_pericardium": 0.9056,
                                     "n_casos": 6, "conjunto": "development"},
         "linhas": linhas,
         "pareado": {s: {m: _pareado(linhas, s, m) for m in METRICAS}
                     for s in ("validation", "test")},
         "veredito": veredito(linhas)}
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "holdout_heart.json").write_text(
        json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with (saida / "holdout_heart.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        for l in linhas:
            w.writerow({**l, "spacing_mm": "x".join(str(z) for z in (l["spacing_mm"] or []))})
    return r


def _autoteste() -> None:
    """Controles positivos: o veredito tem que REPROVAR quando deveria."""
    def linha(split, caso, variante, dice, hd95=1.0):
        return {"split": split, "case_id": caso, "variante": variante, "erro": "",
                "dice": dice, "hd95_mm": hd95, "assd_mm": 1.0}

    # (1) ganho grande e consistente nos dois -> PROMOVE
    ls = []
    for s in ("validation", "test"):
        for i in range(5):
            ls += [linha(s, f"c{i}", VIGENTE, 0.75), linha(s, f"c{i}", CANDIDATO, 0.90)]
    assert veredito(ls)["decisao_final"].startswith("PROMOVER"), veredito(ls)

    # (2) ganho ABAIXO do limiar -> NAO promove (controle do limiar)
    ls2 = []
    for s in ("validation", "test"):
        for i in range(5):
            ls2 += [linha(s, f"c{i}", VIGENTE, 0.750), linha(s, f"c{i}", CANDIDATO, 0.755)]
    assert veredito(ls2)["decisao_final"].startswith("MANTER"), veredito(ls2)

    # (3) ganho so na VALIDATION -> NAO promove (o test tem que confirmar)
    ls3 = []
    for i in range(5):
        ls3 += [linha("validation", f"c{i}", VIGENTE, 0.75),
                linha("validation", f"c{i}", CANDIDATO, 0.90),
                linha("test", f"c{i}", VIGENTE, 0.75),
                linha("test", f"c{i}", CANDIDATO, 0.75)]
    assert veredito(ls3)["decisao_final"].startswith("MANTER"), veredito(ls3)

    # (4) ganho de Dice COM regressao de HD95 acima do limiar -> NAO promove
    ls4 = []
    for s in ("validation", "test"):
        for i in range(5):
            ls4 += [linha(s, f"c{i}", VIGENTE, 0.75, hd95=5.0),
                    linha(s, f"c{i}", CANDIDATO, 0.90, hd95=12.0)]
    assert veredito(ls4)[("validation")]["regressao_hd95"], veredito(ls4)["validation"]
    assert veredito(ls4)["decisao_final"].startswith("MANTER"), veredito(ls4)

    # (5) a diferenca e PAREADA: mediana de medianas subindo com maioria piorando
    #     tem que dar delta NEGATIVO (a armadilha que a fase 5 pegou)
    ls5 = ([linha("validation", "a", VIGENTE, 0.10), linha("validation", "a", CANDIDATO, 0.90)]
           + [linha("validation", f"b{i}", VIGENTE, 0.80) for i in range(4)]
           + [linha("validation", f"b{i}", CANDIDATO, 0.78) for i in range(4)])
    p = _pareado(ls5, "validation", "dice")
    assert p["mediana_delta"] < 0 and p["n_negativos"] > p["n_positivos"], p

    # (6) erro_absoluto nao cancela
    gt = np.zeros((10, 10, 10), bool); gt[2:8, 2:8, 2:8] = True
    pred = np.zeros_like(gt); pred[3:9, 2:8, 2:8] = True  # desloca 1: cria FP e FN
    m = medir_variante(pred, gt, (1.0, 1.0, 1.0))
    assert abs(m["volume_error_pct"]) < 1e-9, m["volume_error_pct"]  # liquido cancela
    assert m["erro_absoluto_ml"] > 0, m  # absoluto nao
    print("holdout_heart.py: autoteste OK (6 controles, 4 deles de REPROVACAO)")


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fase 7 — holdout do mapeamento cardiaco")
    ap.add_argument("--raiz", type=Path, default=RAIZ)
    ap.add_argument("--saida", type=Path, default=SAIDA)
    a = ap.parse_args(argv)
    r = rodar(a.raiz, a.saida)
    print(json.dumps(r["veredito"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        _autoteste()
    else:
        raise SystemExit(_main())
