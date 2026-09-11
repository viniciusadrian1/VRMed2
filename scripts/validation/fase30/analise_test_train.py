"""Fase 30 — quanto um TEST de tamanho n informaria, e o que ele NAO resolve.

A PERGUNTA QUE ESTE MODULO RESPONDE

Nao e "conseguimos criar um TEST?" — e "um TEST mudaria a forca das conclusoes?".
Sao coisas diferentes, e a segunda tem resposta quantitativa.

O QUE E CALCULADO, E DE ONDE VEM CADA NUMERO

  OBSERVADO   os Dice por caso, lidos dos artefatos da Fase 26B/27B. Nada digitado.
  CALCULADO   meia-largura do IC de 95 % da media: t(0,975; n-1) * sigma / sqrt(n).
              Formula exata, sem simulacao.
  CENARIO     sigma e DESCONHECIDO para um TEST futuro. Em vez de escolher um valor,
              o modulo roda os TRES sigmas observados no projeto, que diferem por um
              fator de 7. Apresentar um numero unico seria esconder a incerteza que
              mais importa.
  SIMULACAO   reamostragem com reposicao a partir dos valores observados, para o
              efeito de outlier. Rotulada como simulacao, e limitada pelo n minusculo
              da amostra de origem.

A ARMADILHA QUE O MODULO EVITA

Os tres sigmas vem de ESTIMADORES DIFERENTES — o de 0,0192 e de um ensemble de 5
redes sobre 6 casos; o de 0,1369 e de uma rede por caso sobre 10. Junta-los numa
amostra so seria o mesmo erro que a verificacao da Fase 27B pegou. Aqui eles nunca
sao misturados: cada cenario roda separado e diz de onde veio.

  python -m scripts.validation.fase30.analise_test_train --autoteste
  python -m scripts.validation.fase30.analise_test_train --escrever
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase30"
OBSERVADOS = SAIDA / "dados_observados.json"

NS = (3, 5, 6, 8, 10, 15, 20, 25, 30)

# Os tres sigmas OBSERVADOS no projeto. Nenhum e "o certo" — sao tres regimes.
CENARIOS_SIGMA = (
    ("otimista", 0.0192, "reservado n=6, ensemble de 5 folds, mix estreito de casos"),
    ("intermediario", 0.0558, "out-of-fold n=8, uma rede por caso, sem os 2 colapsos"),
    ("pessimista", 0.1369, "out-of-fold n=10, uma rede por caso, COM os 2 colapsos"),
)

# Variacao entre as 5 redes do cross-validation. E o numero que decide a fase:
# se ele for maior que a meia-largura do IC, o gargalo nao e medir melhor.
DP_ENTRE_FOLDS = 0.0898
DICE_POR_FOLD = (0.7613, 0.6009, 0.7672, 0.7706, 0.6042)

# Fracao de "colapsos" observada no pool: 2 casos abaixo de 0,5 em 16 avaliados.
COLAPSOS, TOTAL_AVALIADO = 2, 16


def t_975(gl: int) -> float:
    """t de Student bicaudal a 95 %. Tabela ate 30 gl; acima disso, o limite normal.

    Tabela em vez de scipy: o valor precisa ser auditavel a olho, e a dependencia
    externa nao acrescenta nada para uma lista fixa de graus de liberdade.
    """
    tab = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
           8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
           15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
           21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056,
           27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}
    if gl < 1:
        return float("nan")
    return tab.get(gl, 1.960)


def meia_largura(n: int, sigma: float) -> float:
    """Meia-largura do IC 95 % da media. CALCULADO, formula exata."""
    if n < 2:
        return float("nan")
    return t_975(n - 1) * sigma / math.sqrt(n)


def efeito_de_um_caso(n: int, valor_do_caso: float, media_atual: float) -> float:
    """Quanto UM caso desloca a media de um TEST de tamanho n. Aritmetica exata."""
    return (valor_do_caso - media_atual) / n


def prob_ao_menos_um_colapso(n: int, p: float = COLAPSOS / TOTAL_AVALIADO) -> float:
    """Binomial: chance de um TEST de n conter ao menos um caso de colapso.

    PREMISSA EXPLICITA: p vem da frequencia observada (2 em 16) e e ela mesma
    incertissima com esse n. O numero serve para ordem de grandeza, nao para decisao
    fina.
    """
    return 1.0 - (1.0 - p) ** n


def simular_media(valores, n: int, repeticoes: int = 20000, semente: int = 20260910) -> dict:
    """SIMULACAO: reamostra com reposicao dos valores observados, n por vez.

    Limitacao declarada: a distribuicao de origem tem 6 ou 10 pontos. A simulacao
    propaga a incerteza da amostragem, nao a da propria distribuicao.
    """
    rnd = random.Random(semente)
    medias = [st.mean(rnd.choices(valores, k=n)) for _ in range(repeticoes)]
    medias.sort()
    lo = medias[int(0.025 * repeticoes)]
    hi = medias[int(0.975 * repeticoes)]
    return {"n": n, "media_das_medias": st.mean(medias), "p2_5": lo, "p97_5": hi,
            "largura": hi - lo, "repeticoes": repeticoes, "origem_n": len(valores)}


def tabela_tamanhos(media_ref: float = 0.7630) -> list:
    """A tabela central da 30B: por n, o que se ganha e o que continua frouxo."""
    linhas = []
    for n in NS:
        linha = {"n": n, "prob_ao_menos_um_colapso": prob_ao_menos_um_colapso(n),
                 "desloc_por_1_colapso": efeito_de_um_caso(n, 0.45, media_ref),
                 "desloc_por_2_colapsos": 2 * efeito_de_um_caso(n, 0.45, media_ref),
                 "desloc_por_1_excelente": efeito_de_um_caso(n, 0.87, media_ref),
                 "ic": {}}
        for nome, sigma, _ in CENARIOS_SIGMA:
            h = meia_largura(n, sigma)
            linha["ic"][nome] = {"sigma": sigma, "meia_largura": h, "largura_total": 2 * h,
                                 "menor_que_dp_entre_folds": h < DP_ENTRE_FOLDS}
        linhas.append(linha)
    return linhas


def comparar_train_vs_test() -> dict:
    """30C — o argumento quantitativo da fase.

    Um TEST reduz a incerteza sobre A MEDIDA. Ele nao reduz a variacao do proprio
    modelo entre folds, que com TRAIN=10 e de 0,0898. Medir com precisao de 0,03 um
    objeto que varia 0,09 e reportar um numero preciso sobre coisa imprecisa.
    """
    fora = {}
    for nome, sigma, origem in CENARIOS_SIGMA:
        fora[nome] = {"origem": origem, "sigma": sigma, "por_n": {}}
        for n in NS:
            h = meia_largura(n, sigma)
            fora[nome]["por_n"][n] = {
                "meia_largura_ic": h,
                "razao_ic_sobre_dp_entre_folds": h / DP_ENTRE_FOLDS,
                "medicao_mais_fina_que_o_modelo": h < DP_ENTRE_FOLDS,
            }
    return {
        "dp_entre_folds": DP_ENTRE_FOLDS,
        "dice_por_fold": list(DICE_POR_FOLD),
        "amplitude_entre_folds": max(DICE_POR_FOLD) - min(DICE_POR_FOLD),
        "cenarios": fora,
        "leitura": ("A variacao ENTRE as 5 redes treinadas com TRAIN=10 e 0,0898 de desvio "
                    "(amplitude 0,170). Assim que a meia-largura do IC do TEST fica abaixo "
                    "disso, aumentar o TEST passa a medir com mais precisao um objeto que "
                    "continua variando mais do que a propria medida."),
    }


def autoteste() -> int:
    falhas = []

    # 1. o IC encolhe com n e cresce com sigma — propriedades basicas
    if not (meia_largura(30, 0.05) < meia_largura(10, 0.05) < meia_largura(5, 0.05)):
        falhas.append("o IC nao encolhe monotonicamente com n")
    if not (meia_largura(10, 0.02) < meia_largura(10, 0.14)):
        falhas.append("o IC nao cresce com sigma")

    # 2. valor conhecido, conferivel a mao: n=6, sigma=0,0192 -> t(5)=2,571
    esperado = 2.571 * 0.0192 / math.sqrt(6)
    if abs(meia_largura(6, 0.0192) - esperado) > 1e-9:
        falhas.append("meia_largura divergiu da formula: %s" % meia_largura(6, 0.0192))
    # e bate com o IC que o proprio projeto ja reportou para n=6 (ordem de 0,02)
    if not (0.015 < meia_largura(6, 0.0192) < 0.025):
        falhas.append("IC de n=6 fora da ordem esperada")

    # 3. n<2 nao produz numero plausivel
    if not math.isnan(meia_largura(1, 0.05)):
        falhas.append("n=1 devolveu IC em vez de nan")

    # 4. o efeito de um caso encolhe com 1/n, exatamente
    a = efeito_de_um_caso(5, 0.45, 0.763)
    b = efeito_de_um_caso(10, 0.45, 0.763)
    if abs(a - 2 * b) > 1e-9:
        falhas.append("o deslocamento nao escala com 1/n")
    if a >= 0:
        falhas.append("um caso ruim deveria puxar a media para baixo")
    if efeito_de_um_caso(10, 0.87, 0.763) <= 0:
        falhas.append("um caso excelente deveria puxar a media para cima")

    # 5. a probabilidade de colapso cresce com n e fica em (0,1)
    ps = [prob_ao_menos_um_colapso(n) for n in (3, 10, 30)]
    if not (0 < ps[0] < ps[1] < ps[2] < 1):
        falhas.append("probabilidade de colapso mal comportada: %s" % ps)
    # valor conferivel: n=5, p=0,125 -> 1-0,875^5
    if abs(prob_ao_menos_um_colapso(5) - (1 - 0.875 ** 5)) > 1e-12:
        falhas.append("binomial divergiu da formula")

    # 6. a simulacao e DETERMINISTICA com a mesma semente
    v = [0.74, 0.76, 0.78, 0.80]
    if simular_media(v, 5)["p2_5"] != simular_media(v, 5)["p2_5"]:
        falhas.append("a simulacao nao e reproduzivel com a mesma semente")
    # e a largura simulada encolhe com n
    if not (simular_media(v, 30)["largura"] < simular_media(v, 5)["largura"]):
        falhas.append("a largura simulada nao encolhe com n")

    # 7. CONTROLE POSITIVO da comparacao train x test: com sigma pequeno e n grande,
    #    a medicao DEVE ficar mais fina que a variacao entre folds; com sigma grande
    #    e n pequeno, NAO deve. Sem os dois lados o comparador nao prova nada.
    c = comparar_train_vs_test()
    if not c["cenarios"]["otimista"]["por_n"][30]["medicao_mais_fina_que_o_modelo"]:
        falhas.append("cenario otimista com n=30 deveria medir mais fino que o modelo")
    if c["cenarios"]["pessimista"]["por_n"][3]["medicao_mais_fina_que_o_modelo"]:
        falhas.append("cenario pessimista com n=3 nao deveria medir mais fino que o modelo")

    # 8. os tres sigmas vem de estimadores diferentes e NAO podem ter sido fundidos
    if len({s for _, s, _ in CENARIOS_SIGMA}) != 3:
        falhas.append("os cenarios de sigma colapsaram num so")
    for _, _, origem in CENARIOS_SIGMA:
        if not origem:
            falhas.append("cenario de sigma sem origem declarada")

    # 9. a tabela cobre todos os n e todos os cenarios
    t = tabela_tamanhos()
    if [l["n"] for l in t] != list(NS):
        falhas.append("a tabela nao cobre os n declarados")
    if any(len(l["ic"]) != 3 for l in t):
        falhas.append("alguma linha da tabela nao tem os tres cenarios")

    # 10. o dp entre folds e o observado, nao um numero solto
    if abs(st.stdev(DICE_POR_FOLD) - DP_ENTRE_FOLDS) > 5e-4:
        falhas.append("DP_ENTRE_FOLDS nao bate com os Dice por fold: %.4f"
                      % st.stdev(DICE_POR_FOLD))

    for f in falhas:
        print("FALHA:", f)
    print("autoteste analise_test_train: %d verificacoes, %d falhas" % (10, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    obs = json.loads(OBSERVADOS.read_text(encoding="utf-8")) if OBSERVADOS.exists() else {}
    tab = tabela_tamanhos()
    cmp_ = comparar_train_vs_test()

    print("MEIA-LARGURA DO IC 95 %% DA MEDIA DE DICE  (CALCULADO: t*sigma/sqrt(n))")
    print("%4s | %-22s | %-22s | %-22s" % ("n", "sigma 0,0192 (otim.)",
                                           "sigma 0,0558 (interm.)", "sigma 0,1369 (pess.)"))
    for l in tab:
        c = l["ic"]
        print("%4d | +/- %.4f  %-8s | +/- %.4f  %-8s | +/- %.4f  %-8s"
              % (l["n"],
                 c["otimista"]["meia_largura"], "" if c["otimista"]["menor_que_dp_entre_folds"] else "(>dp)",
                 c["intermediario"]["meia_largura"], "" if c["intermediario"]["menor_que_dp_entre_folds"] else "(>dp)",
                 c["pessimista"]["meia_largura"], "" if c["pessimista"]["menor_que_dp_entre_folds"] else "(>dp)"))
    print()
    print("SENSIBILIDADE A CASO EXTREMO (deslocamento da media, aritmetica exata)")
    print("%4s | %11s | %11s | %11s | %s" % ("n", "1 colapso", "2 colapsos", "1 excelente",
                                             "P(>=1 colapso)"))
    for l in tab:
        print("%4d | %+11.4f | %+11.4f | %+11.4f | %13.1f %%"
              % (l["n"], l["desloc_por_1_colapso"], l["desloc_por_2_colapsos"],
                 l["desloc_por_1_excelente"], 100 * l["prob_ao_menos_um_colapso"]))
    print()
    print("TRAIN x TEST — dp ENTRE as 5 redes com TRAIN=10: %.4f (amplitude %.3f)"
          % (cmp_["dp_entre_folds"], cmp_["amplitude_entre_folds"]))
    for nome in ("otimista", "intermediario", "pessimista"):
        n15 = cmp_["cenarios"][nome]["por_n"][15]
        print("   sigma %-14s n=15: IC +/- %.4f  = %.2f x o dp entre folds"
              % (nome, n15["meia_largura_ic"], n15["razao_ic_sobre_dp_entre_folds"]))
    print()
    print(cmp_["leitura"])

    if obs:
        print()
        print("SIMULACAO (reamostragem dos %d valores do reservado; SIMULACAO, nao teoria)"
              % len(obs["reservado6_dice"]))
        for n in (5, 10, 15, 20):
            s = simular_media(obs["reservado6_dice"], n)
            print("   n=%2d  IC simulado [%.4f ; %.4f]  largura %.4f" % (n, s["p2_5"], s["p97_5"], s["largura"]))

    if a.escrever:
        SAIDA.mkdir(parents=True, exist_ok=True)
        (SAIDA / "analise.json").write_text(json.dumps({
            "tabela_tamanhos": tab, "train_vs_test": cmp_,
            "cenarios_sigma": [{"nome": n, "sigma": s, "origem": o} for n, s, o in CENARIOS_SIGMA],
            "simulacao_reservado": ({str(n): simular_media(obs["reservado6_dice"], n)
                                     for n in NS} if obs else {}),
            "premissas": [
                "sigma e DESCONHECIDO para um TEST futuro; os tres cenarios sao os sigmas observados no projeto",
                "os tres sigmas vem de estimadores diferentes e NAO sao misturados",
                "p de colapso = 2/16, frequencia observada, ela mesma muito incerta",
                "o IC assume amostragem independente de uma populacao; com casos de uma so coorte isso e aproximacao",
            ],
        }, indent=1, ensure_ascii=False), encoding="utf-8")
        print("\nescrito:", SAIDA / "analise.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
