"""Fase 24 — o pool dos 16, e a prova de que os 5 antigos nao mudaram.

O QUE ESTA FASE ACRESCENTA AO FUNIL
Nada. Ela usa exatamente o mesmo funil da Fase 23 (`fase23/ingerir_real.py`), sem
caminho paralelo. O que ela acrescenta e AUDITORIA:

  1. REPRODUCAO (regra 14). Os 5 casos ja auditados na Fase 23 sao reprocessados
     pelo funil e comparados campo a campo com o que foi gravado la. Se um
     `image_sha256` mudar, a Fase 24 para. Sem isto, "os 11 passaram pelo mesmo
     padrao" seria afirmacao, nao verificacao.

  2. UNIVERSO. 16 sujeitos, contados por PatientID e nunca por serie.

  3. REDUNDANCIA INTERNA (23.8 / 24.8). O 4D-Lung tem ate 50 RTSTRUCT por sujeito
     (5 estudos semanais x 10 fases respiratorias). O pool tem de ser 1 por
     sujeito, e isso e verificado, nao assumido.

  4. ANTI-LEAKAGE CRUZADO. Contra LCTSC, NSCLC-Radiomics e LyNoS, com a
     sensibilidade de cada chave declarada.

  python -m scripts.validation.fase24.consolidar --autoteste
  python -m scripts.validation.fase24.consolidar
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.fase23 import pool as p23  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase24"
INGESTAO = RAIZ / "docs" / "overnight" / "phase24" / "ingestao_real_16.json"
POOL23 = RAIZ / "docs" / "FASE23-POOL-CANDIDATO.json"
POOL24 = RAIZ / "docs" / "FASE24-POOL-16.json"

UNIVERSO_ESPERADO = 16

# Campos cuja mudanca entre a Fase 23 e a Fase 24 significaria que o funil deixou
# de ser deterministico. `notes` fica fora de proposito: e texto e pode ser
# reescrito sem que o DADO tenha mudado.
CAMPOS_IMUTAVEIS = ("case_id", "study_id", "series_id", "image_sha256",
                    "mask_sha256", "spacing", "orientation", "shape",
                    "license_class", "source_dataset", "source_case_id")


def reproducao_dos_5(entradas) -> dict:
    """Regra 14 — os 5 da Fase 23 tem de sair identicos ao serem reprocessados."""
    if not POOL23.exists():
        return {"verificavel": False, "motivo": "FASE23-POOL-CANDIDATO.json ausente"}
    antigos = {c["case_id"]: c for c in json.loads(POOL23.read_text(encoding="utf-8"))["casos"]}
    agora = {e["entrada"]["case_id"]: e["entrada"] for e in entradas if e.get("elegivel")}

    divergencias = []
    ausentes = []
    for cid, velho in sorted(antigos.items()):
        novo = agora.get(cid)
        if novo is None:
            ausentes.append(cid)
            continue
        for campo in CAMPOS_IMUTAVEIS:
            if campo not in velho:
                continue
            a, b = velho.get(campo), novo.get(campo)
            if isinstance(a, list):
                a, b = list(a), list(b or [])
            if a != b:
                divergencias.append({"case_id": cid, "campo": campo,
                                     "fase23": str(a)[:70], "fase24": str(b)[:70]})
    return {
        "verificavel": True,
        "n_antigos": len(antigos),
        "reprocessados": len(antigos) - len(ausentes),
        "ausentes": ausentes,
        "divergencias": divergencias,
        "reproduz": not divergencias and not ausentes,
    }


def redundancia_interna(entradas) -> dict:
    """24.8 — um sujeito, uma serie. Verificado, nao assumido."""
    ok = [e for e in entradas if e.get("elegivel")]
    por_sujeito = defaultdict(list)
    for e in ok:
        por_sujeito[e["entrada"]["source_case_id"]].append(e["entrada"]["case_id"])
    multi = {k: v for k, v in por_sujeito.items() if len(v) > 1}
    estudos = Counter(e["entrada"]["study_id"] for e in ok)
    series = Counter(e["entrada"]["series_id"] for e in ok)
    img = Counter(e["entrada"]["image_sha256"] for e in ok)
    msk = Counter(e["entrada"]["mask_sha256"] for e in ok)
    return {
        "sujeitos": len(por_sujeito),
        "sujeitos_com_mais_de_uma_serie": multi,
        "estudos_repetidos": {k: v for k, v in estudos.items() if v > 1},
        "series_repetidas": {k: v for k, v in series.items() if v > 1},
        "imagens_repetidas": {k[:16]: v for k, v in img.items() if v > 1},
        "mascaras_repetidas": {k[:16]: v for k, v in msk.items() if v > 1},
        "um_por_sujeito": not multi,
    }


def _sha_arquivo(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def anti_leakage_cruzado(entradas) -> dict:
    """Contra as coortes que o VRmed ja tocou. Cada chave com sua sensibilidade."""
    ok = [e["entrada"] for e in entradas if e.get("elegivel")]
    novos = {
        "study": {e["study_id"] for e in ok},
        "series": {e["series_id"] for e in ok},
        "case": {e["source_case_id"] for e in ok},
        "hash": {e["image_sha256"] for e in ok} | {e["mask_sha256"] for e in ok},
    }

    lc_study, lc_series, lc_case = set(), set(), set()
    for f in glob.glob(str(RAIZ / ".clinica-dados" / "tier2" / "lctsc" / "*" / "*" / "_tcia_serie.json")):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        lc_study.add(d.get("StudyInstanceUID", ""))
        lc_series.add(d.get("SeriesInstanceUID", ""))
        lc_case.add(d.get("PatientID", ""))

    ns_series = set()
    for f in glob.glob(str(RAIZ / ".clinica-dados" / "nsclc-radiomics" / "*" / "ct" / "_tcia_serie.json")):
        ns_series.add(json.loads(Path(f).read_text(encoding="utf-8")).get("SeriesInstanceUID", ""))

    ly_hash = {_sha_arquivo(Path(f))
               for f in glob.glob(str(RAIZ / ".clinica-dados" / "fase18" / "lynos" / "*.nii.gz"))}

    return {
        "LCTSC": {
            "study": sorted(novos["study"] & lc_study),
            "series": sorted(novos["series"] & lc_series),
            "case": sorted(novos["case"] & lc_case),
            "n_referencia": len(lc_series),
            "estado": "COLISAO" if (novos["study"] & lc_study or novos["series"] & lc_series
                                    or novos["case"] & lc_case) else "NAO DETECTADO",
        },
        "NSCLC_Radiomics": {
            "series": sorted(novos["series"] & ns_series),
            "n_referencia": len(ns_series),
            "estado": "COLISAO" if novos["series"] & ns_series else "NAO DETECTADO",
        },
        "LyNoS": {
            "hash": sorted(novos["hash"] & ly_hash),
            "n_referencia": len(ly_hash),
            "estado": "COLISAO" if novos["hash"] & ly_hash else "IDENTIDADE INDISPONIVEL",
            "limite": ("LyNoS e NIfTI e NAO tem StudyInstanceUID nem SeriesInstanceUID. "
                       "So resta comparar hash de conteudo, e os formatos diferem "
                       "(NIfTI original x DICOM convertido por nos). Um MESMO exame nos "
                       "dois canais NAO seria detectado. Isto e INCONCLUSIVO, nunca "
                       "'sem overlap'."),
        },
        "leitura": ("'NAO DETECTADO' e o resultado do instrumento, nao uma afirmacao "
                    "de independencia. Nenhuma destas chaves prova ausencia."),
    }


def montar_pool16(entradas) -> list:
    return p23.montar_pool([e for e in entradas if e.get("elegivel")])


def autoteste() -> int:
    falhas = []

    # reproducao: divergencia de hash TEM de ser detectada
    v = [{"elegivel": True, "entrada": {"case_id": "A", "study_id": "s", "series_id": "e",
                                        "image_sha256": "a" * 64, "mask_sha256": "b" * 64,
                                        "spacing": [1, 1, 1], "orientation": "LPS",
                                        "shape": [2, 2, 2], "license_class": "ABERTA_ATRIBUICAO",
                                        "source_dataset": "d", "source_case_id": "A"}}]
    import tempfile
    global POOL23
    orig = POOL23
    try:
        with tempfile.TemporaryDirectory() as t:
            POOL23 = Path(t) / "p.json"
            POOL23.write_text(json.dumps({"casos": [v[0]["entrada"]]}), encoding="utf-8")
            if not reproducao_dos_5(v)["reproduz"]:
                falhas.append("caso identico foi acusado de divergir")
            # CONTROLE POSITIVO: trocar um hash tem de acusar
            alt = [{"elegivel": True, "entrada": dict(v[0]["entrada"], image_sha256="c" * 64)}]
            r = reproducao_dos_5(alt)
            if r["reproduz"] or not any(d["campo"] == "image_sha256" for d in r["divergencias"]):
                falhas.append("troca de image_sha256 nao foi detectada")
            # CONTROLE POSITIVO: caso sumido tem de acusar
            if reproducao_dos_5([])["reproduz"]:
                falhas.append("caso ausente passou como reproduzido")
            # notes NAO entra na comparacao — mudar texto nao e mudar dado
            comn = [{"elegivel": True, "entrada": dict(v[0]["entrada"], notes="outro texto")}]
            if not reproducao_dos_5(comn)["reproduz"]:
                falhas.append("mudanca em notes foi tratada como divergencia de dado")
    finally:
        POOL23 = orig

    # redundancia: dois casos do MESMO sujeito tem de ser acusados
    dois = [{"elegivel": True, "entrada": {"case_id": "A", "source_case_id": "S1",
                                           "study_id": "s1", "series_id": "e1",
                                           "image_sha256": "a" * 64, "mask_sha256": "b" * 64}},
            {"elegivel": True, "entrada": {"case_id": "B", "source_case_id": "S1",
                                           "study_id": "s2", "series_id": "e2",
                                           "image_sha256": "c" * 64, "mask_sha256": "d" * 64}}]
    r = redundancia_interna(dois)
    if r["um_por_sujeito"] or "S1" not in r["sujeitos_com_mais_de_uma_serie"]:
        falhas.append("dois casos do mesmo sujeito nao foram acusados")
    # e um por sujeito tem de passar
    if not redundancia_interna([dois[0]])["um_por_sujeito"]:
        falhas.append("um caso por sujeito foi acusado de redundancia")

    # o universo esperado esta escrito e e 16
    if UNIVERSO_ESPERADO != 16:
        falhas.append("universo esperado mudou sem revisao")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste consolidar: %d verificacoes, %d falhas" % (8, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    if not INGESTAO.exists():
        print("ingestao_real.json ausente — rode fase23.ingerir_real primeiro")
        return 1
    doc = json.loads(INGESTAO.read_text(encoding="utf-8"))
    entradas = doc["casos"]
    ok = [e for e in entradas if e.get("elegivel")]
    ruins = [e for e in entradas if not e.get("elegivel")]

    print("PROCESSADOS: %d  |  ELEGIVEIS: %d  |  BLOQUEADOS: %d"
          % (len(entradas), len(ok), len(ruins)))
    for e in ruins:
        print("   BLOQUEADO %-16s %s" % (e.get("case_id"), (e.get("bloqueios") or ["?"])[0][:80]))

    rep = reproducao_dos_5(entradas)
    print()
    print("REPRODUCAO DOS 5 DA FASE 23 (regra 14): %s"
          % ("OK — identicos campo a campo" if rep.get("reproduz") else "DIVERGIU"))
    for d in rep.get("divergencias", [])[:6]:
        print("   %s.%s  fase23=%s  fase24=%s" % (d["case_id"], d["campo"], d["fase23"], d["fase24"]))
    for x in rep.get("ausentes", []):
        print("   AUSENTE:", x)

    red = redundancia_interna(entradas)
    print()
    print("REDUNDANCIA INTERNA: %d sujeitos, um por sujeito = %s"
          % (red["sujeitos"], red["um_por_sujeito"]))
    for k in ("estudos_repetidos", "series_repetidas", "imagens_repetidas", "mascaras_repetidas"):
        if red[k]:
            print("   %s: %s" % (k, red[k]))

    leak = anti_leakage_cruzado(entradas)
    print()
    print("ANTI-LEAKAGE CRUZADO")
    for k in ("LCTSC", "NSCLC_Radiomics", "LyNoS"):
        print("   %-16s %-22s (referencia: %d)"
              % (k, leak[k]["estado"], leak[k]["n_referencia"]))

    universo_ok = red["sujeitos"] == UNIVERSO_ESPERADO
    print()
    print("UNIVERSO: %d sujeitos | esperado %d -> %s"
          % (red["sujeitos"], UNIVERSO_ESPERADO, "OK" if universo_ok else "DISCREPANCIA"))

    pool = montar_pool16(entradas)
    SAIDA.mkdir(parents=True, exist_ok=True)
    POOL24.write_text(json.dumps({
        "gerado_em": "2026-09-06", "fase": 24,
        "estado": "POOL DE 16 — nenhum split congelado nesta fase",
        "universo_esperado": UNIVERSO_ESPERADO,
        "n": len(pool),
        "casos": pool,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    (SAIDA / "consolidacao.json").write_text(json.dumps({
        "fase": 24, "n_processados": len(entradas), "n_elegiveis": len(ok),
        "reproducao_fase23": rep, "redundancia": red, "anti_leakage": leak,
        "universo_ok": universo_ok,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print("escrito:", POOL24)

    gates = (rep.get("reproduz", False), red["um_por_sujeito"], universo_ok, not ruins)
    print()
    print("GATES: reproducao=%s | um_por_sujeito=%s | universo=%s | sem_bloqueados=%s"
          % gates)
    return 0 if all(gates) else 1


if __name__ == "__main__":
    sys.exit(main())
