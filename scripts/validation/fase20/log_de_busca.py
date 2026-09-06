"""Fase 20.11 — o log de consultas, extraido do journal do workflow.

POR QUE ELE EXISTE
A regra que a Fase 15 estabeleceu e que este projeto nao abandonou: sem log de
consulta, um arm de busca nao e evidencia — e testemunho. Uma negativa de busca
("nao existe dataset assim") so vale se der para ver ONDE se procurou.

O log nao e digitado a mao. Ele e EXTRAIDO do journal do workflow, que grava o
retorno estruturado de cada agente. Redigitar consultas seria a mesma classe de
erro que redigitar numeros: a fonte da verdade vira a memoria de quem escreve.

COLUNAS (as pedidas em 20.11)
  query, source, url, date, candidate, result, classification, notes

  python -m scripts.validation.fase20.log_de_busca --autoteste
  python -m scripts.validation.fase20.log_de_busca --journal <caminho>
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase20"

DATA = "2026-09-06"

# Fonte inferida da propria string da consulta. Heuristica declarada: quando nao
# reconhece, devolve "outra" — nunca chuta um nome de repositorio.
FONTES = [
    (r"zenodo", "Zenodo"),
    (r"datacite", "DataCite"),
    (r"figshare", "Figshare"),
    (r"dryad", "Dryad"),
    (r"osf\.io|\bOSF\b", "OSF"),
    (r"physionet", "PhysioNet"),
    (r"midrc", "MIDRC"),
    (r"grand-challenge|grand challenge", "Grand Challenge"),
    (r"synapse", "Synapse"),
    (r"huggingface|\bHF\b", "HuggingFace"),
    (r"cancerimagingarchive|\bTCIA\b|nbia", "TCIA"),
    (r"imaging\.datacommons|\bIDC\b", "IDC"),
    (r"europepmc|europe pmc", "Europe PMC"),
    (r"pubmed|ncbi", "PubMed"),
    (r"arxiv", "arXiv"),
    (r"medrxiv|biorxiv", "medRxiv/bioRxiv"),
    (r"crossref", "Crossref"),
    (r"unpaywall", "Unpaywall"),
    (r"openalex", "OpenAlex"),
    (r"github", "GitHub"),
    (r"kaggle", "Kaggle"),
    (r"^https?://", "web"),
]


def fonte_de(consulta: str) -> str:
    s = str(consulta)
    for padrao, nome in FONTES:
        if re.search(padrao, s, re.IGNORECASE):
            return nome
    return "outra"


def url_de(consulta: str) -> str:
    m = re.search(r"https?://[^\s\"'\)\],]+", str(consulta))
    return m.group(0) if m else ""


def extrair(journal: Path) -> dict:
    """Le o journal e devolve consultas + candidatos, por arm."""
    arms, ceticos, criticos = [], [], []
    for linha in Path(journal).read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            d = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if d.get("type") != "result":
            continue
        r = d.get("result")
        if not isinstance(r, dict):
            continue
        if "candidatos" in r and "consultas" in r:
            arms.append(r)
        elif "veredito_do_cetico" in r:
            ceticos.append(r)
        elif "melhores_tres" in r or "existe_rota_plausivel" in r:
            criticos.append(r)
    return {"arms": arms, "ceticos": ceticos, "criticos": criticos}


def linhas_de_log(dados: dict) -> list:
    out = []
    # reclassificacoes do cetico, para anotar o candidato que mudou de classe
    mudou = {}
    for c in dados["ceticos"]:
        for r in c.get("reclassificados", []) or []:
            mudou[str(r.get("candidato", "")).lower()[:40]] = r

    for arm in dados["arms"]:
        nome_arm = str(arm.get("arm", ""))[:60]
        for q in arm.get("consultas", []) or []:
            out.append({
                "query": str(q)[:300], "source": fonte_de(q), "url": url_de(q),
                "date": DATA, "candidate": "", "result": "consulta registrada",
                "classification": "", "notes": nome_arm,
            })
        for c in arm.get("candidatos", []) or []:
            chave = str(c.get("nome", "")).lower()[:40]
            rc = mudou.get(chave)
            out.append({
                "query": "", "source": fonte_de(c.get("url", "")) or "outra",
                "url": str(c.get("url", ""))[:200], "date": DATA,
                "candidate": str(c.get("nome", ""))[:120],
                "result": ("licenca=%s | identidade=%s | humano=%s"
                           % (str(c.get("licenca_dataset", "?"))[:40],
                              str(c.get("identidade_disponivel", "?"))[:40],
                              str(c.get("anotacao_humana", "?"))[:40])),
                "classification": (str(rc.get("para")) + " (reclassificado de "
                                   + str(rc.get("de", "?")) + ")") if rc
                                  else str(c.get("classificacao", "")),
                "notes": (str(rc.get("motivo"))[:200] if rc
                          else str(c.get("por_que", ""))[:200]),
            })
    return out


def autoteste() -> int:
    falhas = []
    for q, esperado in (("zenodo.org/api/records?q=esophagus", "Zenodo"),
                        ("https://api.datacite.org/dois?query=esophagus", "DataCite"),
                        ("TCIA getSeries Collection=LCTSC", "TCIA"),
                        ("busca no HuggingFace por LyNoS", "HuggingFace"),
                        ("uma frase sem fonte reconhecivel", "outra")):
        if fonte_de(q) != esperado:
            falhas.append("fonte_de(%r) deu %r, esperado %r" % (q, fonte_de(q), esperado))
    if url_de("veja https://zenodo.org/records/1 para detalhes") != "https://zenodo.org/records/1":
        falhas.append("url_de nao extraiu a URL")
    if url_de("sem url nenhuma") != "":
        falhas.append("url_de inventou URL")

    # extrator: um journal sintetico com um arm, um cetico e um critico
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        j = Path(t) / "journal.jsonl"
        j.write_text("\n".join([
            json.dumps({"type": "started"}),
            json.dumps({"type": "result", "result": {
                "arm": "x", "consultas": ["zenodo esophagus"], "lacunas": [],
                "veredito": "v", "achados": [],
                "candidatos": [{"nome": "DS1", "url": "https://zenodo.org/records/9",
                                "classificacao": "B", "por_que": "motivo",
                                "licenca_dataset": "CC BY 4.0",
                                "identidade_disponivel": "4/4",
                                "anotacao_humana": "SIM"}]}}),
            json.dumps({"type": "result", "result": {
                "refutadas": [], "confirmadas": [], "veredito_do_cetico": "ok",
                "reclassificados": [{"candidato": "DS1", "de": "B", "para": "F",
                                     "motivo": "GT de modelo"}]}}),
            json.dumps({"type": "result", "result": {
                "faltando": [], "contradicoes": [], "melhores_tres": [],
                "existe_rota_plausivel": "SIM"}}),
        ]), encoding="utf-8")
        d = extrair(j)
        if len(d["arms"]) != 1 or len(d["ceticos"]) != 1 or len(d["criticos"]) != 1:
            falhas.append("extrator classificou errado: " + str({k: len(v) for k, v in d.items()}))
        linhas = linhas_de_log(d)
        if len(linhas) != 2:
            falhas.append("esperava 2 linhas (1 consulta + 1 candidato), veio %d" % len(linhas))
        cand = [l for l in linhas if l["candidate"]][0]
        # a reclassificacao do cetico TEM de aparecer no log; se o log mostrasse so a
        # classe do arm, ele registraria a versao que o cetico derrubou.
        if not cand["classification"].startswith("F"):
            falhas.append("reclassificacao do cetico nao apareceu: " + cand["classification"])
        if "reclassificado de B" not in cand["classification"]:
            falhas.append("o log perdeu a classe original")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste log_de_busca: %d verificacoes, %d falhas" % (11, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--journal", default=None)
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    if not a.journal:
        print("uso: --journal <caminho do journal.jsonl do workflow da Fase 20>")
        return 1
    dados = extrair(Path(a.journal))
    linhas = linhas_de_log(dados)
    if not linhas:
        print("journal sem arms — nada a registrar")
        return 1

    SAIDA.mkdir(parents=True, exist_ok=True)
    campos = ["query", "source", "url", "date", "candidate", "result",
              "classification", "notes"]
    with (SAIDA / "source_log.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for l in linhas:
            w.writerow(l)

    consultas = [l for l in linhas if l["query"]]
    cands = [l for l in linhas if l["candidate"]]
    from collections import Counter
    print("arms: %d | ceticos: %d | criticos: %d"
          % (len(dados["arms"]), len(dados["ceticos"]), len(dados["criticos"])))
    print("consultas registradas: %d" % len(consultas))
    print("candidatos: %d" % len(cands))
    print()
    print("por fonte:")
    for k, v in Counter(l["source"] for l in consultas).most_common():
        print("   %-20s %d" % (k, v))
    print()
    print("por classificacao:")
    for k, v in Counter(l["classification"].split(" ")[0] for l in cands).most_common():
        print("   %-8s %d" % (k or "(sem)", v))
    print("\nescrito:", SAIDA / "source_log.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
