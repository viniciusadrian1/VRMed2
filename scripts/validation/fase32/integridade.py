"""Fase 32 — impressao digital do estado, tirada ANTES e DEPOIS da fase.

POR QUE ESTE MODULO EXISTE, E POR QUE ELE E O PRIMEIRO

Tres vezes neste projeto (Fases 24, 29 e 31) um script de fase nova sobrescreveu um
artefato historico. Nas tres o dano so foi visto porque alguem foi conferir. A Fase 31
respondeu com um parametro `--saida`; o incidente daquela fase mostrou que criar o
parametro nao basta se ele nao for LIGADO ao caminho de escrita.

Este modulo e a resposta seguinte: em vez de confiar que cada script se comporta, a fase
tira uma foto do que NAO pode mudar, faz o trabalho, tira outra foto, e compara. Qualquer
divergencia nao declarada e FALHA da fase — nao aviso.

O QUE E FOTOGRAFADO

Conteudo, nao data de modificacao. `sha256` de arquivo e `sha256` canonico do manifesto
(ordem de caso e de chave fixas), porque os dois respondem perguntas diferentes: o
primeiro pega ate reescrita byte-identica-em-conteudo-mas-nao-em-bytes; o segundo pega
mudanca de conteudo mesmo que alguem reformate o arquivo.

Diretorios entram como (contagem, lista ordenada de nomes, sha256 de cada arquivo). Os
`.pth` de 245 MB entram inteiros: um checkpoint alterado e exatamente o tipo de dano que
uma contagem de arquivos nao veria.

  python -m scripts.validation.fase32.integridade --autoteste
  python -m scripts.validation.fase32.integridade --gravar docs/overnight/phase32/antes.json
  python -m scripts.validation.fase32.integridade --comparar A.json B.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]

# Cada alvo e (rotulo, caminho relativo a RAIZ, tipo). O rotulo e o que aparece no
# relatorio; o caminho e o que e lido. Nada aqui e glob solto: um glob que nao casa
# devolve lista vazia e passaria despercebido, entao diretorio inteiro e "arvore".
ALVOS = [
    # ---- V1: congelada na Fase 25, imutavel para sempre
    ("v1_manifesto", "docs/VRMED-ESOFAGO-MANIFESTO-V1.jsonl", "manifesto"),
    ("v1_snapshot", "docs/VRMED-ESOFAGO-SNAPSHOT-V1.json", "arquivo"),
    ("v1_pool16", "docs/FASE24-POOL-16.json", "arquivo"),
    ("v1_prerregistro", "docs/BASELINE-ESOPHAGUS-VRMED-V1.md", "arquivo"),
    # ---- V2: congelada na Fase 31, imutavel a partir dela
    ("v2_manifesto", "docs/VRMED-ESOPHAGUS-MANIFESTO-V2.jsonl", "manifesto"),
    ("v2_snapshot", "docs/VRMED-ESOPHAGUS-SNAPSHOT-V2.json", "arquivo"),
    ("v2_pool", "docs/VRMED-ESOPHAGUS-POOL-V2.json", "arquivo"),
    ("v2_regra_split", "docs/VRMED-SPLIT-RULE-V2.md", "arquivo"),
    # ---- ontologia e esquema, dos quais tudo depende
    ("ontologia", "docs/ESOPHAGUS-ONTOLOGY-V1.md", "arquivo"),
    ("prerregistro_v2", "docs/BASELINE-ESOPHAGUS-VRMED-V2.md", "arquivo"),
    # ---- Fase 26: o run de 1000 epocas, interrompido e preservado como esta
    ("f26_results", ".clinica-dados/fase26/nnUNet_results", "arvore"),
    ("f26_raw", ".clinica-dados/fase26/nnUNet_raw", "arvore"),
    ("f26_holdout", ".clinica-dados/fase26/validation_holdout", "arvore"),
    # ---- Fase 26B: o experimento de 250 epocas, 5 folds completos
    ("f26b_results", ".clinica-dados/fase26b/nnUNet_results", "arvore"),
    ("f26b_raw", ".clinica-dados/fase26b/nnUNet_raw", "arvore"),
    ("f26b_preprocessed", ".clinica-dados/fase26b/nnUNet_preprocessed", "arvore"),
    ("f26b_predicoes", ".clinica-dados/fase26b/predicoes_holdout", "arvore"),
    # ---- as avaliacoes ja publicadas
    ("f27_avaliacoes", "docs/overnight/phase27", "arvore"),
    ("f26b_curvas", "docs/overnight/phase26b/curvas.json", "arquivo"),
]

# Arquivos historicos que ja foram sobrescritos uma vez. Nao basta estarem na lista
# acima: aqui declara-se o CONTEUDO minimo que cada um tem de continuar tendo, para
# que a checagem falhe por motivo legivel e nao so por hash diferente.
SENTINELAS = [
    ("docs/overnight/phase23/ingestao_real.json", "HM10395", 5),
    ("docs/overnight/phase21/mutacao.json", None, None),
    ("docs/overnight/phase23/aquisicao.json", None, None),
]


def sha256_arquivo(p: Path) -> str:
    return man.sha256_arquivo(p)


def _foto_arquivo(p: Path) -> dict:
    if not p.exists():
        return {"existe": False}
    return {"existe": True, "bytes": p.stat().st_size, "sha256": sha256_arquivo(p)}


def _foto_manifesto(p: Path) -> dict:
    """Duas identidades: a do arquivo e a do conteudo canonico.

    Sao diferentes de proposito. Reordenar as linhas do JSONL muda a primeira e nao a
    segunda; trocar um valor muda as duas. Guardar so uma perderia um dos dois casos.
    """
    f = _foto_arquivo(p)
    if not f["existe"]:
        return f
    ent = man.carregar(p)
    f["n_casos"] = len(ent)
    f["sha256_canonico"] = man.sha256_texto(man._canonico(ent))
    f["split"] = {s: sum(1 for e in ent if e["split"] == s)
                  for s in ("train", "validation", "test")}
    return f


def _foto_arvore(d: Path) -> dict:
    if not d.exists():
        return {"existe": False}
    arquivos = sorted(p for p in d.rglob("*") if p.is_file())
    return {
        "existe": True,
        "n_arquivos": len(arquivos),
        "bytes_total": sum(p.stat().st_size for p in arquivos),
        "arquivos": {str(p.relative_to(d)).replace("\\", "/"): sha256_arquivo(p)
                     for p in arquivos},
    }


def tirar_foto() -> dict:
    foto = {"alvos": {}}
    for rotulo, rel, tipo in ALVOS:
        p = RAIZ / rel
        if tipo == "manifesto":
            foto["alvos"][rotulo] = {"caminho": rel, **_foto_manifesto(p)}
        elif tipo == "arvore":
            foto["alvos"][rotulo] = {"caminho": rel, **_foto_arvore(p)}
        else:
            foto["alvos"][rotulo] = {"caminho": rel, **_foto_arquivo(p)}

    foto["sentinelas"] = {}
    for rel, marcador, n in SENTINELAS:
        p = RAIZ / rel
        d = {"existe": p.exists(), **({} if not p.exists() else _foto_arquivo(p))}
        if p.exists() and marcador is not None:
            d["ocorrencias_%s" % marcador] = p.read_text(encoding="utf-8").count(marcador)
            d["esperado"] = n
        foto["sentinelas"][rel] = d

    foto["git"] = _git()
    return foto


def _git() -> dict:
    def rodar(*a):
        try:
            return subprocess.run(["git", *a], cwd=RAIZ, capture_output=True,
                                  text=True, timeout=60).stdout.strip()
        except Exception as e:  # pragma: no cover - ambiente sem git
            return "ERRO: %s" % e
    return {
        "head": rodar("rev-parse", "HEAD"),
        "branch": rodar("rev-parse", "--abbrev-ref", "HEAD"),
        "sujo": rodar("status", "--porcelain"),
    }


def comparar(antes: dict, depois: dict) -> dict:
    """Divergencias entre duas fotos. Lista vazia = nada historico mudou."""
    div = []
    for rotulo in sorted(set(antes["alvos"]) | set(depois["alvos"])):
        a = antes["alvos"].get(rotulo)
        b = depois["alvos"].get(rotulo)
        if a is None or b is None:
            div.append({"alvo": rotulo, "o_que": "alvo apareceu ou sumiu da lista"})
            continue
        if a.get("existe") != b.get("existe"):
            div.append({"alvo": rotulo, "o_que": "existencia mudou",
                        "antes": a.get("existe"), "depois": b.get("existe")})
            continue
        if not a.get("existe"):
            continue
        for campo in ("sha256", "sha256_canonico", "n_casos", "split", "n_arquivos"):
            if campo in a or campo in b:
                if a.get(campo) != b.get(campo):
                    div.append({"alvo": rotulo, "o_que": campo,
                                "antes": a.get(campo), "depois": b.get(campo)})
        if "arquivos" in a:
            na, nb = set(a["arquivos"]), set(b["arquivos"])
            for nome in sorted(nb - na):
                div.append({"alvo": rotulo, "o_que": "arquivo novo", "arquivo": nome})
            for nome in sorted(na - nb):
                div.append({"alvo": rotulo, "o_que": "arquivo sumiu", "arquivo": nome})
            for nome in sorted(na & nb):
                if a["arquivos"][nome] != b["arquivos"][nome]:
                    div.append({"alvo": rotulo, "o_que": "conteudo mudou",
                                "arquivo": nome})

    for rel in sorted(set(antes["sentinelas"]) | set(depois["sentinelas"])):
        a = antes["sentinelas"].get(rel, {})
        b = depois["sentinelas"].get(rel, {})
        if a != b:
            div.append({"alvo": "sentinela:%s" % rel, "o_que": "sentinela mudou",
                        "antes": a, "depois": b})
    return {"divergencias": div, "intacto": not div, "n_divergencias": len(div)}


def autoteste() -> int:
    import tempfile
    falhas = []

    foto = tirar_foto()

    # 1. os alvos que a fase declara imutaveis existem de verdade. Uma foto de alvo
    #    inexistente compararia "nao existe" com "nao existe" e passaria sempre.
    ausentes = [r for r, d in foto["alvos"].items() if not d.get("existe")]
    if ausentes:
        falhas.append("alvos ausentes (a foto nao provaria nada sobre eles): %s" % ausentes)

    # 2. o manifesto V1 continua com 16 casos e o split congelado 10/6/0
    v1 = foto["alvos"]["v1_manifesto"]
    if v1.get("n_casos") != 16 or v1.get("split") != {"train": 10, "validation": 6, "test": 0}:
        falhas.append("V1 divergiu: %s %s" % (v1.get("n_casos"), v1.get("split")))

    # 3. e o V2 com 46 e 32/14/0
    v2 = foto["alvos"]["v2_manifesto"]
    if v2.get("n_casos") != 46 or v2.get("split") != {"train": 32, "validation": 14, "test": 0}:
        falhas.append("V2 divergiu: %s %s" % (v2.get("n_casos"), v2.get("split")))

    # 4. o sha256 canonico do V2 e o que a Fase 31 congelou
    esperado = "f4bd480e8f8046923a8990096d40832145fb405f1a84ca85e8f3be6e6d20f60b"
    if v2.get("sha256_canonico") != esperado:
        falhas.append("sha256 canonico do V2 nao e o congelado: %s" % v2.get("sha256_canonico"))

    # 5. a sentinela da Fase 23 continua com os 5 casos que a Fase 31 quase apagou
    s = foto["sentinelas"]["docs/overnight/phase23/ingestao_real.json"]
    if s.get("ocorrencias_HM10395", 0) < 5:
        falhas.append("a sentinela da Fase 23 perdeu casos: %s" % s)

    # 6. comparar(foto, foto) e vazio
    if not comparar(foto, foto)["intacto"]:
        falhas.append("comparar() acusou divergencia entre uma foto e ela mesma")

    # 7. CONTROLE POSITIVO — se um sha256 mudar, comparar() TEM de acusar.
    #    Sem isto, um comparador que sempre devolve "intacto" passaria em 6.
    import copy
    adulterada = copy.deepcopy(foto)
    adulterada["alvos"]["v1_manifesto"]["sha256"] = "0" * 64
    r = comparar(foto, adulterada)
    if r["intacto"] or not any(d["alvo"] == "v1_manifesto" for d in r["divergencias"]):
        falhas.append("comparar() nao viu um sha256 adulterado")

    # 8. e se um arquivo DENTRO de uma arvore mudar, tambem
    adulterada = copy.deepcopy(foto)
    arv = adulterada["alvos"]["f26b_results"]
    if arv.get("arquivos"):
        primeiro = sorted(arv["arquivos"])[0]
        arv["arquivos"][primeiro] = "0" * 64
        r = comparar(foto, adulterada)
        if not any(d.get("arquivo") == primeiro for d in r["divergencias"]):
            falhas.append("comparar() nao viu um arquivo alterado dentro da arvore")
    else:
        falhas.append("a arvore f26b_results esta vazia; a checagem 8 nao prova nada")

    # 9. arquivo novo dentro de uma arvore tambem e divergencia. Escrever DENTRO de
    #    uma arvore historica e exatamente o incidente que este modulo existe para pegar.
    adulterada = copy.deepcopy(foto)
    adulterada["alvos"]["f26b_results"]["arquivos"]["intruso.txt"] = "1" * 64
    if not any(d.get("arquivo") == "intruso.txt"
               for d in comparar(foto, adulterada)["divergencias"]):
        falhas.append("comparar() nao viu um arquivo novo dentro da arvore")

    # 10. as fotos sobrevivem a ida e volta por JSON (e assim que sao guardadas)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "f.json"
        p.write_text(json.dumps(foto, ensure_ascii=False), encoding="utf-8")
        if not comparar(json.loads(p.read_text(encoding="utf-8")), foto)["intacto"]:
            falhas.append("a foto nao sobreviveu a serializacao JSON")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste integridade: %d verificacoes, %d falhas" % (10, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--gravar", help="caminho do JSON da foto")
    ap.add_argument("--comparar", nargs=2, metavar=("ANTES", "DEPOIS"))
    a = ap.parse_args(argv)

    if a.autoteste:
        return autoteste()

    if a.comparar:
        antes = json.loads(Path(a.comparar[0]).read_text(encoding="utf-8"))
        depois = json.loads(Path(a.comparar[1]).read_text(encoding="utf-8"))
        r = comparar(antes, depois)
        print("INTEGRIDADE ANTES x DEPOIS")
        print("   divergencias: %d" % r["n_divergencias"])
        for d in r["divergencias"][:50]:
            print("   ! %s" % d)
        print("\nPORTAO DE INTEGRIDADE: %s" % ("OK" if r["intacto"] else "REPROVADO"))
        return 0 if r["intacto"] else 1

    foto = tirar_foto()
    print("FOTO DE INTEGRIDADE  (head %s, branch %s)"
          % (foto["git"]["head"][:8], foto["git"]["branch"]))
    for rotulo, d in foto["alvos"].items():
        if not d.get("existe"):
            print("   %-20s AUSENTE  %s" % (rotulo, d["caminho"]))
        elif "n_arquivos" in d:
            print("   %-20s %4d arquivos  %8.1f MB  %s"
                  % (rotulo, d["n_arquivos"], d["bytes_total"] / 1e6, d["caminho"]))
        elif "n_casos" in d:
            print("   %-20s %d casos  %s  canonico %s"
                  % (rotulo, d["n_casos"], d["split"], d["sha256_canonico"][:16]))
        else:
            print("   %-20s %s  %s" % (rotulo, d["sha256"][:16], d["caminho"]))
    print("   git sujo: %s" % (foto["git"]["sujo"] or "(nada)"))

    if a.gravar:
        p = Path(a.gravar)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(foto, indent=1, ensure_ascii=False), encoding="utf-8")
        print("\nescrito:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
