"""Fase 27 — avaliacao diagnostica do baseline contra o GT congelado.

AS OITO METRICAS SAO AS CONGELADAS, E O CODIGO E O QUE JA EXISTIA

    dice, iou                       -> segmentation_metrics.compare_masks
    hd95, assd                      -> segmentation_metrics.surface_distances (mm)
    precision, recall               -> benchmark_tier2.recall_containment
    erro_volume_absoluto (mL)       -> aqui, por contagem de voxels x volume do voxel
    erro_volume_percentual (%)      -> segmentation_metrics.volume_error_pct

Nenhuma metrica nova entra no criterio. `nsd` e `hd` saem do mesmo calculo e sao
publicados como EXPLORATORIOS, fora do criterio, exatamente como a ontologia permite.

CONTRA O QUE SE COMPARA

Contra o GT do MANIFESTO CONGELADO, lido do caminho que o manifesto declara, e nao
contra a copia relabelada que foi para a arvore do nnU-Net. A copia foi provada
identica em conjunto de foreground na Fase 26, mas comparar contra o original remove
a copia da cadeia de evidencia por completo.

O QUE ESTE MODULO NAO FAZ

Nao treina, nao ajusta limiar, nao remove outlier, nao escolhe caso, nao toca em TEST
(que nao existe), e nao altera predicao nenhuma. Ele le duas mascaras e devolve numeros.

  python -m scripts.validation.fase27.avaliar --autoteste
  python -m scripts.validation.fase27.avaliar --predicoes <dir> --rotulo <nome>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402
from scripts.validation import segmentation_metrics as sm  # noqa: E402
from scripts.validation.tier2.benchmark_tier2 import recall_containment  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SAIDA = RAIZ / "docs" / "overnight" / "phase27"

# Os nomes congelados, e a traducao para as chaves que os modulos existentes usam.
# A traducao mora aqui, num lugar so, para nao haver duas grafias circulando.
CONGELADAS = onto.METRICAS_CONGELADAS
EXPLORATORIAS = ("hd_mm", "nsd_1mm", "nsd_2mm", "nsd_1vox", "nsd_2vox")


def _carregar(caminho: Path):
    import numpy as np
    import nibabel as nib
    im = nib.load(str(caminho))
    return np.asanyarray(im.dataobj), im.affine


def _spacing(affine) -> tuple:
    import numpy as np
    return tuple(float(x) for x in np.sqrt((np.asarray(affine)[:3, :3] ** 2).sum(axis=0)))


def metricas_do_caso(pred, gt, spacing) -> dict:
    """As oito congeladas + as exploratorias, num dicionario so, com nomes congelados."""
    import numpy as np
    base = sm.compare_masks(pred, gt, spacing)
    rc = recall_containment(pred, gt)
    voxel_mm3 = float(np.prod(np.asarray(spacing, dtype=float)))
    vol_pred = float((np.asarray(pred) > 0.5).sum()) * voxel_mm3 / 1000.0   # mL
    vol_gt = float((np.asarray(gt) > 0.5).sum()) * voxel_mm3 / 1000.0       # mL
    return {
        # ---- as oito congeladas
        "dice": base["dice"],
        "iou": base["iou"],
        "precision": rc["precision_pred"],
        "recall": rc["recall_gt"],
        "hd95": base["hd95_mm"],
        "assd": base["assd_mm"],
        "erro_volume_absoluto": abs(vol_pred - vol_gt),
        "erro_volume_percentual": base["volume_error_pct"],
        # ---- contexto, nao criterio
        "volume_gt_ml": vol_gt,
        "volume_pred_ml": vol_pred,
        "voxel_mm3": voxel_mm3,
        "spacing": list(spacing),
        "predicao_vazia": bool(vol_pred == 0.0),
        # ---- exploratorias, declaradas fora do criterio
        "exploratorias": {k: base[k] for k in EXPLORATORIAS if k in base},
    }


def resumo(valores) -> dict:
    """media, mediana, desvio, min, max, IQR. Sem n, nenhum destes numeros vale nada."""
    import numpy as np
    v = np.asarray([x for x in valores if isinstance(x, (int, float))
                    and not (isinstance(x, float) and np.isnan(x))], dtype=float)
    if v.size == 0:
        return {"n": 0}
    q1, q3 = (float(np.percentile(v, 25)), float(np.percentile(v, 75))) if v.size > 1 else (float(v[0]), float(v[0]))
    return {
        "n": int(v.size),
        "media": float(v.mean()),
        "mediana": float(np.median(v)),
        # desvio AMOSTRAL (ddof=1): com n pequeno, o populacional subestima
        "desvio": float(v.std(ddof=1)) if v.size > 1 else None,
        "min": float(v.min()),
        "max": float(v.max()),
        "q1": q1, "q3": q3, "iqr": q3 - q1,
    }


def avaliar(predicoes: Path, split: str, contexto: str) -> dict:
    """Avalia todas as predicoes encontradas contra o GT do manifesto congelado."""
    ent = man.carregar(MANIFESTO)
    alvo = [e for e in man.carregar_particao(ent, split, contexto) if e["split"] == split]
    alvo.sort(key=lambda e: e["case_id"])

    casos, ausentes = [], []
    for e in alvo:
        p = Path(predicoes) / ("%s.nii.gz" % e["case_id"])
        if not p.exists():
            ausentes.append(e["case_id"])
            continue
        gt, aff_gt = _carregar(RAIZ / e["mask_path"])
        pr, _ = _carregar(p)
        if pr.shape != gt.shape:
            ausentes.append("%s (forma %s != GT %s)" % (e["case_id"], pr.shape, gt.shape))
            continue
        m = metricas_do_caso(pr, gt, _spacing(aff_gt))
        casos.append({"case_id": e["case_id"], "split": e["split"],
                      "mask_path": e["mask_path"], **m})

    agregado = {k: resumo([c[k] for c in casos]) for k in CONGELADAS}
    return {
        "split_avaliado": split,
        "contexto_de_leitura": contexto,
        "n_esperado": len(alvo),
        "n_avaliado": len(casos),
        "ausentes": ausentes,
        "metricas_congeladas": list(CONGELADAS),
        "agregado": agregado,
        "casos": casos,
        "aviso_n": ("n = %d. Com n desta ordem, media e desvio sao descritivos e nao "
                    "sustentam inferencia. Nenhum numero aqui e desempenho externo."
                    % len(casos)),
    }


def autoteste() -> int:
    import numpy as np
    falhas = []

    sp = (1.0, 1.0, 1.0)
    a = np.zeros((20, 20, 20), np.uint8)
    a[5:15, 5:15, 5:15] = 1

    # 1. identidade: predicao == GT tem de dar dice 1 e erro de volume 0
    m = metricas_do_caso(a, a, sp)
    if abs(m["dice"] - 1.0) > 1e-9 or abs(m["iou"] - 1.0) > 1e-9:
        falhas.append("dice/iou != 1 para mascaras identicas: %s" % m["dice"])
    if m["erro_volume_absoluto"] != 0.0 or abs(m["erro_volume_percentual"]) > 1e-9:
        falhas.append("erro de volume != 0 para mascaras identicas")
    if m["hd95"] != 0.0 or m["assd"] != 0.0:
        falhas.append("distancias != 0 para mascaras identicas")

    # 2. as oito congeladas estao TODAS presentes, com o nome congelado
    faltando = [k for k in CONGELADAS if k not in m]
    if faltando:
        falhas.append("metrica congelada ausente da saida: %s" % faltando)

    # 3. e nenhuma metrica exploratoria vazou para o nivel do criterio
    for k in EXPLORATORIAS:
        if k in m:
            falhas.append("metrica exploratoria %r no nivel do criterio" % k)

    # 4. assimetria: precision e recall NAO sao a mesma coisa.
    #    Predicao maior que o GT -> recall alto, precision baixa.
    grande = np.zeros_like(a)
    grande[3:17, 3:17, 3:17] = 1
    mg = metricas_do_caso(grande, a, sp)
    if not (mg["recall"] > 0.99 and mg["precision"] < 0.5):
        falhas.append("predicao inflada nao produziu recall alto e precision baixa: %s"
                      % {k: mg[k] for k in ("precision", "recall")})
    if mg["erro_volume_percentual"] <= 0:
        falhas.append("predicao inflada deu erro percentual nao positivo")

    # 5. e o espelho: predicao menor -> precision alta, recall baixo
    pequena = np.zeros_like(a)
    pequena[7:12, 7:12, 7:12] = 1
    mp = metricas_do_caso(pequena, a, sp)
    if not (mp["precision"] > 0.99 and mp["recall"] < 0.5):
        falhas.append("predicao encolhida nao produziu precision alta e recall baixo")
    if mp["erro_volume_percentual"] >= 0:
        falhas.append("predicao encolhida deu erro percentual nao negativo")

    # 6. predicao VAZIA nao pode virar numero plausivel
    vazia = np.zeros_like(a)
    mv = metricas_do_caso(vazia, a, sp)
    if mv["dice"] != 0.0:
        falhas.append("dice de predicao vazia != 0")
    if not mv["predicao_vazia"]:
        falhas.append("predicao vazia nao foi sinalizada")
    if isinstance(mv["precision"], float):
        falhas.append("precision de predicao vazia virou float — deveria ser 'invalido'")

    # 7. distancia em MILIMETROS, nao em indice de voxel: dobrar o spacing dobra hd95
    m1 = metricas_do_caso(pequena, a, (1.0, 1.0, 1.0))
    m2 = metricas_do_caso(pequena, a, (2.0, 2.0, 2.0))
    if not (abs(m2["hd95"] - 2 * m1["hd95"]) < 1e-6):
        falhas.append("hd95 nao escalou com o spacing: %s vs %s" % (m1["hd95"], m2["hd95"]))

    # 8. volume absoluto em mL, e sensivel ao spacing
    if not (abs(m2["erro_volume_absoluto"] - 8 * m1["erro_volume_absoluto"]) < 1e-6):
        falhas.append("erro_volume_absoluto nao escalou com o volume do voxel")

    # 9. resumo: n, mediana e IQR corretos num caso conhecido
    r = resumo([1.0, 2.0, 3.0, 4.0])
    if r["n"] != 4 or abs(r["mediana"] - 2.5) > 1e-9 or abs(r["iqr"] - 1.5) > 1e-9:
        falhas.append("resumo incorreto: %s" % r)
    # desvio AMOSTRAL, nao populacional
    if abs(r["desvio"] - 1.2909944487358056) > 1e-9:
        falhas.append("desvio nao e amostral (ddof=1): %s" % r["desvio"])

    # 10. resumo ignora NaN em vez de propagar
    rn = resumo([1.0, float("nan"), 3.0])
    if rn["n"] != 2 or abs(rn["media"] - 2.0) > 1e-9:
        falhas.append("resumo nao lidou com NaN: %s" % rn)

    # 11. resumo de lista vazia nao inventa numero
    if resumo([])["n"] != 0 or "media" in resumo([]):
        falhas.append("resumo de lista vazia produziu estatistica")

    # 12. a lista congelada e a da ontologia, nao uma copia local que pode divergir
    if tuple(CONGELADAS) != tuple(onto.METRICAS_CONGELADAS):
        falhas.append("a lista de metricas divergiu da ontologia congelada")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste avaliar: %d verificacoes, %d falhas" % (12, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--predicoes")
    ap.add_argument("--split", default="validation")
    ap.add_argument("--contexto", default="validacao")
    ap.add_argument("--rotulo", default="validation")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    if not a.predicoes:
        print("faltou --predicoes")
        return 1
    print()

    r = avaliar(Path(a.predicoes), a.split, a.contexto)
    print("AVALIACAO  split=%s  contexto=%s  |  %d/%d casos"
          % (r["split_avaliado"], r["contexto_de_leitura"], r["n_avaliado"], r["n_esperado"]))
    if r["ausentes"]:
        print("   AUSENTES:", r["ausentes"])
    print()
    print("%-24s %6s %6s %6s %6s %8s %7s %9s %9s"
          % ("case_id", "dice", "iou", "prec", "rec", "hd95mm", "assdmm", "dVol_mL", "dVol_%"))
    for c in r["casos"]:
        pr = c["precision"] if isinstance(c["precision"], float) else float("nan")
        rc = c["recall"] if isinstance(c["recall"], float) else float("nan")
        print("%-24s %6.4f %6.4f %6.4f %6.4f %8.2f %7.3f %9.2f %9.2f"
              % (c["case_id"], c["dice"], c["iou"], pr, rc,
                 c["hd95"], c["assd"], c["erro_volume_absoluto"], c["erro_volume_percentual"]))
    print()
    for k in CONGELADAS:
        s = r["agregado"][k]
        if s["n"] == 0:
            print("   %-24s n=0" % k)
            continue
        print("   %-24s n=%d media %8.4f | mediana %8.4f | dp %s | min %8.4f | max %8.4f | IQR %.4f"
              % (k, s["n"], s["media"], s["mediana"],
                 ("%7.4f" % s["desvio"]) if s["desvio"] is not None else "    n/a",
                 s["min"], s["max"], s["iqr"]))
    print()
    print(r["aviso_n"])

    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / ("avaliacao_%s.json" % a.rotulo)
    destino.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\nescrito:", destino)
    return 0


if __name__ == "__main__":
    sys.exit(main())
