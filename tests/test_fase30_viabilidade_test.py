"""Fase 30 — a fase nao podia tocar em nada, e os calculos tem de ser reproduziveis.

Tres metades:

  [INTEGRIDADE]  compara o estado atual com a impressao digital tirada ANTES da fase:
                 manifesto, snapshot, pool16, split, epocas por fold, tamanho e mtime
                 de cada .pth, e contagem de predicoes. Qualquer diferenca = FAIL.

  [CALCULO]      o IC, a sensibilidade a outlier e a binomial sao conferidos contra a
                 formula, nao contra si mesmos. Um calculo que so concorda consigo
                 nao esta verificado.

  [DECISAO]      o JSON publicado tem de ser coerente com a analise e trazer as
                 premissas explicitas — sem premissa, o numero nao e auditavel.

  python tests/test_fase30_viabilidade_test.py
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.fase30.analise_test_train import (  # noqa: E402
    CENARIOS_SIGMA, DICE_POR_FOLD, DP_ENTRE_FOLDS, NS, comparar_train_vs_test,
    efeito_de_um_caso, meia_largura, prob_ao_menos_um_colapso, simular_media,
    t_975, tabela_tamanhos,
)

MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"
POOL16 = RAIZ / "docs" / "FASE24-POOL-16.json"
DECISAO = RAIZ / "docs" / "FASE30-DECISAO-TEST-TRAIN.json"
ANTES = RAIZ / "docs" / "overnight" / "phase30" / "integridade_antes.json"

SHA_CONGELADO = "9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192"
N_TRAIN, N_VALIDATION, N_TEST = 10, 6, 0


class Pulado(Exception):
    """Artefato ausente. NAO e passar."""


def _ent():
    return man.carregar(MANIFESTO)


def _impressao_atual() -> dict:
    fp = {"treino": {}}
    for rot, base in (
        ("26b", ".clinica-dados/fase26b/nnUNet_results/Dataset501_VRmedEsofago/nnUNetTrainer_250epochs__nnUNetPlans__3d_fullres"),
        ("26", ".clinica-dados/fase26/nnUNet_results/Dataset501_VRmedEsofago/nnUNetTrainer__nnUNetPlans__3d_fullres"),
    ):
        b = RAIZ / base
        if not b.exists():
            continue
        for f in sorted(b.glob("fold_*")):
            txt = "".join(p.read_text(encoding="utf-8", errors="replace")
                          for p in sorted(f.glob("training_log_*.txt")))
            fp["treino"]["%s/%s" % (rot, f.name)] = {
                "epocas": len(re.findall(r"Epoch time:", txt)),
                "pth": {p.name: [p.stat().st_size, int(p.stat().st_mtime)]
                        for p in sorted(f.glob("*.pth"))}}
    pred = RAIZ / ".clinica-dados" / "fase26b" / "predicoes_holdout"
    fp["predicoes"] = ({d.name: len(list(d.glob("*.nii.gz")))
                        for d in sorted(pred.iterdir()) if d.is_dir()} if pred.exists() else {})
    return fp


# ------------------------------------------------------------ [INTEGRIDADE]


def test_01_test_continua_zero_e_inalcancavel():
    ent = _ent()
    assert [e for e in ent if e["split"] == "test"] == [], "apareceu caso em TEST"
    for ctx in ("treino", "validacao"):
        try:
            man.carregar_particao(ent, "test", ctx)
        except man.AcessoIndevido:
            continue
        raise AssertionError("contexto %r alcancou o TEST" % ctx)
    assert len(man.carregar_particao(ent, "train", "treino")) == N_TRAIN  # controle negativo


def test_02_manifesto_nao_mudou():
    r = man.verificar_congelamento(_ent(), json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    assert r["intacto"] and r["sha256_atual"] == SHA_CONGELADO, r["mudancas"]


def test_03_snapshot_e_pool16_nao_mudaram():
    if not ANTES.exists():
        raise Pulado("impressao digital ausente")
    antes = json.loads(ANTES.read_text(encoding="utf-8"))
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == antes["snapshot_sha256"]
    assert hashlib.sha256(POOL16.read_bytes()).hexdigest() == antes["pool16_sha256"]


def test_04_split_nao_mudou():
    por = {p: sum(1 for e in _ent() if e["split"] == p) for p in man.PARTICOES}
    assert por == {"train": N_TRAIN, "validation": N_VALIDATION, "test": N_TEST}, por


def test_05_checkpoints_e_treino_intactos():
    """Nenhum treino novo, nenhum .pth reescrito. Epoca a epoca, byte a byte."""
    if not ANTES.exists():
        raise Pulado("impressao digital ausente")
    antes = json.loads(ANTES.read_text(encoding="utf-8"))["treino"]
    agora = _impressao_atual()["treino"]
    assert set(antes) == set(agora), "conjunto de folds mudou: %s" % (set(antes) ^ set(agora))
    difs = []
    for k, v in antes.items():
        if agora[k]["epocas"] != v["epocas"]:
            difs.append("%s: %d epocas, era %d — TREINO NOVO" % (k, agora[k]["epocas"], v["epocas"]))
        if agora[k]["pth"] != v["pth"]:
            difs.append("%s: checkpoint alterado" % k)
    assert not difs, "\n  ".join(difs)


def test_06_nenhuma_inferencia_nova():
    if not ANTES.exists():
        raise Pulado("impressao digital ausente")
    antes = json.loads(ANTES.read_text(encoding="utf-8"))["predicoes"]
    assert _impressao_atual()["predicoes"] == antes, "contagem de predicoes mudou"


def test_07_nenhum_dataset_novo():
    fontes = {e["source_dataset"] for e in _ent()}
    assert fontes == {"4D-Lung (TCIA)"}, "source_dataset novo: %s" % sorted(fontes)
    # e nenhuma arvore de dados nova apareceu em .clinica-dados
    base = RAIZ / ".clinica-dados"
    if base.exists():
        novos = [d.name for d in base.iterdir() if d.is_dir() and d.name.startswith("fase3")]
        assert not novos, "diretorio de dados novo: %s" % novos


# --------------------------------------------------------------- [CALCULO]


def test_08_ic_confere_com_a_formula():
    """Contra a formula t*sigma/sqrt(n), nao contra si mesmo."""
    for n, sigma in ((6, 0.0192), (10, 0.0558), (15, 0.1369), (30, 0.05)):
        esperado = t_975(n - 1) * sigma / math.sqrt(n)
        assert abs(meia_largura(n, sigma) - esperado) < 1e-12, "IC divergiu em n=%d" % n
    # monotonia nos dois eixos
    assert meia_largura(30, 0.05) < meia_largura(10, 0.05) < meia_largura(5, 0.05)
    assert meia_largura(10, 0.02) < meia_largura(10, 0.14)
    # n<2 nao produz numero
    assert math.isnan(meia_largura(1, 0.05))


def test_09_sensibilidade_a_outlier_escala_com_1_sobre_n():
    a = efeito_de_um_caso(5, 0.45, 0.763)
    b = efeito_de_um_caso(10, 0.45, 0.763)
    c = efeito_de_um_caso(20, 0.45, 0.763)
    assert abs(a - 2 * b) < 1e-12 and abs(b - 2 * c) < 1e-12, "nao escala com 1/n"
    assert a < 0 < efeito_de_um_caso(10, 0.87, 0.763), "os sinais estao trocados"
    # valor conferivel a mao: (0,45 - 0,763)/5
    assert abs(a - (0.45 - 0.763) / 5) < 1e-12


def test_10_binomial_de_colapso():
    assert abs(prob_ao_menos_um_colapso(5) - (1 - 0.875 ** 5)) < 1e-12
    ps = [prob_ao_menos_um_colapso(n) for n in (3, 10, 30)]
    assert 0 < ps[0] < ps[1] < ps[2] < 1, ps
    assert prob_ao_menos_um_colapso(0) == 0.0


def test_11_dp_entre_folds_vem_dos_dados_observados():
    """A constante nao pode ser um numero solto: tem de sair dos Dice por fold."""
    assert abs(st.stdev(DICE_POR_FOLD) - DP_ENTRE_FOLDS) < 5e-4, (
        "DP_ENTRE_FOLDS=%.4f mas os folds dao %.4f" % (DP_ENTRE_FOLDS, st.stdev(DICE_POR_FOLD)))
    assert len(DICE_POR_FOLD) == 5


def test_12_simulacao_e_reproduzivel():
    v = [0.74, 0.76, 0.78, 0.80]
    a, b = simular_media(v, 10), simular_media(v, 10)
    assert a == b, "a simulacao nao e deterministica com a mesma semente"
    assert simular_media(v, 30)["largura"] < simular_media(v, 5)["largura"]


def test_13_os_tres_sigmas_nao_foram_fundidos():
    """Misturar estimadores diferentes foi exatamente o erro que a Fase 27B pegou."""
    sigmas = [s for _, s, _ in CENARIOS_SIGMA]
    assert len(set(sigmas)) == 3, "os cenarios de sigma colapsaram"
    assert all(o and len(o) > 20 for _, _, o in CENARIOS_SIGMA), "sigma sem origem declarada"
    assert max(sigmas) / min(sigmas) > 5, "os cenarios deveriam cobrir uma faixa larga"


def test_14_comparador_train_vs_test_tem_os_dois_lados():
    """Controle positivo e negativo: senao o comparador nao prova nada."""
    c = comparar_train_vs_test()
    assert c["cenarios"]["otimista"]["por_n"][30]["medicao_mais_fina_que_o_modelo"] is True
    assert c["cenarios"]["pessimista"]["por_n"][3]["medicao_mais_fina_que_o_modelo"] is False


# --------------------------------------------------------------- [DECISAO]


def test_15_json_de_decisao_e_valido_e_coerente():
    if not DECISAO.exists():
        raise Pulado("FASE30-DECISAO-TEST-TRAIN.json ausente")
    d = json.loads(DECISAO.read_text(encoding="utf-8"))
    for campo in ("fase", "test_atual", "train_atual", "validation_atual", "cenarios",
                  "test_sizes", "recommended_test_size", "recommended_next_step",
                  "reasoning", "confidence"):
        assert campo in d, "campo obrigatorio ausente: %s" % campo
    assert d["test_atual"] == N_TEST and d["train_atual"] == N_TRAIN
    assert d["validation_atual"] == N_VALIDATION
    assert d["recommended_test_size"] in [l["n"] for l in d["test_sizes"]], (
        "o tamanho recomendado nao esta na tabela")
    assert d["recommended_test_size"] >= d["minimo_com_utilidade_real"]
    assert len(d["cenarios"]) == 4, "esperava os 4 cenarios A-D"
    assert {c["id"] for c in d["cenarios"]} == {"A", "B", "C", "D"}
    assert len(d["reasoning"]) >= 3, "fundamentacao rasa demais"


def test_16_cenarios_e_tamanhos_tem_premissas_explicitas():
    """Numero sem premissa nao e auditavel."""
    if not DECISAO.exists():
        raise Pulado("decisao ausente")
    d = json.loads(DECISAO.read_text(encoding="utf-8"))
    assert d.get("premissas") and len(d["premissas"]) >= 4, "premissas ausentes ou rasas"
    junto = " ".join(d["premissas"]).lower()
    for termo in ("sigma", "desconhecido", "estimadores diferentes", "aproximacao"):
        assert termo in junto, "premissa nao menciona %r" % termo
    # cada cenario declara risco, custo e tempo
    for c in d["cenarios"]:
        for k in ("risco", "custo", "tempo", "resolve", "nao_resolve"):
            assert c.get(k), "cenario %s sem %s" % (c["id"], k)
    # a tabela cobre os mesmos n da analise
    assert [l["n"] for l in d["test_sizes"]] == list(NS)


def test_17_a_tabela_publicada_bate_com_o_calculo():
    """Reaplica o calculo sobre o JSON publicado — nao confia no que foi gravado."""
    if not DECISAO.exists():
        raise Pulado("decisao ausente")
    d = json.loads(DECISAO.read_text(encoding="utf-8"))
    ref = {l["n"]: l for l in tabela_tamanhos()}
    for linha in d["test_sizes"]:
        n = linha["n"]
        for nome, _, _ in CENARIOS_SIGMA:
            esperado = round(ref[n]["ic"][nome]["meia_largura"], 4)
            assert abs(linha["ic_meia_largura"][nome] - esperado) < 1e-9, (
                "IC publicado para n=%d/%s diverge do calculo" % (n, nome))
        assert abs(linha["desloc_por_1_colapso"] - round(ref[n]["desloc_por_1_colapso"], 4)) < 1e-9


def main() -> int:
    testes = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    falhas, pulados = [], []
    for nome, f in testes:
        try:
            f()
            print("  ok     %s" % nome)
        except Pulado as p:
            pulados.append(nome)
            print("  PULADO %s: %s" % (nome, p))
        except Exception as exc:  # noqa: BLE001
            falhas.append(nome)
            print("  FALHA  %s: %s" % (nome, exc))
    print("\n%d/%d passaram | %d pulados | %d falharam"
          % (len(testes) - len(falhas) - len(pulados), len(testes), len(pulados), len(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
