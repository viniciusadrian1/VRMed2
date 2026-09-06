"""Fase 12 — a banda de concordancia HUMANA do esofago, recalculada da fonte aberta.

O QUE ESTE NUMERO E
Concordancia de UM medico contra UMA referencia humana curada, no MESMO esofago, na
MESMA TC, sob o atlas RTOG 1106. Vem do Source Data aberto (CC BY-NC-ND) de
Niu G. et al., "A prospective multicenter trial of deep learning auto-segmentation for
organs at risk in thoracic radiotherapy", Nat Commun 2026, DOI 10.1038/s41467-026-70863-9,
PMCID PMC13199442, ensaio NCT05787522.

POR QUE ISSO E CONCORDANCIA HUMANO-CONTRA-HUMANO, e nao "acuracia contra um consenso"
O padrao-ouro do estudo NAO e fusao matematica — nao e STAPLE, nao e media, nao e voto.
O Expert C ESCOLHE, orgao a orgao, o contorno do Expert A OU o do Expert B, com ajustes
menores (verbatim dos Methods: "compared and selected the most accurate delineations from
Experts A and B (e.g., the right lung from Expert A and the spinal cord from Expert B)").
Logo o esofago da referencia E o contorno de UM unico especialista senior, editado.
Os dois grupos humanos sao disjuntos por declaracao reciproca: os 37 medicos dos bracos
"were not involved in the ground truth generation", e A/B/C "were not involved in the
manual or AI-assisted delineation". Nao ha circularidade.

O QUE ESTE NUMERO NAO E — leia antes de citar
 - NAO e variabilidade interobservador medida entre dois contornos humanos par a par.
   Essa medida NAO EXISTE na fonte: "agreement" e "concordance" aparecem ZERO vezes no
   artigo, no protocolo e no peer review; "inter-observer" aparece uma vez, citando
   literatura alheia. A e B nunca sao comparados entre si.
 - NAO e a coluna ABS--M-vDSC (|Delta| de desempenho). Aquilo e
   |vDSC(medico1, GT) - vDSC(medico2, GT)|: dois medicos com contornos radicalmente
   diferentes podem dar |Delta| = 0. Este modulo usa as colunas CRUAS, de proposito.
 - NAO e um piso: a referencia e curada e travada por concordancia dos tres especialistas,
   entao a concordancia contra ela e SISTEMATICAMENTE MAIOR que entre dois humanos
   quaisquer. E um TETO OTIMISTA. Dois observadores arbitrarios concordariam <= isto.
 - NAO e limiar. E distribuicao, e entra como faixa de CONTEXTO.
 - NAO e amostra aleatoria: as colunas se chamam LE-M / E-M (less-experienced /
   experienced) e o par foi escolhido pelo CONTRASTE de experiencia, sobre as imagens
   circuladas entre centros adjacentes. 277 pares de 496 possiveis.

DEFEITO NO DADO PUBLICADO, encontrado na conferencia e reproduzido aqui
A coluna CW da aba "Fig. 4", rotulada `ABS-M-HD95`, NAO e diferenca absoluta nenhuma:
e copia literal da coluna CN (`E-M`, o HD95 do medico experiente contra o GT), identica
em 252/252 linhas de esofago. Quem confiar no rotulo obtem 4,60 mm no lugar do 1,177 mm
publicado na Fig. 4i. O autoteste abaixo trava essa armadilha.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

FONTE = Path(".clinica-dados/fase12/41467_2026_70863_MOESM4_ESM.xlsx")
ABA = "Fig. 4"

# Colunas por indice 0-based da aba, medidas em 2026-09-06. O bloco F traz vDSC e o
# bloco G traz HD95; cada bloco tem sua PROPRIA coluna de rotulo de OAR, e usar a do
# bloco errado desalinha silenciosamente.
COL_OAR_VDSC, COL_OAR_HD95 = 83, 89
COLUNAS = {
    "vDSC LE-M": (COL_OAR_VDSC, 84), "vDSC E-M": (COL_OAR_VDSC, 85),
    "vDSC LE-Aa": (COL_OAR_VDSC, 86), "vDSC E-Aa": (COL_OAR_VDSC, 87),
    "HD95 LE-M": (COL_OAR_HD95, 90), "HD95 E-M": (COL_OAR_HD95, 91),
}
COL_ABS_HD95_DEFEITUOSA = 100  # CW

ALVO = "Esophagus"

# Publicado nas Figs. 4f/4g, para conferencia. Fonte: artigo.
PUBLICADO = {"vDSC LE-M": 0.749, "vDSC E-M": 0.761, "HD95 LE-M": 5.00, "HD95 E-M": 4.58}


def _dist(v: np.ndarray, n_total: int) -> dict:
    q = np.percentile(v, [5, 25, 50, 75, 95])
    return {
        "n": int(len(v)), "n_linhas_do_alvo": int(n_total),
        "completude": round(len(v) / n_total, 4) if n_total else None,
        "min": float(v.min()), "p5": float(q[0]), "p25": float(q[1]),
        "mediana": float(q[2]), "p75": float(q[3]), "p95": float(q[4]),
        "max": float(v.max()), "media": float(v.mean()),
    }


def banda(caminho: Path = FONTE) -> dict:
    d = pd.read_excel(caminho, sheet_name=ABA, header=None)
    saida, brutos = {}, {}
    for nome, (col_oar, col_val) in COLUNAS.items():
        alvo = d.iloc[:, col_oar].astype(str).str.strip().eq(ALVO)
        v = pd.to_numeric(d.loc[alvo, col_val], errors="coerce").dropna().values
        brutos[nome] = v
        saida[nome] = _dist(v, int(alvo.sum()))

    # A banda que interessa: os DOIS medicos manuais juntos. Nao e media de medianas —
    # e a distribuicao empilhada, que e o que a Parte G da fase 12 pede.
    for rotulo, chaves in (("BANDA vDSC manual", ("vDSC LE-M", "vDSC E-M")),
                           ("BANDA HD95 manual (mm)", ("HD95 LE-M", "HD95 E-M"))):
        pool = np.concatenate([brutos[k] for k in chaves])
        saida[rotulo] = _dist(pool, sum(saida[k]["n_linhas_do_alvo"] for k in chaves))

    # O defeito do dado publicado, medido e nao citado.
    alvo_hd = d.iloc[:, COL_OAR_HD95].astype(str).str.strip().eq(ALVO)
    cw = pd.to_numeric(d.loc[alvo_hd, COL_ABS_HD95_DEFEITUOSA], errors="coerce").dropna().values
    cn = brutos["HD95 E-M"]
    saida["_defeito_CW_e_copia_de_CN"] = bool(len(cw) == len(cn) and np.array_equal(cw, cn))
    return saida


def _autoteste(caminho: Path = FONTE) -> None:
    """Tres controles. O terceiro e o que impede repetir o erro do dado publicado."""
    r = banda(caminho)

    # 1. bate com o publicado nas Figs. 4f/4g (tolerancia de arredondamento do artigo)
    for chave, esperado in PUBLICADO.items():
        obtido = r[chave]["mediana"]
        assert abs(obtido - esperado) < 0.02 * max(1.0, abs(esperado)), (
            f"{chave}: mediana {obtido:.4f} nao reproduz o publicado {esperado}")

    # 2. completude declarada, nunca silenciosa — 88-92% do bloco, o resto sao vazios
    for chave in COLUNAS:
        assert 0.85 < r[chave]["completude"] < 1.0, f"{chave}: completude fora do esperado"

    # 3. CONTROLE DO DEFEITO: se um dia a planilha for corrigida na origem, este assert
    #    cai e o modulo avisa em vez de continuar apontando um defeito que nao existe mais.
    assert r["_defeito_CW_e_copia_de_CN"], (
        "a coluna CW deixou de ser copia de CN — o defeito do dado publicado foi corrigido "
        "na origem; reler o relatorio da Fase 12, que o documenta como presente")

    print("banda_humana_esofago.py: autoteste OK (3 controles; o publicado reproduz, "
          "completude declarada, defeito CW confirmado)")


if __name__ == "__main__":
    import json
    import sys

    if not FONTE.exists():
        raise SystemExit(f"fonte ausente: {FONTE}\n"
                         "baixe o Source Data aberto de PMC13199442 (Europe PMC "
                         "supplementaryFiles) antes de rodar.")
    _autoteste()
    if "--autoteste" not in sys.argv:
        r = banda()
        print("\nOBJETO = ESOFAGO · concordancia de UM medico contra referencia HUMANA "
              "curada (RTOG 1106)\nNAO e interobservador par a par · e TETO OTIMISTA, "
              "nao piso · faixa de contexto, nunca limiar\n")
        for k, v in r.items():
            if k.startswith("_"):
                continue
            print(f"{k:<24} n={v['n']:>4} ({v['completude']*100:.1f}%)  "
                  f"P5 {v['p5']:.4f} | P25 {v['p25']:.4f} | MED {v['mediana']:.4f} | "
                  f"P75 {v['p75']:.4f} | P95 {v['p95']:.4f}")
        Path(".clinica-dados/fase12/banda_humana_esofago.json").write_text(
            json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
