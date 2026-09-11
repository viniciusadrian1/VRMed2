"""Fase 29 — a regra de aprovacao A, com independencia decomposta em cinco eixos.

POR QUE CINCO EIXOS E NAO UM

A Fase 28 tratava independencia como campo unico, e isso esconde o problema que a
propria Fase 28 descobriu: o rotulo de esofago do baseline descende de SegTHOR. Isso
nao e sobreposicao de imagem nem de paciente — e **linhagem de anotacao**, e nenhuma
comparacao de UID ou sha256 a detecta, porque nao ha imagem em comum.

Separar os eixos torna esse buraco visivel em vez de diluido:

  imagem              as imagens sao outras?
  exame               os estudos/series sao outros?
  instituicao         a origem e outra?
  anotacao            quem anotou nao anotou o nosso dado?
  linhagem_anotacao   o ROTULO nao descende de modelo que tocou o nosso pipeline?

Um candidato so e A com os CINCO em DEMONSTRADA. "PLAUSIVEL" nao basta, e
"NAO DETECTADO" nunca vira "DEMONSTRADA" — regra que o projeto carrega desde a Fase 18.

  python -m scripts.validation.fase29.decisao --autoteste
  python -m scripts.validation.fase29.decisao --escrever
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
SAIDA = RAIZ / "docs" / "overnight" / "phase29"
DECISAO = RAIZ / "docs" / "FASE29-DECISAO-TEST.json"

EIXOS_INDEPENDENCIA = ("imagem", "exame", "instituicao", "anotacao", "linhagem_anotacao")

# Os cinco requisitos do pedido, em codigo.
ONTOLOGIA_OK = ("COMPATIVEL",)
ANOTACAO_OK = ("HUMANA_MANUAL", "HUMANA_REVISADA")
ACESSO_OK = ("ABERTO", "CADASTRO")
PROIBIDOS_COMO_TEST = ("lctsc", "lynos", "nsclc-radiomics", "segthor")


def pode_ser_A(c: dict) -> tuple:
    """Devolve (pode, impedimentos). O teste reaplica exatamente esta funcao."""
    imp = []

    # 1. independencia suficiente — os CINCO eixos demonstrados
    ind = c.get("independencia") or {}
    for eixo in EIXOS_INDEPENDENCIA:
        v = str(ind.get(eixo, "INCONCLUSIVO")).upper()
        if v != "DEMONSTRADA":
            imp.append("independencia.%s=%s" % (eixo, v or "AUSENTE"))

    # 2. ontologia compativel
    if c.get("ontologia") not in ONTOLOGIA_OK:
        imp.append("ontologia=%s" % c.get("ontologia"))

    # 3. anotacao humana documentada
    if c.get("anotacao_tipo") not in ANOTACAO_OK:
        imp.append("anotacao_tipo=%s" % c.get("anotacao_tipo"))

    # 4. acesso viavel
    if c.get("acesso") not in ACESSO_OK:
        imp.append("acesso=%s" % c.get("acesso"))

    # 5. licenca nao bloqueante
    if c.get("licenca_classe") in man.LICENCAS_BLOQUEANTES:
        imp.append("licenca_classe=%s" % c.get("licenca_classe"))

    # e os tres impedimentos adicionais do pedido
    if str(c.get("overlap", "")).upper() in ("DETECTADO", "CONFIRMADO", "IDENTIDADE"):
        imp.append("overlap=%s" % c.get("overlap"))
    if c.get("conflito_metodologico_critico"):
        imp.append("conflito metodologico critico")
    if any(p in str(c.get("nome", "")).lower() for p in PROIBIDOS_COMO_TEST):
        imp.append("proibido como TEST por decisao de projeto")

    return (not imp, imp)


def conferir(candidatos) -> list:
    """Rebaixa qualquer A que nao cumpra a regra, e registra por que."""
    out = []
    for c in candidatos:
        c = dict(c)
        pode, imp = pode_ser_A(c)
        if c.get("status") == "A" and not pode:
            c["status_pedido"], c["status"] = "A", "B"
            c["rebaixado_por"] = imp
        c["pode_ser_A"], c["impedimentos_para_A"] = pode, imp
        out.append(c)
    return out


def _perfeito(**kw):
    base = {
        "nome": "SINTETICO",
        "independencia": {e: "DEMONSTRADA" for e in EIXOS_INDEPENDENCIA},
        "ontologia": "COMPATIVEL", "anotacao_tipo": "HUMANA_MANUAL",
        "acesso": "ABERTO", "licenca_classe": "ABERTA_ATRIBUICAO",
        "overlap": "NAO DETECTADO",
    }
    base.update(kw)
    return base


def autoteste() -> int:
    falhas = []

    # 1. candidato perfeito -> A  (sem isto a regra poderia reprovar tudo)
    if not pode_ser_A(_perfeito())[0]:
        falhas.append("candidato perfeito foi reprovado: %s" % pode_ser_A(_perfeito())[1])

    # 2. sem licenca -> nao A
    for lic in ("UNKNOWN", "CONFLITO", "RESTRITA", "ABERTA_SEM_DERIVADAS"):
        if pode_ser_A(_perfeito(licenca_classe=lic))[0]:
            falhas.append("aceitou A com licenca %s" % lic)

    # 3. ontologia desconhecida -> nao A
    for o in ("UNKNOWN", "PARCIAL", "INCOMPATIVEL"):
        if pode_ser_A(_perfeito(ontologia=o))[0]:
            falhas.append("aceitou A com ontologia %s" % o)

    # 4. anotacao desconhecida -> nao A
    for a in ("UNKNOWN", "AUTOMATICA", "SEMIAUTOMATICA", "DERIVADA_DE_MODELO"):
        if pode_ser_A(_perfeito(anotacao_tipo=a))[0]:
            falhas.append("aceitou A com anotacao %s" % a)

    # 5. independencia inconclusiva -> nao A, EIXO POR EIXO.
    #    E o teste que mais importa: basta UM eixo fraco para impedir.
    for eixo in EIXOS_INDEPENDENCIA:
        for v in ("INCONCLUSIVO", "PLAUSIVEL", "NAO DEMONSTRADA", "NAO VERIFICAVEL"):
            ind = {e: "DEMONSTRADA" for e in EIXOS_INDEPENDENCIA}
            ind[eixo] = v
            if pode_ser_A(_perfeito(independencia=ind))[0]:
                falhas.append("aceitou A com independencia.%s=%s" % (eixo, v))

    # 6. overlap confirmado -> nao A
    for ov in ("DETECTADO", "CONFIRMADO", "IDENTIDADE"):
        if pode_ser_A(_perfeito(overlap=ov))[0]:
            falhas.append("aceitou A com overlap %s" % ov)

    # 7. acesso inviavel -> nao A
    for ac in ("EULA", "DUA", "RESTRITO", "INDISPONIVEL", "UNKNOWN"):
        if pode_ser_A(_perfeito(acesso=ac))[0]:
            falhas.append("aceitou A com acesso %s" % ac)

    # 8. conflito metodologico critico -> nao A
    if pode_ser_A(_perfeito(conflito_metodologico_critico=True))[0]:
        falhas.append("aceitou A com conflito metodologico critico")

    # 9. os quatro proibidos nunca sobem, mesmo com ficha perfeita
    for p in PROIBIDOS_COMO_TEST:
        if pode_ser_A(_perfeito(nome="%s 2019" % p))[0]:
            falhas.append("aceitou A para proibido: %s" % p)

    # 10. conferir() rebaixa um A indevido e preserva um legitimo
    r = conferir([_perfeito(nome="X", status="A",
                            independencia={**{e: "DEMONSTRADA" for e in EIXOS_INDEPENDENCIA},
                                           "linhagem_anotacao": "INCONCLUSIVO"})])
    if r[0]["status"] != "B" or r[0].get("status_pedido") != "A":
        falhas.append("nao rebaixou um A sem linhagem demonstrada")
    if conferir([_perfeito(nome="Y", status="A")])[0]["status"] != "A":
        falhas.append("rebaixou um A legitimo")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste decisao: %d verificacoes, %d falhas" % (10, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--entrada", default=str(SAIDA / "candidatos_brutos.json"))
    ap.add_argument("--quando", default="2026-09-10T00:00:00Z")
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
    aprovados = [c["nome"] for c in cands if c["status"] == "A"]

    ent = man.carregar(RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl")
    n_test = sum(1 for e in ent if e["split"] == "test")

    print("CANDIDATOS: %d" % len(cands))
    for s in ("A", "B", "C", "D", "E"):
        print("   %s: %d" % (s, por.get(s, 0)))
    print()
    for c in sorted(cands, key=lambda x: (x["status"], x["nome"])):
        if c["status"] in ("A", "B", "C"):
            print("   [%s] %-34s %s" % (c["status"], c["nome"][:34],
                                        "; ".join(c["impedimentos_para_A"])[:70]))
    print()
    print("TEST no manifesto: %d" % n_test)
    print("APROVADOS A: %s" % (aprovados or "NENHUM"))

    if a.escrever:
        SAIDA.mkdir(parents=True, exist_ok=True)
        (SAIDA / "candidatos.json").write_text(
            json.dumps({**{k: v for k, v in doc.items() if k != "candidatos"},
                        "por_status": dict(por), "candidatos": cands},
                       indent=1, ensure_ascii=False), encoding="utf-8")
        DECISAO.write_text(json.dumps({
            "fase": "29",
            "status": doc.get("status", "CONCLUIDA"),
            "test_atual": {"n": n_test, "estado": "PROTEGIDO"},
            "candidatos": [{"nome": c["nome"], "status": c["status"],
                            "impedimentos_para_A": c["impedimentos_para_A"]} for c in cands],
            "aprovados_A": aprovados,
            "pendencias": doc.get("pendencias", []),
            "decisao": doc.get("decisao", ""),
            "regra_A": ("cinco eixos de independencia DEMONSTRADA (imagem, exame, instituicao, "
                        "anotacao, linhagem_anotacao) + ontologia COMPATIVEL + anotacao humana "
                        "documentada + acesso viavel + licenca nao bloqueante, sem overlap e "
                        "sem conflito metodologico critico"),
            "timestamp": a.quando,
        }, indent=1, ensure_ascii=False), encoding="utf-8")
        print("\nescrito:", SAIDA / "candidatos.json")
        print("escrito:", DECISAO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
