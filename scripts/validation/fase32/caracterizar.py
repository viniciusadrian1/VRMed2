"""Fase 32 — o V2 esta pronto para treinar, e o TRAIN ficou mais diverso?

DUAS PERGUNTAS DIFERENTES, RESPONDIDAS SEPARADAMENTE

A primeira e de integridade: os 46 casos existem em disco, com o `sha256` que o
manifesto declara, geometria legivel e licenca que sustenta obra derivada. Isso e
verificacao — passa ou reprova.

A segunda e de composicao: o TRAIN saiu de 10 para 32, mas "mais casos" e "mais
diverso" nao sao a mesma coisa. Trinta e dois casos de um mesmo aparelho, mesmo
protocolo e mesma instituicao seriam 32 repeticoes. Esta parte MEDE a distribuicao e
mostra os dois lados; a leitura fica no relatorio, nao aqui.

O QUE ESTE MODULO NAO FAZ

Nao move caso, nao reescreve manifesto, nao decide split. Le o que a Fase 31 congelou
e o que as Fases 24 e 31 mediram na ingestao, e junta.

DE ONDE VEM CADA MEDIDA

Geometria e mascara: dos registros de ingestao (`ontologia.medidas`), que sao o que o
instrumento congelado mediu no arquivo real. Procedencia e licenca: do manifesto. As
duas fontes sao cruzadas por `case_id` e a divergencia entre elas e ERRO, nao ajuste —
se o manifesto diz um spacing e a medida diz outro, alguem esta lendo outro arquivo.

TRAIN E VALIDATION NUNCA SAO MISTURADOS. As tabelas de 32C descrevem SO os 32 de
train; as de 32D, so os 14 de validation.

  python -m scripts.validation.fase32.caracterizar --autoteste
  python -m scripts.validation.fase32.caracterizar --gravar docs/overnight/phase32/caracterizacao.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
MANIFESTO_V1 = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
MANIFESTO_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-MANIFESTO-V2.jsonl"
SNAPSHOT_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-SNAPSHOT-V2.json"

# Onde cada colecao registrou as medidas da ingestao. Nao ha terceira fonte: se um
# case_id do manifesto nao aparecer em nenhum destes, e erro declarado, nao lacuna
# preenchida por estimativa.
INGESTOES = (
    RAIZ / "docs" / "overnight" / "phase24" / "ingestao_real_16.json",
    RAIZ / "docs" / "overnight" / "phase31" / "ingestao_real.json",
)

ESPERADO = {"n": 46, "train": 32, "validation": 14, "test": 0}
SHA_V2 = "f4bd480e8f8046923a8990096d40832145fb405f1a84ca85e8f3be6e6d20f60b"


def medidas_de_ingestao() -> dict:
    """`case_id` -> medidas + algoritmo declarado, lidos dos registros de ingestao."""
    out = {}
    for p in INGESTOES:
        d = json.loads(p.read_text(encoding="utf-8"))
        for r in d["casos"]:
            cid = r.get("entrada", {}).get("case_id")
            if not cid:
                continue
            out[cid] = {
                "medidas": r["ontologia"]["medidas"],
                "roi_nome": r["roi_esofago"]["nome"],
                "algoritmo_declarado": r["roi_esofago"]["algoritmo_declarado"],
                "n_rois": r["roi_esofago"]["n_rois"],
                "elegivel": r["elegivel"],
                "origem_registro": p.name,
            }
    return out


def fase_respiratoria(roi_nome: str) -> str:
    """4D-Lung nomeia a ROI com o bin respiratorio (`Esophagus_c80` = 80 %).

    Nao ha inferencia aqui: ou o sufixo `_cNN` esta no nome da ROI do RTSTRUCT, ou a
    fase e UNKNOWN. Uma TC de planejamento 3D (LCTSC) nao tem bin, e isso e
    NAO_APLICAVEL — que nao e a mesma coisa que desconhecido.
    """
    import re
    m = re.search(r"_c(\d{2,3})$", roi_nome or "")
    return ("%s%%" % m.group(1)) if m else man.DESCONHECIDO


def juntar(entradas, med: dict) -> list:
    """Uma linha por caso, com procedencia do manifesto e geometria da ingestao."""
    linhas = []
    for e in sorted(entradas, key=lambda x: x["case_id"]):
        cid = e["case_id"]
        i = med.get(cid)
        sp = e["spacing"]
        lin = {
            "case_id": cid,
            "split": e["split"],
            "source_dataset": e["source_dataset"],
            "source_case_id": e["source_case_id"],
            "institution": e["institution"],
            "annotation_protocol": e["annotation_protocol"],
            "license_class": e["license_class"],
            "spacing_xy": round(float(sp[0]), 4),
            "spacing_z": round(float(sp[2]), 4),
            "shape": e["shape"],
            "orientation": e["orientation"],
            "tem_medida": i is not None,
        }
        if i is None:
            lin["erro"] = "sem registro de ingestao para este case_id"
            linhas.append(lin)
            continue
        m = i["medidas"]
        vox_mm3 = float(sp[0]) * float(sp[1]) * float(sp[2])
        lin.update({
            "algoritmo_declarado": i["algoritmo_declarado"],
            "fase_respiratoria": fase_respiratoria(i["roi_nome"]),
            "roi_nome": i["roi_nome"],
            "volume_ml": m["volume_ml"],
            "extensao_axial_mm": m["extensao_axial_mm"],
            "n_componentes_3d": m["n_componentes_3d"],
            "buracos_2d_pct": m["buracos_2d_pct"],
            "voxels_mascara": int(round(m["volume_ml"] * 1000.0 / vox_mm3)),
            "voxel_mm3": round(vox_mm3, 5),
            # a medida foi tirada do MESMO arquivo que o manifesto aponta?
            "spacing_bate": [round(float(x), 4) for x in m["spacing_mm"]]
                            == [round(float(x), 4) for x in sp],
            "shape_bate": list(m["shape"]) == list(e["shape"]),
            "orientacao_bate": m["orientacao"] == e["orientation"],
        })
        linhas.append(lin)
    return linhas


def _dist(vals) -> dict:
    vals = [v for v in vals if v is not None]
    if not vals:
        return {}
    return {
        "n": len(vals),
        "min": round(min(vals), 3),
        "mediana": round(statistics.median(vals), 3),
        "max": round(max(vals), 3),
        "media": round(statistics.fmean(vals), 3),
        "dp": round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0,
        "valores_distintos": len(set(round(float(v), 4) for v in vals)),
    }


def perfil(linhas: list) -> dict:
    """Os 12 atributos de 32C, calculados sobre EXATAMENTE as linhas recebidas."""
    return {
        "n": len(linhas),
        "source_dataset": dict(Counter(l["source_dataset"] for l in linhas)),
        "institution": dict(Counter(l["institution"] for l in linhas)),
        "annotation_protocol": dict(Counter(
            ("UNKNOWN" if l["annotation_protocol"] == man.DESCONHECIDO else "RTOG 1106")
            for l in linhas)),
        "algoritmo_declarado": dict(Counter(l.get("algoritmo_declarado", "?")
                                            for l in linhas)),
        "fase_respiratoria": dict(Counter(l.get("fase_respiratoria", "?") for l in linhas)),
        "license_class": dict(Counter(l["license_class"] for l in linhas)),
        "orientation": dict(Counter(l["orientation"] for l in linhas)),
        "spacing_z_valores": dict(Counter(l["spacing_z"] for l in linhas)),
        "spacing_xy_valores": dict(Counter(l["spacing_xy"] for l in linhas)),
        "spacing_z": _dist([l["spacing_z"] for l in linhas]),
        "spacing_xy": _dist([l["spacing_xy"] for l in linhas]),
        "volume_ml": _dist([l.get("volume_ml") for l in linhas]),
        "extensao_axial_mm": _dist([l.get("extensao_axial_mm") for l in linhas]),
        "voxels_mascara": _dist([l.get("voxels_mascara") for l in linhas]),
        "shape_z": _dist([l["shape"][2] for l in linhas]),
        "n_componentes_3d": dict(Counter(l.get("n_componentes_3d") for l in linhas)),
        "buracos_2d_pct": _dist([l.get("buracos_2d_pct") for l in linhas]),
        "shapes_distintos": len(set(tuple(l["shape"]) for l in linhas)),
    }


def integridade_em_disco(entradas, conferir_hash: bool) -> dict:
    """32B — os arquivos existem e o conteudo e o que o manifesto declara."""
    faltando, hash_errado, conferidos = [], [], 0
    for e in entradas:
        for campo, esperado in (("image_path", e["image_sha256"]),
                                ("mask_path", e["mask_sha256"])):
            p = RAIZ / e[campo]
            if not p.exists():
                faltando.append("%s: %s" % (e["case_id"], e[campo]))
                continue
            if conferir_hash:
                conferidos += 1
                if man.sha256_arquivo(p) != esperado:
                    hash_errado.append("%s: %s" % (e["case_id"], campo))
    return {
        "hashes_conferidos": conferir_hash,
        "n_arquivos_conferidos": conferidos,
        "faltando": faltando,
        "hash_divergente": hash_errado,
        "ok": not faltando and not hash_errado,
    }


def duplicatas(entradas) -> dict:
    """Duplicidade de identidade e sujeito nos dois lados do split.

    Quatro chaves, nao uma: `case_id` pega o registro repetido; `series_id` pega o
    mesmo exame entrando duas vezes com nomes diferentes; `image_sha256` pega o mesmo
    ARQUIVO; e `(source_dataset, source_case_id)` pega o mesmo SUJEITO em dois splits,
    que e o vazamento que importa e que nenhuma das outras tres veria.
    """
    def repetidos(chave):
        c = Counter(chave(e) for e in entradas)
        return sorted(k for k, n in c.items() if n > 1 and k)

    por_sujeito = {}
    for e in entradas:
        por_sujeito.setdefault((e["source_dataset"], e["source_case_id"]), set()).add(e["split"])
    sujeito_em_dois = sorted("%s/%s" % k for k, v in por_sujeito.items() if len(v) > 1)

    return {
        "case_id_repetido": repetidos(lambda e: e["case_id"]),
        "series_id_repetido": repetidos(lambda e: e["series_id"]),
        "study_id_repetido": repetidos(lambda e: e["study_id"]),
        "image_sha256_repetido": repetidos(lambda e: e["image_sha256"]),
        "mask_sha256_repetido": repetidos(lambda e: e["mask_sha256"]),
        "n_sujeitos": len(por_sujeito),
        "sujeito_em_dois_splits": sujeito_em_dois,
    }


def rodar(conferir_hash: bool = True) -> dict:
    v2 = man.carregar(MANIFESTO_V2)
    v1 = man.carregar(MANIFESTO_V1)
    snap = json.loads(SNAPSHOT_V2.read_text(encoding="utf-8"))
    conf = man.verificar_congelamento(v2, snap)

    med = medidas_de_ingestao()
    linhas = juntar(v2, med)
    linhas_v1 = juntar(v1, med)

    tr = [l for l in linhas if l["split"] == "train"]
    va = [l for l in linhas if l["split"] == "validation"]
    te = [l for l in linhas if l["split"] == "test"]
    tr_v1 = [l for l in linhas_v1 if l["split"] == "train"]

    contagem = {"n": len(v2), "train": len(tr), "validation": len(va), "test": len(te)}

    r = {
        "fase": 32,
        "manifesto_v2_sha256": conf["sha256_atual"],
        "congelamento_intacto": conf["intacto"],
        "contagem": contagem,
        "contagem_confere": contagem == ESPERADO,
        "sha256_confere": conf["sha256_atual"] == SHA_V2,
        "casos_sem_medida": [l["case_id"] for l in linhas if not l["tem_medida"]],
        "geometria_divergente": [
            l["case_id"] for l in linhas if l["tem_medida"]
            and not (l["spacing_bate"] and l["shape_bate"] and l["orientacao_bate"])],
        "licencas_bloqueantes": sorted(set(
            l["license_class"] for l in linhas
            if l["license_class"] in man.LICENCAS_BLOQUEANTES)),
        "duplicatas": duplicatas(v2),
        "disco": integridade_em_disco(v2, conferir_hash),
        # 32C e 32D — separados de proposito
        "perfil_train_v2": perfil(tr),
        "perfil_train_v1": perfil(tr_v1),
        "perfil_validation_v2": perfil(va),
        "linhas": linhas,
    }
    d = r["duplicatas"]
    r["portao"] = bool(
        r["contagem_confere"] and r["sha256_confere"] and r["congelamento_intacto"]
        and not r["casos_sem_medida"] and not r["geometria_divergente"]
        and not r["licencas_bloqueantes"] and r["disco"]["ok"]
        and not d["case_id_repetido"] and not d["series_id_repetido"]
        and not d["image_sha256_repetido"] and not d["mask_sha256_repetido"]
        and not d["sujeito_em_dois_splits"] and d["n_sujeitos"] == ESPERADO["n"])
    return r


def autoteste() -> int:
    falhas = []

    # 1. a leitura do bin respiratorio le o que esta no nome, e so isso
    if fase_respiratoria("Esophagus_c80") != "80%":
        falhas.append("nao leu o bin respiratorio de Esophagus_c80")
    if fase_respiratoria("Esophagus") != man.DESCONHECIDO:
        falhas.append("inventou fase respiratoria para uma ROI sem sufixo")
    if fase_respiratoria("Esophagus_c100") != "100%":
        falhas.append("nao leu bin de 3 digitos")

    # 2. os registros de ingestao cobrem os 46 case_id do manifesto
    v2 = man.carregar(MANIFESTO_V2)
    med = medidas_de_ingestao()
    sem = [e["case_id"] for e in v2 if e["case_id"] not in med]
    if sem:
        falhas.append("case_id sem registro de ingestao: %s" % sem[:5])

    # 3. o cruzamento roda sem inventar campo
    linhas = juntar(v2, med)
    if len(linhas) != 46:
        falhas.append("juntar() nao devolveu 46 linhas: %d" % len(linhas))

    # 4. perfil() descreve EXATAMENTE as linhas que recebe.
    #    Um perfil que somasse train+validation por engano e o erro que 32C proibe.
    tr = [l for l in linhas if l["split"] == "train"]
    p = perfil(tr)
    if p["n"] != 32 or sum(p["source_dataset"].values()) != 32:
        falhas.append("perfil de train contou algo que nao e train: %s" % p["n"])

    # 5. CONTROLE POSITIVO — duplicatas() tem de VER um sujeito em dois splits.
    #    Sem isto, um verificador que sempre devolve lista vazia passaria.
    import copy
    adulterado = copy.deepcopy(v2)
    alvo = next(e for e in adulterado if e["split"] == "train")
    gemeo = copy.deepcopy(alvo)
    gemeo["case_id"] = alvo["case_id"] + "-COPIA"
    gemeo["split"] = "validation"
    adulterado.append(gemeo)
    d = duplicatas(adulterado)
    if not d["sujeito_em_dois_splits"]:
        falhas.append("duplicatas() nao viu o mesmo sujeito nos dois splits")
    if not d["image_sha256_repetido"]:
        falhas.append("duplicatas() nao viu o mesmo arquivo duas vezes")

    # 6. e CONTROLE NEGATIVO: no manifesto real, nenhuma das cinco chaves repete
    d = duplicatas(v2)
    for k in ("case_id_repetido", "series_id_repetido", "study_id_repetido",
              "image_sha256_repetido", "mask_sha256_repetido", "sujeito_em_dois_splits"):
        if d[k]:
            falhas.append("o manifesto V2 tem %s: %s" % (k, d[k][:3]))

    # 7. o numero de sujeitos e igual ao de casos: uma serie por sujeito nas duas fontes
    if d["n_sujeitos"] != 46:
        falhas.append("46 casos mas %d sujeitos" % d["n_sujeitos"])

    # 8. _dist nao mente sobre dispersao de valor unico
    u = _dist([3.0, 3.0, 3.0])
    if u["dp"] != 0.0 or u["valores_distintos"] != 1:
        falhas.append("_dist errou em valores identicos: %s" % u)

    # 9. o V1 continua com 10 de train, e e sobre ELES que a comparacao e feita
    v1 = man.carregar(MANIFESTO_V1)
    if sum(1 for e in v1 if e["split"] == "train") != 10:
        falhas.append("o TRAIN da V1 nao tem 10 casos")

    # 10. os 10 de train da V1 sao subconjunto dos 32 de train da V2 — a propriedade
    #     de estabilidade da regra de split. Se cair, a comparacao 26B x V2 morre.
    ids_v1 = set(e["case_id"] for e in v1 if e["split"] == "train")
    ids_v2 = set(l["case_id"] for l in tr)
    if not ids_v1 <= ids_v2:
        falhas.append("TRAIN da V1 nao esta contido no TRAIN da V2: %s" % (ids_v1 - ids_v2))

    for f in falhas:
        print("FALHA:", f)
    print("autoteste caracterizar: %d verificacoes, %d falhas" % (10, len(falhas)))
    return 1 if falhas else 0


def _tab(rot, a, b):
    print("   %-24s %-28s %s" % (rot, a, b))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--gravar")
    ap.add_argument("--sem-hash", action="store_true",
                    help="pula a conferencia de sha256 dos 92 arquivos (rapido)")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    r = rodar(conferir_hash=not a.sem_hash)

    print("32B  INTEGRIDADE DO V2")
    print("   contagem      : %s  (esperado %s) -> %s"
          % (r["contagem"], ESPERADO, r["contagem_confere"]))
    print("   sha256        : %s -> %s" % (r["manifesto_v2_sha256"][:24], r["sha256_confere"]))
    print("   congelamento  : %s" % r["congelamento_intacto"])
    print("   arquivos      : %d conferidos por sha256, %d faltando, %d divergentes"
          % (r["disco"]["n_arquivos_conferidos"], len(r["disco"]["faltando"]),
             len(r["disco"]["hash_divergente"])))
    print("   geometria     : %d casos divergentes entre manifesto e medida"
          % len(r["geometria_divergente"]))
    print("   licencas      : bloqueantes = %s" % (r["licencas_bloqueantes"] or "nenhuma"))
    d = r["duplicatas"]
    print("   duplicatas    : case_id %d, series %d, study %d, imagem %d, mascara %d"
          % (len(d["case_id_repetido"]), len(d["series_id_repetido"]),
             len(d["study_id_repetido"]), len(d["image_sha256_repetido"]),
             len(d["mask_sha256_repetido"])))
    print("   sujeitos      : %d, em dois splits: %s"
          % (d["n_sujeitos"], d["sujeito_em_dois_splits"] or "nenhum"))

    a1, a2 = r["perfil_train_v1"], r["perfil_train_v2"]
    print("\n32C  TRAIN: V1 (10) x V2 (32) — SO train, validation nao entra")
    _tab("", "V1 TRAIN = 10", "V2 TRAIN = 32")
    _tab("source_dataset", a1["source_dataset"], a2["source_dataset"])
    _tab("institution", a1["institution"], a2["institution"])
    _tab("annotation_protocol", a1["annotation_protocol"], a2["annotation_protocol"])
    _tab("algoritmo declarado", a1["algoritmo_declarado"], a2["algoritmo_declarado"])
    _tab("fase respiratoria", a1["fase_respiratoria"], a2["fase_respiratoria"])
    _tab("spacing z (valores)", a1["spacing_z_valores"], a2["spacing_z_valores"])
    _tab("spacing xy distintos", a1["spacing_xy"]["valores_distintos"],
         a2["spacing_xy"]["valores_distintos"])
    for k in ("volume_ml", "extensao_axial_mm", "voxels_mascara", "shape_z"):
        _tab(k, "%s..%s med %s" % (a1[k]["min"], a1[k]["max"], a1[k]["mediana"]),
             "%s..%s med %s" % (a2[k]["min"], a2[k]["max"], a2[k]["mediana"]))
    _tab("componentes 3D", a1["n_componentes_3d"], a2["n_componentes_3d"])
    _tab("buracos 2D %", "max %s" % a1["buracos_2d_pct"]["max"],
         "max %s" % a2["buracos_2d_pct"]["max"])
    _tab("shapes distintos", a1["shapes_distintos"], a2["shapes_distintos"])

    v = r["perfil_validation_v2"]
    print("\n32D  VALIDATION V2 (14) — descrita separada, nenhum caso movido")
    print("   fontes        : %s" % v["source_dataset"])
    print("   spacing z     : %s" % v["spacing_z_valores"])
    print("   protocolo     : %s" % v["annotation_protocol"])
    print("   algoritmo     : %s" % v["algoritmo_declarado"])
    print("   volume mL     : %s..%s mediana %s"
          % (v["volume_ml"]["min"], v["volume_ml"]["max"], v["volume_ml"]["mediana"]))
    print("   componentes   : %s" % v["n_componentes_3d"])

    print("\nPORTAO DO DATASET V2: %s" % ("OK" if r["portao"] else "REPROVADO"))
    if a.gravar:
        p = Path(a.gravar)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
        print("escrito:", p)
    return 0 if r["portao"] else 1


if __name__ == "__main__":
    sys.exit(main())
