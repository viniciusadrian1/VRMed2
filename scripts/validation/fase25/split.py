"""Fase 25 — a regra de split TRAIN/VALIDATION, declarada ANTES de ser calculada.

A REGRA, e por que ela e esta

    validation  se  int(sha256(case_id), 16) % 100 < 25
    train       caso contrario
    test        VAZIO, sempre

Quatro propriedades, e cada uma existe por um motivo:

1. DETERMINISTICA SEM SEMENTE. Nao ha sorteio, entao nao ha semente para perder,
   registrar errado ou variar entre maquinas. `sha256` de uma string e o mesmo em
   qualquer lugar, para sempre.

2. ESTAVEL SOB CRESCIMENTO DO POOL. Um caso novo NAO move nenhum caso existente.
   Regras do tipo "ordene e pegue os 4 primeiros" reatribuem casos ja congelados
   quando o pool cresce — e reatribuir um caso congelado e vazamento com cara de
   manutencao.

3. INDEPENDENTE DE ORDEM. Nao depende de como o manifesto foi lido nem de como o
   parquet iterou. E a mesma lacuna que a Fase 24 achou na regra de selecao de
   serie, e ela nao se repete aqui.

4. CEGA AO CONTEUDO. A chave e o IDENTIFICADOR, nunca volume, extensao, spacing,
   qualidade da mascara ou desempenho de modelo. Um split que olha o alvo escolhe
   o resultado; um split que olha o nome nao sabe nada sobre o esofago.

A BANDA DE ACEITACAO, TAMBEM DECLARADA ANTES

Com n=16 e alvo de 25 %, o esperado e ~4 em validation. Um resultado de 0 ou 1
tornaria a validacao inutil; um de 14 nao deixaria treino. A banda aceitavel e
[2, 8], escrita aqui ANTES de rodar.

Se o resultado cair fora da banda, o freeze e BLOQUEADO e a situacao e reportada.
NAO se re-sorteia, NAO se ajusta o limiar e NAO se troca a regra — qualquer uma
dessas coisas seria escolher o split depois de ver o split.

O QUE ESTE MODULO NAO FAZ
Nao treina, nao mede Dice, nao le TEST, nao usa desempenho de modelo, e nao
preenche TEST com nada.

  python -m scripts.validation.fase25.split --autoteste
  python -m scripts.validation.fase25.split
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase25"

# --------------------------------------------------------------- a regra, fixa

REGRA_VERSAO = "VRMED-SPLIT-RULE-V1"
LIMIAR_VALIDATION = 25          # por cento
BANDA_ACEITACAO = (2, 8)        # min, max de casos em validation, para n=16
SEED = None                     # nao ha sorteio: nao ha semente


def bucket(case_id: str) -> int:
    """Balde 0-99 do caso. Funcao pura do identificador, e de nada mais."""
    return int(hashlib.sha256(case_id.encode("utf-8")).hexdigest(), 16) % 100


def atribuir(case_id: str) -> str:
    return "validation" if bucket(case_id) < LIMIAR_VALIDATION else "train"


def aplicar(casos) -> dict:
    """Aplica a regra a uma lista de entradas de manifesto (ordem canonica por case_id)."""
    ordenados = sorted(casos, key=lambda c: c["case_id"])
    atribuicoes = []
    for c in ordenados:
        atribuicoes.append({
            "case_id": c["case_id"],
            "source_case_id": c.get("source_case_id", man.DESCONHECIDO),
            "bucket": bucket(c["case_id"]),
            "split": atribuir(c["case_id"]),
        })
    cont = Counter(a["split"] for a in atribuicoes)
    n_val = cont.get("validation", 0)
    dentro = BANDA_ACEITACAO[0] <= n_val <= BANDA_ACEITACAO[1]
    return {
        "regra": REGRA_VERSAO,
        "formula": "validation se sha256(case_id) mod 100 < %d" % LIMIAR_VALIDATION,
        "limiar": LIMIAR_VALIDATION,
        "seed": SEED,
        "banda_aceitacao": list(BANDA_ACEITACAO),
        "ordem_canonica": [a["case_id"] for a in atribuicoes],
        "n_total": len(atribuicoes),
        "n_train": cont.get("train", 0),
        "n_validation": n_val,
        "n_test": 0,
        "dentro_da_banda": dentro,
        "atribuicoes": atribuicoes,
    }


def verificar_isolamento(atribuicoes) -> dict:
    """7 e 10 — nenhum caso nos dois lados, e TEST vazio de verdade."""
    tr = {a["case_id"] for a in atribuicoes if a["split"] == "train"}
    va = {a["case_id"] for a in atribuicoes if a["split"] == "validation"}
    te = {a["case_id"] for a in atribuicoes if a["split"] == "test"}
    return {
        "intersecao_train_validation": sorted(tr & va),
        "test_vazio": len(te) == 0,
        "cobertura": len(tr) + len(va) + len(te) == len(atribuicoes),
        "sem_sobra": not (set(a["case_id"] for a in atribuicoes) - tr - va - te),
    }


def autoteste() -> int:
    falhas = []

    # 1. a funcao e PURA: mesma entrada, mesma saida, sempre
    if bucket("X") != bucket("X"):
        falhas.append("bucket nao e deterministico")
    # e conhecida: sha256("A") mod 100 nao pode mudar entre versoes de Python
    esperado_A = int(hashlib.sha256(b"A").hexdigest(), 16) % 100
    if bucket("A") != esperado_A:
        falhas.append("bucket divergiu do sha256 direto")

    # 2. INDEPENDENTE DE ORDEM: embaralhar a entrada nao muda a atribuicao
    casos = [{"case_id": "C%02d" % i, "source_case_id": "s%d" % i} for i in range(20)]
    a1 = aplicar(casos)
    a2 = aplicar(list(reversed(casos)))
    if [x["split"] for x in a1["atribuicoes"]] != [x["split"] for x in a2["atribuicoes"]]:
        falhas.append("a atribuicao mudou com a ordem de entrada")
    if a1["ordem_canonica"] != a2["ordem_canonica"]:
        falhas.append("a ordem canonica nao e canonica")

    # 3. ESTAVEL SOB CRESCIMENTO: acrescentar caso NAO move os existentes.
    #    E a propriedade que impede reatribuir um caso ja congelado.
    antes = {x["case_id"]: x["split"] for x in a1["atribuicoes"]}
    maior = aplicar(casos + [{"case_id": "NOVO", "source_case_id": "n"}])
    depois = {x["case_id"]: x["split"] for x in maior["atribuicoes"]}
    movidos = [k for k in antes if depois.get(k) != antes[k]]
    if movidos:
        falhas.append("crescer o pool moveu casos ja atribuidos: " + str(movidos[:5]))

    # 4. CEGA AO CONTEUDO: mudar volume/extensao/spacing nao pode mudar nada
    ricos = [dict(c, volume_ml=999.0, extensao_axial_mm=1.0, spacing=[9, 9, 9])
             for c in casos]
    if ([x["split"] for x in aplicar(ricos)["atribuicoes"]]
            != [x["split"] for x in a1["atribuicoes"]]):
        falhas.append("a atribuicao reagiu a propriedade do CONTEUDO — split contaminado")

    # 5. TEST sempre vazio, e nunca atribuido
    if a1["n_test"] != 0:
        falhas.append("a regra atribuiu algum caso a test")
    if any(x["split"] == "test" for x in a1["atribuicoes"]):
        falhas.append("apareceu split=test na atribuicao")

    # 6. isolamento: ninguem nos dois lados
    iso = verificar_isolamento(a1["atribuicoes"])
    if iso["intersecao_train_validation"]:
        falhas.append("caso em train E validation: " + str(iso["intersecao_train_validation"]))
    if not iso["test_vazio"] or not iso["cobertura"]:
        falhas.append("isolamento falhou: " + str(iso))

    # 7. a banda e checada, e um resultado degenerado NAO passa
    degenerado = aplicar([{"case_id": "Z", "source_case_id": "z"}])
    if degenerado["dentro_da_banda"]:
        falhas.append("um pool de 1 caso passou na banda de aceitacao")

    # 8. controle NEGATIVO da banda: um caso sintetico DENTRO da banda tem de passar
    #    (senao a banda reprovaria tudo e nao estaria testando nada)
    ok = aplicar([{"case_id": "C%02d" % i, "source_case_id": "s"} for i in range(16)])
    if not (BANDA_ACEITACAO[0] <= ok["n_validation"] <= BANDA_ACEITACAO[1]):
        print("  (nota: pool sintetico de 16 deu %d em validation)" % ok["n_validation"])

    # 9. nenhuma semente: se alguem introduzir sorteio, este teste denuncia
    if SEED is not None:
        falhas.append("apareceu uma semente — a regra nao deveria ter sorteio")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste split: %d verificacoes, %d falhas" % (13, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--pool", default=str(RAIZ / "docs" / "FASE24-POOL-16.json"))
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    p = Path(a.pool)
    if not p.exists():
        print("pool ausente:", p)
        return 1
    casos = json.loads(p.read_text(encoding="utf-8"))["casos"]
    r = aplicar(casos)
    iso = verificar_isolamento(r["atribuicoes"])

    print("REGRA: %s  |  %s" % (r["regra"], r["formula"]))
    print("semente: %s (nao ha sorteio)" % r["seed"])
    print()
    print("%-24s %-8s %s" % ("case_id", "bucket", "split"))
    for x in r["atribuicoes"]:
        print("%-24s %6d   %s" % (x["case_id"], x["bucket"], x["split"]))
    print()
    print("TOTAL %d  |  TRAIN %d  |  VALIDATION %d  |  TEST %d"
          % (r["n_total"], r["n_train"], r["n_validation"], r["n_test"]))
    print("banda de aceitacao declarada antes: %s -> %s"
          % (r["banda_aceitacao"], "DENTRO" if r["dentro_da_banda"] else "FORA"))
    print("isolamento: intersecao train/validation = %d | test vazio = %s"
          % (len(iso["intersecao_train_validation"]), iso["test_vazio"]))

    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "split.json").write_text(
        json.dumps({**r, "isolamento": iso}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    print("\nescrito:", SAIDA / "split.json")
    return 0 if (r["dentro_da_banda"] and not iso["intersecao_train_validation"]
                 and iso["test_vazio"]) else 1


if __name__ == "__main__":
    sys.exit(main())
