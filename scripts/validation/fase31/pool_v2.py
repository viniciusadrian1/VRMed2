"""Fase 31 — pool V2: 4D-Lung (16) + LCTSC development (30), com split estratificado.

A REGRA DE SPLIT V2, DECLARADA ANTES DE QUALQUER NUMERO SER VISTO

    bucket(case_id) = sha256(case_id) mod 100          # igual a V1: deterministico, sem semente
    validation      se bucket < 25, DENTRO DE CADA ESTRATO
    estrato         = source_dataset
    test            = VAZIO, sempre

O QUE MUDA DA V1, E POR QUE

A V1 aplicava o limiar ao pool inteiro. Com uma fonte so isso bastava. Com duas fontes
de tamanhos diferentes (16 e 30), o sorteio poderia concentrar a validation numa delas
— e uma validation composta so de LCTSC mediria outra coisa que uma composta so de
4D-Lung. A estratificacao por `source_dataset` garante que as duas fontes aparecam nos
dois lados.

O QUE NAO MUDA

O mecanismo do bucket e o mesmo da V1. Isso preserva de proposito a propriedade que a
Fase 25 declarou: **um caso novo nao move nenhum caso existente**. Os 16 do 4D-Lung
caem exatamente onde ja estavam — nao por conveniencia, mas porque reatribuir caso ja
congelado e vazamento com cara de manutencao, e a propriedade foi declarada antes.

A V1 NAO E TOCADA. O manifesto V1, seu snapshot e seu split continuam existindo,
inalterados, como versao historica.

  python -m scripts.validation.fase31.pool_v2 --autoteste
  python -m scripts.validation.fase31.pool_v2 --escrever
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
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase31"

MANIFESTO_V1 = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
INGESTAO_LCTSC = SAIDA / "ingestao_real.json"

MANIFESTO_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-MANIFESTO-V2.jsonl"
SNAPSHOT_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-SNAPSHOT-V2.json"
POOL_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-POOL-V2.json"

VERSAO = "VRMED-ESOPHAGUS-POOL46-V2"
REGRA = "VRMED-SPLIT-RULE-V2"
LIMIAR = 25          # por cento, igual a V1
SEED = None          # nao ha sorteio: nao ha semente

# Bandas declaradas ANTES de calcular. Uma por estrato, mais a global.
BANDAS = {"4D-Lung (TCIA)": (2, 8), "LCTSC (TCIA)": (4, 12), "_global": (6, 20)}

N_ESPERADO_V1, N_ESPERADO_LCTSC = 16, 30


def bucket(case_id: str) -> int:
    """Balde 0-99. Funcao pura do identificador — o mesmo mecanismo da V1."""
    return int(hashlib.sha256(case_id.encode("utf-8")).hexdigest(), 16) % 100


def atribuir(case_id: str) -> str:
    return "validation" if bucket(case_id) < LIMIAR else "train"


def entradas_v2() -> list:
    """Os 16 da V1 (campos preservados) + os 30 do LCTSC, em ordem canonica."""
    v1 = man.carregar(MANIFESTO_V1)
    doc = json.loads(INGESTAO_LCTSC.read_text(encoding="utf-8"))
    novos = [dict(c["entrada"]) for c in doc["casos"] if c.get("elegivel")]
    for e in novos:
        for campo in ("image_path", "mask_path"):
            try:
                e[campo] = Path(e[campo]).resolve().relative_to(RAIZ).as_posix()
            except ValueError:
                pass
    return sorted([dict(e) for e in v1] + novos, key=lambda x: x["case_id"])


def aplicar_split(entradas) -> list:
    """Atribui `split` pela regra V2. Nenhum outro campo e tocado."""
    return [dict(e, split=atribuir(e["case_id"])) for e in entradas]


def auditar(entradas) -> dict:
    """Composicao por estrato, bandas, isolamento e integridade de identidade."""
    por_estrato = {}
    for e in entradas:
        por_estrato.setdefault(e["source_dataset"], []).append(e)

    estratos = {}
    for fonte, casos in sorted(por_estrato.items()):
        c = Counter(x["split"] for x in casos)
        nv = c.get("validation", 0)
        lo, hi = BANDAS.get(fonte, (0, len(casos)))
        estratos[fonte] = {"n": len(casos), "train": c.get("train", 0), "validation": nv,
                           "banda": [lo, hi], "dentro_da_banda": lo <= nv <= hi}

    total = Counter(e["split"] for e in entradas)
    nvg = total.get("validation", 0)
    lo, hi = BANDAS["_global"]

    ident = {}
    for chave in ("case_id", "study_id", "series_id", "image_sha256", "mask_sha256"):
        cc = Counter(e[chave] for e in entradas)
        ident[chave] = {"distintos": len(cc),
                        "repetidos": sorted(k for k, v in cc.items() if v > 1)}
    por_sujeito = {}
    for e in entradas:
        por_sujeito.setdefault((e["source_dataset"], e["source_case_id"]), set()).add(e["split"])
    ident["sujeitos_em_dois_splits"] = sorted(
        "%s/%s" % s for s, v in por_sujeito.items() if len(v) > 1)
    ident["n_sujeitos"] = len(por_sujeito)

    lic = Counter(e["license_class"] for e in entradas)
    return {
        "n_total": len(entradas),
        "por_split": {p: total.get(p, 0) for p in man.PARTICOES},
        "estratos": estratos,
        "banda_global": [lo, hi], "dentro_da_banda_global": lo <= nvg <= hi,
        "identidade": ident,
        "licencas": dict(lic),
        "licencas_bloqueantes": sorted(set(lic) & set(man.LICENCAS_BLOQUEANTES)),
        "fontes": dict(Counter(e["source_dataset"] for e in entradas)),
        "anotacao_declarada": dict(Counter(
            ("MANUAL" if "MANUAL" in e["notes"] and "VAZIO" not in e["notes"]
             else "VAZIO" if "VAZIO" in e["notes"]
             else "SEMIAUTOMATIC" if "SEMIAUTOMATIC" in e["notes"] else "OUTRO")
            for e in entradas)),
    }


def test_protegido(entradas) -> dict:
    r = {"n_test": sum(1 for e in entradas if e["split"] == "test")}
    for ctx, esperado in (("treino", True), ("validacao", True), ("avaliacao", False)):
        try:
            man.carregar_particao(entradas, "test", ctx)
            r[ctx] = {"bloqueado": False}
        except man.AcessoIndevido:
            r[ctx] = {"bloqueado": True}
        r[ctx]["conforme"] = r[ctx]["bloqueado"] == esperado
    r["treino_le_train"] = len(man.carregar_particao(entradas, "train", "treino"))
    try:
        man.carregar_particao(entradas, "validation", "treino")
        r["treino_nao_le_validation"] = False
    except man.AcessoIndevido:
        r["treino_nao_le_validation"] = True
    return r


def autoteste() -> int:
    falhas = []

    # 1. o bucket e o MESMO da V1 — a estabilidade sob crescimento depende disso
    from scripts.validation.fase25 import split as v1s
    for cid in ("4DLUNG-100_HM10395", "LCTSC-Test-S1-101", "X"):
        if bucket(cid) != v1s.bucket(cid):
            falhas.append("o bucket divergiu da V1 em %r" % cid)

    # 2. determinismo e independencia de ordem
    base = [{"case_id": "C%02d" % i, "source_dataset": "A" if i % 2 else "B"} for i in range(20)]
    a1 = aplicar_split(base)
    a2 = aplicar_split(list(reversed(base)))
    if sorted((x["case_id"], x["split"]) for x in a1) != sorted((x["case_id"], x["split"]) for x in a2):
        falhas.append("a atribuicao mudou com a ordem de entrada")

    # 3. ESTABILIDADE SOB CRESCIMENTO — a propriedade herdada da V1
    antes = {x["case_id"]: x["split"] for x in a1}
    maior = aplicar_split(base + [{"case_id": "NOVO", "source_dataset": "A"}])
    movidos = [k for k, v in {x["case_id"]: x["split"] for x in maior}.items()
               if k in antes and v != antes[k]]
    if movidos:
        falhas.append("crescer o pool moveu casos: %s" % movidos[:4])

    # 4. CEGA AO CONTEUDO — volume, spacing e extensao nao podem mudar nada
    ricos = [dict(c, volume_ml=999.0, spacing=[9, 9, 9], extensao_axial_mm=1.0) for c in base]
    if ([x["split"] for x in aplicar_split(ricos)] != [x["split"] for x in a1]):
        falhas.append("a atribuicao reagiu ao CONTEUDO — split contaminado")

    # 5. TEST sempre vazio
    if any(x["split"] == "test" for x in a1):
        falhas.append("a regra atribuiu caso a test")

    # 6. a auditoria detecta sujeito em dois splits (controle POSITIVO)
    sujado = [{"case_id": "a", "split": "train", "source_dataset": "A", "source_case_id": "S",
               "study_id": "1", "series_id": "1", "image_sha256": "x", "mask_sha256": "y",
               "license_class": "ABERTA_ATRIBUICAO", "notes": "MANUAL"},
              {"case_id": "b", "split": "validation", "source_dataset": "A", "source_case_id": "S",
               "study_id": "2", "series_id": "2", "image_sha256": "z", "mask_sha256": "w",
               "license_class": "ABERTA_ATRIBUICAO", "notes": "MANUAL"}]
    if not auditar(sujado)["identidade"]["sujeitos_em_dois_splits"]:
        falhas.append("sujeito em dois splits NAO foi detectado — detector cego")

    # 7. e NAO acusa quando nao ha (controle negativo)
    limpo = [dict(sujado[0]), dict(sujado[1], source_case_id="T")]
    if auditar(limpo)["identidade"]["sujeitos_em_dois_splits"]:
        falhas.append("acusou sujeito em dois splits onde nao ha")

    # 8. licenca bloqueante e detectada
    ruim = [dict(sujado[0], license_class="UNKNOWN")]
    if not auditar(ruim)["licencas_bloqueantes"]:
        falhas.append("license_class UNKNOWN nao foi marcada como bloqueante")

    # 9. as bandas foram declaradas para os dois estratos e para o global
    for k in ("4D-Lung (TCIA)", "LCTSC (TCIA)", "_global"):
        if k not in BANDAS:
            falhas.append("banda nao declarada para %r" % k)

    # 10. TEST protegido, com controle negativo
    tp = test_protegido(aplicar_split([dict(sujado[0]), dict(sujado[1], source_case_id="T")]))
    if not (tp["treino"]["conforme"] and tp["validacao"]["conforme"]
            and tp["avaliacao"]["conforme"] and tp["treino_nao_le_validation"]):
        falhas.append("travas de particao nao conformes: %s" % tp)

    for f in falhas:
        print("FALHA:", f)
    print("autoteste pool_v2: %d verificacoes, %d falhas" % (10, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--quando", default="2026-09-10T00:00:00Z")
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    ent = aplicar_split(entradas_v2())
    aud = auditar(ent)
    tp = test_protegido(ent)
    v = man.validar_manifesto(ent)

    print("POOL V2: %d casos  |  %s" % (aud["n_total"], aud["fontes"]))
    print("esquema %s | validas %s | erros %d" % (man.VERSAO_ESQUEMA, v["valido"], len(v["erros"])))
    for e in v["erros"][:6]:
        print("   ERRO:", e)
    print()
    print("SPLIT V2 (%s, limiar %d %%, estratificado por source_dataset)" % (REGRA, LIMIAR))
    print("   %-22s %5s %7s %13s %s" % ("estrato", "n", "train", "validation", "banda"))
    for fonte, s in aud["estratos"].items():
        print("   %-22s %5d %7d %13d %s -> %s"
              % (fonte, s["n"], s["train"], s["validation"], s["banda"],
                 "DENTRO" if s["dentro_da_banda"] else "FORA"))
    print("   %-22s %5d %7d %13d %s -> %s"
          % ("TOTAL", aud["n_total"], aud["por_split"]["train"], aud["por_split"]["validation"],
             aud["banda_global"], "DENTRO" if aud["dentro_da_banda_global"] else "FORA"))
    print("   test: %d" % aud["por_split"]["test"])
    print()
    print("IDENTIDADE  sujeitos %d | em dois splits: %s"
          % (aud["identidade"]["n_sujeitos"],
             aud["identidade"]["sujeitos_em_dois_splits"] or "nenhum"))
    for k in ("case_id", "study_id", "series_id", "image_sha256", "mask_sha256"):
        print("   %-14s distintos %2d | repetidos %s"
              % (k, aud["identidade"][k]["distintos"], aud["identidade"][k]["repetidos"] or "-"))
    print()
    print("LICENCAS %s | bloqueantes: %s" % (aud["licencas"], aud["licencas_bloqueantes"] or "nenhuma"))
    print("ANOTACAO declarada por caso: %s" % aud["anotacao_declarada"])
    print()
    print("TEST  n=%d | treino=%s validacao=%s avaliacao=%s | treino le train: %d | treino le validation: %s"
          % (tp["n_test"],
             "BLOQ" if tp["treino"]["bloqueado"] else "ABERTO",
             "BLOQ" if tp["validacao"]["bloqueado"] else "ABERTO",
             "BLOQ" if tp["avaliacao"]["bloqueado"] else "ABERTO",
             tp["treino_le_train"], not tp["treino_nao_le_validation"]))

    ok = (v["valido"] and aud["dentro_da_banda_global"]
          and all(s["dentro_da_banda"] for s in aud["estratos"].values())
          and not aud["identidade"]["sujeitos_em_dois_splits"]
          and not aud["licencas_bloqueantes"] and tp["n_test"] == 0
          and all(tp[c]["conforme"] for c in ("treino", "validacao", "avaliacao")))
    print()
    if not ok:
        print("PORTAO REPROVOU — nada foi congelado.")
        return 1
    if not a.escrever:
        print("PORTOES OK. Rode com --escrever para congelar a V2.")
        return 0

    sha = man.gravar(ent, MANIFESTO_V2)
    snap = man.congelar(ent, SNAPSHOT_V2, VERSAO, a.quando)
    conf = man.verificar_congelamento(ent, snap)
    POOL_V2.write_text(json.dumps({
        "gerado_em": a.quando, "fase": 31, "versao": VERSAO, "regra_split": REGRA,
        "limiar": LIMIAR, "seed": SEED, "bandas": {k: list(v) for k, v in BANDAS.items()},
        "ontologia": onto.VERSAO, "esquema": man.VERSAO_ESQUEMA,
        "sha256_manifesto": sha, "auditoria": aud,
        "casos": [{"case_id": e["case_id"], "split": e["split"], "bucket": bucket(e["case_id"]),
                   "source_dataset": e["source_dataset"], "source_case_id": e["source_case_id"],
                   "image_sha256": e["image_sha256"], "mask_sha256": e["mask_sha256"],
                   "license_class": e["license_class"], "spacing": e["spacing"],
                   "shape": e["shape"]} for e in ent],
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print("CONGELADO %s em %s" % (VERSAO, a.quando))
    print("   manifesto : %s" % MANIFESTO_V2.name)
    print("   sha256    : %s" % sha)
    print("   snapshot  : %s" % SNAPSHOT_V2.name)
    print("   pool      : %s" % POOL_V2.name)
    print("   intacto   : %s" % conf["intacto"])
    return 0 if conf["intacto"] else 1


if __name__ == "__main__":
    sys.exit(main())
