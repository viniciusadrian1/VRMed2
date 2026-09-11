"""Fase 28 — consolida as fichas pesquisadas em classificacao A-E, com a regra em codigo.

A REGRA DO STATUS A, E POR QUE ELA MORA AQUI E NAO NO RELATORIO

Prosa nao impede ninguem de promover um candidato duvidoso na proxima fase. Codigo
impede. Um candidato so pode ser A com evidencia POSITIVA em quatro eixos —
independencia, ontologia, anotacao e acesso — mais licenca nao bloqueante e nenhum
overlap detectado. `tests/test_fase28_test_discovery.py` reaplica exatamente esta
regra sobre o JSON gerado, com controle positivo dos dois lados.

O QUE ESTE MODULO NAO FAZ
Nao baixa dado, nao toca no manifesto, nao cria TEST, nao roda modelo.

  python -m scripts.validation.fase28.classificar --autoteste
  python -m scripts.validation.fase28.classificar --escrever
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase28"

EXIGENCIAS_A = {
    "independencia": ("DEMONSTRAVEL",),
    "ontologia": ("COMPATIVEL",),
    "anotacao_tipo": ("HUMANA_MANUAL", "HUMANA_REVISADA"),
    "acesso": ("ABERTO", "CADASTRO"),
}
PROIBIDOS_COMO_TEST = ("lctsc", "lynos", "nsclc-radiomics", "segthor")


def pode_ser_A(c: dict) -> tuple:
    """Devolve (pode, impedimentos). A mesma funcao que o teste reaplica."""
    imp = []
    for campo, aceitos in EXIGENCIAS_A.items():
        v = c.get(campo, "UNKNOWN")
        if v not in aceitos:
            imp.append("%s=%r" % (campo, v))
    if c.get("licenca_classe", "UNKNOWN") in man.LICENCAS_BLOQUEANTES:
        imp.append("licenca_classe=%r bloqueante" % c.get("licenca_classe"))
    if c.get("overlap") == "DETECTADO":
        imp.append("overlap DETECTADO")
    if any(p in c.get("nome", "").lower() for p in PROIBIDOS_COMO_TEST):
        imp.append("dataset proibido como TEST por decisao de projeto")
    return (not imp, imp)


def conferir(candidatos) -> list:
    """Recalcula o status: nenhum A sobrevive sem os quatro eixos."""
    saida = []
    for c in candidatos:
        c = dict(c)
        pode, imp = pode_ser_A(c)
        if c.get("status") == "A" and not pode:
            c["status_pedido"] = "A"
            c["status"] = "B"
            c["rebaixado_por"] = imp
        c["pode_ser_A"] = pode
        c["impedimentos_para_A"] = imp
        saida.append(c)
    return saida


def autoteste() -> int:
    falhas = []
    base = {"nome": "S", "independencia": "DEMONSTRAVEL", "ontologia": "COMPATIVEL",
            "anotacao_tipo": "HUMANA_MANUAL", "acesso": "ABERTO",
            "licenca_classe": "ABERTA_ATRIBUICAO", "overlap": "NAO DETECTADO"}

    # 1. controle POSITIVO: um candidato que cumpre tudo PODE ser A.
    #    Sem isto a regra poderia estar reprovando tudo e passaria sem provar nada.
    if not pode_ser_A(base)[0]:
        falhas.append("a regra reprovou um candidato que cumpre todos os eixos")

    # 2. e cada eixo, quebrado sozinho, tem de impedir
    for campo, valor in (("independencia", "INCONCLUSIVA"), ("ontologia", "PARCIAL"),
                         ("ontologia", "UNKNOWN"), ("anotacao_tipo", "AUTOMATICA"),
                         ("anotacao_tipo", "DERIVADA_DE_MODELO"), ("anotacao_tipo", "UNKNOWN"),
                         ("acesso", "EULA"), ("licenca_classe", "UNKNOWN"),
                         ("licenca_classe", "CONFLITO"), ("licenca_classe", "RESTRITA"),
                         ("overlap", "DETECTADO")):
        if pode_ser_A({**base, campo: valor})[0]:
            falhas.append("aceitou A com %s=%r" % (campo, valor))

    # 3. os quatro proibidos nunca passam, mesmo com ficha perfeita
    for p in PROIBIDOS_COMO_TEST:
        if pode_ser_A({**base, "nome": "%s dataset" % p})[0]:
            falhas.append("aceitou A para dataset proibido: %s" % p)

    # 4. conferir() REBAIXA um A indevido em vez de deixar passar
    r = conferir([{**base, "nome": "X", "status": "A", "independencia": "INCONCLUSIVA"}])
    if r[0]["status"] != "B" or r[0].get("status_pedido") != "A":
        falhas.append("conferir() nao rebaixou um A sem evidencia: %s" % r[0])

    # 5. e NAO rebaixa um A legitimo
    r2 = conferir([{**base, "nome": "Y", "status": "A"}])
    if r2[0]["status"] != "A":
        falhas.append("conferir() rebaixou um A legitimo")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste classificar: %d verificacoes, %d falhas" % (5, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--entrada", default=str(SAIDA / "candidatos_brutos.json"))
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    p = Path(a.entrada)
    if not p.exists():
        print("entrada ausente:", p)
        return 1
    doc = json.loads(p.read_text(encoding="utf-8"))
    cands = conferir(doc["candidatos"])
    por = Counter(c["status"] for c in cands)

    print("CANDIDATOS: %d" % len(cands))
    for s in ("A", "B", "C", "D", "E"):
        print("   %s: %d" % (s, por.get(s, 0)))
    print()
    for c in sorted(cands, key=lambda x: (x["status"], x["nome"])):
        if c["status"] in ("A", "B"):
            print("   [%s] %-40s %s" % (c["status"], c["nome"][:40],
                                        ", ".join(c["impedimentos_para_A"])[:60]))
    rebaixados = [c for c in cands if c.get("status_pedido") == "A"]
    if rebaixados:
        print()
        print("REBAIXADOS de A:")
        for c in rebaixados:
            print("   %-40s %s" % (c["nome"][:40], "; ".join(c["rebaixado_por"])))

    if a.escrever:
        SAIDA.mkdir(parents=True, exist_ok=True)
        (SAIDA / "candidatos.json").write_text(json.dumps(
            {**{k: v for k, v in doc.items() if k != "candidatos"},
             "regra_A": ("evidencia POSITIVA em independencia=DEMONSTRAVEL, "
                         "ontologia=COMPATIVEL, anotacao humana, acesso aberto/cadastro; "
                         "licenca nao bloqueante; sem overlap detectado; e nao ser um dos "
                         "quatro proibidos por decisao de projeto"),
             "por_status": dict(por), "candidatos": cands},
            indent=1, ensure_ascii=False), encoding="utf-8")
        print("\nescrito:", SAIDA / "candidatos.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
