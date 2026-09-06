"""Fase 23 — o pool elegivel, a auditoria de duplicata e a de anonimizacao.

O QUE E UM POOL, E O QUE ELE NAO E
Pool NAO e split. Ele lista os casos que passaram em TODOS os criterios do 23.18 e
para ali. Nao congela TRAIN/VALIDATION/TEST, nao fixa proporcao, nao promove nada.
Com n pequeno, congelar seria escolher o resultado antes de ter o dado.

AUDITORIA DE DUPLICATA (23.14) — cinco chaves, e elas nao sao redundantes
  sha256 do conteudo  -> pega o mesmo arquivo sob outro nome
  PatientID           -> pega o mesmo sujeito
  StudyInstanceUID    -> pega o mesmo exame
  SeriesInstanceUID   -> pega a mesma serie
  (shape, spacing)    -> NAO e identidade: e TRIAGEM. Dois exames diferentes do
                         mesmo scanner tem a mesma grade. Um par que casa so aqui e
                         FALSO POSITIVO por construcao, e o modulo o rotula assim.

A quinta existe justamente para produzir falso positivo de proposito e mostrar que
as outras quatro nao dependem dela.

ANONIMIZACAO (23.17)
Reusa `fase21/anonimizacao.py`. O veredito por caso e REMOVIDO / PRESERVADO /
INDETERMINADO por tag — nunca "anonimizado".

  python -m scripts.validation.fase23.pool --autoteste
  python -m scripts.validation.fase23.pool
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.fase21 import anonimizacao as anon  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
DADOS = RAIZ / ".clinica-dados" / "fase23" / "4dlung"
SAIDA = RAIZ / "docs" / "overnight" / "phase23"

# Coortes que o VRmed JA usou. Um caso novo que colidir com qualquer uma delas e
# vazamento com cara de dado novo.
JA_USADAS = ("lctsc", "nsclc_radiomics", "lynos", "aeropath")


def _entradas() -> list:
    doc = json.loads((SAIDA / "ingestao_real.json").read_text(encoding="utf-8"))
    return [c for c in doc["casos"] if c.get("elegivel")]


def duplicatas(entradas) -> dict:
    """As cinco chaves. As quatro primeiras acusam; a quinta so tria."""
    def colisoes(chave, extrair):
        onde = defaultdict(list)
        for e in entradas:
            v = extrair(e)
            if v not in (None, "", man.DESCONHECIDO):
                onde[v].append(e["entrada"]["case_id"])
        return {k: v for k, v in onde.items() if len(v) > 1}

    ident = {
        "image_sha256": colisoes("image_sha256", lambda e: e["entrada"]["image_sha256"]),
        "mask_sha256": colisoes("mask_sha256", lambda e: e["entrada"]["mask_sha256"]),
        "case_id": colisoes("case_id", lambda e: e["entrada"]["case_id"]),
        "study_id": colisoes("study_id", lambda e: e["entrada"]["study_id"]),
        "series_id": colisoes("series_id", lambda e: e["entrada"]["series_id"]),
    }
    # a quinta chave: grade. Deliberadamente fraca.
    grade = colisoes("grade", lambda e: (tuple(e["entrada"]["shape"]),
                                         tuple(e["entrada"]["spacing"])))
    return {
        "por_identidade": {k: v for k, v in ident.items()},
        "colisoes_de_identidade": sum(len(v) for v in ident.values()),
        "por_grade": {str(k): v for k, v in grade.items()},
        "colisoes_de_grade": len(grade),
        "leitura_da_grade": (
            "colisao de (shape, spacing) e FALSO POSITIVO por construcao: dois exames "
            "distintos do mesmo protocolo compartilham a grade. Ela entra como triagem "
            "para mostrar que as quatro chaves de identidade nao dependem dela."
        ),
    }


def anonimizacao_por_caso(casos_dir: Path) -> list:
    out = []
    for d in sorted([p for p in casos_dir.glob("*") if p.is_dir()
                     and not p.name.startswith("_")]):
        ct = d / "ct"
        if not ct.exists():
            continue
        try:
            r = anon.auditar_dicom(ct, amostra=20)
        except Exception as e:  # noqa: BLE001
            out.append({"caso": d.name, "erro": str(e)[:120]})
            continue
        achados = {x["nome"]: {"estado": x["estado"], "exemplos": x["exemplos"]}
                   for x in r["eixo1_tags_identificadoras"] if x["estado"] != "OK"}
        out.append({
            "caso": d.name,
            "tags_com_achado": achados,
            "tags_privadas": r["eixo3_tags_privadas"]["n_tags_privadas_distintas"],
            "caminho": r["eixo4_caminho"]["estado"],
            "uids": {u["uid"]: u["estado"] for u in r["eixo2_uids"]},
            "veredito": r["veredito"],
        })
    return out


def montar_pool(entradas) -> list:
    pool = []
    for e in entradas:
        d = e["entrada"]
        pool.append({
            "case_id": d["case_id"],
            "study_id": d["study_id"],
            "series_id": d["series_id"],
            "image_sha256": d["image_sha256"],
            "mask_sha256": d["mask_sha256"],
            "source_dataset": d["source_dataset"],
            "source_case_id": d["source_case_id"],
            "license": d["license"],
            "license_class": d["license_class"],
            "annotation_source": d["annotation_source"],
            "annotation_method_declared": e["roi_esofago"]["algoritmo_declarado"],
            "institution": d["institution"],
            "mascara_origem": e["mascara_origem"],
            "vinculo_confirmado_por": e["vinculo"]["metodo"],
            "volume_ml": e["ontologia"]["medidas"]["volume_ml"],
            "extensao_axial_mm": e["ontologia"]["medidas"]["extensao_axial_mm"],
            "orientation": d["orientation"],
            "spacing": d["spacing"],
            "shape": d["shape"],
            "split": "NAO ATRIBUIDO",
        })
    return pool


def autoteste() -> int:
    falhas = []
    base = [
        {"entrada": {"case_id": "A", "study_id": "s1", "series_id": "e1",
                     "image_sha256": "a" * 64, "mask_sha256": "b" * 64,
                     "shape": [512, 512, 100], "spacing": [1.0, 1.0, 3.0]}},
        {"entrada": {"case_id": "B", "study_id": "s2", "series_id": "e2",
                     "image_sha256": "c" * 64, "mask_sha256": "d" * 64,
                     "shape": [512, 512, 100], "spacing": [1.0, 1.0, 3.0]}},
    ]
    d = duplicatas(base)
    if d["colisoes_de_identidade"] != 0:
        falhas.append("dois casos distintos acusados como duplicata")
    # a grade DEVE colidir aqui — e o falso positivo de proposito
    if d["colisoes_de_grade"] != 1:
        falhas.append("a triagem por grade deveria colidir (mesmo protocolo)")

    # duplicata real por conteudo, com ids diferentes: a chave que pega o disfarce
    dup = [base[0], {"entrada": dict(base[1]["entrada"], image_sha256="a" * 64)}]
    d2 = duplicatas(dup)
    if not d2["por_identidade"]["image_sha256"]:
        falhas.append("mesmo conteudo sob ids diferentes NAO foi detectado")

    # mesmo sujeito com series diferentes — o padrao do 4D-Lung
    mesmo = [base[0], {"entrada": dict(base[1]["entrada"], case_id="A")}]
    if not duplicatas(mesmo)["por_identidade"]["case_id"]:
        falhas.append("mesmo case_id em dois registros nao foi detectado")

    # UNKNOWN nao pode virar colisao
    unk = [{"entrada": dict(base[0]["entrada"], study_id=man.DESCONHECIDO)},
           {"entrada": dict(base[1]["entrada"], study_id=man.DESCONHECIDO)}]
    if duplicatas(unk)["por_identidade"]["study_id"]:
        falhas.append("dois UNKNOWN foram tratados como o mesmo estudo")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste pool: %d verificacoes, %d falhas" % (5, len(falhas)))
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

    ent = _entradas()
    pool = montar_pool(ent)
    dup = duplicatas(ent)
    anonim = anonimizacao_por_caso(DADOS)

    print("POOL ELEGIVEL: %d casos" % len(pool))
    print("  sujeitos distintos: %d" % len({p["source_case_id"] for p in pool}))
    print("  estudos distintos:  %d" % len({p["study_id"] for p in pool}))
    print("  series distintas:   %d" % len({p["series_id"] for p in pool}))
    print("  licencas: %s" % dict(Counter(p["license_class"] for p in pool)))
    print("  metodo de anotacao declarado: %s"
          % dict(Counter(p["annotation_method_declared"] for p in pool)))
    print("  origem da mascara: %s" % dict(Counter(p["mascara_origem"] for p in pool)))
    print()
    print("DUPLICATA (23.14)")
    print("  colisoes por IDENTIDADE (4 chaves): %d" % dup["colisoes_de_identidade"])
    print("  colisoes por GRADE (triagem):       %d%s"
          % (dup["colisoes_de_grade"],
             "  <- FALSO POSITIVO por construcao" if dup["colisoes_de_grade"]
             else "  (as 5 grades sao distintas; o mecanismo e provado no autoteste)"))
    for k, v in dup["por_grade"].items():
        print("     %s -> %s" % (k[:44], v))
    print()
    print("ANONIMIZACAO (23.17) — por caso")
    for r in anonim:
        if "erro" in r:
            print("  %-16s ERRO %s" % (r["caso"], r["erro"]))
            continue
        achados = ", ".join("%s=%s%s" % (k, v["estado"],
                                         (" " + str(v["exemplos"])) if v["exemplos"] else "")
                            for k, v in r["tags_com_achado"].items())
        print("  %-16s privadas=%d caminho=%s | %s"
              % (r["caso"], r["tags_privadas"], r["caminho"], achados[:96]))

    SAIDA.mkdir(parents=True, exist_ok=True)
    (RAIZ / "docs" / "FASE23-POOL-CANDIDATO.json").write_text(json.dumps({
        "gerado_em": "2026-09-06", "fase": 23,
        "estado": "POOL — nenhum split congelado, nenhuma proporcao fixada",
        "n": len(pool),
        "criterio": "23.18 — todos os campos obrigatorios, vinculo por UID, ontologia aprovada",
        "casos": pool,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    (SAIDA / "duplicatas.json").write_text(json.dumps(dup, indent=1, ensure_ascii=False),
                                           encoding="utf-8")
    (SAIDA / "anonimizacao_real.json").write_text(
        json.dumps(anonim, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\nescrito: docs/FASE23-POOL-CANDIDATO.json e overnight/phase23/*.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
