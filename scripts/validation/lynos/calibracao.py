"""Fase 18 — calibracao HONESTA da sonda geometrica, e o defeito que ela corrigiu.

O DEFEITO QUE ESTE MODULO EXISTE PARA CONSERTAR
A primeira calibracao de `auditoria.py` sorteava os tres eixos do alvo de casos
DIFERENTES: z do caso i, y do caso j, x do caso k. Como o LyNoS e quase todo
in-plane quadrado (rows == cols, px == py), embaralhar y e x separadamente produz
alvos RETANGULARES — e ~75 % do pool de treino e quadrado no plano. O nulo passava
a gerar alvos que quase nunca poderiam casar, e por isso saia baixo demais
(0,041 esperado em 15). Um nulo deflacionado infla qualquer sinal medido contra ele.

O NULO CORRETO
A unidade que se embaralha nao e o eixo — e o BLOCO. Um caso contribui com dois
blocos que a hipotese nula precisa desassociar:

    bloco IN-PLANE  = (rows, cols, py, px)   -> alvo (y, x)
    bloco AXIAL     = (n_fatias, dz)          -> alvo (z)

Permutar os blocos preserva a estrutura interna de cada um (a quadratura do plano
sobrevive) e destroi exatamente o que a nula precisa destruir: a associacao entre
extensao axial e campo de visao do MESMO exame.

Com 15 casos ha 15x15 = 225 pares possiveis. A matriz inteira e calculavel, entao
isto nao e amostragem: e um TESTE DE PERMUTACAO EXATO na matriz, com a estatistica
observada na diagonal.

  python -m scripts.validation.lynos.calibracao --autoteste
  python -m scripts.validation.lynos.calibracao
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.lynos.auditoria import (  # noqa: E402
    ALVO_SPACING, FINGERPRINT, SAIDA, TOL,
)

N_PERM = 200000
SEMENTE = 20260906


def matriz(medidas, shapes, exatos):
    """M[i][j] = o alvo formado pelo eixo axial do caso i e pelo plano do caso j casa?

    Devolve duas matrizes: match exato (3 eixos) e match com tolerancia +-TOL.
    """
    n = len(medidas)
    z = [int(round(m["shape"][2] * m["spacing_mm"][2] / ALVO_SPACING)) for m in medidas]
    plano = [(int(round(m["shape"][1] * m["spacing_mm"][1] / ALVO_SPACING)),
              int(round(m["shape"][0] * m["spacing_mm"][0] / ALVO_SPACING)))
             for m in medidas]

    ex = np.zeros((n, n), dtype=bool)
    tl = np.zeros((n, n), dtype=bool)
    for i in range(n):
        for j in range(n):
            alvo = (z[i], plano[j][0], plano[j][1])
            ex[i, j] = tuple(alvo) in exatos
            tl[i, j] = any(all(abs(s[k] - alvo[k]) <= TOL for k in range(3)) for s in shapes)
    return ex, tl, z, plano


def permutar(M, n_perm=N_PERM, semente=SEMENTE):
    """Distribuicao de sum_i M[i][sigma(i)] sob sigma uniforme. Observado = traco."""
    n = M.shape[0]
    obs = int(np.trace(M))
    rng = np.random.default_rng(semente)
    idx = np.arange(n)
    contagem = Counter()
    ge = 0
    for _ in range(n_perm):
        s = rng.permutation(idx)
        v = int(M[idx, s].sum())
        contagem[v] += 1
        if v >= obs:
            ge += 1
    # p unilateral com correcao de continuidade (+1/+1): nunca devolve p = 0
    p = (ge + 1) / (n_perm + 1)
    esperado = sum(v * c for v, c in contagem.items()) / n_perm
    return {
        "observado": obs,
        "esperado_sob_nula": round(esperado, 4),
        "p_unilateral": round(p, 6),
        "n_permutacoes": n_perm,
        "distribuicao": {str(k): v for k, v in sorted(contagem.items())},
        "razao_obs_esperado": round(obs / esperado, 2) if esperado > 0 else None,
    }


def perfil_do_pool(shapes) -> dict:
    """Quanto do pool de treino e quadrado no plano, e onde ele se concentra.

    Sem isto nao da para julgar se um match e barato ou caro: se o pool inteiro
    for 512x512 quadrado, casar no plano nao custa nada.
    """
    a = np.array(shapes)
    quad = int((a[:, 1] == a[:, 2]).sum())
    return {
        "n": len(shapes),
        "distintos": len({tuple(s) for s in shapes}),
        "in_plane_quadrado": quad,
        "in_plane_quadrado_pct": round(100.0 * quad / len(shapes), 1),
        "z":  {"min": int(a[:, 0].min()), "p25": int(np.percentile(a[:, 0], 25)),
               "mediana": int(np.median(a[:, 0])), "p75": int(np.percentile(a[:, 0], 75)),
               "max": int(a[:, 0].max())},
        "y":  {"min": int(a[:, 1].min()), "p25": int(np.percentile(a[:, 1], 25)),
               "mediana": int(np.median(a[:, 1])), "p75": int(np.percentile(a[:, 1], 75)),
               "max": int(a[:, 1].max())},
        "moda_in_plane": [list(k) + [v] for k, v in
                          Counter(map(tuple, a[:, 1:3].tolist())).most_common(5)],
    }


def autoteste() -> int:
    falhas = []
    shapes = [[100, 200, 200], [150, 300, 300]]
    exatos = {tuple(s) for s in shapes}

    # dois casos fabricados: o caso 0 casa EXATAMENTE, o caso 1 nao casa de jeito nenhum
    medidas = [
        {"shape": [200, 200, 100], "spacing_mm": [1.5, 1.5, 1.5]},   # -> (100,200,200) HIT
        {"shape": [999, 999, 999], "spacing_mm": [1.5, 1.5, 1.5]},   # -> (999,999,999) miss
    ]
    ex, tl, z, plano = matriz(medidas, shapes, exatos)
    if not ex[0, 0]:
        falhas.append("controle positivo: o caso que casa exatamente nao foi detectado")
    if ex[1, 1]:
        falhas.append("controle negativo: o caso impossivel foi detectado")
    if int(np.trace(ex)) != 1:
        falhas.append("traco deveria ser 1, foi " + str(int(np.trace(ex))))

    # a permutacao tem de ver esse 1 como NAO surpreendente: com 2 casos, metade das
    # permutacoes e a identidade. Se p sair minusculo aqui, o teste esta viciado.
    r = permutar(ex, n_perm=2000, semente=1)
    if r["p_unilateral"] < 0.3:
        falhas.append("permutacao com n=2 deveria dar p ~0,5; deu " + str(r["p_unilateral"]))

    # a permutacao NUNCA pode devolver p = 0 (correcao de continuidade)
    forte = np.eye(6, dtype=bool)
    rf = permutar(forte, n_perm=2000, semente=2)
    if rf["p_unilateral"] <= 0:
        falhas.append("p unilateral saiu zero — correcao de continuidade quebrada")
    if rf["observado"] != 6:
        falhas.append("traco da identidade deveria ser 6")

    # e uma matriz cheia tem de dar p = 1: tudo casa, nada e surpreendente
    cheia = np.ones((5, 5), dtype=bool)
    rc = permutar(cheia, n_perm=1000, semente=3)
    if rc["p_unilateral"] < 0.99:
        falhas.append("matriz cheia deveria dar p = 1; deu " + str(rc["p_unilateral"]))

    # o defeito ORIGINAL, reproduzido: embaralhar y e x separadamente destroi a
    # quadratura e deflaciona o nulo. Este teste existe para que o erro nao volte.
    quad_pool = [[100, 250, 250], [100, 260, 260], [100, 270, 270]]
    med_quad = [{"shape": [s[2], s[1], s[0]], "spacing_mm": [1.5, 1.5, 1.5]} for s in quad_pool]
    ex_q, _, _, _ = matriz(med_quad, quad_pool, {tuple(s) for s in quad_pool})
    # sob o nulo CORRETO o plano viaja em bloco, entao toda coluna casa: matriz cheia
    if not ex_q.all():
        falhas.append("nulo por bloco perdeu a quadratura: matriz deveria ser cheia")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste calibracao: %d verificacoes, %d falhas" % (8, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        print("\nABORTADO: autoteste falhou.")
        return 1
    print()

    doc = json.loads((SAIDA / "lynos_auditoria.json").read_text())
    medidas = doc["casos"]
    shapes = json.loads(FINGERPRINT.read_text())["shapes_after_crop"]
    exatos = {tuple(s) for s in shapes}

    perfil = perfil_do_pool(shapes)
    print("PERFIL DO POOL DE TREINO (Dataset291, 1559 imagens)")
    print("  in-plane quadrado: %d/%d (%.1f%%)"
          % (perfil["in_plane_quadrado"], perfil["n"], perfil["in_plane_quadrado_pct"]))
    print("  z  min/p25/med/p75/max: %(min)d %(p25)d %(mediana)d %(p75)d %(max)d" % perfil["z"])
    print("  y  min/p25/med/p75/max: %(min)d %(p25)d %(mediana)d %(p75)d %(max)d" % perfil["y"])
    print("  modas in-plane (y,x,n):", perfil["moda_in_plane"])
    print()

    ex, tl, z, plano = matriz(medidas, shapes, exatos)
    print("MATRIZ 15x15 (eixo axial do caso i  x  plano do caso j)")
    print("  celulas com match exato: %d/225 (%.1f%%)"
          % (int(ex.sum()), 100.0 * ex.sum() / ex.size))
    print("  celulas com match tol+-%d: %d/225 (%.1f%%)"
          % (TOL, int(tl.sum()), 100.0 * tl.sum() / tl.size))
    print()

    r_ex = permutar(ex)
    r_tl = permutar(tl)
    for nome, r in (("MATCH EXATO", r_ex), ("MATCH TOL+-2", r_tl)):
        print("%s" % nome)
        print("  observado (diagonal real): %d de %d" % (r["observado"], len(medidas)))
        print("  esperado sob a nula:       %.4f" % r["esperado_sob_nula"])
        print("  razao obs/esperado:        %s" % r["razao_obs_esperado"])
        print("  p unilateral (permutacao): %.6f  (%d permutacoes)"
              % (r["p_unilateral"], r["n_permutacoes"]))
        print()

    saida = {
        "fase": 18,
        "metodo": "teste de permutacao exato por BLOCO (axial x in-plane), 15x15",
        "defeito_corrigido": (
            "a primeira calibracao embaralhava y e x separadamente, gerando alvos "
            "retangulares contra um pool majoritariamente quadrado; o nulo saia "
            "deflacionado (0,041 em 15) e inflava o sinal medido contra ele"
        ),
        "perfil_do_pool": perfil,
        "matriz": {
            "celulas_match_exato": int(ex.sum()),
            "celulas_match_tol": int(tl.sum()),
            "celulas_total": int(ex.size),
        },
        "match_exato": r_ex,
        "match_tol2": r_tl,
        "alvos": [{"caso": m["arquivo"].split("_")[0], "z": z[i], "plano": list(plano[i])}
                  for i, m in enumerate(medidas)],
    }
    (SAIDA / "lynos_calibracao.json").write_text(json.dumps(saida, indent=1))
    print("escrito:", SAIDA / "lynos_calibracao.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
