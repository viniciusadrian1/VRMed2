"""Fase 25 — congela TRAIN/VALIDATION do pool de 16, com TEST vazio e protegido.

O QUE ESTE MODULO FAZ, NA ORDEM EM QUE IMPORTA

1. Le as entradas de manifesto que a Fase 24 JA produziu. Nao as reconstroi: o
   `entrada` de cada caso em `ingestao_real_16.json` ja tem os 22 campos do esquema,
   com `source_doi` levantado em fase anterior. Reconstruir seria inventar de novo o
   que ja foi auditado.
2. Normaliza `image_path`/`mask_path` para caminho relativo a raiz do repositorio.
   O caminho absoluto da maquina continua registrado no artefato historico da Fase
   24; o `sha256` — que e a identidade — nao muda.
3. Aplica a regra de split declarada em `fase25/split.py`, escrita ANTES de qualquer
   numero ter sido visto.
4. Audita a distribuicao do pool. **Isto e DIAGNOSTICO, e so.** O resultado da
   auditoria NAO realimenta o split. Um split que se ajusta ate a distribuicao ficar
   bonita e um split escolhido depois de ver o alvo.
5. Valida o manifesto, congela com snapshot e hash, e prova por execucao que o TEST
   e inalcancavel a partir do contexto de treino.

O QUE ELE NAO FAZ
Nao treina, nao mede Dice, nao preenche TEST, nao altera a ontologia, e nao reordena
nem reatribui nenhum caso por causa de uma metrica.

  python -m scripts.validation.fase25.congelar --autoteste
  python -m scripts.validation.fase25.congelar
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
from scripts.validation.fase25 import split as sp  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
INGESTAO = RAIZ / "docs" / "overnight" / "phase24" / "ingestao_real_16.json"
POOL16 = RAIZ / "docs" / "FASE24-POOL-16.json"
SAIDA = RAIZ / "docs" / "overnight" / "phase25"

MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"

VERSAO = "VRMED-ESOPHAGUS-POOL16-V1"
N_ESPERADO = 16


def _relativo(p: str) -> str:
    """Caminho relativo a raiz, em POSIX. Se ja for de fora da raiz, devolve como veio."""
    try:
        return Path(p).resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return p


def entradas_do_pool() -> list:
    """As 16 entradas de manifesto, como a Fase 24 as deixou, com caminho normalizado."""
    doc = json.loads(INGESTAO.read_text(encoding="utf-8"))
    saida = []
    for c in doc["casos"]:
        if not c.get("elegivel"):
            continue
        e = dict(c["entrada"])
        e["image_path"] = _relativo(e["image_path"])
        e["mask_path"] = _relativo(e["mask_path"])
        saida.append(e)
    return sorted(saida, key=lambda x: x["case_id"])


def aplicar_split(entradas) -> list:
    """Atribui `split` pela regra declarada. Nenhum outro campo e tocado."""
    return [dict(e, split=sp.atribuir(e["case_id"])) for e in entradas]


def integridade_de_identidade(entradas) -> dict:
    """Duas entradas nao podem descrever o mesmo objeto sob nomes diferentes."""
    r = {}
    for chave in ("case_id", "study_id", "series_id", "image_sha256", "mask_sha256"):
        c = Counter(e[chave] for e in entradas)
        r[chave] = {"distintos": len(c), "repetidos": sorted(k for k, v in c.items() if v > 1)}
    # o sujeito e o prefixo do case_id: dois casos do MESMO sujeito em splits
    # diferentes seria vazamento por sujeito, que `validar_vazamento` nao pega
    # sozinho porque ele compara case_id inteiro.
    por_sujeito = {}
    for e in entradas:
        por_sujeito.setdefault(e["source_case_id"], set()).add(e["split"])
    r["sujeitos_em_dois_splits"] = sorted(s for s, v in por_sujeito.items() if len(v) > 1)
    r["n_sujeitos"] = len(por_sujeito)
    return r


def procedencia_e_licenca(entradas) -> dict:
    return {
        "source_dataset": dict(Counter(e["source_dataset"] for e in entradas)),
        "source_doi": dict(Counter(e["source_doi"] for e in entradas)),
        "license": dict(Counter(e["license"] for e in entradas)),
        "license_class": dict(Counter(e["license_class"] for e in entradas)),
        "institution": dict(Counter(e["institution"] for e in entradas)),
        "annotation_protocol": dict(Counter(e["annotation_protocol"] for e in entradas)),
        "annotation_date_known": dict(Counter(str(e["annotation_date_known"]) for e in entradas)),
        "bloqueantes": sorted({e["license_class"] for e in entradas}
                              & set(man.LICENCAS_BLOQUEANTES)),
    }


def distribuicao(entradas) -> dict:
    """DIAGNOSTICO. Existe para EXPOR anomalia, nunca para corrigir o split.

    Se uma dimensao ficar concentrada num lado, isso vira texto no relatorio — nao
    vira reatribuicao de caso.
    """
    pool = {c["case_id"]: c for c in json.loads(POOL16.read_text(encoding="utf-8"))["casos"]}
    linhas = []
    for e in entradas:
        p = pool.get(e["case_id"], {})
        fase_resp = Path(e["mask_path"]).name.replace("mask_Esophagus_", "").replace(".nii.gz", "")
        linhas.append({
            "case_id": e["case_id"],
            "split": e["split"],
            "volume_ml": p.get("volume_ml"),
            "extensao_axial_mm": p.get("extensao_axial_mm"),
            "spacing": tuple(e["spacing"]),
            "shape_z": e["shape"][2],
            "fase_respiratoria": fase_resp,
        })

    def resumo(sel, campo):
        v = sorted(x[campo] for x in linhas if x["split"] == sel and x[campo] is not None)
        if not v:
            return None
        meio = len(v) // 2
        mediana = v[meio] if len(v) % 2 else (v[meio - 1] + v[meio]) / 2
        return {"n": len(v), "min": min(v), "mediana": round(mediana, 2), "max": max(v)}

    return {
        "linhas": linhas,
        "por_split": {
            s: {
                "n": sum(1 for x in linhas if x["split"] == s),
                "volume_ml": resumo(s, "volume_ml"),
                "extensao_axial_mm": resumo(s, "extensao_axial_mm"),
                "shape_z": resumo(s, "shape_z"),
                "spacing": dict(Counter(str(x["spacing"]) for x in linhas if x["split"] == s)),
                "fase_respiratoria": dict(Counter(x["fase_respiratoria"] for x in linhas
                                                  if x["split"] == s)),
            } for s in ("train", "validation")
        },
        "aviso": ("DIAGNOSTICO. Nenhuma destas medidas realimenta a regra de split. "
                  "Ajustar o split para melhorar qualquer uma delas seria escolher o "
                  "split depois de ver o split."),
    }


def test_protegido(entradas) -> dict:
    """Prova por EXECUCAO que o TEST e inalcancavel de um contexto de treino.

    Nao e convencao de nome nem comentario: e `AcessoIndevido` levantado de verdade.
    """
    r = {"n_test_no_manifesto": sum(1 for e in entradas if e["split"] == "test")}
    for contexto, esperado_bloqueado in (("treino", True), ("validacao", True),
                                         ("avaliacao", False)):
        try:
            lidos = man.carregar_particao(entradas, "test", contexto)
            r[contexto] = {"bloqueado": False, "n_lidos": len(lidos)}
        except man.AcessoIndevido as exc:
            r[contexto] = {"bloqueado": True, "erro": str(exc)[:120]}
        r[contexto]["conforme_esperado"] = r[contexto]["bloqueado"] == esperado_bloqueado
    # e o contrario tambem: treino PODE ler train, senao o guarda so proibiria tudo
    try:
        r["treino_le_train"] = len(man.carregar_particao(entradas, "train", "treino"))
    except man.AcessoIndevido:
        r["treino_le_train"] = "BLOQUEADO — controle negativo falhou"
    return r


def autoteste() -> int:
    falhas = []
    base = [man._entrada("c%d" % i) for i in range(6)]

    # 1. o split aplicado nao altera NENHUM outro campo
    antes = [dict(e) for e in base]
    depois = aplicar_split(base)
    for a, d in zip(antes, depois):
        difs = [k for k in a if k != "split" and a[k] != d[k]]
        if difs:
            falhas.append("aplicar_split mexeu em campo que nao e split: %s" % difs)

    # 2. e nao inventa nem perde entrada
    if len(depois) != len(base):
        falhas.append("aplicar_split mudou a quantidade de entradas")

    # 3. identidade: um pool sadio nao tem repetidos
    idt = integridade_de_identidade(depois)
    if any(idt[k]["repetidos"] for k in ("case_id", "study_id", "series_id")):
        falhas.append("pool sintetico acusou repetido onde nao ha")

    # 4. controle POSITIVO: se dois casos do mesmo sujeito cairem em splits
    #    diferentes, a funcao TEM de acusar. Um detector que nunca acusa nao detecta.
    sujado = [dict(depois[0], case_id="x1", split="train", source_case_id="S"),
              dict(depois[0], case_id="x2", split="validation", source_case_id="S")]
    if not integridade_de_identidade(sujado)["sujeitos_em_dois_splits"]:
        falhas.append("sujeito em dois splits NAO foi detectado — detector cego")

    # 5. TEST vazio de verdade no pool congelado
    tp = test_protegido(depois)
    if tp["n_test_no_manifesto"] != 0:
        falhas.append("apareceu caso em test")

    # 6. e inalcancavel de treino e de validacao, alcancavel de avaliacao
    for ctx in ("treino", "validacao", "avaliacao"):
        if not tp[ctx]["conforme_esperado"]:
            falhas.append("permissao errada para contexto %r: %s" % (ctx, tp[ctx]))

    # 7. controle NEGATIVO: treino PRECISA conseguir ler train, senao o guarda
    #    estaria apenas proibindo tudo e nao provaria nada
    if not isinstance(tp["treino_le_train"], int):
        falhas.append("treino nao conseguiu ler train — o guarda proibe demais")

    # 8. licenca bloqueante e detectada
    ruim = [dict(depois[0], license_class="UNKNOWN")]
    if not procedencia_e_licenca(ruim)["bloqueantes"]:
        falhas.append("license_class UNKNOWN nao foi marcada como bloqueante")

    # 9. caminho relativo: absoluto dentro da raiz vira relativo, de fora fica igual
    if _relativo(str(RAIZ / "a" / "b.txt")) != "a/b.txt":
        falhas.append("_relativo nao normalizou caminho de dentro da raiz")
    if _relativo("Z:/fora/x.txt") != "Z:/fora/x.txt":
        falhas.append("_relativo mexeu em caminho de fora da raiz")

    # 10. o manifesto sintetico congela e o snapshot fecha
    dest = SAIDA / "_autoteste_snapshot.json"
    try:
        snap = man.congelar(depois, dest, "AUTOTESTE", "2026-09-06T00:00:00Z")
        if man.verificar_congelamento(depois, snap)["intacto"] is not True:
            falhas.append("verificar_congelamento reprovou manifesto intacto")
        # e ACUSA quando alguem muda um caso sem subir versao
        mexido = [dict(depois[0], split="validation")] + depois[1:]
        if man.verificar_congelamento(mexido, snap)["intacto"] is True:
            falhas.append("verificar_congelamento aceitou manifesto alterado")
    except Exception as exc:  # noqa: BLE001
        falhas.append("congelamento sintetico falhou: %s" % exc)
    finally:
        if dest.exists():
            dest.unlink()

    for f in falhas:
        print("FALHA:", f)
    print("autoteste congelar: %d verificacoes, %d falhas" % (12, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--quando", default="2026-09-06T00:00:00Z",
                    help="carimbo do congelamento; entra por parametro para ser reproduzivel")
    ap.add_argument("--escrever", action="store_true",
                    help="grava manifesto e snapshot; sem isto, so audita")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    ent = aplicar_split(entradas_do_pool())
    if len(ent) != N_ESPERADO:
        print("PARE: esperava %d entradas, ha %d" % (N_ESPERADO, len(ent)))
        return 1

    v = man.validar_manifesto(ent)
    idt = integridade_de_identidade(ent)
    proc = procedencia_e_licenca(ent)
    dist = distribuicao(ent)
    tp = test_protegido(ent)
    r = sp.aplicar(ent)

    print("ESQUEMA %s  |  entradas %d" % (man.VERSAO_ESQUEMA, v["n_entradas"]))
    print("manifesto valido: %s  |  erros: %d" % (v["valido"], len(v["erros"])))
    for e in v["erros"][:10]:
        print("   ERRO:", e)
    print()
    print("SPLIT  train %d | validation %d | test %d   (banda declarada %s -> %s)"
          % (v["por_split"]["train"], v["por_split"]["validation"], v["por_split"]["test"],
             r["banda_aceitacao"], "DENTRO" if r["dentro_da_banda"] else "FORA"))
    print()
    print("IDENTIDADE  sujeitos %d | sujeito em dois splits: %s"
          % (idt["n_sujeitos"], idt["sujeitos_em_dois_splits"] or "nenhum"))
    for k in ("case_id", "study_id", "series_id", "image_sha256", "mask_sha256"):
        print("   %-14s distintos %2d | repetidos %s"
              % (k, idt[k]["distintos"], idt[k]["repetidos"] or "-"))
    print()
    print("LICENCA  %s | bloqueantes: %s"
          % (proc["license_class"], proc["bloqueantes"] or "nenhuma"))
    print("PROCEDENCIA  institution %s | protocolo %s | data conhecida %s"
          % (proc["institution"], proc["annotation_protocol"], proc["annotation_date_known"]))
    print()
    print("DISTRIBUICAO (diagnostico, nao realimenta o split)")
    for s in ("train", "validation"):
        d = dist["por_split"][s]
        print("   %-11s n=%2d | volume mL %s | extensao mm %s"
              % (s, d["n"], d["volume_ml"], d["extensao_axial_mm"]))
        print("   %-11s fase respiratoria %s" % ("", d["fase_respiratoria"]))
    print()
    print("TEST  no manifesto: %d | treino=%s validacao=%s avaliacao=%s | treino le train: %s"
          % (tp["n_test_no_manifesto"],
             "BLOQUEADO" if tp["treino"]["bloqueado"] else "ABERTO",
             "BLOQUEADO" if tp["validacao"]["bloqueado"] else "ABERTO",
             "BLOQUEADO" if tp["avaliacao"]["bloqueado"] else "ABERTO",
             tp["treino_le_train"]))

    ok = (v["valido"] and r["dentro_da_banda"] and tp["n_test_no_manifesto"] == 0
          and not idt["sujeitos_em_dois_splits"] and not proc["bloqueantes"]
          and all(tp[c]["conforme_esperado"] for c in ("treino", "validacao", "avaliacao")))

    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "auditoria.json").write_text(json.dumps({
        "validacao": v, "identidade": idt, "procedencia": proc,
        "distribuicao": dist, "test_protegido": tp, "split": r,
    }, indent=1, ensure_ascii=False), encoding="utf-8")

    print()
    if not ok:
        print("PORTAO REPROVOU — o freeze NAO foi executado.")
        return 1
    if not a.escrever:
        print("PORTOES OK. Rode com --escrever para congelar.")
        return 0

    sha_manifesto = man.gravar(ent, MANIFESTO)
    snap = man.congelar(ent, SNAPSHOT, VERSAO, a.quando)
    conf = man.verificar_congelamento(ent, snap)
    print("CONGELADO  %s  em %s" % (VERSAO, a.quando))
    print("   manifesto : %s" % MANIFESTO.name)
    print("   sha256    : %s" % sha_manifesto)
    print("   snapshot  : %s" % SNAPSHOT.name)
    print("   integro   : %s" % conf["intacto"])
    return 0 if conf["intacto"] else 1


if __name__ == "__main__":
    sys.exit(main())
