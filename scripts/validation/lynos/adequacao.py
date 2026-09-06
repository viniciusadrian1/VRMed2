"""Fase 18.5 — adequacao estatistica de n=15, SEM gastar o candidato a TEST.

A DECISAO METODOLOGICA QUE ESTE MODULO REGISTRA
A Fase 18.5 pede intervalo de confianca do Dice sobre o LyNoS. A forma obvia seria
rodar o baseline nos 15 casos e medir. Isso NAO foi feito, de proposito:

  medir agora GASTA o conjunto. Se o LyNoS vier a ser o TEST, olhar o resultado antes
  de congelar o protocolo e exatamente o vicio que o projeto inteiro combate — o
  numero passaria a existir na cabeca de quem desenha o treino, e nenhuma trava
  posterior desfaz isso. Um TEST olhado nao volta a ser TEST.

Alem disso a regra 20 desta fase proibe tratar o LyNoS como TEST independente
enquanto a independencia do baseline estiver indeterminada — e ela esta.

O QUE DA PARA RESPONDER SEM MEDIR
"Quao forte seria um resultado em n=15?" e uma pergunta de DESENHO, nao de medicao.
Ela se responde com a dispersao POR CASO que o projeto ja tem, do lado do LCTSC:
os 30 casos do `development` sob o A_BASELINE_V1. Reamostrar 15 de uma distribuicao
com aquela dispersao diz a largura do IC — sem tocar no LyNoS.

FONTE DA DISPERSAO (declarada, nao inventada)
Dice do esofago por caso, `development` (n=30), A_BASELINE_V1, lido de
`.clinica-dados/tier2/lctsc/<caso>/tier2_caso.json`. E a dispersao do LCTSC, NAO uma
previsao do LyNoS: TC com contraste diagnostica dispersa diferente de TC de
planejamento, e quase certamente MAIS. O numero abaixo e portanto um PISO otimista
para a largura do IC.

  python -m scripts.validation.lynos.adequacao --autoteste
  python -m scripts.validation.lynos.adequacao
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.lynos.auditoria import SAIDA  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SPLIT = RAIZ / ".clinica-dados" / "tier2" / "lctsc" / "fase5" / "split.json"
N_BOOT = 20000
SEMENTE = 20260906


def dice_development() -> list:
    """Dice do esofago por caso no `development`. Le o split congelado, nao adivinha."""
    dev = set(json.loads(SPLIT.read_text())["split"]["development"])
    out = []
    for p in sorted(glob.glob(str(RAIZ / ".clinica-dados" / "tier2" / "lctsc" / "*" / "tier2_caso.json"))):
        caso = Path(p).parent.name
        if caso not in dev:
            continue
        d = json.loads(Path(p).read_text())
        try:
            v = d["manifesto"]["geometria"]["pares"]["Esophagus"]["flip"]["dice"]
        except (KeyError, TypeError):
            continue
        if isinstance(v, (int, float)):
            out.append({"caso": caso, "dice": float(v)})
    return out


def bootstrap_ic(valores, n, n_boot=N_BOOT, semente=SEMENTE):
    """IC percentil 95 da MEDIA de uma amostra de tamanho n tirada desta dispersao.

    Reamostragem COM reposicao a partir dos valores observados. Nao supoe normalidade
    e nao supoe que o Dice seja simetrico — ele nao e (limitado em 1 acima).
    """
    rng = np.random.default_rng(semente)
    v = np.asarray(valores, dtype=float)
    medias = np.array([rng.choice(v, size=n, replace=True).mean() for _ in range(n_boot)])
    lo, hi = np.percentile(medias, [2.5, 97.5])
    return {
        "n": int(n),
        "media_pontual": round(float(v.mean()), 4),
        "ic95_baixo": round(float(lo), 4),
        "ic95_alto": round(float(hi), 4),
        "largura_ic95": round(float(hi - lo), 4),
        "erro_padrao": round(float(medias.std(ddof=1)), 4),
        "n_boot": n_boot,
    }


def sensibilidade_outlier(valores, n):
    """Quanto UM caso mexe na media quando n=15? Em amostra pequena, muito.

    Mede o deslocamento da media ao trocar o caso mediano pelo pior observado.
    """
    v = sorted(float(x) for x in valores)
    pior, mediano = v[0], v[len(v) // 2]
    delta = (pior - mediano) / n
    return {
        "pior_caso_observado": round(pior, 4),
        "caso_mediano": round(mediano, 4),
        "deslocamento_da_media_por_um_caso": round(delta, 4),
        "leitura": ("com n=%d, trocar UM caso mediano pelo pior observado move a media "
                    "em %.4f de Dice" % (n, abs(delta))),
    }


def poder_comparacao(valores, n, deltas=(0.02, 0.05, 0.10), n_boot=4000, semente=SEMENTE):
    """Que diferenca de Dice n=15 conseguiria distinguir de zero?

    Simulacao de duas amostras independentes de tamanho n da MESMA dispersao, uma
    deslocada de delta. Fracao de vezes em que o IC95 da diferenca exclui zero.
    """
    rng = np.random.default_rng(semente)
    v = np.asarray(valores, dtype=float)
    out = {}
    for d in deltas:
        acertos = 0
        for _ in range(n_boot):
            a = rng.choice(v, size=n, replace=True)
            b = np.clip(rng.choice(v, size=n, replace=True) + d, 0.0, 1.0)
            dif = b.mean() - a.mean()
            se = np.sqrt(a.var(ddof=1) / n + b.var(ddof=1) / n)
            if se > 0 and abs(dif) - 1.96 * se > 0:
                acertos += 1
        out["delta_%.2f" % d] = round(acertos / n_boot, 3)
    return out


def autoteste() -> int:
    falhas = []
    rng = np.random.default_rng(7)

    # 1. IC de amostra maior tem de ser MAIS ESTREITO. Se nao for, o bootstrap mente.
    v = rng.normal(0.78, 0.10, 200).clip(0, 1).tolist()
    a15 = bootstrap_ic(v, 15, n_boot=3000)
    a60 = bootstrap_ic(v, 60, n_boot=3000)
    if not a60["largura_ic95"] < a15["largura_ic95"]:
        falhas.append("IC de n=60 nao ficou mais estreito que o de n=15")

    # razao esperada ~ sqrt(60/15) = 2. Tolerancia larga: e Monte Carlo.
    razao = a15["largura_ic95"] / a60["largura_ic95"]
    if not 1.5 < razao < 2.6:
        falhas.append("razao de larguras fora do esperado por sqrt(n): %.2f" % razao)

    # 2. dispersao ZERO tem de dar IC de largura ZERO (controle degenerado)
    z = bootstrap_ic([0.5] * 30, 15, n_boot=500)
    if z["largura_ic95"] != 0.0:
        falhas.append("dispersao nula deu IC de largura " + str(z["largura_ic95"]))

    # 3. o poder tem de CRESCER com o tamanho do efeito
    p = poder_comparacao(v, 15, deltas=(0.01, 0.20), n_boot=800)
    if not p["delta_0.20"] > p["delta_0.01"]:
        falhas.append("poder nao cresceu com o efeito: " + str(p))
    # e um efeito de 0,01 em n=15 tem de ser praticamente indetectavel
    if p["delta_0.01"] > 0.25:
        falhas.append("poder alto demais para efeito de 0,01 em n=15: " + str(p["delta_0.01"]))

    # 4. sensibilidade a outlier tem de encolher quando n cresce
    s15 = sensibilidade_outlier(v, 15)
    s60 = sensibilidade_outlier(v, 60)
    if not abs(s60["deslocamento_da_media_por_um_caso"]) < abs(s15["deslocamento_da_media_por_um_caso"]):
        falhas.append("sensibilidade a outlier nao caiu com n maior")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste adequacao: %d verificacoes, %d falhas" % (6, len(falhas)))
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

    casos = dice_development()
    v = [c["dice"] for c in casos]
    if len(v) < 10:
        print("dispersao insuficiente: %d casos" % len(v))
        return 1
    arr = np.array(v)
    print("DISPERSAO DE REFERENCIA — Dice do esofago, development do LCTSC, A_BASELINE_V1")
    print("  n=%d  media %.4f  mediana %.4f  dp %.4f  min %.4f  max %.4f"
          % (len(v), arr.mean(), np.median(arr), arr.std(ddof=1), arr.min(), arr.max()))
    print("  P25 %.4f  P75 %.4f  IQR %.4f"
          % (np.percentile(arr, 25), np.percentile(arr, 75),
             np.percentile(arr, 75) - np.percentile(arr, 25)))
    print()

    ics = {str(n): bootstrap_ic(v, n) for n in (15, 30, 60, 100)}
    print("LARGURA DO IC95 DA MEDIA POR TAMANHO DE AMOSTRA (bootstrap, %d reamostras)" % N_BOOT)
    for n, r in ics.items():
        print("  n=%-4s IC95 [%.4f ; %.4f]  largura %.4f  EP %.4f"
              % (n, r["ic95_baixo"], r["ic95_alto"], r["largura_ic95"], r["erro_padrao"]))
    print()

    sens = sensibilidade_outlier(v, 15)
    print("SENSIBILIDADE A OUTLIER EM n=15")
    print("  " + sens["leitura"])
    print()

    poder = poder_comparacao(v, 15)
    print("PODER DE n=15 PARA DISTINGUIR UMA DIFERENCA DE DICE DE ZERO")
    for k, p in poder.items():
        print("  %s -> poder %.3f" % (k, p))
    print()

    saida = {
        "fase": 18.5,
        "decisao": "NAO MEDIDO NO LyNoS — de proposito",
        "motivo": (
            "medir agora gastaria o candidato a TEST: um conjunto olhado antes de o "
            "protocolo ser congelado deixa de poder servir de TEST. Alem disso a regra "
            "20 desta fase proibe tratar o LyNoS como TEST enquanto a independencia do "
            "baseline estiver indeterminada, e ela esta."
        ),
        "dispersao_de_referencia": {
            "fonte": "Dice do esofago por caso, split development (n=30), A_BASELINE_V1, LCTSC",
            "ressalva": (
                "e a dispersao do LCTSC (TC de planejamento, sem contraste). O LyNoS e "
                "TC diagnostica COM contraste; a dispersao dele quase certamente e MAIOR. "
                "Estes ICs sao portanto um PISO otimista de largura."
            ),
            "n": len(v),
            "media": round(float(arr.mean()), 4),
            "mediana": round(float(np.median(arr)), 4),
            "desvio_padrao": round(float(arr.std(ddof=1)), 4),
            "min": round(float(arr.min()), 4),
            "max": round(float(arr.max()), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
            "por_caso": casos,
        },
        "ic_por_n": ics,
        "sensibilidade_outlier_n15": sens,
        "poder_n15": poder,
    }
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "lynos_adequacao.json").write_text(json.dumps(saida, indent=1))
    print("escrito:", SAIDA / "lynos_adequacao.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
