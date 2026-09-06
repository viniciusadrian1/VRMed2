"""Fase 21.14 — treze mutantes plantados nas guardas, e a exigencia de que morram.

O ARGUMENTO
Uma suite verde prova que o codigo RODA. Nao prova que ele VE. A unica forma de
provar que ve e quebrar a guarda de proposito e exigir que a suite caia — se ela
continuar verde com a guarda quebrada, ela nunca esteve testando aquela guarda.

O pedido da Fase 21.14 e explicito: pelo menos 5 mutacoes em validators, 5 em
loader e 3 em hashing/snapshot. Sao 13, e cada uma nomeia QUAL teste deveria cair.

COMO
Cada mutante roda numa COPIA da arvore `scripts/` num diretorio temporario, com
uma substituicao textual, em subprocesso proprio. O repositorio real nunca e
tocado — nem por um instante, nem "com restauracao depois". Um mutante que
escreve no repo e um mutante que pode ficar la se a execucao morrer no meio.

UM MUTANTE QUE SOBREVIVE NAO E UM BUG DO MUTANTE: e um buraco na suite.

  python -m scripts.validation.fase21.mutacao --autoteste
  python -m scripts.validation.fase21.mutacao
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase21"
PY = RAIZ / ".venv-pipeline" / "Scripts" / "python.exe"

MAN = "scripts/validation/baseline_v1/manifesto.py"
PLANO = "scripts/validation/baseline_v1/plano.py"
FUNIL = "scripts/validation/fase21/funil.py"

# O comando que cada mutante tem de derrubar. `funil` cobre as fixtures reais e os
# 14 casos; `manifesto` cobre o esquema; `suite` cobre os testes da Fase 19.
ALVOS = {
    "funil": ["-m", "scripts.validation.fase21.funil", "--autoteste"],
    "manifesto": ["-m", "scripts.validation.baseline_v1.manifesto", "--autoteste"],
    "suite": ["tests/test_baseline_v1.py"],
}

MUTANTES = [
    # ---------------------------------------------------------- validators (5)
    {"id": "V1", "grupo": "validators", "arquivo": MAN, "alvo": "funil",
     "o_que": "validar_vazamento devolve lista vazia",
     "de": 'def validar_vazamento(entradas) -> list:\n    """',
     "para": 'def validar_vazamento(entradas) -> list:\n    return []\n    """',
     "deveria_derrubar": "casos 9, 10, 11 e 12"},
    {"id": "V2", "grupo": "validators", "arquivo": MAN, "alvo": "funil",
     "o_que": "validar_licenca devolve lista vazia",
     "de": 'def validar_licenca(e: dict) -> list:\n    """',
     "para": 'def validar_licenca(e: dict) -> list:\n    return []\n    """',
     "deveria_derrubar": "casos 7 e 8"},
    {"id": "V3", "grupo": "validators", "arquivo": MAN, "alvo": "manifesto",
     "o_que": "campos obrigatorios ausentes deixam de ser detectados",
     "de": "    faltando = [c for c in CAMPOS if c not in e]",
     "para": "    faltando = []",
     "deveria_derrubar": "campo obrigatorio ausente"},
    {"id": "V4", "grupo": "validators", "arquivo": MAN, "alvo": "manifesto",
     "o_que": "sha256 malformado passa",
     "de": "            if len(v) != 64 or any(c not in \"0123456789abcdef\" for c in v.lower()):",
     "para": "            if False:",
     "deveria_derrubar": "sha256 invalido"},
    {"id": "V5", "grupo": "validators", "arquivo": PLANO, "alvo": "funil",
     "o_que": "validar_alvo aprova qualquer coisa (ontologia desligada)",
     "de": "    return {\"medidas\": m, \"ontologia\": v, \"problemas\": problemas, \"aprovado\": not problemas}",
     "para": "    return {\"medidas\": m, \"ontologia\": v, \"problemas\": [], \"aprovado\": True}",
     "deveria_derrubar": "casos 2 e 13"},

    # -------------------------------------------------------------- loader (5)
    {"id": "L1", "grupo": "loader", "arquivo": MAN, "alvo": "funil",
     "o_que": "carregar_particao sem a checagem de permissao",
     "de": "    if split not in PERMISSOES[contexto]:",
     "para": "    if False:",
     "deveria_derrubar": "caso 14"},
    {"id": "L2", "grupo": "loader", "arquivo": MAN, "alvo": "manifesto",
     "o_que": "treino passa a poder ler test",
     "de": '    "treino":    ("train",),',
     "para": '    "treino":    ("train", "validation", "test"),',
     "deveria_derrubar": "AcessoIndevido do contexto treino"},
    {"id": "L3", "grupo": "loader", "arquivo": MAN, "alvo": "manifesto",
     "o_que": "validacao passa a poder ler test",
     "de": '    "validacao": ("train", "validation"),',
     "para": '    "validacao": ("train", "validation", "test"),',
     "deveria_derrubar": "AcessoIndevido do contexto validacao"},
    {"id": "L4", "grupo": "loader", "arquivo": MAN, "alvo": "manifesto",
     "o_que": "contexto desconhecido deixa de ser recusado",
     "de": "    if contexto not in PERMISSOES:",
     "para": "    if False and contexto not in PERMISSOES:",
     "deveria_derrubar": "contexto invalido"},
    {"id": "L5", "grupo": "loader", "arquivo": MAN, "alvo": "manifesto",
     "o_que": "carregar_particao devolve TUDO, ignorando o split pedido",
     "de": '    return [e for e in entradas if e["split"] == split]',
     "para": "    return list(entradas)",
     "deveria_derrubar": "contagem por particao"},

    # ---------------------------------------------------- hashing/snapshot (3)
    {"id": "H1", "grupo": "hashing", "arquivo": MAN, "alvo": "funil",
     "o_que": "verificar_congelamento sempre diz INTACTO",
     "de": '    igual = atual == snapshot["sha256_manifesto"]',
     "para": "    igual = True",
     "deveria_derrubar": "caso 6"},
    {"id": "H2", "grupo": "hashing", "arquivo": MAN, "alvo": "manifesto",
     "o_que": "a serializacao canonica deixa de ordenar por case_id",
     "de": "    for e in sorted(entradas, key=lambda x: x[\"case_id\"]):",
     "para": "    for e in entradas:",
     "deveria_derrubar": "hash independente da ordem de insercao"},
    {"id": "H3", "grupo": "hashing", "arquivo": MAN, "alvo": "manifesto",
     "o_que": "congelar aceita manifesto invalido",
     "de": '        raise ManifestoInvalido("nao se congela manifesto invalido:\\n  " + "\\n  ".join(v["erros"]))',
     "para": "        pass",
     "deveria_derrubar": "recusa de congelar manifesto com vazamento"},
]


def _rodar(arvore: Path, alvo: str) -> tuple:
    cmd = [str(PY)] + ALVOS[alvo]
    p = subprocess.run(cmd, cwd=str(arvore), capture_output=True, text=True,
                       timeout=900, env={"PYTHONIOENCODING": "utf-8",
                                         "PATH": "", "SYSTEMROOT": "C:\\Windows"})
    return p.returncode, (p.stdout or "")[-400:] + (p.stderr or "")[-200:]


def _preparar(base: Path) -> Path:
    """Copia o que a suite PRECISA LER, nao so o que ela executa.

    A primeira versao copiava so `scripts/` e `tests/`. O controle negativo pegou:
    `test_17` (acrescentado na Fase 21) le
    `docs/VRMED-ESOPHAGUS-DATASET-V2-PROPOSTA.md` para garantir que a V2 nao foi
    promovida em silencio — e numa arvore sem `docs/` ele falha por ausencia de
    arquivo, nao por mutacao. O controle recusou-se a interpretar os mutantes contra
    uma arvore quebrada, que e exatamente para isso que ele existe.

    `docs/` entra apenas com os .md (os .json e .csv de medicao sao grandes e a suite
    nao os le).
    """
    arvore = base / "arvore"
    arvore.mkdir(parents=True, exist_ok=True)
    shutil.copytree(RAIZ / "scripts", arvore / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(RAIZ / "tests", arvore / "tests",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (arvore / "docs").mkdir(exist_ok=True)
    for md in (RAIZ / "docs").glob("*.md"):
        shutil.copy2(md, arvore / "docs" / md.name)
    return arvore


def executar() -> dict:
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)
        arvore = _preparar(base)

        # CONTROLE NEGATIVO, antes de tudo: a arvore intacta tem de passar. Sem
        # isto, uma copia quebrada faria os 13 mutantes "morrerem" por outro motivo
        # e a suite pareceria excelente sem testar nada.
        limpos = {}
        for alvo in ALVOS:
            rc, saida = _rodar(arvore, alvo)
            limpos[alvo] = {"returncode": rc, "ok": rc == 0, "saida": saida[-200:]}
        if not all(v["ok"] for v in limpos.values()):
            return {"erro": "arvore intacta nao passou — mutacao nao e interpretavel",
                    "controle_negativo": limpos}

        originais = {f: (arvore / f).read_text(encoding="utf-8")
                     for f in {m["arquivo"] for m in MUTANTES}}

        linhas = []
        for m in MUTANTES:
            p = arvore / m["arquivo"]
            orig = originais[m["arquivo"]]
            if m["de"] not in orig:
                linhas.append({**{k: m[k] for k in ("id", "grupo", "o_que", "alvo",
                                                    "deveria_derrubar")},
                               "aplicado": False, "derrubou": False,
                               "nota": "TRECHO NAO ENCONTRADO — o mutante nao pode ser "
                                       "aplicado; o codigo mudou e este mutante esta obsoleto"})
                continue
            p.write_text(orig.replace(m["de"], m["para"], 1), encoding="utf-8")
            try:
                rc, saida = _rodar(arvore, m["alvo"])
            finally:
                p.write_text(orig, encoding="utf-8")
            linhas.append({**{k: m[k] for k in ("id", "grupo", "o_que", "alvo",
                                                "deveria_derrubar")},
                           "aplicado": True, "derrubou": rc != 0,
                           "returncode": rc, "saida": saida[-260:]})

        # o controle negativo de novo, no fim: a arvore tem de voltar ao estado bom
        depois = {}
        for alvo in ALVOS:
            rc, _ = _rodar(arvore, alvo)
            depois[alvo] = rc == 0

        return {"controle_negativo_antes": limpos,
                "controle_negativo_depois": depois,
                "mutantes": linhas}


def autoteste() -> int:
    falhas = []
    ids = [m["id"] for m in MUTANTES]
    if len(ids) != len(set(ids)):
        falhas.append("ids de mutante repetidos")
    if len(MUTANTES) != 13:
        falhas.append("esperava 13 mutantes, ha %d" % len(MUTANTES))
    for g, n in (("validators", 5), ("loader", 5), ("hashing", 3)):
        k = sum(1 for m in MUTANTES if m["grupo"] == g)
        if k != n:
            falhas.append("grupo %s deveria ter %d mutantes, tem %d" % (g, n, k))
    for m in MUTANTES:
        if m["de"] == m["para"]:
            falhas.append(m["id"] + ": mutacao nula — de == para")
        if m["alvo"] not in ALVOS:
            falhas.append(m["id"] + ": alvo desconhecido " + m["alvo"])
    # o trecho a substituir tem de existir NO REPOSITORIO REAL, senao o mutante
    # e letra morta e a suite mediria 13 mutantes dos quais alguns nunca rodam
    for m in MUTANTES:
        txt = (RAIZ / m["arquivo"]).read_text(encoding="utf-8")
        if m["de"] not in txt:
            falhas.append(m["id"] + ": trecho nao existe em " + m["arquivo"])
    for f in falhas:
        print("FALHA:", f)
    print("autoteste mutacao: %d verificacoes, %d falhas"
          % (5 + len(MUTANTES) * 2, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    # A saida e parametro porque re-rodar a suite numa fase posterior NAO pode
    # sobrescrever o resultado historico da Fase 21 (regra 6). O caminho padrao
    # continua sendo o da Fase 21, entao nada muda para quem ja usava.
    ap.add_argument("--saida", default=str(SAIDA / "mutacao.json"))
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    print("plantando %d mutantes numa COPIA da arvore (o repo nao e tocado)...\n"
          % len(MUTANTES))
    r = executar()
    if "erro" in r:
        print("ABORTADO:", r["erro"])
        print(json.dumps(r["controle_negativo"], indent=1)[:800])
        return 1

    print("controle negativo (arvore intacta): " +
          ", ".join("%s=%s" % (k, "OK" if v["ok"] else "FALHOU")
                    for k, v in r["controle_negativo_antes"].items()))
    print()
    print("%-4s %-11s %-52s %-10s %s" % ("id", "grupo", "mutacao", "alvo", "resultado"))
    for m in r["mutantes"]:
        estado = ("MORREU" if m["derrubou"] else
                  ("SOBREVIVEU" if m["aplicado"] else "NAO APLICADO"))
        print("%-4s %-11s %-52s %-10s %s"
              % (m["id"], m["grupo"], m["o_que"][:52], m["alvo"], estado))
        if not m["derrubou"]:
            print("      -> deveria derrubar: %s | %s"
                  % (m["deveria_derrubar"], m.get("nota", m.get("saida", ""))[:120]))

    mortos = sum(1 for m in r["mutantes"] if m["derrubou"])
    print()
    print("MUTANTES MORTOS: %d/%d" % (mortos, len(r["mutantes"])))
    print("controle negativo depois: " +
          ", ".join("%s=%s" % (k, "OK" if v else "FALHOU")
                    for k, v in r["controle_negativo_depois"].items()))

    destino = Path(a.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({
        "fase": 21.14,
        "mortos": mortos, "total": len(r["mutantes"]),
        "por_grupo": {g: {"total": sum(1 for m in r["mutantes"] if m["grupo"] == g),
                          "mortos": sum(1 for m in r["mutantes"]
                                        if m["grupo"] == g and m["derrubou"])}
                      for g in ("validators", "loader", "hashing")},
        **r,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print("escrito:", destino)
    return 0 if mortos == len(r["mutantes"]) else 1


if __name__ == "__main__":
    sys.exit(main())
